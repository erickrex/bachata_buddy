"""
MMPose Couple Pose Detector

Multi-person pose detector for couple dancing using MMPose (CPU-only).

Features:
- Detects both lead and follow dancers
- Tracks consistent person IDs across frames
- Extracts detailed hand keypoints
- Handles occlusions and overlapping dancers
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import cv2
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class PersonPose:
    """
    Pose data for a single person.
    
    Attributes:
        person_id: Unique identifier (1=lead, 2=follow)
        body_keypoints: Array of shape (17, 3) containing x, y, confidence for COCO keypoints
        left_hand_keypoints: Optional array of shape (21, 3) for left hand
        right_hand_keypoints: Optional array of shape (21, 3) for right hand
        bbox: Bounding box as (x, y, w, h)
        confidence: Overall confidence score for this person's pose
    """
    person_id: int
    body_keypoints: np.ndarray  # (17, 3) - x, y, confidence
    left_hand_keypoints: Optional[np.ndarray]  # (21, 3)
    right_hand_keypoints: Optional[np.ndarray]  # (21, 3)
    bbox: Tuple[float, float, float, float]  # x, y, w, h
    confidence: float
    
    def __post_init__(self):
        """Validate pose data dimensions."""
        if self.body_keypoints.shape != (17, 3):
            raise ValueError(
                f"body_keypoints must have shape (17, 3), got {self.body_keypoints.shape}"
            )
        
        if self.left_hand_keypoints is not None and self.left_hand_keypoints.shape != (21, 3):
            raise ValueError(
                f"left_hand_keypoints must have shape (21, 3), got {self.left_hand_keypoints.shape}"
            )
        
        if self.right_hand_keypoints is not None and self.right_hand_keypoints.shape != (21, 3):
            raise ValueError(
                f"right_hand_keypoints must have shape (21, 3), got {self.right_hand_keypoints.shape}"
            )


@dataclass
class CouplePose:
    """
    Pose data for both dancers in a frame.
    
    Attributes:
        lead: Pose data for lead dancer (person_id=1)
        follow: Pose data for follow dancer (person_id=2)
        frame_idx: Frame index in video
        timestamp: Timestamp in seconds
    """
    lead: Optional[PersonPose]
    follow: Optional[PersonPose]
    frame_idx: int
    timestamp: float
    
    @property
    def has_both_dancers(self) -> bool:
        """Check if both dancers are detected in this frame."""
        return self.lead is not None and self.follow is not None
    
    @property
    def detection_count(self) -> int:
        """Count how many dancers are detected."""
        count = 0
        if self.lead is not None:
            count += 1
        if self.follow is not None:
            count += 1
        return count


class PersonTracker:
    """
    IoU-based person tracker for maintaining consistent person IDs across frames.
    
    This tracker:
    1. Assigns person IDs (1=lead, 2=follow) based on bounding box overlap
    2. Uses Intersection over Union (IoU) to match detections across frames
    3. Handles temporary occlusions and re-appearances
    
    Attributes:
        iou_threshold: Minimum IoU for matching (default: 0.3)
        max_missing_frames: Maximum frames a person can be missing before ID is lost
    """
    
    def __init__(self, iou_threshold: float = 0.3, max_missing_frames: int = 10):
        """
        Initialize person tracker.
        
        Args:
            iou_threshold: Minimum IoU for matching detections (0.0-1.0)
            max_missing_frames: Maximum consecutive frames a person can be missing
        """
        self.iou_threshold = iou_threshold
        self.max_missing_frames = max_missing_frames
        
        # Track last known bounding boxes for each person ID
        self.tracked_persons = {}  # {person_id: {'bbox': (x, y, w, h), 'missing_count': int}}
        
        logger.debug(f"PersonTracker initialized (IoU threshold: {iou_threshold})")
    
    def update(self, detections: List[Tuple[float, float, float, float]]) -> List[int]:
        """
        Update tracker with new detections and assign person IDs.
        
        Args:
            detections: List of bounding boxes [(x, y, w, h), ...]
        
        Returns:
            List of person IDs corresponding to each detection [1, 2, ...]
            Returns empty list if no detections
        """
        if not detections:
            # Increment missing count for all tracked persons
            for person_id in list(self.tracked_persons.keys()):
                self.tracked_persons[person_id]['missing_count'] += 1
                
                # Remove person if missing too long
                if self.tracked_persons[person_id]['missing_count'] > self.max_missing_frames:
                    logger.debug(f"Lost track of person {person_id}")
                    del self.tracked_persons[person_id]
            
            return []
        
        # Match detections to existing tracked persons using IoU
        person_ids = []
        matched_detections = set()
        matched_persons = set()
        
        # First pass: match detections to existing persons
        for det_idx, det_bbox in enumerate(detections):
            best_iou = 0.0
            best_person_id = None
            
            for person_id, tracked_data in self.tracked_persons.items():
                if person_id in matched_persons:
                    continue
                
                iou = self._compute_iou(det_bbox, tracked_data['bbox'])
                
                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_person_id = person_id
            
            if best_person_id is not None:
                # Matched to existing person
                person_ids.append(best_person_id)
                matched_detections.add(det_idx)
                matched_persons.add(best_person_id)
                
                # Update tracked bbox and reset missing count
                self.tracked_persons[best_person_id]['bbox'] = det_bbox
                self.tracked_persons[best_person_id]['missing_count'] = 0
            else:
                # No match yet, will assign new ID in second pass
                person_ids.append(None)
        
        # Second pass: assign new IDs to unmatched detections
        for det_idx, person_id in enumerate(person_ids):
            if person_id is None:
                # Assign new person ID (prefer 1 and 2 for lead/follow)
                new_id = self._get_next_person_id()
                person_ids[det_idx] = new_id
                
                # Add to tracked persons
                self.tracked_persons[new_id] = {
                    'bbox': detections[det_idx],
                    'missing_count': 0
                }
                
                logger.debug(f"Assigned new person ID: {new_id}")
        
        # Increment missing count for unmatched tracked persons
        for person_id in self.tracked_persons.keys():
            if person_id not in matched_persons:
                self.tracked_persons[person_id]['missing_count'] += 1
                
                # Remove if missing too long
                if self.tracked_persons[person_id]['missing_count'] > self.max_missing_frames:
                    logger.debug(f"Lost track of person {person_id}")
                    del self.tracked_persons[person_id]
        
        return person_ids
    
    def _compute_iou(self, bbox1: Tuple[float, float, float, float], 
                     bbox2: Tuple[float, float, float, float]) -> float:
        """
        Compute Intersection over Union (IoU) between two bounding boxes.
        
        Args:
            bbox1: First bounding box (x, y, w, h)
            bbox2: Second bounding box (x, y, w, h)
        
        Returns:
            IoU score (0.0-1.0)
        """
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Convert to (x1, y1, x2, y2) format
        box1_x1, box1_y1 = x1, y1
        box1_x2, box1_y2 = x1 + w1, y1 + h1
        
        box2_x1, box2_y1 = x2, y2
        box2_x2, box2_y2 = x2 + w2, y2 + h2
        
        # Compute intersection
        inter_x1 = max(box1_x1, box2_x1)
        inter_y1 = max(box1_y1, box2_y1)
        inter_x2 = min(box1_x2, box2_x2)
        inter_y2 = min(box1_y2, box2_y2)
        
        inter_width = max(0, inter_x2 - inter_x1)
        inter_height = max(0, inter_y2 - inter_y1)
        inter_area = inter_width * inter_height
        
        # Compute union
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - inter_area
        
        # Compute IoU
        if union_area > 0:
            return inter_area / union_area
        return 0.0
    
    def _get_next_person_id(self) -> int:
        """
        Get next available person ID, preferring 1 and 2 for lead/follow.
        
        Returns:
            Next available person ID (1, 2, 3, ...)
        """
        # Prefer IDs 1 and 2 for couple dancing (lead and follow)
        if 1 not in self.tracked_persons:
            return 1
        if 2 not in self.tracked_persons:
            return 2
        
        # If both 1 and 2 are taken, use next available
        existing_ids = set(self.tracked_persons.keys())
        next_id = 3
        while next_id in existing_ids:
            next_id += 1
        return next_id
    
    def reset(self):
        """Reset tracker state (clear all tracked persons)."""
        self.tracked_persons.clear()
        logger.debug("PersonTracker reset")


class MMPoseCoupleDetector:
    """
    Multi-person pose detector for couple dancing using MMPose (CPU-only).
    
    This class integrates:
    1. Person detection (Faster R-CNN)
    2. Body pose estimation (HRNet-W48, 17 COCO keypoints)
    3. Hand detection (HRNet-W18, 21 keypoints per hand)
    4. IoU-based person tracking across frames
    
    All models run on CPU without GPU requirements.
    """
    
    def __init__(self, checkpoint_path: str, confidence_threshold: float = 0.3, 
                 enable_hand_detection: bool = True):
        """
        Initialize MMPose models (CPU-only).
        
        Args:
            checkpoint_path: Path to directory containing model checkpoints
            confidence_threshold: Minimum confidence for keypoint detection (0.0-1.0)
            enable_hand_detection: Whether to detect hand keypoints
        
        Raises:
            FileNotFoundError: If checkpoint files are not found
            ImportError: If MMPose/MMDetection packages are not installed
        """
        self.checkpoint_path = Path(checkpoint_path)
        self.confidence_threshold = confidence_threshold
        self.enable_hand_detection = enable_hand_detection
        
        logger.info(f"Initializing MMPose Couple Detector (CPU-only)")
        logger.info(f"Checkpoint path: {self.checkpoint_path}")
        logger.info(f"Confidence threshold: {self.confidence_threshold}")
        logger.info(f"Hand detection: {self.enable_hand_detection}")
        
        # Verify checkpoint directory exists
        if not self.checkpoint_path.exists():
            raise FileNotFoundError(
                f"Checkpoint directory not found: {self.checkpoint_path}\n"
                f"Please run: python scripts/download_mmpose_models.py"
            )
        
        # Import MMPose/MMDetection (lazy import to avoid errors if not installed)
        try:
            from mmpose.apis import init_model as init_pose_model
            from mmdet.apis import init_detector
            self._init_pose_model = init_pose_model
            self._init_detector = init_detector
        except ImportError as e:
            raise ImportError(
                f"MMPose/MMDetection not installed: {e}\n"
                f"Please run: pip install mmpose mmdet mmcv"
            ) from e
        
        # Initialize models
        self._init_person_detector()
        self._init_pose_estimator()
        if self.enable_hand_detection:
            self._init_hand_detector()
        else:
            self.hand_detector = None
        
        # Initialize person tracker
        self.person_tracker = PersonTracker(iou_threshold=0.3, max_missing_frames=10)
        
        logger.info("✓ MMPose Couple Detector initialized successfully")
    
    def _init_person_detector(self):
        """Initialize Faster R-CNN person detector (CPU mode)."""
        logger.info("Loading person detector (Faster R-CNN)...")
        
        config_file = self.checkpoint_path / "faster_rcnn_r50_fpn_1x_coco.py"
        checkpoint_file = self._find_checkpoint("faster_rcnn_r50_fpn_1x_coco*.pth")
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"Person detector config not found: {config_file}\n"
                f"Please run: python scripts/download_mmpose_models.py"
            )
        
        if not checkpoint_file:
            raise FileNotFoundError(
                f"Person detector checkpoint not found in {self.checkpoint_path}\n"
                f"Expected pattern: faster_rcnn_r50_fpn_1x_coco*.pth\n"
                f"Please run: python scripts/download_mmpose_models.py"
            )
        
        self.person_detector = self._init_detector(
            config=str(config_file),
            checkpoint=str(checkpoint_file),
            device='cpu'
        )
        
        logger.info(f"✓ Person detector loaded from {checkpoint_file.name}")
    
    def _init_pose_estimator(self):
        """Initialize HRNet-W48 pose estimator (CPU mode)."""
        logger.info("Loading pose estimator (HRNet-W48)...")
        
        config_file = self.checkpoint_path / "td-hm_hrnet-w48_8xb32-210e_coco-384x288.py"
        checkpoint_file = self._find_checkpoint("hrnet_w48_coco_384x288*.pth")
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"Pose estimator config not found: {config_file}\n"
                f"Please run: python scripts/download_mmpose_models.py"
            )
        
        if not checkpoint_file:
            raise FileNotFoundError(
                f"Pose estimator checkpoint not found in {self.checkpoint_path}\n"
                f"Expected pattern: hrnet_w48_coco_384x288*.pth\n"
                f"Please run: python scripts/download_mmpose_models.py"
            )
        
        self.pose_estimator = self._init_pose_model(
            config=str(config_file),
            checkpoint=str(checkpoint_file),
            device='cpu'
        )
        
        logger.info(f"✓ Pose estimator loaded from {checkpoint_file.name}")
    
    def _init_hand_detector(self):
        """Initialize HRNet-W18 hand detector (CPU mode)."""
        logger.info("Loading hand detector (HRNet-W18)...")
        
        config_file = self.checkpoint_path / "td-hm_hrnetv2-w18_8xb64-210e_onehand10k-256x256.py"
        checkpoint_file = self._find_checkpoint("hrnetv2_w18_onehand10k_256x256*.pth")
        
        if not config_file.exists():
            logger.warning(
                f"Hand detector config not found: {config_file}\n"
                f"Hand detection will be disabled."
            )
            self.hand_detector = None
            return
        
        if not checkpoint_file:
            logger.warning(
                f"Hand detector checkpoint not found in {self.checkpoint_path}\n"
                f"Hand detection will be disabled."
            )
            self.hand_detector = None
            return
        
        self.hand_detector = self._init_pose_model(
            config=str(config_file),
            checkpoint=str(checkpoint_file),
            device='cpu'
        )
        
        logger.info(f"✓ Hand detector loaded from {checkpoint_file.name}")
    
    def _find_checkpoint(self, pattern: str) -> Optional[Path]:
        """
        Find checkpoint file matching pattern.
        
        Args:
            pattern: Glob pattern to match (e.g., "hrnet_w48*.pth")
        
        Returns:
            Path to checkpoint file, or None if not found
        """
        import glob
        matches = list(self.checkpoint_path.glob(pattern))
        if matches:
            return matches[0]
        return None
    
    def detect_persons(self, frame: np.ndarray, 
                      person_score_threshold: float = 0.5) -> List[Tuple[float, float, float, float]]:
        """
        Detect persons in a frame using Faster R-CNN.
        
        Args:
            frame: Input frame (BGR format from OpenCV)
            person_score_threshold: Minimum confidence for person detection (0.0-1.0)
        
        Returns:
            List of bounding boxes [(x, y, w, h), ...] for detected persons
            Returns empty list if no persons detected
        """
        try:
            from mmdet.apis import inference_detector
        except ImportError as e:
            raise ImportError(
                f"MMDetection not installed: {e}\n"
                f"Please run: pip install mmdet"
            ) from e
        
        # Run person detection
        result = inference_detector(self.person_detector, frame)
        
        # Extract person detections (COCO class 0 = person)
        # Result format: list of arrays, one per class
        # Each array has shape (N, 5) where columns are [x1, y1, x2, y2, score]
        person_detections = result[0]  # Class 0 = person
        
        # Filter by confidence threshold
        bboxes = []
        for detection in person_detections:
            x1, y1, x2, y2, score = detection
            
            if score >= person_score_threshold:
                # Convert from (x1, y1, x2, y2) to (x, y, w, h)
                x = float(x1)
                y = float(y1)
                w = float(x2 - x1)
                h = float(y2 - y1)
                
                bboxes.append((x, y, w, h))
        
        logger.debug(f"Detected {len(bboxes)} persons (threshold: {person_score_threshold})")
        
        return bboxes
    
    def track_persons(self, bboxes: List[Tuple[float, float, float, float]]) -> List[int]:
        """
        Assign consistent person IDs to detected bounding boxes.
        
        Uses IoU-based tracking to maintain consistent IDs across frames.
        Person IDs: 1=lead, 2=follow
        
        Args:
            bboxes: List of bounding boxes [(x, y, w, h), ...]
        
        Returns:
            List of person IDs [1, 2, ...] corresponding to each bbox
        """
        return self.person_tracker.update(bboxes)
    
    def reset_tracker(self):
        """Reset person tracker state (useful when starting a new video)."""
        self.person_tracker.reset()
        logger.debug("Person tracker reset")
    
    def estimate_pose(self, frame: np.ndarray, bbox: Tuple[float, float, float, float]) -> Optional[np.ndarray]:
        """
        Estimate body pose (17 COCO keypoints) for a person in a bounding box.
        
        Args:
            frame: Input frame (BGR format from OpenCV)
            bbox: Bounding box (x, y, w, h) for the person
        
        Returns:
            Array of shape (17, 3) containing [x, y, confidence] for each keypoint
            Returns None if pose estimation fails
        
        COCO 17 keypoints order:
        0: nose, 1: left_eye, 2: right_eye, 3: left_ear, 4: right_ear,
        5: left_shoulder, 6: right_shoulder, 7: left_elbow, 8: right_elbow,
        9: left_wrist, 10: right_wrist, 11: left_hip, 12: right_hip,
        13: left_knee, 14: right_knee, 15: left_ankle, 16: right_ankle
        """
        try:
            from mmpose.apis import inference_topdown
            from mmpose.structures import PoseDataSample
        except ImportError as e:
            raise ImportError(
                f"MMPose not installed: {e}\n"
                f"Please run: pip install mmpose"
            ) from e
        
        # Convert bbox to format expected by MMPose: [x1, y1, x2, y2]
        x, y, w, h = bbox
        bbox_xyxy = np.array([[x, y, x + w, y + h]])
        
        # Run pose estimation
        results = inference_topdown(self.pose_estimator, frame, bboxes=bbox_xyxy)
        
        if not results or len(results) == 0:
            logger.debug(f"Pose estimation failed for bbox {bbox}")
            return None
        
        # Extract keypoints from result
        result = results[0]
        
        # Get keypoints and scores
        if hasattr(result, 'pred_instances'):
            keypoints = result.pred_instances.keypoints[0]  # (17, 2)
            scores = result.pred_instances.keypoint_scores[0]  # (17,)
            
            # Combine into (17, 3) array [x, y, confidence]
            pose_keypoints = np.zeros((17, 3), dtype=np.float32)
            pose_keypoints[:, :2] = keypoints
            pose_keypoints[:, 2] = scores
            
            # Filter by confidence threshold
            low_confidence_mask = scores < self.confidence_threshold
            pose_keypoints[low_confidence_mask, :] = 0.0  # Mark low-confidence keypoints as invalid
            
            avg_confidence = float(np.mean(scores))
            logger.debug(f"Pose estimated with avg confidence: {avg_confidence:.3f}")
            
            return pose_keypoints
        else:
            logger.debug("No pred_instances in pose estimation result")
            return None
    
    def detect_hands(self, frame: np.ndarray, wrist_keypoints: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Detect hand keypoints (21 per hand) based on wrist positions.
        
        Args:
            frame: Input frame (BGR format from OpenCV)
            wrist_keypoints: Array of shape (17, 3) containing body keypoints
                            Wrist indices: 9=left_wrist, 10=right_wrist
        
        Returns:
            Tuple of (left_hand_keypoints, right_hand_keypoints)
            Each is an array of shape (21, 3) or None if detection fails
        
        Hand keypoints order (21 points):
        0: wrist, 1-4: thumb, 5-8: index, 9-12: middle, 13-16: ring, 17-20: pinky
        """
        if self.hand_detector is None:
            logger.debug("Hand detection disabled")
            return None, None
        
        try:
            from mmpose.apis import inference_topdown
        except ImportError as e:
            raise ImportError(
                f"MMPose not installed: {e}\n"
                f"Please run: pip install mmpose"
            ) from e
        
        # Extract wrist positions
        left_wrist = wrist_keypoints[9]  # (x, y, confidence)
        right_wrist = wrist_keypoints[10]
        
        left_hand_kpts = None
        right_hand_kpts = None
        
        # Detect left hand if wrist is visible
        if left_wrist[2] >= self.confidence_threshold:
            left_hand_kpts = self._detect_single_hand(frame, left_wrist[:2])
        
        # Detect right hand if wrist is visible
        if right_wrist[2] >= self.confidence_threshold:
            right_hand_kpts = self._detect_single_hand(frame, right_wrist[:2])
        
        return left_hand_kpts, right_hand_kpts
    
    def _detect_single_hand(self, frame: np.ndarray, wrist_pos: np.ndarray, 
                           hand_bbox_size: int = 128) -> Optional[np.ndarray]:
        """
        Detect keypoints for a single hand.
        
        Args:
            frame: Input frame (BGR format)
            wrist_pos: Wrist position [x, y]
            hand_bbox_size: Size of bounding box around wrist (default: 128 pixels)
        
        Returns:
            Array of shape (21, 3) containing [x, y, confidence] for each hand keypoint
            Returns None if detection fails
        """
        try:
            from mmpose.apis import inference_topdown
        except ImportError as e:
            raise ImportError(
                f"MMPose not installed: {e}\n"
                f"Please run: pip install mmpose"
            ) from e
        
        # Create bounding box around wrist
        x, y = wrist_pos
        half_size = hand_bbox_size // 2
        
        x1 = max(0, x - half_size)
        y1 = max(0, y - half_size)
        x2 = min(frame.shape[1], x + half_size)
        y2 = min(frame.shape[0], y + half_size)
        
        # Check if bbox is valid
        if x2 <= x1 or y2 <= y1:
            logger.debug(f"Invalid hand bbox: ({x1}, {y1}, {x2}, {y2})")
            return None
        
        bbox_xyxy = np.array([[x1, y1, x2, y2]])
        
        # Run hand detection
        try:
            results = inference_topdown(self.hand_detector, frame, bboxes=bbox_xyxy)
            
            if not results or len(results) == 0:
                logger.debug(f"Hand detection failed for wrist at ({x:.1f}, {y:.1f})")
                return None
            
            # Extract keypoints
            result = results[0]
            
            if hasattr(result, 'pred_instances'):
                keypoints = result.pred_instances.keypoints[0]  # (21, 2)
                scores = result.pred_instances.keypoint_scores[0]  # (21,)
                
                # Combine into (21, 3) array [x, y, confidence]
                hand_keypoints = np.zeros((21, 3), dtype=np.float32)
                hand_keypoints[:, :2] = keypoints
                hand_keypoints[:, 2] = scores
                
                # Filter by confidence threshold
                low_confidence_mask = scores < self.confidence_threshold
                hand_keypoints[low_confidence_mask, :] = 0.0
                
                avg_confidence = float(np.mean(scores))
                logger.debug(f"Hand detected with avg confidence: {avg_confidence:.3f}")
                
                return hand_keypoints
            else:
                logger.debug("No pred_instances in hand detection result")
                return None
                
        except Exception as e:
            logger.debug(f"Hand detection error: {e}")
            return None
    
    def create_person_pose(self, person_id: int, bbox: Tuple[float, float, float, float],
                          frame: np.ndarray) -> Optional[PersonPose]:
        """
        Create PersonPose object by detecting body pose and hands.
        
        Args:
            person_id: Person identifier (1=lead, 2=follow)
            bbox: Bounding box (x, y, w, h)
            frame: Input frame (BGR format)
        
        Returns:
            PersonPose object or None if pose estimation fails
        """
        # Estimate body pose
        body_keypoints = self.estimate_pose(frame, bbox)
        
        if body_keypoints is None:
            logger.debug(f"Failed to estimate pose for person {person_id}")
            return None
        
        # Calculate average confidence
        valid_keypoints = body_keypoints[body_keypoints[:, 2] >= self.confidence_threshold]
        if len(valid_keypoints) == 0:
            logger.debug(f"No valid keypoints for person {person_id}")
            return None
        
        avg_confidence = float(np.mean(valid_keypoints[:, 2]))
        
        # Detect hands (optional)
        left_hand_kpts = None
        right_hand_kpts = None
        
        if self.enable_hand_detection:
            left_hand_kpts, right_hand_kpts = self.detect_hands(frame, body_keypoints)
        
        # Create PersonPose object
        person_pose = PersonPose(
            person_id=person_id,
            body_keypoints=body_keypoints,
            left_hand_keypoints=left_hand_kpts,
            right_hand_keypoints=right_hand_kpts,
            bbox=bbox,
            confidence=avg_confidence
        )
        
        return person_pose
    
    def detect_couple_poses(self, video_path: str, target_fps: int = 15) -> List[CouplePose]:
        """
        Detect poses for both dancers across all frames.
        
        This method:
        1. Samples frames at target FPS
        2. Detects persons in each frame
        3. Estimates body poses (17 COCO keypoints)
        4. Detects hand keypoints (optional, 21 per hand)
        5. Tracks person IDs across frames using IoU
        
        Args:
            video_path: Path to video file
            target_fps: Target frame rate for sampling (default: 15)
        
        Returns:
            List of CouplePose objects, one per sampled frame
        
        Raises:
            FileNotFoundError: If video file doesn't exist
            ValueError: If video cannot be opened
        """
        video_path = Path(video_path)
        
        # Verify video file exists
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        logger.info(f"Processing video: {video_path.name}")
        logger.info(f"Target FPS: {target_fps}")
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        # Get video properties
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / original_fps if original_fps > 0 else 0
        
        logger.info(f"Video properties: {original_fps:.2f} FPS, {total_frames} frames, {duration:.2f}s")
        
        # Calculate frame sampling interval
        if target_fps >= original_fps:
            # Process all frames if target FPS is higher than video FPS
            frame_interval = 1
            effective_fps = original_fps
        else:
            # Sample frames at target FPS
            frame_interval = int(original_fps / target_fps)
            effective_fps = original_fps / frame_interval
        
        logger.info(f"Sampling every {frame_interval} frame(s), effective FPS: {effective_fps:.2f}")
        
        # Reset tracker for new video
        self.reset_tracker()
        
        # Process frames
        couple_poses = []
        frame_idx = 0
        sampled_frame_idx = 0
        
        # Track statistics
        frames_with_both_dancers = 0
        frames_with_one_dancer = 0
        frames_with_no_dancers = 0
        
        try:
            from tqdm import tqdm
            use_progress_bar = True
        except ImportError:
            use_progress_bar = False
            logger.warning("tqdm not installed, progress bar disabled")
        
        # Create progress bar if available
        if use_progress_bar:
            pbar = tqdm(total=total_frames // frame_interval, 
                       desc=f"Processing {video_path.name}",
                       unit="frame")
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Sample frames at target FPS
            if frame_idx % frame_interval == 0:
                timestamp = frame_idx / original_fps
                
                # Detect persons in frame
                bboxes = self.detect_persons(frame, person_score_threshold=0.5)
                
                # Track person IDs
                person_ids = self.track_persons(bboxes)
                
                # Create PersonPose objects for each detected person
                lead_pose = None
                follow_pose = None
                
                for bbox, person_id in zip(bboxes, person_ids):
                    person_pose = self.create_person_pose(person_id, bbox, frame)
                    
                    if person_pose is not None:
                        if person_id == 1:
                            lead_pose = person_pose
                        elif person_id == 2:
                            follow_pose = person_pose
                
                # Create CouplePose object
                couple_pose = CouplePose(
                    lead=lead_pose,
                    follow=follow_pose,
                    frame_idx=sampled_frame_idx,
                    timestamp=timestamp
                )
                
                couple_poses.append(couple_pose)
                
                # Update statistics
                if couple_pose.has_both_dancers:
                    frames_with_both_dancers += 1
                elif couple_pose.detection_count == 1:
                    frames_with_one_dancer += 1
                else:
                    frames_with_no_dancers += 1
                
                sampled_frame_idx += 1
                
                if use_progress_bar:
                    pbar.update(1)
            
            frame_idx += 1
        
        # Clean up
        cap.release()
        
        if use_progress_bar:
            pbar.close()
        
        # Calculate and report statistics
        total_sampled_frames = len(couple_poses)
        
        if total_sampled_frames > 0:
            couple_detection_rate = frames_with_both_dancers / total_sampled_frames
            
            logger.info(f"Processing complete:")
            logger.info(f"  Total sampled frames: {total_sampled_frames}")
            logger.info(f"  Frames with both dancers: {frames_with_both_dancers} ({couple_detection_rate*100:.1f}%)")
            logger.info(f"  Frames with one dancer: {frames_with_one_dancer}")
            logger.info(f"  Frames with no dancers: {frames_with_no_dancers}")
            
            # Flag videos with low couple detection rate
            if couple_detection_rate < 0.5:
                logger.warning(
                    f"⚠️  Low couple detection rate ({couple_detection_rate*100:.1f}%) - "
                    f"video flagged for quality review"
                )
        else:
            logger.warning("No frames were sampled from video")
        
        return couple_poses
