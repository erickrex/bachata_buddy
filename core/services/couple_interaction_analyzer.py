"""
Couple Interaction Analyzer

Analyzes partner interaction dynamics for couple dancing.

Features analyzed:
- Distance between dancers' centers of mass
- Hand-to-hand connections
- Movement synchronization
- Relative positioning (facing, side-by-side, shadow)
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import logging

from .yolov8_couple_detector import CouplePose, PersonPose
from .pose_feature_extractor import PoseFeatures, PoseFeatureExtractor

logger = logging.getLogger(__name__)


@dataclass
class InteractionFeatures:
    """
    Interaction features between two dancers in a frame.
    
    Attributes:
        distance: Euclidean distance between centers of mass (normalized)
        hand_connections: List of detected hand connections
        relative_position: Type of positioning (facing, side-by-side, shadow)
        synchronization_score: Movement synchronization score (0-1)
        frame_idx: Frame index
    """
    distance: float
    hand_connections: List[str]  # e.g., ['lead_left-follow_right']
    relative_position: str  # 'facing', 'side_by_side', 'shadow', 'unknown'
    synchronization_score: Optional[float]
    frame_idx: int


@dataclass
class TemporalInteractionSequence:
    """
    Temporal sequence of interaction features.
    
    Attributes:
        features: List of InteractionFeatures for each frame
        frame_count: Number of frames in sequence
    """
    features: List[InteractionFeatures]
    frame_count: int
    
    def get_feature_vector(self) -> np.ndarray:
        """
        Aggregate temporal interaction features into a single feature vector.
        
        Returns:
            Feature vector combining all temporal interaction information
        """
        if not self.features:
            return np.array([])
        
        feature_components = []
        
        # 1. Distance statistics
        distances = np.array([f.distance for f in self.features])
        mean_distance = np.mean(distances)
        std_distance = np.std(distances)
        min_distance = np.min(distances)
        max_distance = np.max(distances)
        feature_components.extend([mean_distance, std_distance, min_distance, max_distance])
        
        # 2. Hand connection statistics
        connection_counts = np.array([len(f.hand_connections) for f in self.features])
        mean_connections = np.mean(connection_counts)
        connection_rate = np.sum(connection_counts > 0) / len(self.features)
        feature_components.extend([mean_connections, connection_rate])
        
        # 3. Synchronization statistics
        sync_scores = [f.synchronization_score for f in self.features if f.synchronization_score is not None]
        if sync_scores:
            mean_sync = np.mean(sync_scores)
            std_sync = np.std(sync_scores)
            feature_components.extend([mean_sync, std_sync])
        else:
            feature_components.extend([0.0, 0.0])
        
        # 4. Relative position distribution (one-hot encoding)
        position_types = ['facing', 'side_by_side', 'shadow', 'unknown']
        position_counts = {pos: 0 for pos in position_types}
        for f in self.features:
            if f.relative_position in position_counts:
                position_counts[f.relative_position] += 1
        
        position_distribution = np.array([
            position_counts[pos] / len(self.features) for pos in position_types
        ])
        feature_components.append(position_distribution)
        
        # Concatenate all components
        feature_vector = np.concatenate([
            np.array([comp]) if np.isscalar(comp) else comp.flatten()
            for comp in feature_components
        ])
        
        return feature_vector.astype(np.float32)


class CoupleInteractionAnalyzer:
    """
    Analyzes interaction dynamics between two dancers.
    
    Features:
    - Distance between dancers
    - Hand-to-hand connections
    - Movement synchronization
    - Relative positioning
    """
    
    def __init__(self, hand_connection_threshold: float = 0.15,
                 sync_window_size: int = 5,
                 confidence_threshold: float = 0.3):
        """
        Initialize couple interaction analyzer.
        
        Args:
            hand_connection_threshold: Maximum normalized distance for hand connection (0.15)
            sync_window_size: Window size for synchronization calculation (5 frames)
            confidence_threshold: Minimum confidence for keypoint usage
        """
        self.hand_connection_threshold = hand_connection_threshold
        self.sync_window_size = sync_window_size
        self.confidence_threshold = confidence_threshold
        
        self.pose_extractor = PoseFeatureExtractor(confidence_threshold)
        
        logger.info(
            f"CoupleInteractionAnalyzer initialized "
            f"(hand threshold: {hand_connection_threshold}, "
            f"sync window: {sync_window_size})"
        )
    
    def analyze_frame(self, couple_pose: CouplePose, 
                     frame_width: float, frame_height: float) -> Optional[InteractionFeatures]:
        """
        Analyze interaction features for a single frame.
        
        Args:
            couple_pose: CouplePose object containing both dancers
            frame_width: Video frame width (for normalization)
            frame_height: Video frame height (for normalization)
        
        Returns:
            InteractionFeatures object, or None if both dancers not detected
        """
        # Check if both dancers are detected
        if not couple_pose.has_both_dancers:
            return None
        
        lead = couple_pose.lead_pose
        follow = couple_pose.follow_pose
        
        # Extract pose features for both dancers
        lead_features = self.pose_extractor.extract_features(lead)
        follow_features = self.pose_extractor.extract_features(follow)
        
        # Calculate distance between centers of mass
        distance = self._calculate_distance(
            lead_features.center_of_mass,
            follow_features.center_of_mass,
            frame_width,
            frame_height
        )
        
        # Detect hand connections
        hand_connections = self._detect_hand_connections(
            lead, follow, frame_width, frame_height
        )
        
        # Analyze relative positioning
        relative_position = self._analyze_relative_position(lead, follow)
        
        # Create InteractionFeatures object (synchronization calculated later)
        features = InteractionFeatures(
            distance=distance,
            hand_connections=hand_connections,
            relative_position=relative_position,
            synchronization_score=None,  # Calculated in temporal analysis
            frame_idx=couple_pose.frame_idx
        )
        
        return features
    
    def _calculate_distance(self, center1: Tuple[float, float], 
                           center2: Tuple[float, float],
                           frame_width: float, frame_height: float) -> float:
        """
        Calculate Euclidean distance between two centers of mass.
        
        Distance is normalized by frame diagonal for scale invariance.
        
        Args:
            center1: (x, y) coordinates of first center
            center2: (x, y) coordinates of second center
            frame_width: Video frame width
            frame_height: Video frame height
        
        Returns:
            Normalized distance (0-1 range typically)
        """
        # Calculate Euclidean distance
        dx = center1[0] - center2[0]
        dy = center1[1] - center2[1]
        distance = np.sqrt(dx**2 + dy**2)
        
        # Normalize by frame diagonal
        frame_diagonal = np.sqrt(frame_width**2 + frame_height**2)
        normalized_distance = distance / (frame_diagonal + 1e-8)
        
        return float(normalized_distance)
    
    def _detect_hand_connections(self, lead: PersonPose, follow: PersonPose,
                                frame_width: float, frame_height: float) -> List[str]:
        """
        Detect hand-to-hand connections between dancers.
        
        A connection is detected if the distance between hand keypoints is below
        the threshold (0.15 normalized distance).
        
        Args:
            lead: Lead dancer's pose
            follow: Follow dancer's pose
            frame_width: Video frame width
            frame_height: Video frame height
        
        Returns:
            List of connection strings (e.g., ['lead_left-follow_right'])
        """
        connections = []
        
        # Get wrist keypoints (index 9=left_wrist, 10=right_wrist)
        lead_left_wrist = lead.keypoints[9]
        lead_right_wrist = lead.keypoints[10]
        follow_left_wrist = follow.keypoints[9]
        follow_right_wrist = follow.keypoints[10]
        
        # Frame diagonal for normalization
        frame_diagonal = np.sqrt(frame_width**2 + frame_height**2)
        
        # Check all possible hand combinations
        hand_pairs = [
            (lead_left_wrist, follow_left_wrist, 'lead_left-follow_left'),
            (lead_left_wrist, follow_right_wrist, 'lead_left-follow_right'),
            (lead_right_wrist, follow_left_wrist, 'lead_right-follow_left'),
            (lead_right_wrist, follow_right_wrist, 'lead_right-follow_right'),
        ]
        
        for hand1, hand2, connection_name in hand_pairs:
            # Check confidence
            if (hand1[2] < self.confidence_threshold or 
                hand2[2] < self.confidence_threshold):
                continue
            
            # Calculate distance
            dx = hand1[0] - hand2[0]
            dy = hand1[1] - hand2[1]
            distance = np.sqrt(dx**2 + dy**2)
            
            # Normalize
            normalized_distance = distance / (frame_diagonal + 1e-8)
            
            # Check if connection exists
            if normalized_distance <= self.hand_connection_threshold:
                connections.append(connection_name)
                logger.debug(
                    f"Hand connection detected: {connection_name} "
                    f"(distance: {normalized_distance:.3f})"
                )
        
        return connections
    
    def _analyze_relative_position(self, lead: PersonPose, follow: PersonPose) -> str:
        """
        Analyze relative positioning between dancers.
        
        Positions:
        - 'facing': Dancers facing each other (front-to-front)
        - 'side_by_side': Dancers side by side
        - 'shadow': One dancer behind the other
        - 'unknown': Cannot determine position
        
        Args:
            lead: Lead dancer's pose
            follow: Follow dancer's pose
        
        Returns:
            Position type string
        """
        # Get shoulder keypoints to determine body orientation
        lead_left_shoulder = lead.keypoints[5]
        lead_right_shoulder = lead.keypoints[6]
        follow_left_shoulder = follow.keypoints[5]
        follow_right_shoulder = follow.keypoints[6]
        
        # Check confidence
        if (lead_left_shoulder[2] < self.confidence_threshold or
            lead_right_shoulder[2] < self.confidence_threshold or
            follow_left_shoulder[2] < self.confidence_threshold or
            follow_right_shoulder[2] < self.confidence_threshold):
            return 'unknown'
        
        # Calculate shoulder vectors (left to right)
        lead_shoulder_vec = lead_right_shoulder[:2] - lead_left_shoulder[:2]
        follow_shoulder_vec = follow_right_shoulder[:2] - follow_left_shoulder[:2]
        
        # Calculate center positions
        lead_center = (lead_left_shoulder[:2] + lead_right_shoulder[:2]) / 2
        follow_center = (follow_left_shoulder[:2] + follow_right_shoulder[:2]) / 2
        
        # Vector from lead to follow
        lead_to_follow = follow_center - lead_center
        
        # Normalize vectors
        lead_shoulder_vec = lead_shoulder_vec / (np.linalg.norm(lead_shoulder_vec) + 1e-8)
        follow_shoulder_vec = follow_shoulder_vec / (np.linalg.norm(follow_shoulder_vec) + 1e-8)
        lead_to_follow = lead_to_follow / (np.linalg.norm(lead_to_follow) + 1e-8)
        
        # Calculate dot products to determine orientation
        # Shoulder alignment (parallel vs perpendicular)
        shoulder_alignment = abs(np.dot(lead_shoulder_vec, follow_shoulder_vec))
        
        # Lead facing direction vs lead-to-follow direction
        lead_facing_alignment = abs(np.dot(
            np.array([-lead_shoulder_vec[1], lead_shoulder_vec[0]]),  # Perpendicular to shoulders
            lead_to_follow
        ))
        
        # Determine position type
        if shoulder_alignment > 0.7:  # Shoulders roughly parallel
            return 'side_by_side'
        elif lead_facing_alignment > 0.7:  # Lead facing toward/away from follow
            # Check if they're facing each other or one behind the other
            follow_facing_alignment = abs(np.dot(
                np.array([-follow_shoulder_vec[1], follow_shoulder_vec[0]]),
                -lead_to_follow  # Opposite direction
            ))
            
            if follow_facing_alignment > 0.7:
                return 'facing'
            else:
                return 'shadow'
        else:
            return 'unknown'
    
    def calculate_synchronization(self, lead_features: List[PoseFeatures],
                                  follow_features: List[PoseFeatures]) -> List[float]:
        """
        Calculate movement synchronization scores using velocity correlation.
        
        Uses a sliding window of 5 frames to compute velocity correlation.
        
        Args:
            lead_features: List of PoseFeatures for lead dancer
            follow_features: List of PoseFeatures for follow dancer
        
        Returns:
            List of synchronization scores (0-1) for each frame
        """
        if len(lead_features) != len(follow_features):
            logger.warning(
                f"Feature list length mismatch: lead={len(lead_features)}, "
                f"follow={len(follow_features)}"
            )
            return []
        
        sync_scores = []
        
        for i in range(len(lead_features)):
            # Define window
            window_start = max(0, i - self.sync_window_size // 2)
            window_end = min(len(lead_features), i + self.sync_window_size // 2 + 1)
            
            # Extract velocities in window
            lead_velocities = []
            follow_velocities = []
            
            for j in range(window_start, window_end):
                if (lead_features[j].velocity is not None and
                    follow_features[j].velocity is not None):
                    lead_velocities.append(lead_features[j].velocity)
                    follow_velocities.append(follow_features[j].velocity)
            
            # Calculate correlation if enough data
            if len(lead_velocities) >= 2:
                lead_vel_array = np.array(lead_velocities)
                follow_vel_array = np.array(follow_velocities)
                
                # Calculate correlation coefficient
                correlation = self._calculate_velocity_correlation(
                    lead_vel_array, follow_vel_array
                )
                
                # Convert to 0-1 range (correlation is -1 to 1)
                sync_score = (correlation + 1) / 2
                sync_scores.append(sync_score)
            else:
                # Not enough data for correlation
                sync_scores.append(0.5)  # Neutral score
        
        return sync_scores
    
    def _calculate_velocity_correlation(self, velocities1: np.ndarray,
                                       velocities2: np.ndarray) -> float:
        """
        Calculate correlation between two velocity sequences.
        
        Args:
            velocities1: Array of shape (N, 2) containing velocity vectors
            velocities2: Array of shape (N, 2) containing velocity vectors
        
        Returns:
            Correlation coefficient (-1 to 1)
        """
        # Flatten velocity arrays
        v1_flat = velocities1.flatten()
        v2_flat = velocities2.flatten()
        
        # Calculate correlation
        if len(v1_flat) < 2:
            return 0.0
        
        correlation = np.corrcoef(v1_flat, v2_flat)[0, 1]
        
        # Handle NaN (can occur if velocities are constant)
        if np.isnan(correlation):
            return 0.0
        
        return float(correlation)
    
    def analyze_temporal_sequence(self, couple_poses: List[CouplePose],
                                  frame_width: float, 
                                  frame_height: float) -> TemporalInteractionSequence:
        """
        Analyze interaction features across entire video sequence.
        
        Args:
            couple_poses: List of CouplePose objects from video
            frame_width: Video frame width
            frame_height: Video frame height
        
        Returns:
            TemporalInteractionSequence object
        """
        # First pass: extract basic interaction features
        interaction_features = []
        
        for couple_pose in couple_poses:
            features = self.analyze_frame(couple_pose, frame_width, frame_height)
            interaction_features.append(features)
        
        # Filter valid frames (both dancers detected)
        valid_indices = [i for i, f in enumerate(interaction_features) if f is not None]
        valid_features = [interaction_features[i] for i in valid_indices]
        
        if not valid_features:
            logger.warning("No valid interaction features found")
            return TemporalInteractionSequence(features=[], frame_count=0)
        
        # Second pass: calculate synchronization scores
        # Extract pose features for lead and follow
        lead_pose_features = []
        follow_pose_features = []
        
        for idx in valid_indices:
            couple_pose = couple_poses[idx]
            lead_feat = self.pose_extractor.extract_features(couple_pose.lead_pose)
            follow_feat = self.pose_extractor.extract_features(couple_pose.follow_pose)
            lead_pose_features.append(lead_feat)
            follow_pose_features.append(follow_feat)
        
        # Calculate synchronization scores
        sync_scores = self.calculate_synchronization(lead_pose_features, follow_pose_features)
        
        # Update interaction features with synchronization scores
        for i, score in enumerate(sync_scores):
            if i < len(valid_features):
                valid_features[i].synchronization_score = score
        
        sequence = TemporalInteractionSequence(
            features=valid_features,
            frame_count=len(valid_features)
        )
        
        logger.info(
            f"Analyzed temporal interaction sequence: "
            f"{len(valid_features)}/{len(couple_poses)} frames with both dancers"
        )
        
        return sequence
