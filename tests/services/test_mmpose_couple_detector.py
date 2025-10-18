"""
Tests for MMPose Couple Detector

Focus on PersonTracker IoU-based tracking functionality and pose detection.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from bachata_buddy.core.services.mmpose_couple_detector import (
    PersonTracker,
    PersonPose,
    CouplePose,
    MMPoseCoupleDetector
)


class TestPersonTracker:
    """Test IoU-based person tracking."""
    
    def test_tracker_initialization(self):
        """Test tracker initializes with correct parameters."""
        tracker = PersonTracker(iou_threshold=0.3, max_missing_frames=10)
        
        assert tracker.iou_threshold == 0.3
        assert tracker.max_missing_frames == 10
        assert len(tracker.tracked_persons) == 0
    
    def test_compute_iou_identical_boxes(self):
        """Test IoU computation for identical boxes."""
        tracker = PersonTracker()
        
        bbox1 = (10, 10, 50, 50)
        bbox2 = (10, 10, 50, 50)
        
        iou = tracker._compute_iou(bbox1, bbox2)
        
        assert iou == 1.0
    
    def test_compute_iou_no_overlap(self):
        """Test IoU computation for non-overlapping boxes."""
        tracker = PersonTracker()
        
        bbox1 = (10, 10, 50, 50)
        bbox2 = (100, 100, 50, 50)
        
        iou = tracker._compute_iou(bbox1, bbox2)
        
        assert iou == 0.0
    
    def test_compute_iou_partial_overlap(self):
        """Test IoU computation for partially overlapping boxes."""
        tracker = PersonTracker()
        
        # Box 1: (0, 0, 100, 100) - area = 10000
        # Box 2: (50, 50, 100, 100) - area = 10000
        # Intersection: (50, 50, 50, 50) - area = 2500
        # Union: 10000 + 10000 - 2500 = 17500
        # IoU: 2500 / 17500 = 0.142857...
        
        bbox1 = (0, 0, 100, 100)
        bbox2 = (50, 50, 100, 100)
        
        iou = tracker._compute_iou(bbox1, bbox2)
        
        assert 0.14 < iou < 0.15
    
    def test_first_detection_assigns_id_1(self):
        """Test first detection gets person ID 1 (lead)."""
        tracker = PersonTracker()
        
        detections = [(10, 10, 50, 50)]
        person_ids = tracker.update(detections)
        
        assert person_ids == [1]
        assert 1 in tracker.tracked_persons
    
    def test_two_detections_assign_ids_1_and_2(self):
        """Test two detections get person IDs 1 and 2 (lead and follow)."""
        tracker = PersonTracker()
        
        detections = [
            (10, 10, 50, 50),
            (100, 10, 50, 50)
        ]
        person_ids = tracker.update(detections)
        
        assert set(person_ids) == {1, 2}
        assert 1 in tracker.tracked_persons
        assert 2 in tracker.tracked_persons
    
    def test_tracking_maintains_ids_across_frames(self):
        """Test person IDs are maintained across frames with similar positions."""
        tracker = PersonTracker(iou_threshold=0.3)
        
        # Frame 1: Two persons
        detections_1 = [
            (10, 10, 50, 50),
            (100, 10, 50, 50)
        ]
        ids_1 = tracker.update(detections_1)
        
        # Frame 2: Same persons, slightly moved (high IoU)
        detections_2 = [
            (12, 12, 50, 50),  # Moved slightly from (10, 10)
            (102, 12, 50, 50)  # Moved slightly from (100, 10)
        ]
        ids_2 = tracker.update(detections_2)
        
        # IDs should be maintained
        assert ids_1 == ids_2
    
    def test_tracking_handles_missing_detection(self):
        """Test tracker handles temporary missing detections."""
        tracker = PersonTracker(iou_threshold=0.3, max_missing_frames=5)
        
        # Frame 1: Two persons
        detections_1 = [
            (10, 10, 50, 50),
            (100, 10, 50, 50)
        ]
        ids_1 = tracker.update(detections_1)
        
        # Frame 2: Only one person detected (other temporarily occluded)
        detections_2 = [(12, 12, 50, 50)]
        ids_2 = tracker.update(detections_2)
        
        # Frame 3: Both persons back
        detections_3 = [
            (14, 14, 50, 50),
            (104, 14, 50, 50)
        ]
        ids_3 = tracker.update(detections_3)
        
        # IDs should be maintained
        assert set(ids_1) == set(ids_3)
    
    def test_tracking_removes_long_missing_persons(self):
        """Test tracker removes persons missing for too many frames."""
        tracker = PersonTracker(iou_threshold=0.3, max_missing_frames=2)
        
        # Frame 1: Two persons
        detections_1 = [
            (10, 10, 50, 50),
            (100, 10, 50, 50)
        ]
        tracker.update(detections_1)
        
        # Frames 2-4: Only one person (other missing for 3 frames)
        for _ in range(3):
            tracker.update([(12, 12, 50, 50)])
        
        # Person 2 should be removed from tracking
        assert len(tracker.tracked_persons) == 1
    
    def test_empty_detections_handled(self):
        """Test tracker handles frames with no detections."""
        tracker = PersonTracker()
        
        # Frame 1: Two persons
        detections_1 = [
            (10, 10, 50, 50),
            (100, 10, 50, 50)
        ]
        tracker.update(detections_1)
        
        # Frame 2: No detections
        ids_2 = tracker.update([])
        
        assert ids_2 == []
        # Persons should still be tracked (missing count incremented)
        assert len(tracker.tracked_persons) == 2
    
    def test_reset_clears_tracked_persons(self):
        """Test reset clears all tracked persons."""
        tracker = PersonTracker()
        
        # Add some detections
        detections = [
            (10, 10, 50, 50),
            (100, 10, 50, 50)
        ]
        tracker.update(detections)
        
        assert len(tracker.tracked_persons) == 2
        
        # Reset
        tracker.reset()
        
        assert len(tracker.tracked_persons) == 0


class TestPersonPose:
    """Test PersonPose dataclass."""
    
    def test_valid_person_pose(self):
        """Test creating valid PersonPose."""
        body_keypoints = np.random.rand(17, 3)
        
        pose = PersonPose(
            person_id=1,
            body_keypoints=body_keypoints,
            left_hand_keypoints=None,
            right_hand_keypoints=None,
            bbox=(10, 10, 50, 50),
            confidence=0.85
        )
        
        assert pose.person_id == 1
        assert pose.body_keypoints.shape == (17, 3)
        assert pose.confidence == 0.85
    
    def test_invalid_body_keypoints_shape(self):
        """Test PersonPose rejects invalid body keypoints shape."""
        body_keypoints = np.random.rand(10, 3)  # Wrong shape
        
        with pytest.raises(ValueError, match="body_keypoints must have shape"):
            PersonPose(
                person_id=1,
                body_keypoints=body_keypoints,
                left_hand_keypoints=None,
                right_hand_keypoints=None,
                bbox=(10, 10, 50, 50),
                confidence=0.85
            )
    
    def test_invalid_hand_keypoints_shape(self):
        """Test PersonPose rejects invalid hand keypoints shape."""
        body_keypoints = np.random.rand(17, 3)
        left_hand_keypoints = np.random.rand(10, 3)  # Wrong shape
        
        with pytest.raises(ValueError, match="left_hand_keypoints must have shape"):
            PersonPose(
                person_id=1,
                body_keypoints=body_keypoints,
                left_hand_keypoints=left_hand_keypoints,
                right_hand_keypoints=None,
                bbox=(10, 10, 50, 50),
                confidence=0.85
            )


class TestCouplePose:
    """Test CouplePose dataclass."""
    
    def test_couple_pose_with_both_dancers(self):
        """Test CouplePose with both dancers detected."""
        lead_pose = PersonPose(
            person_id=1,
            body_keypoints=np.random.rand(17, 3),
            left_hand_keypoints=None,
            right_hand_keypoints=None,
            bbox=(10, 10, 50, 50),
            confidence=0.85
        )
        
        follow_pose = PersonPose(
            person_id=2,
            body_keypoints=np.random.rand(17, 3),
            left_hand_keypoints=None,
            right_hand_keypoints=None,
            bbox=(100, 10, 50, 50),
            confidence=0.90
        )
        
        couple_pose = CouplePose(
            lead=lead_pose,
            follow=follow_pose,
            frame_idx=0,
            timestamp=0.0
        )
        
        assert couple_pose.has_both_dancers is True
        assert couple_pose.detection_count == 2
    
    def test_couple_pose_with_only_lead(self):
        """Test CouplePose with only lead dancer detected."""
        lead_pose = PersonPose(
            person_id=1,
            body_keypoints=np.random.rand(17, 3),
            left_hand_keypoints=None,
            right_hand_keypoints=None,
            bbox=(10, 10, 50, 50),
            confidence=0.85
        )
        
        couple_pose = CouplePose(
            lead=lead_pose,
            follow=None,
            frame_idx=0,
            timestamp=0.0
        )
        
        assert couple_pose.has_both_dancers is False
        assert couple_pose.detection_count == 1
    
    def test_couple_pose_with_no_dancers(self):
        """Test CouplePose with no dancers detected."""
        couple_pose = CouplePose(
            lead=None,
            follow=None,
            frame_idx=0,
            timestamp=0.0
        )
        
        assert couple_pose.has_both_dancers is False
        assert couple_pose.detection_count == 0


class TestMMPoseCoupleDetectorPoseEstimation:
    """Test pose and hand detection methods."""
    
    @pytest.fixture
    def mock_detector(self):
        """Create a mock MMPoseCoupleDetector for testing."""
        with patch('bachata_buddy.core.services.mmpose_couple_detector.MMPoseCoupleDetector._init_person_detector'), \
             patch('bachata_buddy.core.services.mmpose_couple_detector.MMPoseCoupleDetector._init_pose_estimator'), \
             patch('bachata_buddy.core.services.mmpose_couple_detector.MMPoseCoupleDetector._init_hand_detector'):
            
            detector = MMPoseCoupleDetector(
                checkpoint_path="/fake/path",
                confidence_threshold=0.3,
                enable_hand_detection=True
            )
            
            # Mock the models
            detector.pose_estimator = Mock()
            detector.hand_detector = Mock()
            detector.person_detector = Mock()
            
            return detector
    
    def test_estimate_pose_success(self, mock_detector):
        """Test successful pose estimation."""
        # Create mock frame and bbox
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox = (100, 100, 200, 200)
        
        # Mock the inference result
        mock_result = Mock()
        mock_result.pred_instances = Mock()
        mock_result.pred_instances.keypoints = np.random.rand(1, 17, 2)
        mock_result.pred_instances.keypoint_scores = np.random.rand(1, 17) * 0.5 + 0.5  # 0.5-1.0
        
        with patch('bachata_buddy.core.services.mmpose_couple_detector.inference_topdown', return_value=[mock_result]):
            keypoints = mock_detector.estimate_pose(frame, bbox)
        
        assert keypoints is not None
        assert keypoints.shape == (17, 3)
        assert np.all(keypoints[:, 2] >= 0.0)  # Confidence scores
        assert np.all(keypoints[:, 2] <= 1.0)
    
    def test_estimate_pose_failure(self, mock_detector):
        """Test pose estimation failure."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox = (100, 100, 200, 200)
        
        # Mock empty result
        with patch('bachata_buddy.core.services.mmpose_couple_detector.inference_topdown', return_value=[]):
            keypoints = mock_detector.estimate_pose(frame, bbox)
        
        assert keypoints is None
    
    def test_estimate_pose_filters_low_confidence(self, mock_detector):
        """Test that low confidence keypoints are filtered."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox = (100, 100, 200, 200)
        
        # Mock result with some low confidence scores
        mock_result = Mock()
        mock_result.pred_instances = Mock()
        mock_result.pred_instances.keypoints = np.random.rand(1, 17, 2)
        
        # Mix of high and low confidence scores
        scores = np.array([0.9, 0.8, 0.2, 0.1, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.8, 0.9, 0.7, 0.6, 0.5, 0.4])
        mock_result.pred_instances.keypoint_scores = scores.reshape(1, 17)
        
        with patch('bachata_buddy.core.services.mmpose_couple_detector.inference_topdown', return_value=[mock_result]):
            keypoints = mock_detector.estimate_pose(frame, bbox)
        
        assert keypoints is not None
        # Low confidence keypoints (< 0.3) should be zeroed out
        assert np.all(keypoints[scores < 0.3, :] == 0.0)
    
    def test_detect_hands_both_wrists_visible(self, mock_detector):
        """Test hand detection when both wrists are visible."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Create body keypoints with visible wrists
        body_keypoints = np.zeros((17, 3))
        body_keypoints[9] = [200, 300, 0.8]  # Left wrist
        body_keypoints[10] = [400, 300, 0.9]  # Right wrist
        
        # Mock hand detection results
        mock_left_hand = np.random.rand(21, 3)
        mock_right_hand = np.random.rand(21, 3)
        
        with patch.object(mock_detector, '_detect_single_hand', side_effect=[mock_left_hand, mock_right_hand]):
            left_hand, right_hand = mock_detector.detect_hands(frame, body_keypoints)
        
        assert left_hand is not None
        assert right_hand is not None
        assert left_hand.shape == (21, 3)
        assert right_hand.shape == (21, 3)
    
    def test_detect_hands_only_left_wrist_visible(self, mock_detector):
        """Test hand detection when only left wrist is visible."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Create body keypoints with only left wrist visible
        body_keypoints = np.zeros((17, 3))
        body_keypoints[9] = [200, 300, 0.8]  # Left wrist visible
        body_keypoints[10] = [400, 300, 0.1]  # Right wrist not visible (low confidence)
        
        mock_left_hand = np.random.rand(21, 3)
        
        with patch.object(mock_detector, '_detect_single_hand', return_value=mock_left_hand):
            left_hand, right_hand = mock_detector.detect_hands(frame, body_keypoints)
        
        assert left_hand is not None
        assert right_hand is None
    
    def test_detect_hands_disabled(self, mock_detector):
        """Test hand detection when disabled."""
        mock_detector.hand_detector = None
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        body_keypoints = np.random.rand(17, 3)
        
        left_hand, right_hand = mock_detector.detect_hands(frame, body_keypoints)
        
        assert left_hand is None
        assert right_hand is None
    
    def test_detect_single_hand_success(self, mock_detector):
        """Test single hand detection success."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        wrist_pos = np.array([320, 240])
        
        # Mock hand detection result
        mock_result = Mock()
        mock_result.pred_instances = Mock()
        mock_result.pred_instances.keypoints = np.random.rand(1, 21, 2)
        mock_result.pred_instances.keypoint_scores = np.random.rand(1, 21) * 0.5 + 0.5
        
        with patch('bachata_buddy.core.services.mmpose_couple_detector.inference_topdown', return_value=[mock_result]):
            hand_keypoints = mock_detector._detect_single_hand(frame, wrist_pos)
        
        assert hand_keypoints is not None
        assert hand_keypoints.shape == (21, 3)
    
    def test_detect_single_hand_invalid_bbox(self, mock_detector):
        """Test single hand detection with invalid bbox."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        wrist_pos = np.array([-100, -100])  # Outside frame
        
        hand_keypoints = mock_detector._detect_single_hand(frame, wrist_pos)
        
        # Should handle gracefully
        assert hand_keypoints is None or hand_keypoints.shape == (21, 3)
    
    def test_create_person_pose_success(self, mock_detector):
        """Test creating PersonPose with successful detection."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox = (100, 100, 200, 200)
        
        # Mock successful pose estimation
        mock_body_keypoints = np.random.rand(17, 3)
        mock_body_keypoints[:, 2] = 0.8  # High confidence
        
        mock_left_hand = np.random.rand(21, 3)
        mock_right_hand = np.random.rand(21, 3)
        
        with patch.object(mock_detector, 'estimate_pose', return_value=mock_body_keypoints), \
             patch.object(mock_detector, 'detect_hands', return_value=(mock_left_hand, mock_right_hand)):
            
            person_pose = mock_detector.create_person_pose(1, bbox, frame)
        
        assert person_pose is not None
        assert person_pose.person_id == 1
        assert person_pose.body_keypoints.shape == (17, 3)
        assert person_pose.left_hand_keypoints is not None
        assert person_pose.right_hand_keypoints is not None
        assert person_pose.confidence > 0.0
    
    def test_create_person_pose_no_valid_keypoints(self, mock_detector):
        """Test creating PersonPose when no valid keypoints detected."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox = (100, 100, 200, 200)
        
        # Mock pose estimation with all low confidence
        mock_body_keypoints = np.random.rand(17, 3)
        mock_body_keypoints[:, 2] = 0.1  # All low confidence
        
        with patch.object(mock_detector, 'estimate_pose', return_value=mock_body_keypoints):
            person_pose = mock_detector.create_person_pose(1, bbox, frame)
        
        assert person_pose is None
    
    def test_create_person_pose_estimation_failure(self, mock_detector):
        """Test creating PersonPose when pose estimation fails."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox = (100, 100, 200, 200)
        
        with patch.object(mock_detector, 'estimate_pose', return_value=None):
            person_pose = mock_detector.create_person_pose(1, bbox, frame)
        
        assert person_pose is None
    
    def test_create_person_pose_without_hand_detection(self, mock_detector):
        """Test creating PersonPose with hand detection disabled."""
        mock_detector.enable_hand_detection = False
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox = (100, 100, 200, 200)
        
        mock_body_keypoints = np.random.rand(17, 3)
        mock_body_keypoints[:, 2] = 0.8
        
        with patch.object(mock_detector, 'estimate_pose', return_value=mock_body_keypoints):
            person_pose = mock_detector.create_person_pose(1, bbox, frame)
        
        assert person_pose is not None
        assert person_pose.left_hand_keypoints is None
        assert person_pose.right_hand_keypoints is None


class TestDetectCouplePoses:
    """Test frame processing pipeline."""
    
    @pytest.fixture
    def mock_detector(self):
        """Create a mock MMPoseCoupleDetector for testing."""
        with patch('bachata_buddy.core.services.mmpose_couple_detector.MMPoseCoupleDetector._init_person_detector'), \
             patch('bachata_buddy.core.services.mmpose_couple_detector.MMPoseCoupleDetector._init_pose_estimator'), \
             patch('bachata_buddy.core.services.mmpose_couple_detector.MMPoseCoupleDetector._init_hand_detector'):
            
            detector = MMPoseCoupleDetector(
                checkpoint_path="/fake/path",
                confidence_threshold=0.3,
                enable_hand_detection=True
            )
            
            # Mock the models
            detector.pose_estimator = Mock()
            detector.hand_detector = Mock()
            detector.person_detector = Mock()
            
            return detector
    
    def test_detect_couple_poses_file_not_found(self, mock_detector):
        """Test detect_couple_poses raises error for non-existent file."""
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            mock_detector.detect_couple_poses("/nonexistent/video.mp4")
    
    def test_detect_couple_poses_success(self, mock_detector, tmp_path):
        """Test successful couple pose detection on a video."""
        # Create a simple test video
        video_path = tmp_path / "test_video.mp4"
        
        # Create a simple 1-second video with 30 FPS (30 frames)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (640, 480))
        
        # Write 30 frames
        for i in range(30):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Add some variation to frames
            cv2.circle(frame, (320 + i*5, 240), 50, (255, 255, 255), -1)
            out.write(frame)
        
        out.release()
        
        # Mock the detection methods
        mock_body_keypoints = np.random.rand(17, 3)
        mock_body_keypoints[:, 2] = 0.8  # High confidence
        
        # Mock detect_persons to return two bounding boxes
        mock_bboxes = [(100, 100, 100, 100), (400, 100, 100, 100)]
        
        with patch.object(mock_detector, 'detect_persons', return_value=mock_bboxes), \
             patch.object(mock_detector, 'estimate_pose', return_value=mock_body_keypoints), \
             patch.object(mock_detector, 'detect_hands', return_value=(None, None)):
            
            # Process video at 15 FPS (should sample 15 frames from 30)
            couple_poses = mock_detector.detect_couple_poses(str(video_path), target_fps=15)
        
        # Verify results
        assert len(couple_poses) == 15  # 30 frames at 30 FPS, sampled at 15 FPS = 15 frames
        
        # Check that all frames have both dancers
        for couple_pose in couple_poses:
            assert couple_pose.has_both_dancers is True
            assert couple_pose.lead is not None
            assert couple_pose.follow is not None
            assert couple_pose.lead.person_id == 1
            assert couple_pose.follow.person_id == 2
    
    def test_detect_couple_poses_low_detection_rate(self, mock_detector, tmp_path):
        """Test detection with low couple detection rate (< 50%)."""
        # Create a test video
        video_path = tmp_path / "test_video_low_detection.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (640, 480))
        
        for i in range(30):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            out.write(frame)
        
        out.release()
        
        # Mock detection to return only one person (low detection rate)
        mock_body_keypoints = np.random.rand(17, 3)
        mock_body_keypoints[:, 2] = 0.8
        
        # Only one bbox (one dancer detected)
        mock_bboxes = [(100, 100, 100, 100)]
        
        with patch.object(mock_detector, 'detect_persons', return_value=mock_bboxes), \
             patch.object(mock_detector, 'estimate_pose', return_value=mock_body_keypoints), \
             patch.object(mock_detector, 'detect_hands', return_value=(None, None)):
            
            couple_poses = mock_detector.detect_couple_poses(str(video_path), target_fps=15)
        
        # Verify results
        assert len(couple_poses) == 15
        
        # All frames should have only one dancer
        for couple_pose in couple_poses:
            assert couple_pose.has_both_dancers is False
            assert couple_pose.detection_count == 1
    
    def test_detect_couple_poses_no_detections(self, mock_detector, tmp_path):
        """Test detection with no persons detected."""
        # Create a test video
        video_path = tmp_path / "test_video_no_detection.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (640, 480))
        
        for i in range(30):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            out.write(frame)
        
        out.release()
        
        # Mock detection to return no persons
        with patch.object(mock_detector, 'detect_persons', return_value=[]):
            couple_poses = mock_detector.detect_couple_poses(str(video_path), target_fps=15)
        
        # Verify results
        assert len(couple_poses) == 15
        
        # All frames should have no dancers
        for couple_pose in couple_poses:
            assert couple_pose.has_both_dancers is False
            assert couple_pose.detection_count == 0
            assert couple_pose.lead is None
            assert couple_pose.follow is None
    
    def test_detect_couple_poses_frame_sampling(self, mock_detector, tmp_path):
        """Test that frame sampling works correctly at different FPS."""
        # Create a test video with 60 frames at 30 FPS (2 seconds)
        video_path = tmp_path / "test_video_sampling.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (640, 480))
        
        for i in range(60):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            out.write(frame)
        
        out.release()
        
        mock_body_keypoints = np.random.rand(17, 3)
        mock_body_keypoints[:, 2] = 0.8
        mock_bboxes = [(100, 100, 100, 100), (400, 100, 100, 100)]
        
        with patch.object(mock_detector, 'detect_persons', return_value=mock_bboxes), \
             patch.object(mock_detector, 'estimate_pose', return_value=mock_body_keypoints), \
             patch.object(mock_detector, 'detect_hands', return_value=(None, None)):
            
            # Test different target FPS values
            # 30 FPS: should sample all 60 frames
            couple_poses_30 = mock_detector.detect_couple_poses(str(video_path), target_fps=30)
            assert len(couple_poses_30) == 60
            
            # Reset tracker between videos
            mock_detector.reset_tracker()
            
            # 15 FPS: should sample 30 frames (every 2nd frame)
            couple_poses_15 = mock_detector.detect_couple_poses(str(video_path), target_fps=15)
            assert len(couple_poses_15) == 30
            
            # Reset tracker between videos
            mock_detector.reset_tracker()
            
            # 10 FPS: should sample 20 frames (every 3rd frame)
            couple_poses_10 = mock_detector.detect_couple_poses(str(video_path), target_fps=10)
            assert len(couple_poses_10) == 20
    
    def test_detect_couple_poses_tracker_reset(self, mock_detector, tmp_path):
        """Test that tracker is reset when processing a new video."""
        # Create a test video
        video_path = tmp_path / "test_video_tracker.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (640, 480))
        
        for i in range(30):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            out.write(frame)
        
        out.release()
        
        # Add some tracked persons to the tracker
        mock_detector.person_tracker.tracked_persons = {
            1: {'bbox': (100, 100, 100, 100), 'missing_count': 0},
            2: {'bbox': (400, 100, 100, 100), 'missing_count': 0}
        }
        
        mock_body_keypoints = np.random.rand(17, 3)
        mock_body_keypoints[:, 2] = 0.8
        mock_bboxes = [(100, 100, 100, 100)]
        
        with patch.object(mock_detector, 'detect_persons', return_value=mock_bboxes), \
             patch.object(mock_detector, 'estimate_pose', return_value=mock_body_keypoints), \
             patch.object(mock_detector, 'detect_hands', return_value=(None, None)):
            
            # Process video - tracker should be reset
            couple_poses = mock_detector.detect_couple_poses(str(video_path), target_fps=15)
        
        # Verify tracker was used (it should have tracked the single detection)
        assert len(couple_poses) > 0
