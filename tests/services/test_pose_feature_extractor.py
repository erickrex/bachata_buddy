"""
Tests for PoseFeatureExtractor service.

Tests pose feature extraction including joint angles, center of mass,
and temporal sequences with NaN handling.
"""

import pytest
import numpy as np
from unittest.mock import Mock

from video_processing.services.pose_feature_extractor import (
    PoseFeatureExtractor,
    PoseFeatures,
    TemporalPoseSequence
)
from video_processing.services.yolov8_couple_detector import PersonPose


@pytest.fixture
def extractor():
    """Create extractor instance."""
    return PoseFeatureExtractor(confidence_threshold=0.3)


@pytest.fixture
def valid_person_pose():
    """Create PersonPose with all keypoints visible."""
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
def partial_person_pose():
    """Create PersonPose with some low-confidence keypoints."""
    keypoints = np.array([
        [100, 100, 0.9],  # 0: nose
        [95, 95, 0.9],    # 1: left_eye
        [105, 95, 0.9],   # 2: right_eye
        [90, 100, 0.8],   # 3: left_ear
        [110, 100, 0.8],  # 4: right_ear
        [80, 150, 0.9],   # 5: left_shoulder
        [120, 150, 0.9],  # 6: right_shoulder
        [70, 200, 0.2],   # 7: left_elbow - LOW CONFIDENCE
        [130, 200, 0.8],  # 8: right_elbow
        [60, 250, 0.1],   # 9: left_wrist - LOW CONFIDENCE
        [140, 250, 0.7],  # 10: right_wrist
        [85, 300, 0.9],   # 11: left_hip
        [115, 300, 0.9],  # 12: right_hip
        [80, 400, 0.2],   # 13: left_knee - LOW CONFIDENCE
        [120, 400, 0.8],  # 14: right_knee
        [75, 500, 0.1],   # 15: left_ankle - LOW CONFIDENCE
        [125, 500, 0.7],  # 16: right_ankle
    ])
    
    return PersonPose(
        person_id=0,
        keypoints=keypoints,
        bbox=np.array([50, 50, 150, 550]),
        confidence=0.75,
        frame_idx=0
    )


class TestPoseFeatureExtractor:
    """Test suite for PoseFeatureExtractor."""
    
    def test_initialization(self, extractor):
        """Test extractor initializes correctly."""
        assert extractor.confidence_threshold == 0.3
        assert hasattr(extractor, 'KEYPOINT_INDICES')
    
    def test_extract_features_valid_pose(self, extractor, valid_person_pose):
        """Test extracting features from valid pose."""
        features = extractor.extract_features(valid_person_pose)
        
        assert isinstance(features, PoseFeatures)
        assert isinstance(features.joint_angles, dict)
        assert len(features.joint_angles) > 0
        assert isinstance(features.center_of_mass, tuple)
        assert len(features.center_of_mass) == 2
        assert features.velocity is None  # No previous frame
        assert features.keypoint_positions.shape == (17, 2)
        assert features.keypoint_confidences.shape == (17,)
    
    def test_extract_features_with_velocity(self, extractor, valid_person_pose):
        """Test velocity calculation with previous frame."""
        # First frame
        features1 = extractor.extract_features(valid_person_pose)
        
        # Second frame (moved slightly)
        pose2 = PersonPose(
            person_id=0,
            keypoints=valid_person_pose.keypoints + np.array([5, 5, 0]),
            bbox=valid_person_pose.bbox + np.array([5, 5, 5, 5]),
            confidence=0.85,
            frame_idx=1
        )
        
        features2 = extractor.extract_features(pose2, previous_features=features1)
        
        assert features2.velocity is not None
        assert len(features2.velocity) == 2
        assert features2.velocity[0] > 0  # Moved right
        assert features2.velocity[1] > 0  # Moved down
    
    def test_calculate_joint_angles_all_visible(self, extractor, valid_person_pose):
        """Test joint angle calculation with all keypoints visible."""
        angles = extractor._calculate_joint_angles(valid_person_pose.keypoints)
        
        assert isinstance(angles, dict)
        # Should have all 5 angles
        expected_angles = ['left_elbow', 'right_elbow', 'left_knee', 'right_knee', 'torso']
        for angle_name in expected_angles:
            assert angle_name in angles
            assert isinstance(angles[angle_name], float)
            assert 0 <= angles[angle_name] <= np.pi
    
    def test_calculate_joint_angles_partial_visibility(self, extractor, partial_person_pose):
        """Test joint angle calculation with some low-confidence keypoints."""
        angles = extractor._calculate_joint_angles(partial_person_pose.keypoints)
        
        assert isinstance(angles, dict)
        # Should have fewer angles due to low confidence
        # Right side should be present, left side might be missing
        assert 'right_elbow' in angles
        assert 'right_knee' in angles
    
    def test_calculate_angle_valid_points(self, extractor):
        """Test angle calculation between three valid points."""
        point1 = np.array([0, 0, 0.9])
        point2 = np.array([1, 0, 0.9])
        point3 = np.array([1, 1, 0.9])
        
        angle = extractor._calculate_angle(point1, point2, point3)
        
        assert angle is not None
        assert 0 <= angle <= np.pi
        # Should be approximately 90 degrees (pi/2)
        assert abs(angle - np.pi/2) < 0.1
    
    def test_calculate_angle_low_confidence(self, extractor):
        """Test angle calculation with low confidence points."""
        point1 = np.array([0, 0, 0.1])  # Low confidence
        point2 = np.array([1, 0, 0.9])
        point3 = np.array([1, 1, 0.9])
        
        angle = extractor._calculate_angle(point1, point2, point3)
        
        assert angle is None  # Should return None for low confidence
    
    def test_calculate_center_of_mass(self, extractor, valid_person_pose):
        """Test center of mass calculation."""
        center = extractor._calculate_center_of_mass(valid_person_pose.keypoints)
        
        assert isinstance(center, tuple)
        assert len(center) == 2
        assert 50 < center[0] < 150  # Within bbox x range
        assert 50 < center[1] < 550  # Within bbox y range
    
    def test_calculate_torso_angle(self, extractor, valid_person_pose):
        """Test torso angle calculation."""
        angle = extractor._calculate_torso_angle(valid_person_pose.keypoints)
        
        assert angle is not None
        assert 0 <= angle <= np.pi
    
    def test_extract_temporal_sequence(self, extractor, valid_person_pose):
        """Test extracting temporal sequence from multiple poses."""
        # Create sequence of poses
        poses = []
        for i in range(10):
            pose = PersonPose(
                person_id=0,
                keypoints=valid_person_pose.keypoints + np.array([i, i, 0]),
                bbox=valid_person_pose.bbox + np.array([i, i, i, i]),
                confidence=0.85,
                frame_idx=i
            )
            poses.append(pose)
        
        # Note: extract_temporal_sequence expects CouplePose objects, not PersonPose
        # Convert PersonPose to CouplePose for testing
        from video_processing.services.yolov8_couple_detector import CouplePose
        couple_poses = [
            CouplePose(
                lead_pose=pose,
                follow_pose=pose,  # Use same pose for both for testing
                frame_idx=pose.frame_idx,
                timestamp=pose.frame_idx / 30.0,
                has_both_dancers=True
            )
            for pose in poses
        ]
        
        sequence = extractor.extract_temporal_sequence(couple_poses, person_id=1)
        
        assert isinstance(sequence, TemporalPoseSequence)
        assert len(sequence.features) == 10
        assert sequence.frame_count == 10
        assert sequence.person_id == 1
        # All but first should have velocity
        assert sum(1 for f in sequence.features if f.velocity is not None) == 9


class TestPoseFeatures:
    """Test PoseFeatures dataclass."""
    
    def test_creation(self):
        """Test creating PoseFeatures."""
        features = PoseFeatures(
            joint_angles={'left_elbow': 1.5, 'right_elbow': 1.6},
            center_of_mass=(100, 200),
            bbox=np.array([50, 50, 150, 250]),
            velocity=(1.0, 2.0),
            keypoint_positions=np.zeros((17, 2)),
            keypoint_confidences=np.ones(17)
        )
        
        assert len(features.joint_angles) == 2
        assert features.center_of_mass == (100, 200)
        assert features.velocity == (1.0, 2.0)


class TestTemporalPoseSequence:
    """Test TemporalPoseSequence dataclass."""
    
    def test_creation(self):
        """Test creating TemporalPoseSequence."""
        features = [
            PoseFeatures(
                joint_angles={'left_elbow': 1.5},
                center_of_mass=(100, 200),
                bbox=np.array([50, 50, 150, 250]),
                velocity=None,
                keypoint_positions=np.zeros((17, 2)),
                keypoint_confidences=np.ones(17)
            )
            for _ in range(10)
        ]
        
        sequence = TemporalPoseSequence(features=features, person_id=0, frame_count=10)
        
        assert len(sequence.features) == 10
        assert sequence.frame_count == 10
        assert sequence.person_id == 0
    
    def test_get_feature_vector_consistent_angles(self):
        """Test feature vector with all angles present."""
        features = []
        for i in range(20):
            feat = PoseFeatures(
                joint_angles={
                    'left_elbow': 1.5 + i*0.01,
                    'right_elbow': 1.6 + i*0.01,
                    'left_knee': 1.7 + i*0.01,
                    'right_knee': 1.8 + i*0.01,
                    'torso': 0.1 + i*0.01
                },
                center_of_mass=(100 + i, 200 + i),
                bbox=np.array([50, 50, 150, 250]),
                velocity=(1.0, 2.0) if i > 0 else None,
                keypoint_positions=np.zeros((17, 2)),
                keypoint_confidences=np.ones(17) * 0.8
            )
            features.append(feat)
        
        sequence = TemporalPoseSequence(features=features, person_id=0, frame_count=20)
        vector = sequence.get_feature_vector()
        
        assert isinstance(vector, np.ndarray)
        assert len(vector) > 0
        assert not np.any(np.isnan(vector))
        assert not np.any(np.isinf(vector))
    
    def test_get_feature_vector_missing_angles(self):
        """Test feature vector with some missing angles (NaN handling)."""
        features = []
        for i in range(20):
            # Randomly omit some angles
            angles = {}
            if i % 2 == 0:
                angles['left_elbow'] = 1.5
            if i % 3 == 0:
                angles['right_elbow'] = 1.6
            angles['torso'] = 0.1  # Always present
            
            feat = PoseFeatures(
                joint_angles=angles,
                center_of_mass=(100 + i, 200 + i),
                bbox=np.array([50, 50, 150, 250]),
                velocity=(1.0, 2.0) if i > 0 else None,
                keypoint_positions=np.zeros((17, 2)),
                keypoint_confidences=np.ones(17) * 0.8
            )
            features.append(feat)
        
        sequence = TemporalPoseSequence(features=features, person_id=0, frame_count=20)
        vector = sequence.get_feature_vector()
        
        # Should handle missing angles with NaN padding and nanmean/nanstd
        assert isinstance(vector, np.ndarray)
        assert len(vector) > 0
        assert not np.any(np.isnan(vector))  # NaN should be replaced with 0
        assert not np.any(np.isinf(vector))
    
    def test_get_feature_vector_no_velocities(self):
        """Test feature vector when no velocities are available."""
        features = []
        for i in range(10):
            feat = PoseFeatures(
                joint_angles={'torso': 0.1},
                center_of_mass=(100, 200),
                bbox=np.array([50, 50, 150, 250]),
                velocity=None,  # No velocity
                keypoint_positions=np.zeros((17, 2)),
                keypoint_confidences=np.ones(17)
            )
            features.append(feat)
        
        sequence = TemporalPoseSequence(features=features, person_id=0, frame_count=10)
        vector = sequence.get_feature_vector()
        
        # Should add zeros for velocity stats
        assert isinstance(vector, np.ndarray)
        assert not np.any(np.isnan(vector))
    
    def test_get_feature_vector_empty_sequence(self):
        """Test feature vector with empty sequence."""
        sequence = TemporalPoseSequence(features=[], person_id=0, frame_count=0)
        vector = sequence.get_feature_vector()
        
        assert isinstance(vector, np.ndarray)
        assert len(vector) == 0
