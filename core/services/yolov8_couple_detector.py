"""
YOLOv8-based couple pose detector for Bachata dancing.

This module provides multi-person pose detection using Ultralytics YOLOv8-Pose.
Detects and tracks both dancers (lead + follow) across video frames.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

logger = logging.getLogger(__name__)


@dataclass
class PersonPose:
    """Single person pose detection result."""
    person_id: int
    keypoints: np.ndarray  # Shape: (17, 3) - [x, y, confidence] for COCO format
    bbox: np.ndarray       # Shape: (4,) - [x1, y1, x2, y2]
    confidence: float
    frame_idx: int


@dataclass
class CouplePose:
    """Couple pose detection result (lead + follow)."""
    lead_pose: Optional[PersonPose]
    follow_pose: Optional[PersonPose]
    frame_idx: int
    timestamp: float
    has_both_dancers: bool


class PersonTracker:
    """
    IoU-based person tracker for maintaining consistent IDs across frames.
    
    Tracks people across video frames using bounding box overlap (IoU).
    Assigns consistent IDs to lead and follow dancers throughout the video.
    """
    
    def __init__(self, iou_threshold: float = 0.5):
        """
        Initialize person tracker.
        
        Args:
            iou_threshold: Minimum IoU for matching detections to tracks
        """
        self.iou_threshold = iou_threshold
        self.tracks: Dict[int, np.ndarray] = {}  # track_id -> last_bbox
        self.next_id = 0
        self.max_age = 30  # Max frames to keep track without detection
        self.track_ages: Dict[int, int] = {}  # track_id -> frames_since_last_seen
    
    def update(
        self,
        detections: List[PersonPose],
        frame_idx: int
    ) -> List[PersonPose]:
        """
        Update tracks with new detections and assign consistent IDs.
        
        Args:
            detections: New detections from current frame
            frame_idx: Current frame index
            
        Returns:
            Detections with updated person IDs
        """
        if len(detections) == 0:
            # Age all tracks
            for track_id in list(self.track_ages.keys()):
                self.track_ages[track_id] += 1
                if self.track_ages[track_id] > self.max_age:
                    del self.tracks[track_id]
                    del self.track_ages[track_id]
            return []
        
        # Match detections to existing tracks
        if len(self.tracks) > 0:
            matches = self._match_detections_to_tracks(detections)
        else:
            matches = {}
        
        # Update matched tracks and create new tracks
        updated_detections = []
        matched_track_ids = set()
        
        for det_idx, detection in enumerate(detections):
            if det_idx in matches:
                # Matched to existing track
                track_id = matches[det_idx]
                detection.person_id = track_id
                self.tracks[track_id] = detection.bbox
                self.track_ages[track_id] = 0
                matched_track_ids.add(track_id)
            else:
                # New track
                track_id = self.next_id
                self.next_id += 1
                detection.person_id = track_id
                self.tracks[track_id] = detection.bbox
                self.track_ages[track_id] = 0
            
            updated_detections.append(detection)
        
        # Age unmatched tracks
        for track_id in list(self.track_ages.keys()):
            if track_id not in matched_track_ids:
                self.track_ages[track_id] += 1
                if self.track_ages[track_id] > self.max_age:
                    del self.tracks[track_id]
                    del self.track_ages[track_id]
        
        return updated_detections
    
    def _compute_iou(self, bbox1: np.ndarray, bbox2: np.ndarray) -> float:
        """
        Compute Intersection over Union (IoU) between two bounding boxes.
        
        Args:
            bbox1: First bbox [x1, y1, x2, y2]
            bbox2: Second bbox [x1, y1, x2, y2]
            
        Returns:
            IoU score (0.0 to 1.0)
        """
        # Compute intersection
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        
        # Compute union
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _match_detections_to_tracks(
        self,
        detections: List[PersonPose]
    ) -> Dict[int, int]:
        """
        Match detections to existing tracks using Hungarian algorithm.
        
        Args:
            detections: New detections from current frame
            
        Returns:
            Dictionary mapping detection_idx -> track_id
        """
        if len(self.tracks) == 0 or len(detections) == 0:
            return {}
        
        # Compute IoU matrix
        track_ids = list(self.tracks.keys())
        iou_matrix = np.zeros((len(detections), len(track_ids)))
        
        for det_idx, detection in enumerate(detections):
            for track_idx, track_id in enumerate(track_ids):
                iou = self._compute_iou(detection.bbox, self.tracks[track_id])
                iou_matrix[det_idx, track_idx] = iou
        
        # Use Hungarian algorithm for optimal matching
        det_indices, track_indices = linear_sum_assignment(-iou_matrix)
        
        # Filter matches by IoU threshold
        matches = {}
        for det_idx, track_idx in zip(det_indices, track_indices):
            if iou_matrix[det_idx, track_idx] >= self.iou_threshold:
                matches[det_idx] = track_ids[track_idx]
        
        return matches


class YOLOv8CoupleDetector:
    """
    Multi-person pose detector using YOLOv8-Pose.
    
    Detects and tracks both dancers (lead + follow) across video frames.
    Uses IoU-based tracking to maintain consistent person IDs.
    
    Example:
        detector = YOLOv8CoupleDetector()
        couple_poses = detector.detect_couple_poses('dance_video.mp4')
        
        for pose in couple_poses:
            if pose.has_both_dancers:
                print(f"Frame {pose.frame_idx}: Both dancers detected")
    """
    
    def __init__(
        self,
        model_name: str = 'yolov8n-pose.pt',
        confidence_threshold: float = 0.3,
        device: str = 'cpu',
        iou_threshold: float = 0.5,
        max_det: int = 10
    ):
        """
        Initialize YOLOv8 pose detector.
        
        Args:
            model_name: YOLOv8 model variant (yolov8n/s/m/l/x-pose.pt)
            confidence_threshold: Minimum confidence for detections (0.0-1.0)
            device: 'cpu' or 'cuda'
            iou_threshold: IoU threshold for tracking (0.0-1.0)
            max_det: Maximum detections per frame
        """
        try:
            from ultralytics import YOLO
            
            logger.info(f"Loading YOLOv8 model: {model_name}")
            self.model = YOLO(model_name)
            logger.info(f"✓ Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            raise RuntimeError(
                f"Failed to load YOLOv8 model '{model_name}'. "
                f"Error: {e}. "
                f"Please check internet connection and model name."
            )
        
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.iou_threshold = iou_threshold
        self.max_det = max_det
        self.tracker = PersonTracker(iou_threshold=iou_threshold)
        
        logger.info(f"YOLOv8CoupleDetector initialized:")
        logger.info(f"  Model: {model_name}")
        logger.info(f"  Confidence threshold: {confidence_threshold}")
        logger.info(f"  Device: {device}")
        logger.info(f"  IoU threshold: {iou_threshold}")
    
    def reset_tracker(self):
        """
        Reset the person tracker.
        
        Call this between videos to ensure person IDs start fresh.
        """
        self.tracker = PersonTracker(iou_threshold=self.iou_threshold)
    
    def detect_couple_poses(
        self,
        video_path: str,
        target_fps: int = 15
    ) -> List[CouplePose]:
        """
        Detect couple poses across all video frames.
        
        Args:
            video_path: Path to video file
            target_fps: Target FPS for processing (downsamples if needed)
            
        Returns:
            List of CouplePose objects, one per processed frame
            
        Raises:
            FileNotFoundError: If video file doesn't exist
            ValueError: If video cannot be opened or no frames processed
        """
        # Validate video file
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        logger.info(f"Processing video: {video_path.name}")
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Get video properties
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_skip = max(1, int(original_fps / target_fps))
        
        logger.info(f"Video properties:")
        logger.info(f"  Original FPS: {original_fps:.2f}")
        logger.info(f"  Total frames: {total_frames}")
        logger.info(f"  Target FPS: {target_fps}")
        logger.info(f"  Frame skip: {frame_skip}")
        
        # Process frames
        couple_poses = []
        frame_count = 0
        processed_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Skip frames to match target FPS
                if frame_count % frame_skip != 0:
                    frame_count += 1
                    continue
                
                try:
                    # Detect people in frame
                    detections = self._detect_frame(frame)
                    
                    # Update tracking
                    detections = self.tracker.update(detections, processed_count)
                    
                    # Assign lead/follow
                    lead, follow = self._assign_lead_follow(detections)
                    
                    # Create CouplePose
                    timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                    couple_pose = CouplePose(
                        lead_pose=lead,
                        follow_pose=follow,
                        frame_idx=processed_count,
                        timestamp=timestamp,
                        has_both_dancers=(lead is not None and follow is not None)
                    )
                    couple_poses.append(couple_pose)
                    processed_count += 1
                    
                    # Log progress
                    if processed_count % 50 == 0:
                        detection_rate = sum(1 for cp in couple_poses if cp.has_both_dancers) / len(couple_poses)
                        logger.info(f"Processed {processed_count} frames, detection rate: {detection_rate:.1%}")
                    
                except Exception as e:
                    logger.warning(f"Frame {frame_count} failed: {e}")
                    # Add empty frame to maintain timing
                    couple_poses.append(CouplePose(
                        lead_pose=None,
                        follow_pose=None,
                        frame_idx=processed_count,
                        timestamp=cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0,
                        has_both_dancers=False
                    ))
                    processed_count += 1
                
                frame_count += 1
        
        finally:
            cap.release()
        
        # Validate results
        if len(couple_poses) == 0:
            raise ValueError(f"No frames processed from video: {video_path}")
        
        # Calculate and log quality metrics
        detection_rate = sum(1 for cp in couple_poses if cp.has_both_dancers) / len(couple_poses)
        avg_confidence = np.mean([
            cp.lead_pose.confidence if cp.lead_pose else 0.0
            for cp in couple_poses
        ])
        
        logger.info(f"✓ Processing complete:")
        logger.info(f"  Processed frames: {len(couple_poses)}")
        logger.info(f"  Couple detection rate: {detection_rate:.1%}")
        logger.info(f"  Average confidence: {avg_confidence:.2f}")
        
        if detection_rate < 0.3:
            logger.warning(
                f"Low couple detection rate: {detection_rate:.1%} "
                f"for video: {video_path.name}"
            )
        
        return couple_poses
    
    def _detect_frame(self, frame: np.ndarray) -> List[PersonPose]:
        """
        Detect all people in a single frame.
        
        Args:
            frame: Video frame (BGR format)
            
        Returns:
            List of PersonPose objects for detected people
        """
        # Run YOLOv8 inference
        results = self.model(
            frame,
            conf=self.confidence_threshold,
            device=self.device,
            max_det=self.max_det,
            verbose=False
        )
        
        detections = []
        
        # Extract detections from results
        if len(results) > 0 and results[0].keypoints is not None:
            result = results[0]
            
            # Get keypoints, boxes, and confidences
            keypoints = result.keypoints.data.cpu().numpy()  # Shape: (N, 17, 3)
            boxes = result.boxes.xyxy.cpu().numpy()  # Shape: (N, 4)
            confidences = result.boxes.conf.cpu().numpy()  # Shape: (N,)
            
            for i in range(len(boxes)):
                detection = PersonPose(
                    person_id=-1,  # Will be assigned by tracker
                    keypoints=keypoints[i],  # Shape: (17, 3)
                    bbox=boxes[i],  # Shape: (4,)
                    confidence=float(confidences[i]),
                    frame_idx=-1  # Will be set later
                )
                detections.append(detection)
        
        return detections
    
    def _assign_lead_follow(
        self,
        detections: List[PersonPose]
    ) -> Tuple[Optional[PersonPose], Optional[PersonPose]]:
        """
        Assign detected people to lead/follow roles.
        
        Uses spatial heuristics: left person = lead, right person = follow.
        Maintains consistency using tracking IDs.
        
        Args:
            detections: List of detected people in frame
            
        Returns:
            Tuple of (lead_pose, follow_pose). Either can be None.
        """
        if len(detections) == 0:
            return None, None
        
        if len(detections) == 1:
            # Only one person detected - assign to lead by default
            return detections[0], None
        
        # Sort by x-coordinate (left to right)
        sorted_detections = sorted(detections, key=lambda d: d.bbox[0])
        
        # Assign leftmost to lead, rightmost to follow
        lead = sorted_detections[0]
        follow = sorted_detections[-1]
        
        return lead, follow
