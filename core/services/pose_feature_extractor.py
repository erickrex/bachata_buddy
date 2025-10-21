"""
Pose Feature Extraction

Extracts pose features from body keypoints for embedding generation.

Features extracted:
- Joint angles (elbows, knees, torso)
- Center of mass for each dancer
- Bounding boxes for spatial tracking
- Temporal sequences for movement analysis
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import logging

from .yolov8_couple_detector import PersonPose, CouplePose

logger = logging.getLogger(__name__)


@dataclass
class PoseFeatures:
    """
    Extracted pose features for a single person in a frame.
    
    Attributes:
        joint_angles: Dictionary of joint angles in radians
        center_of_mass: (x, y) coordinates of center of mass
        bbox: Bounding box (x, y, w, h)
        velocity: (vx, vy) velocity vector (None for first frame)
        keypoint_positions: (17, 2) array of keypoint positions
        keypoint_confidences: (17,) array of keypoint confidences
    """
    joint_angles: dict  # {joint_name: angle_in_radians}
    center_of_mass: Tuple[float, float]
    bbox: Tuple[float, float, float, float]
    velocity: Optional[Tuple[float, float]]
    keypoint_positions: np.ndarray  # (17, 2)
    keypoint_confidences: np.ndarray  # (17,)


@dataclass
class TemporalPoseSequence:
    """
    Temporal sequence of pose features for embedding generation.
    
    Attributes:
        features: List of PoseFeatures for each frame
        person_id: Person identifier (1=lead, 2=follow)
        frame_count: Number of frames in sequence
    """
    features: List[PoseFeatures]
    person_id: int
    frame_count: int
    
    def get_feature_vector(self) -> np.ndarray:
        """
        Aggregate temporal features into a single feature vector.
        
        Returns:
            Feature vector combining all temporal information
        """
        if not self.features:
            return np.array([])
        
        # Aggregate features across time
        feature_components = []
        
        # 1. Mean and std of joint angles
        # Define expected angle keys to ensure consistent shape
        angle_keys = ['left_elbow', 'right_elbow', 'left_knee', 'right_knee', 'torso']
        all_angles = []
        for feat in self.features:
            # Create fixed-size angle vector with NaN for missing angles
            angle_vector = [feat.joint_angles.get(key, np.nan) for key in angle_keys]
            all_angles.append(angle_vector)
        
        if all_angles:
            all_angles = np.array(all_angles)  # (frames, num_angles)
            # Use nanmean/nanstd to handle missing values
            mean_angles = np.nanmean(all_angles, axis=0)
            std_angles = np.nanstd(all_angles, axis=0)
            # Replace any remaining NaN with 0
            mean_angles = np.nan_to_num(mean_angles, nan=0.0)
            std_angles = np.nan_to_num(std_angles, nan=0.0)
            feature_components.extend([mean_angles, std_angles])
        
        # 2. Mean and std of center of mass
        centers = np.array([feat.center_of_mass for feat in self.features])
        mean_center = np.mean(centers, axis=0)
        std_center = np.std(centers, axis=0)
        feature_components.extend([mean_center, std_center])
        
        # 3. Mean and std of velocities (excluding None values)
        velocities = [feat.velocity for feat in self.features if feat.velocity is not None]
        if velocities:
            velocities = np.array(velocities)
            mean_velocity = np.mean(velocities, axis=0)
            std_velocity = np.std(velocities, axis=0)
            feature_components.extend([mean_velocity, std_velocity])
        else:
            # Add zeros if no velocities available
            feature_components.extend([np.zeros(2), np.zeros(2)])
        
        # 4. Mean keypoint confidences
        all_confidences = np.array([feat.keypoint_confidences for feat in self.features])
        mean_confidences = np.mean(all_confidences, axis=0)
        feature_components.append(mean_confidences)
        
        # 5. Bounding box statistics (mean size and position)
        bboxes = np.array([feat.bbox for feat in self.features])
        mean_bbox = np.mean(bboxes, axis=0)
        std_bbox = np.std(bboxes, axis=0)
        feature_components.extend([mean_bbox, std_bbox])
        
        # Concatenate all components
        feature_vector = np.concatenate([
            comp.flatten() for comp in feature_components
        ])
        
        return feature_vector.astype(np.float32)


class PoseFeatureExtractor:
    """
    Extracts pose features from body keypoints.
    
    Features:
    - Joint angles (elbows, knees, torso)
    - Center of mass
    - Bounding boxes
    - Velocities
    """
    
    # COCO keypoint indices
    KEYPOINT_INDICES = {
        'nose': 0,
        'left_eye': 1,
        'right_eye': 2,
        'left_ear': 3,
        'right_ear': 4,
        'left_shoulder': 5,
        'right_shoulder': 6,
        'left_elbow': 7,
        'right_elbow': 8,
        'left_wrist': 9,
        'right_wrist': 10,
        'left_hip': 11,
        'right_hip': 12,
        'left_knee': 13,
        'right_knee': 14,
        'left_ankle': 15,
        'right_ankle': 16,
    }
    
    def __init__(self, confidence_threshold: float = 0.3):
        """
        Initialize pose feature extractor.
        
        Args:
            confidence_threshold: Minimum confidence for using keypoints
        """
        self.confidence_threshold = confidence_threshold
        logger.info(f"PoseFeatureExtractor initialized (confidence threshold: {confidence_threshold})")
    
    def extract_features(self, person_pose: PersonPose, 
                        previous_features: Optional[PoseFeatures] = None) -> PoseFeatures:
        """
        Extract pose features from a PersonPose object.
        
        Args:
            person_pose: PersonPose object containing keypoints
            previous_features: Features from previous frame (for velocity calculation)
        
        Returns:
            PoseFeatures object
        """
        keypoints = person_pose.keypoints  # (17, 3) - x, y, confidence
        
        # Extract positions and confidences
        positions = keypoints[:, :2]  # (17, 2)
        confidences = keypoints[:, 2]  # (17,)
        
        # Calculate joint angles
        joint_angles = self._calculate_joint_angles(keypoints)
        
        # Calculate center of mass
        center_of_mass = self._calculate_center_of_mass(keypoints)
        
        # Calculate velocity (if previous frame available)
        velocity = None
        if previous_features is not None:
            prev_center = previous_features.center_of_mass
            velocity = (
                center_of_mass[0] - prev_center[0],
                center_of_mass[1] - prev_center[1]
            )
        
        # Create PoseFeatures object
        features = PoseFeatures(
            joint_angles=joint_angles,
            center_of_mass=center_of_mass,
            bbox=person_pose.bbox,
            velocity=velocity,
            keypoint_positions=positions,
            keypoint_confidences=confidences
        )
        
        return features
    
    def _calculate_joint_angles(self, keypoints: np.ndarray) -> dict:
        """
        Calculate joint angles from keypoints.
        
        Angles calculated:
        - Left elbow angle
        - Right elbow angle
        - Left knee angle
        - Right knee angle
        - Torso angle (relative to vertical)
        
        Args:
            keypoints: Array of shape (17, 3) containing x, y, confidence
        
        Returns:
            Dictionary of joint angles in radians
        """
        angles = {}
        
        # Left elbow angle (shoulder-elbow-wrist)
        left_elbow_angle = self._calculate_angle(
            keypoints[self.KEYPOINT_INDICES['left_shoulder']],
            keypoints[self.KEYPOINT_INDICES['left_elbow']],
            keypoints[self.KEYPOINT_INDICES['left_wrist']]
        )
        if left_elbow_angle is not None:
            angles['left_elbow'] = left_elbow_angle
        
        # Right elbow angle (shoulder-elbow-wrist)
        right_elbow_angle = self._calculate_angle(
            keypoints[self.KEYPOINT_INDICES['right_shoulder']],
            keypoints[self.KEYPOINT_INDICES['right_elbow']],
            keypoints[self.KEYPOINT_INDICES['right_wrist']]
        )
        if right_elbow_angle is not None:
            angles['right_elbow'] = right_elbow_angle
        
        # Left knee angle (hip-knee-ankle)
        left_knee_angle = self._calculate_angle(
            keypoints[self.KEYPOINT_INDICES['left_hip']],
            keypoints[self.KEYPOINT_INDICES['left_knee']],
            keypoints[self.KEYPOINT_INDICES['left_ankle']]
        )
        if left_knee_angle is not None:
            angles['left_knee'] = left_knee_angle
        
        # Right knee angle (hip-knee-ankle)
        right_knee_angle = self._calculate_angle(
            keypoints[self.KEYPOINT_INDICES['right_hip']],
            keypoints[self.KEYPOINT_INDICES['right_knee']],
            keypoints[self.KEYPOINT_INDICES['right_ankle']]
        )
        if right_knee_angle is not None:
            angles['right_knee'] = right_knee_angle
        
        # Torso angle (relative to vertical)
        torso_angle = self._calculate_torso_angle(keypoints)
        if torso_angle is not None:
            angles['torso'] = torso_angle
        
        return angles
    
    def _calculate_angle(self, point1: np.ndarray, point2: np.ndarray, 
                        point3: np.ndarray) -> Optional[float]:
        """
        Calculate angle at point2 formed by point1-point2-point3.
        
        Args:
            point1: First point (x, y, confidence)
            point2: Middle point (vertex of angle)
            point3: Third point
        
        Returns:
            Angle in radians, or None if any point has low confidence
        """
        # Check confidence
        if (point1[2] < self.confidence_threshold or 
            point2[2] < self.confidence_threshold or 
            point3[2] < self.confidence_threshold):
            return None
        
        # Extract positions
        p1 = point1[:2]
        p2 = point2[:2]
        p3 = point3[:2]
        
        # Calculate vectors
        v1 = p1 - p2
        v2 = p3 - p2
        
        # Calculate angle using dot product
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
        
        # Clamp to [-1, 1] to avoid numerical errors
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        angle = np.arccos(cos_angle)
        
        return float(angle)
    
    def _calculate_torso_angle(self, keypoints: np.ndarray) -> Optional[float]:
        """
        Calculate torso angle relative to vertical.
        
        Uses midpoint of shoulders and midpoint of hips to define torso line.
        
        Args:
            keypoints: Array of shape (17, 3)
        
        Returns:
            Angle in radians, or None if keypoints have low confidence
        """
        # Get shoulder and hip keypoints
        left_shoulder = keypoints[self.KEYPOINT_INDICES['left_shoulder']]
        right_shoulder = keypoints[self.KEYPOINT_INDICES['right_shoulder']]
        left_hip = keypoints[self.KEYPOINT_INDICES['left_hip']]
        right_hip = keypoints[self.KEYPOINT_INDICES['right_hip']]
        
        # Check confidence
        if (left_shoulder[2] < self.confidence_threshold or 
            right_shoulder[2] < self.confidence_threshold or
            left_hip[2] < self.confidence_threshold or 
            right_hip[2] < self.confidence_threshold):
            return None
        
        # Calculate midpoints
        shoulder_mid = (left_shoulder[:2] + right_shoulder[:2]) / 2
        hip_mid = (left_hip[:2] + right_hip[:2]) / 2
        
        # Calculate torso vector
        torso_vector = shoulder_mid - hip_mid
        
        # Calculate angle relative to vertical (0, -1) vector
        vertical = np.array([0, -1])
        
        cos_angle = np.dot(torso_vector, vertical) / (np.linalg.norm(torso_vector) + 1e-8)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        angle = np.arccos(cos_angle)
        
        return float(angle)
    
    def _calculate_center_of_mass(self, keypoints: np.ndarray) -> Tuple[float, float]:
        """
        Calculate center of mass from keypoints.
        
        Uses weighted average of all valid keypoints, with confidence as weight.
        
        Args:
            keypoints: Array of shape (17, 3) containing x, y, confidence
        
        Returns:
            (x, y) coordinates of center of mass
        """
        # Filter valid keypoints (confidence >= threshold)
        valid_mask = keypoints[:, 2] >= self.confidence_threshold
        
        if not np.any(valid_mask):
            # If no valid keypoints, use bbox center as fallback
            logger.warning("No valid keypoints for center of mass calculation")
            return (0.0, 0.0)
        
        valid_keypoints = keypoints[valid_mask]
        
        # Calculate weighted average using confidence as weight
        positions = valid_keypoints[:, :2]
        confidences = valid_keypoints[:, 2]
        
        weighted_sum = np.sum(positions * confidences[:, np.newaxis], axis=0)
        total_weight = np.sum(confidences)
        
        center = weighted_sum / (total_weight + 1e-8)
        
        return (float(center[0]), float(center[1]))
    
    def extract_temporal_sequence(self, couple_poses: List[CouplePose], 
                                  person_id: int) -> TemporalPoseSequence:
        """
        Extract temporal sequence of pose features for a person.
        
        Args:
            couple_poses: List of CouplePose objects from video
            person_id: Person identifier (1=lead, 2=follow)
        
        Returns:
            TemporalPoseSequence object
        """
        features_list = []
        previous_features = None
        
        for couple_pose in couple_poses:
            # Get person pose based on person_id
            if person_id == 1:
                person_pose = couple_pose.lead_pose
            elif person_id == 2:
                person_pose = couple_pose.follow_pose
            else:
                raise ValueError(f"Invalid person_id: {person_id}. Must be 1 (lead) or 2 (follow)")
            
            # Skip if person not detected in this frame
            if person_pose is None:
                # Add None to maintain temporal alignment
                features_list.append(None)
                previous_features = None
                continue
            
            # Extract features
            features = self.extract_features(person_pose, previous_features)
            features_list.append(features)
            previous_features = features
        
        # Filter out None values for final sequence
        valid_features = [f for f in features_list if f is not None]
        
        sequence = TemporalPoseSequence(
            features=valid_features,
            person_id=person_id,
            frame_count=len(valid_features)
        )
        
        logger.info(
            f"Extracted temporal sequence for person {person_id}: "
            f"{len(valid_features)}/{len(couple_poses)} frames"
        )
        
        return sequence
