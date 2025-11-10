"""
Tests for TaskStatusUpdater

Run with:
    python manage.py test services.test_task_status_updater
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.choreography.models import ChoreographyTask
from services.task_status_updater import TaskStatusUpdater
import uuid

User = get_user_model()


class TaskStatusUpdaterTestCase(TestCase):
    """Test cases for TaskStatusUpdater"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.task_id = str(uuid.uuid4())
        self.task = ChoreographyTask.objects.create(
            task_id=self.task_id,
            user=self.user,
            status='started',
            progress=0,
            stage='initializing',
            message='Starting...'
        )
        
        self.updater = TaskStatusUpdater()
    
    def test_update_status(self):
        """Test updating task status"""
        result = self.updater.update_status(
            task_id=self.task_id,
            status='running',
            progress=50,
            stage='processing',
            message='Processing video...'
        )
        
        self.assertTrue(result)
        
        # Refresh from database
        self.task.refresh_from_db()
        
        self.assertEqual(self.task.status, 'running')
        self.assertEqual(self.task.progress, 50)
        self.assertEqual(self.task.stage, 'processing')
        self.assertEqual(self.task.message, 'Processing video...')
    
    def test_update_status_partial(self):
        """Test updating only some fields"""
        result = self.updater.update_status(
            task_id=self.task_id,
            progress=25
        )
        
        self.assertTrue(result)
        
        # Refresh from database
        self.task.refresh_from_db()
        
        self.assertEqual(self.task.progress, 25)
        self.assertEqual(self.task.status, 'started')  # Unchanged
    
    def test_update_status_clamps_progress(self):
        """Test that progress is clamped to 0-100"""
        # Test upper bound
        self.updater.update_status(task_id=self.task_id, progress=150)
        self.task.refresh_from_db()
        self.assertEqual(self.task.progress, 100)
        
        # Test lower bound
        self.updater.update_status(task_id=self.task_id, progress=-10)
        self.task.refresh_from_db()
        self.assertEqual(self.task.progress, 0)
    
    def test_update_status_nonexistent_task(self):
        """Test updating nonexistent task returns False"""
        result = self.updater.update_status(
            task_id='nonexistent-uuid',
            status='running'
        )
        
        self.assertFalse(result)
    
    def test_mark_completed(self):
        """Test marking task as completed"""
        result_data = {
            'video_url': 'gs://bucket/video.mp4',
            'thumbnail_url': 'gs://bucket/thumb.jpg',
            'duration': 180.5,
            'moves_count': 12
        }
        
        result = self.updater.mark_completed(
            task_id=self.task_id,
            result=result_data
        )
        
        self.assertTrue(result)
        
        # Refresh from database
        self.task.refresh_from_db()
        
        self.assertEqual(self.task.status, 'completed')
        self.assertEqual(self.task.progress, 100)
        self.assertEqual(self.task.stage, 'completed')
        self.assertEqual(self.task.message, 'Choreography generated successfully!')
        self.assertEqual(self.task.result, result_data)
        self.assertIsNone(self.task.error)
    
    def test_mark_completed_custom_message(self):
        """Test marking task as completed with custom message"""
        result = self.updater.mark_completed(
            task_id=self.task_id,
            result={'video_url': 'gs://bucket/video.mp4'},
            message='Custom success message'
        )
        
        self.assertTrue(result)
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.message, 'Custom success message')
    
    def test_mark_failed(self):
        """Test marking task as failed"""
        result = self.updater.mark_failed(
            task_id=self.task_id,
            error='Failed to download audio'
        )
        
        self.assertTrue(result)
        
        # Refresh from database
        self.task.refresh_from_db()
        
        self.assertEqual(self.task.status, 'failed')
        self.assertEqual(self.task.progress, 0)
        self.assertEqual(self.task.stage, 'failed')
        self.assertEqual(self.task.message, 'Job failed')
        self.assertEqual(self.task.error, 'Failed to download audio')
        self.assertIsNone(self.task.result)
    
    def test_mark_failed_custom_message(self):
        """Test marking task as failed with custom message"""
        result = self.updater.mark_failed(
            task_id=self.task_id,
            error='Network error',
            message='Custom failure message'
        )
        
        self.assertTrue(result)
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.message, 'Custom failure message')
        self.assertEqual(self.task.error, 'Network error')
    
    def test_get_task_status(self):
        """Test getting task status"""
        status = self.updater.get_task_status(self.task_id)
        
        self.assertIsNotNone(status)
        self.assertEqual(status['task_id'], self.task_id)
        self.assertEqual(status['status'], 'started')
        self.assertEqual(status['progress'], 0)
        self.assertEqual(status['stage'], 'initializing')
        self.assertEqual(status['message'], 'Starting...')
        self.assertIsNone(status['result'])
        self.assertIsNone(status['error'])
        self.assertIsNotNone(status['created_at'])
        self.assertIsNotNone(status['updated_at'])
    
    def test_get_task_status_nonexistent(self):
        """Test getting status of nonexistent task returns None"""
        status = self.updater.get_task_status('nonexistent-uuid')
        
        self.assertIsNone(status)
