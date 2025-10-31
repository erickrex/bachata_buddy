"""
Unit tests for YOLOv8CoupleDetector service.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

from video_processing.services.yolov8_couple_detector import (
    PersonPose,
    CouplePose,
    PersonTracker,
    YOLOv8CoupleDetector
)


class TestPersonPose:
    """Test PersonPose dataclass."""
    
    def test_person_pose_creation(self):
        """Test PersonPose can be created with valid data."""
        keypoints = np.random.rand(17, 3)
        bbox = np.array([100, 100, 200, 200])
        
        pose = PersonPose(
            person_id=0,
            keypoints=keypoints,
            bbox=bbox,
            confidence=0.85,
            frame_idx=0
        )
        
        assert pose.person_id == 0
        assert pose.keypoints.shape == (17, 3)
        assert pose.bbox.shape == (4,)
        assert pose.confidence == 0.85
        assert pose.frame_idx == 0


class TestCouplePose:
    """Test CouplePose dataclass."""
    
    def test_couple_pose_with_both_dancers(self):
        """Test CouplePose with both lead and follow."""
        lead = PersonPose(
            person_id=0,
            keypoints=np.random.rand(17, 3),
            bbox=np.array([50, 50, 150, 250]),
            confidence=0.9,
            frame_idx=0
        )
        follow = PersonPose(
            person_id=1,
            keypoints=np.random.rand(17, 3),
            bbox=np.array([200, 50, 300, 250]),
            confidence=0.85,
            frame_idx=0
        )
        
        couple = CouplePose(
            lead_pose=lead,
            follow_pose=follow,
            frame_idx=0,
            timestamp=0.0,
            has_both_dancers=True
        )
        
        assert couple.lead_pose is not None
        assert couple.follow_pose is not None
        assert couple.has_both_dancers is True
    
    def test_couple_pose_with_one_dancer(self):
        """Test CouplePose with only one dancer."""
        lead = PersonPose(
            person_id=0,
            keypoints=np.random.rand(17, 3),
            bbox=np.array([50, 50, 150, 250]),
            confidence=0.9,
            frame_idx=0
        )
        
        couple = CouplePose(
            lead_pose=lead,
            follow_pose=None,
            frame_idx=0,
            timestamp=0.0,
            has_both_dancers=False
        )
        
        assert couple.lead_pose is not None
        assert couple.follow_pose is None
        assert couple.has_both_dancers is False


class TestPersonTracker:
    """Test PersonTracker class."""
    
    def test_tracker_initialization(self):
        """Test tracker initializes correctly."""
        tracker = PersonTracker(iou_threshold=0.5)
        
        assert tracker.iou_threshold == 0.5
        assert len(tracker.tracks) == 0
        assert tracker.next_id == 0
    
    def test_compute_iou_no_overlap(self):
        """Test IoU computation with no overlap."""
        tracker = PersonTracker()
        
        bbox1 = np.array([0, 0, 100, 100])
        bbox2 = np.array([200, 200, 300, 300])
        
        iou = tracker._compute_iou(bbox1, bbox2)
        assert iou == 0.0
    
    def test_compute_iou_full_overlap(self):
        """Test IoU computation with full overlap."""
        tracker = PersonTracker()
        
        bbox1 = np.array([0, 0, 100, 100])
        bbox2 = np.array([0, 0, 100, 100])
        
        iou = tracker._compute_iou(bbox1, bbox2)
        assert iou == 1.0
    
    def test_compute_iou_partial_overlap(self):
        """Test IoU computation with partial overlap."""
        tracker = PersonTracker()
        
        bbox1 = np.array([0, 0, 100, 100])
        bbox2 = np.array([50, 50, 150, 150])
        
        iou = tracker._compute_iou(bbox1, bbox2)
        assert 0.0 < iou < 1.0
    
    def test_update_with_no_detections(self):
        """Test update with no detections."""
        tracker = PersonTracker()
        
        updated = tracker.update([], frame_idx=0)
        
        assert len(updated) == 0
        assert len(tracker.tracks) == 0
    
    def test_update_creates_new_tracks(self):
        """Test update creates new tracks for first detections."""
        tracker = PersonTracker()
        
        detections = [
            PersonPose(
                person_id=-1,
                keypoints=np.random.rand(17, 3),
                bbox=np.array([50, 50, 150, 250]),
                confidence=0.9,
                frame_idx=0
            ),
            PersonPose(
                person_id=-1,
                keypoints=np.random.rand(17, 3),
                bbox=np.array([200, 50, 300, 250]),
                confidence=0.85,
                frame_idx=0
            )
        ]
        
        updated = tracker.update(detections, frame_idx=0)
        
        assert len(updated) == 2
        assert updated[0].person_id == 0
        assert updated[1].person_id == 1
        assert len(tracker.tracks) == 2
    
    def test_update_maintains_track_ids(self):
        """Test update maintains consistent track IDs across frames."""
        tracker = PersonTracker()
        
        # Frame 0: Two people
        detections_0 = [
            PersonPose(
                person_id=-1,
                keypoints=np.random.rand(17, 3),
                bbox=np.array([50, 50, 150, 250]),
                confidence=0.9,
                frame_idx=0
            ),
            PersonPose(
                person_id=-1,
                keypoints=np.random.rand(17, 3),
                bbox=np.array([200, 50, 300, 250]),
                confidence=0.85,
                frame_idx=0
            )
        ]
        updated_0 = tracker.update(detections_0, frame_idx=0)
        
        # Frame 1: Same two people, slightly moved
        detections_1 = [
            PersonPose(
                person_id=-1,
                keypoints=np.random.rand(17, 3),
                bbox=np.array([55, 55, 155, 255]),  # Moved slightly
                confidence=0.9,
                frame_idx=1
            ),
            PersonPose(
                person_id=-1,
                keypoints=np.random.rand(17, 3),
                bbox=np.array([205, 55, 305, 255]),  # Moved slightly
                confidence=0.85,
                frame_idx=1
            )
        ]
        updated_1 = tracker.update(detections_1, frame_idx=1)
        
        # IDs should be maintained
        assert updated_1[0].person_id == updated_0[0].person_id
        assert updated_1[1].person_id == updated_0[1].person_id


class TestYOLOv8CoupleDetector:
    """Test YOLOv8CoupleDetector class."""
    
    def test_initialization_default_params(self):
        """Test detector initializes with default parameters."""
        with patch('ultralytics.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_yolo.return_value = mock_model
            
            detector = YOLOv8CoupleDetector()
            
            assert detector.model_name == 'yolov8n-pose.pt'
            assert detector.confidence_threshold == 0.3
            assert detector.device == 'cpu'
            assert detector.iou_threshold == 0.5
            assert detector.max_det == 10
            mock_yolo.assert_called_once_with('yolov8n-pose.pt')
    
    def test_initialization_custom_params(self):
        """Test detector initializes with custom parameters."""
        with patch('ultralytics.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_yolo.return_value = mock_model
            
            detector = YOLOv8CoupleDetector(
                model_name='yolov8s-pose.pt',
                confidence_threshold=0.5,
                device='cuda',
                iou_threshold=0.6,
                max_det=5
            )
            
            assert detector.model_name == 'yolov8s-pose.pt'
            assert detector.confidence_threshold == 0.5
            assert detector.device == 'cuda'
            assert detector.iou_threshold == 0.6
            assert detector.max_det == 5
            mock_yolo.assert_called_once_with('yolov8s-pose.pt')
    
    def test_initialization_failure(self):
        """Test detector handles initialization failure."""
        with patch('ultralytics.YOLO') as mock_yolo:
            mock_yolo.side_effect = Exception("Model not found")
            
            with pytest.raises(RuntimeError, match="Failed to load YOLOv8 model"):
                YOLOv8CoupleDetector()
    
    def test_assign_lead_follow_no_detections(self):
        """Test lead/follow assignment with no detections."""
        with patch('ultralytics.YOLO'):
            detector = YOLOv8CoupleDetector()
            
            lead, follow = detector._assign_lead_follow([])
            
            assert lead is None
            assert follow is None
    
    def test_assign_lead_follow_one_detection(self):
        """Test lead/follow assignment with one detection."""
        with patch('ultralytics.YOLO'):
            detector = YOLOv8CoupleDetector()
            
            detection = PersonPose(
                person_id=0,
                keypoints=np.random.rand(17, 3),
                bbox=np.array([100, 100, 200, 200]),
                confidence=0.9,
                frame_idx=0
            )
            
            lead, follow = detector._assign_lead_follow([detection])
            
            assert lead is not None
            assert follow is None
    
    def test_assign_lead_follow_two_detections(self):
        """Test lead/follow assignment with two detections."""
        with patch('ultralytics.YOLO'):
            detector = YOLOv8CoupleDetector()
            
            # Left person (should be lead)
            detection1 = PersonPose(
                person_id=0,
                keypoints=np.random.rand(17, 3),
                bbox=np.array([50, 100, 150, 200]),  # x1=50
                confidence=0.9,
                frame_idx=0
            )
            
            # Right person (should be follow)
            detection2 = PersonPose(
                person_id=1,
                keypoints=np.random.rand(17, 3),
                bbox=np.array([200, 100, 300, 200]),  # x1=200
                confidence=0.85,
                frame_idx=0
            )
            
            lead, follow = detector._assign_lead_follow([detection1, detection2])
            
            assert lead is not None
            assert follow is not None
            assert lead.bbox[0] < follow.bbox[0]  # Lead is left of follow
    
    def test_detect_couple_poses_invalid_video(self):
        """Test detection with invalid video file."""
        with patch('ultralytics.YOLO'):
            detector = YOLOv8CoupleDetector()
            
            with pytest.raises(FileNotFoundError):
                detector.detect_couple_poses('nonexistent_video.mp4')
    
    @patch('cv2.VideoCapture')
    def test_detect_couple_poses_cannot_open(self, mock_cap):
        """Test detection when video cannot be opened."""
        with patch('ultralytics.YOLO'):
            detector = YOLOv8CoupleDetector()
            
            # Mock video file exists but cannot be opened
            mock_cap_instance = Mock()
            mock_cap_instance.isOpened.return_value = False
            mock_cap.return_value = mock_cap_instance
            
            with patch('pathlib.Path.exists', return_value=True):
                with pytest.raises(ValueError, match="Cannot open video"):
                    detector.detect_couple_poses('test_video.mp4')
    
    def test_detect_frame_with_mock_results(self):
        """Test frame detection with mocked YOLO results."""
        with patch('ultralytics.YOLO') as mock_yolo:
            # Setup mock model
            mock_model = Mock()
            mock_yolo.return_value = mock_model
            
            # Setup mock results
            mock_result = Mock()
            mock_result.keypoints.data.cpu.return_value.numpy.return_value = np.random.rand(2, 17, 3)
            mock_result.boxes.xyxy.cpu.return_value.numpy.return_value = np.array([
                [50, 50, 150, 250],
                [200, 50, 300, 250]
            ])
            mock_result.boxes.conf.cpu.return_value.numpy.return_value = np.array([0.9, 0.85])
            
            mock_model.return_value = [mock_result]
            
            detector = YOLOv8CoupleDetector()
            
            # Test detection
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            detections = detector._detect_frame(frame)
            
            assert len(detections) == 2
            assert detections[0].keypoints.shape == (17, 3)
            assert detections[0].bbox.shape == (4,)
            assert 0.0 <= detections[0].confidence <= 1.0


class TestIntegration:
    """Integration tests for the full detection pipeline."""
    
    @patch('cv2.VideoCapture')
    def test_full_pipeline_mock(self, mock_cap):
        """Test full detection pipeline with mocked video."""
        with patch('ultralytics.YOLO') as mock_yolo:
            # Setup mock model
            mock_model = Mock()
            mock_yolo.return_value = mock_model
            
            # Setup mock video capture
            mock_cap_instance = Mock()
            mock_cap_instance.isOpened.return_value = True
            mock_cap_instance.get.side_effect = lambda prop: {
                3: 30.0,  # FPS
                7: 90     # Total frames
            }.get(prop, 0)
            
            # Mock 3 frames
            frames = [
                (True, np.zeros((480, 640, 3), dtype=np.uint8)),
                (True, np.zeros((480, 640, 3), dtype=np.uint8)),
                (True, np.zeros((480, 640, 3), dtype=np.uint8)),
                (False, None)  # End of video
            ]
            mock_cap_instance.read.side_effect = frames
            mock_cap.return_value = mock_cap_instance
            
            # Setup mock YOLO results
            mock_result = Mock()
            mock_result.keypoints.data.cpu.return_value.numpy.return_value = np.random.rand(2, 17, 3)
            mock_result.boxes.xyxy.cpu.return_value.numpy.return_value = np.array([
                [50, 50, 150, 250],
                [200, 50, 300, 250]
            ])
            mock_result.boxes.conf.cpu.return_value.numpy.return_value = np.array([0.9, 0.85])
            mock_model.return_value = [mock_result]
            
            detector = YOLOv8CoupleDetector()
            
            with patch('pathlib.Path.exists', return_value=True):
                couple_poses = detector.detect_couple_poses('test_video.mp4', target_fps=15)
            
            # Should process 2 frames (frame skip = 2 for 30fps -> 15fps)
            assert len(couple_poses) == 2
            assert all(isinstance(cp, CouplePose) for cp in couple_poses)
