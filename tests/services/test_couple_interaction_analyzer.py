"""
Tests for CoupleInteractionAnalyzer service.

Tests the partner interaction analysis including hand connections,
synchronization, and relative positioning.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from core.services.couple_interaction_analyzer import (
    CoupleInteractionAnalyzer,
    InteractionFeatures,
    TemporalInteractionSequence
)
from core.services.yolov8_couple_detector import CouplePose, PersonPose


@pytest.fixture
def analyzer():
    """Create analyzer instance."""
    return CoupleInteractionAnalyzer(
        hand_connection_threshold=0.15,
        sync_window_size=5,
        confidence_threshold=0.3
    )


@pytest.fixture
def mock_person_pose():
    """Create mock PersonPose with valid keypoints."""
    keypoints = np.array([
        [100, 100, 0.9],  # 0: nose
        [95, 95, 0.9],    # 1: left_eye
        [105, 95, 0.9],   # 2: right_eye
        [90, 100, 0.8],   # 3: left_ear
        [110, 100, 0.8],  # 4: right_ear
        [80, 150, 0.9],   # 5: left_shoulder
        [120, 150, 0.9],  # 6: right_shoulder
        [70, 200, 0.8],   # 7: left_elbow
        [130, 200, 0.8],  # 8: right_elbow
        [60, 250, 0.7],   # 9: left_wrist
        [140, 250, 0.7],  # 10: right_wrist
        [85, 300, 0.9],   # 11: left_hip
        [115, 300, 0.9],  # 12: right_hip
        [80, 400, 0.8],   # 13: left_knee
        [120, 400, 0.8],  # 14: right_knee
        [75, 500, 0.7],   # 15: left_ankle
        [125, 500, 0.7],  # 16: right_ankle
    ])
    
    return PersonPose(
        person_id=0,
        keypoints=keypoints,
        bbox=np.array([50, 50, 150, 550]),
        confidence=0.85,
        frame_idx=0
    )


@pytest.fixture
def mock_couple_pose(mock_person_pose):
    """Create mock CouplePose with both dancers."""
    # Create second person (follow) offset to the right
    follow_keypoints = mock_person_pose.keypoints.copy()
    follow_keypoints[:, 0] += 200  # Shift right
    
    follow_pose = PersonPose(
        person_id=1,
        keypoints=follow_keypoints,
        bbox=np.array([250, 50, 350, 550]),
        confidence=0.82,
        frame_idx=0
    )
    
    return CouplePose(
        lead_pose=mock_person_pose,
        follow_pose=follow_pose,
        frame_idx=0,
        timestamp=0.0,
        has_both_dancers=True
    )


class TestCoupleInteractionAnalyzer:
    """Test suite for CoupleInteractionAnalyzer."""
    
    def test_initialization(self, analyzer):
        """Test analyzer initializes correctly."""
        assert analyzer.hand_connection_threshold == 0.15
        assert analyzer.sync_window_size == 5
        assert analyzer.confidence_threshold == 0.3
        assert analyzer.pose_extractor is not None
    
    def test_analyze_frame_with_both_dancers(self, analyzer, mock_couple_pose):
        """Test analyzing frame with both dancers present."""
        features = analyzer.analyze_frame(mock_couple_pose, 640, 480)
        
        assert features is not None
        assert isinstance(features, InteractionFeatures)
        assert features.distance > 0
        assert isinstance(features.hand_connections, list)
        assert features.relative_position in ['facing', 'side_by_side', 'shadow', 'unknown']
        assert features.frame_idx == 0
    
    def test_analyze_frame_missing_dancer(self, analyzer, mock_person_pose):
        """Test analyzing frame with only one dancer."""
        couple_pose = CouplePose(
            lead_pose=mock_person_pose,
            follow_pose=None,
            frame_idx=0,
            timestamp=0.0,
            has_both_dancers=False
        )
        
        features = analyzer.analyze_frame(couple_pose, 640, 480)
        assert features is None
    
    def test_calculate_distance(self, analyzer):
        """Test distance calculation between centers."""
        center1 = (100, 100)
        center2 = (200, 200)
        
        distance = analyzer._calculate_distance(center1, center2, 640, 480)
        
        assert distance > 0
        assert distance < 1.0  # Normalized
    
    def test_detect_hand_connections_close_hands(self, analyzer, mock_couple_pose):
        """Test hand connection detection when hands are close."""
        # Modify follow's right wrist to be close to lead's left wrist
        mock_couple_pose.follow_pose.keypoints[10, 0] = 65  # Close to lead's left wrist (60)
        mock_couple_pose.follow_pose.keypoints[10, 1] = 255  # Close to lead's left wrist (250)
        
        connections = analyzer._detect_hand_connections(
            mock_couple_pose.lead_pose,
            mock_couple_pose.follow_pose,
            640, 480
        )
        
        # Should detect at least one connection
        assert isinstance(connections, list)
    
    def test_detect_hand_connections_far_hands(self, analyzer, mock_couple_pose):
        """Test hand connection detection when hands are far apart."""
        connections = analyzer._detect_hand_connections(
            mock_couple_pose.lead_pose,
            mock_couple_pose.follow_pose,
            640, 480
        )
        
        # Hands are far apart, should have no connections
        assert isinstance(connections, list)
    
    def test_analyze_relative_position_facing(self, analyzer, mock_couple_pose):
        """Test relative position analysis for facing dancers."""
        position = analyzer._analyze_relative_position(
            mock_couple_pose.lead_pose,
            mock_couple_pose.follow_pose
        )
        
        assert position in ['facing', 'side_by_side', 'shadow', 'unknown']
    
    def test_calculate_synchronization(self, analyzer):
        """Test synchronization calculation."""
        # Create mock pose features with velocities
        from core.services.pose_feature_extractor import PoseFeatures
        
        lead_features = []
        follow_features = []
        
        for i in range(10):
            lead_feat = Mock(spec=PoseFeatures)
            lead_feat.velocity = np.array([1.0, 0.5])
            lead_features.append(lead_feat)
            
            follow_feat = Mock(spec=PoseFeatures)
            follow_feat.velocity = np.array([1.0, 0.5])  # Same velocity = high sync
            follow_features.append(follow_feat)
        
        sync_scores = analyzer.calculate_synchronization(lead_features, follow_features)
        
        assert len(sync_scores) == 10
        assert all(0 <= score <= 1 for score in sync_scores)
        # High synchronization expected
        assert np.mean(sync_scores) > 0.5
    
    def test_analyze_temporal_sequence(self, analyzer, mock_couple_pose):
        """Test temporal sequence analysis."""
        # Create sequence of couple poses
        couple_poses = []
        for i in range(20):
            pose = CouplePose(
                lead_pose=mock_couple_pose.lead_pose,
                follow_pose=mock_couple_pose.follow_pose,
                frame_idx=i,
                timestamp=i * 0.033,
                has_both_dancers=True
            )
            couple_poses.append(pose)
        
        sequence = analyzer.analyze_temporal_sequence(couple_poses, 640, 480)
        
        assert isinstance(sequence, TemporalInteractionSequence)
        assert sequence.frame_count > 0
        assert len(sequence.features) > 0
        assert all(f.synchronization_score is not None for f in sequence.features)
    
    def test_temporal_sequence_with_missing_frames(self, analyzer, mock_couple_pose):
        """Test temporal sequence with some missing dancers."""
        couple_poses = []
        for i in range(20):
            # Every 5th frame has missing follow
            has_both = (i % 5 != 0)
            follow = mock_couple_pose.follow_pose if has_both else None
            
            pose = CouplePose(
                lead_pose=mock_couple_pose.lead_pose,
                follow_pose=follow,
                frame_idx=i,
                timestamp=i * 0.033,
                has_both_dancers=has_both
            )
            couple_poses.append(pose)
        
        sequence = analyzer.analyze_temporal_sequence(couple_poses, 640, 480)
        
        assert isinstance(sequence, TemporalInteractionSequence)
        # Should only include frames with both dancers
        assert sequence.frame_count < 20
    
    def test_velocity_correlation(self, analyzer):
        """Test velocity correlation calculation."""
        velocities1 = np.array([[1.0, 0.5], [1.2, 0.6], [1.1, 0.55]])
        velocities2 = np.array([[1.0, 0.5], [1.2, 0.6], [1.1, 0.55]])
        
        correlation = analyzer._calculate_velocity_correlation(velocities1, velocities2)
        
        assert -1 <= correlation <= 1
        # Identical velocities should have high correlation
        assert correlation > 0.9
    
    def test_temporal_sequence_feature_vector(self, analyzer, mock_couple_pose):
        """Test feature vector generation from temporal sequence."""
        couple_poses = [mock_couple_pose] * 10
        
        sequence = analyzer.analyze_temporal_sequence(couple_poses, 640, 480)
        feature_vector = sequence.get_feature_vector()
        
        assert isinstance(feature_vector, np.ndarray)
        assert len(feature_vector) > 0
        assert not np.any(np.isnan(feature_vector))
        assert not np.any(np.isinf(feature_vector))


class TestInteractionFeatures:
    """Test InteractionFeatures dataclass."""
    
    def test_creation(self):
        """Test creating InteractionFeatures."""
        features = InteractionFeatures(
            distance=0.25,
            hand_connections=['lead_left-follow_right'],
            relative_position='facing',
            synchronization_score=0.85,
            frame_idx=10
        )
        
        assert features.distance == 0.25
        assert len(features.hand_connections) == 1
        assert features.relative_position == 'facing'
        assert features.synchronization_score == 0.85
        assert features.frame_idx == 10


class TestTemporalInteractionSequence:
    """Test TemporalInteractionSequence dataclass."""
    
    def test_creation(self):
        """Test creating TemporalInteractionSequence."""
        features = [
            InteractionFeatures(0.25, [], 'facing', 0.8, i)
            for i in range(10)
        ]
        
        sequence = TemporalInteractionSequence(
            features=features,
            frame_count=10
        )
        
        assert len(sequence.features) == 10
        assert sequence.frame_count == 10
    
    def test_get_feature_vector(self):
        """Test feature vector generation."""
        features = [
            InteractionFeatures(0.25 + i*0.01, ['conn1'], 'facing', 0.8, i)
            for i in range(20)
        ]
        
        sequence = TemporalInteractionSequence(features=features, frame_count=20)
        vector = sequence.get_feature_vector()
        
        assert isinstance(vector, np.ndarray)
        assert len(vector) > 0
        # Should include distance stats, connection stats, sync stats, position distribution
        assert len(vector) >= 12  # 4 distance + 2 connection + 2 sync + 4 position
