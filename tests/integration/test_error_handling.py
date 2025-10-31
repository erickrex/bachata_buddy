"""
Tests for error handling and edge cases in Django views.

Requirements: 8.3
- Test invalid form submissions
- Test unauthorized access attempts
- Test missing resources (404)
- Test task failures
"""
import pytest
import json
import uuid
from unittest.mock import patch, Mock
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from choreography.models import SavedChoreography
from instructors.models import ClassPlan
from common.exceptions import (
    YouTubeDownloadError,
    MusicAnalysisError,
    VideoGenerationError
)

User = get_user_model()


@pytest.fixture
def django_client():
    """Create a Django test client"""
    return Client()


@pytest.fixture
def authenticated_django_client(django_user):
    """Create an authenticated Django test client"""
    client = Client()
    client.force_login(django_user)
    return client


@pytest.mark.django_db
class TestChoreographyErrorHandling:
    """Test error handling in choreography views"""
    
    def test_create_choreography_invalid_form(self, authenticated_django_client):
        """Test create_choreography with invalid form data"""
        # Missing required fields
        response = authenticated_django_client.post(reverse('choreography:create'), {
            'song_selection': '',  # Empty
            'difficulty': 'invalid_difficulty'  # Invalid choice
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'errors' in data
    
    def test_create_choreography_missing_youtube_url(self, authenticated_django_client):
        """Test create_choreography with new_song but no YouTube URL"""
        response = authenticated_django_client.post(reverse('choreography:create'), {
            'song_selection': 'new_song',
            'difficulty': 'beginner',
            # youtube_url is missing
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_create_choreography_unauthenticated(self, django_client):
        """Test create_choreography requires authentication"""
        response = django_client.post(reverse('choreography:create'), {
            'song_selection': 'Amor.mp3',
            'difficulty': 'beginner'
        })
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login/' in response.url
    
    def test_task_status_invalid_task_id_format(self, authenticated_django_client):
        """Test task_status with invalid UUID format"""
        response = authenticated_django_client.get(reverse('choreography:task_status', args=['invalid-uuid']))
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'Invalid task ID format' in data['error']
    
    def test_task_status_not_found(self, authenticated_django_client):
        """Test task_status with non-existent task"""
        fake_task_id = str(uuid.uuid4())
        response = authenticated_django_client.get(reverse('choreography:task_status', args=[fake_task_id]))
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
        assert 'Task not found' in data['error']
    
    def test_task_status_unauthorized_access(self, authenticated_django_client, django_user):
        """Test task_status with another user's task"""
        from choreography.utils import create_task
        
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123',
            display_name='Other User'
        )
        
        # Create task for other user
        task_id = str(uuid.uuid4())
        create_task(task_id, other_user.id)
        
        # Try to access with django_user
        response = authenticated_django_client.get(reverse('choreography:task_status', args=[task_id]))
        
        assert response.status_code == 403
        data = response.json()
        assert 'error' in data
        assert 'Unauthorized' in data['error']
    
    def test_serve_video_invalid_file_type(self, authenticated_django_client):
        """Test serve_video with invalid file type"""
        response = authenticated_django_client.get(reverse('choreography:serve_video', args=['malicious.exe']))
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'Invalid file type' in data['error']
    
    def test_serve_video_path_traversal_attempt(self, authenticated_django_client):
        """Test serve_video blocks path traversal attempts"""
        # Use a filename with path traversal characters that will pass URL routing
        response = authenticated_django_client.get(reverse('choreography:serve_video', args=['..%2F..%2F..%2Fetc%2Fpasswd']))
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_serve_video_not_found(self, authenticated_django_client):
        """Test serve_video with non-existent video"""
        response = authenticated_django_client.get(reverse('choreography:serve_video', args=['nonexistent.mp4']))
        
        assert response.status_code == 404
    
    def test_serve_video_unauthenticated(self, django_client):
        """Test serve_video requires authentication"""
        response = django_client.get(reverse('choreography:serve_video', args=['test.mp4']))
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login/' in response.url


@pytest.mark.django_db
class TestCollectionErrorHandling:
    """Test error handling in collection views"""
    
    def test_save_choreography_invalid_form(self, authenticated_django_client):
        """Test save_choreography with invalid form data"""
        response = authenticated_django_client.post(reverse('collections:save'), {
            'title': '',  # Empty title (required)
            'difficulty': 'invalid'  # Invalid choice
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'success' in data
        assert data['success'] is False
        assert 'errors' in data
    
    def test_save_choreography_invalid_duration(self, authenticated_django_client):
        """Test save_choreography with invalid duration value"""
        response = authenticated_django_client.post(reverse('collections:save'), {
            'title': 'Test Choreography',
            'difficulty': 'beginner',
            'video_path': '/path/to/video.mp4',
            'duration': 'not-a-number'  # Invalid
        })
        
        # Should handle gracefully and default to 0
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_save_choreography_invalid_json(self, authenticated_django_client):
        """Test save_choreography with invalid JSON in music_info"""
        response = authenticated_django_client.post(reverse('collections:save'), {
            'title': 'Test Choreography',
            'difficulty': 'beginner',
            'video_path': '/path/to/video.mp4',
            'duration': '120',
            'music_info': 'not-valid-json'  # Invalid JSON
        })
        
        # Should handle gracefully and use empty dict
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    def test_choreography_detail_not_found(self, authenticated_django_client):
        """Test choreography_detail with non-existent choreography"""
        fake_uuid = uuid.uuid4()
        response = authenticated_django_client.get(reverse('collections:detail', args=[fake_uuid]))
        
        assert response.status_code == 404
    
    def test_choreography_detail_unauthorized(self, authenticated_django_client):
        """Test choreography_detail with another user's choreography"""
        # Create another user and their choreography
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123',
            display_name='Other User'
        )
        
        choreography = SavedChoreography.objects.create(
            user=other_user,
            title='Other User Choreography',
            difficulty='beginner',
            video_path='/path/to/video.mp4',
            duration=120
        )
        
        # Try to access with django_user
        response = authenticated_django_client.get(reverse('collections:detail', args=[choreography.id]))
        
        assert response.status_code == 404  # get_object_or_404 returns 404 for unauthorized
    
    def test_choreography_delete_unauthorized(self, authenticated_django_client):
        """Test choreography_delete with another user's choreography"""
        # Create another user and their choreography
        other_user = User.objects.create_user(
            username='otheruser2',
            email='other2@example.com',
            password='testpass123',
            display_name='Other User'
        )
        
        choreography = SavedChoreography.objects.create(
            user=other_user,
            title='Other User Choreography',
            difficulty='beginner',
            video_path='/path/to/video.mp4',
            duration=120
        )
        
        # Try to delete with django_user
        response = authenticated_django_client.post(reverse('collections:delete', args=[choreography.id]))
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestUserErrorHandling:
    """Test error handling in user views"""
    
    def test_register_duplicate_email(self, django_client, django_user):
        """Test registration with duplicate email"""
        response = django_client.post(reverse('users:register'), {
            'email': django_user.email,  # Already exists
            'password1': 'newpass123',
            'password2': 'newpass123',
            'display_name': 'New User'
        })
        
        # Should show form with errors
        assert response.status_code == 200
        assert b'error' in response.content or b'already' in response.content.lower()
    
    def test_register_password_mismatch(self, django_client):
        """Test registration with mismatched passwords"""
        response = django_client.post(reverse('users:register'), {
            'email': 'newuser@example.com',
            'password1': 'password123',
            'password2': 'different123',  # Mismatch
            'display_name': 'New User'
        })
        
        # Should show form with errors
        assert response.status_code == 200
        assert b'error' in response.content or b'match' in response.content.lower()
    
    def test_update_preferences_invalid_json(self, authenticated_django_client):
        """Test update_preferences with invalid JSON"""
        response = authenticated_django_client.post(
            reverse('users:update_preferences'),
            data='not-valid-json',
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'Invalid JSON' in data['error']
    
    def test_update_preferences_invalid_keys(self, authenticated_django_client):
        """Test update_preferences with invalid preference keys"""
        response = authenticated_django_client.post(
            reverse('users:update_preferences'),
            data=json.dumps({'invalid_key': True}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'Invalid preference keys' in data['error']
    
    def test_update_preferences_invalid_value_type(self, authenticated_django_client):
        """Test update_preferences with invalid value type"""
        response = authenticated_django_client.post(
            reverse('users:update_preferences'),
            data=json.dumps({'auto_save_choreographies': 'not-a-boolean'}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'must be a boolean' in data['error']


@pytest.mark.django_db
class TestInstructorErrorHandling:
    """Test error handling in instructor views"""
    
    def test_instructor_views_require_instructor_role(self, authenticated_django_client):
        """Test instructor views require is_instructor=True"""
        # django_user is not an instructor
        response = authenticated_django_client.get(reverse('instructors:dashboard'))
        
        # Should raise PermissionDenied (403)
        assert response.status_code == 403
    
    def test_class_plan_detail_unauthorized(self):
        """Test class_plan_detail with another instructor's plan"""
        # Create instructor users
        instructor1 = User.objects.create_user(
            username='instructor1',
            email='instructor1@example.com',
            password='testpass123',
            display_name='Instructor 1',
            is_instructor=True
        )
        
        instructor2 = User.objects.create_user(
            username='instructor2',
            email='instructor2@example.com',
            password='testpass123',
            display_name='Instructor 2',
            is_instructor=True
        )
        
        # Create class plan for instructor1
        class_plan = ClassPlan.objects.create(
            instructor=instructor1,
            title='Instructor 1 Plan',
            difficulty_level='beginner'
        )
        
        # Try to access with instructor2
        client = Client()
        client.force_login(instructor2)
        response = client.get(reverse('instructors:class_plan_detail', args=[class_plan.id]))
        
        assert response.status_code == 404
    
    def test_sequence_add_missing_choreography_id(self):
        """Test sequence_add with missing choreography_id"""
        # Create instructor and class plan
        instructor = User.objects.create_user(
            username='instructor3',
            email='instructor3@example.com',
            password='testpass123',
            display_name='Instructor',
            is_instructor=True
        )
        
        class_plan = ClassPlan.objects.create(
            instructor=instructor,
            title='Test Plan',
            difficulty_level='beginner'
        )
        
        client = Client()
        client.force_login(instructor)
        response = client.post(reverse('instructors:sequence_add', args=[class_plan.id]), {
            # choreography_id is missing
            'notes': 'Test notes'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'Choreography ID is required' in data['error']
    
    def test_sequence_add_invalid_estimated_time(self):
        """Test sequence_add with invalid estimated_time"""
        # Create instructor, class plan, and choreography
        instructor = User.objects.create_user(
            username='instructor4',
            email='instructor4@example.com',
            password='testpass123',
            display_name='Instructor',
            is_instructor=True
        )
        
        class_plan = ClassPlan.objects.create(
            instructor=instructor,
            title='Test Plan',
            difficulty_level='beginner'
        )
        
        choreography = SavedChoreography.objects.create(
            user=instructor,
            title='Test Choreography',
            difficulty='beginner',
            video_path='/path/to/video.mp4',
            duration=120
        )
        
        client = Client()
        client.force_login(instructor)
        response = client.post(reverse('instructors:sequence_add', args=[class_plan.id]), {
            'choreography_id': str(choreography.id),
            'estimated_time': 'not-a-number'  # Invalid
        })
        
        # Should handle gracefully and redirect (or return JSON if HTMX)
        # The view redirects by default when not an HTMX request
        assert response.status_code in [200, 302]
        if response.status_code == 200:
            data = response.json()
            assert data['success'] is True


@pytest.mark.django_db
class TestBackgroundTaskErrors:
    """Test error handling in background tasks"""
    
    @patch('choreography.views.ChoreoGenerationPipeline')
    def test_youtube_download_error(self, mock_pipeline, django_user):
        """Test background task handles YouTubeDownloadError"""
        from choreography.views import generate_choreography_background
        from choreography.utils import get_task, create_task
        
        # Mock pipeline to raise YouTubeDownloadError
        mock_instance = Mock()
        mock_pipeline.return_value = mock_instance
        
        async def mock_generate(*args, **kwargs):
            raise YouTubeDownloadError(
                message="Video unavailable",
                url="https://youtube.com/watch?v=test"
            )
        
        mock_instance.generate_choreography = mock_generate
        
        # Create task
        task_id = str(uuid.uuid4())
        create_task(task_id, django_user.id)
        
        # Run background function
        generate_choreography_background(
            task_id=task_id,
            user_id=django_user.id,
            audio_input="https://youtube.com/watch?v=test",
            difficulty="beginner",
            auto_save=False
        )
        
        # Check task status
        task_data = get_task(task_id)
        assert task_data['status'] == 'failed'
        assert 'YouTube download failed' in task_data['error']
    
    @patch('choreography.views.ChoreoGenerationPipeline')
    def test_music_analysis_error(self, mock_pipeline, django_user):
        """Test background task handles MusicAnalysisError"""
        from choreography.views import generate_choreography_background
        from choreography.utils import get_task, create_task
        
        # Mock pipeline to raise MusicAnalysisError
        mock_instance = Mock()
        mock_pipeline.return_value = mock_instance
        
        async def mock_generate(*args, **kwargs):
            raise MusicAnalysisError(
                message="Unable to analyze audio",
                audio_path="/path/to/audio.mp3"
            )
        
        mock_instance.generate_choreography = mock_generate
        
        # Create task
        task_id = str(uuid.uuid4())
        create_task(task_id, django_user.id)
        
        # Run background function
        generate_choreography_background(
            task_id=task_id,
            user_id=django_user.id,
            audio_input="Amor.mp3",
            difficulty="beginner",
            auto_save=False
        )
        
        # Check task status
        task_data = get_task(task_id)
        assert task_data['status'] == 'failed'
        assert 'Music analysis failed' in task_data['error']
    
    @patch('choreography.views.ChoreoGenerationPipeline')
    def test_video_generation_error(self, mock_pipeline, django_user):
        """Test background task handles VideoGenerationError"""
        from choreography.views import generate_choreography_background
        from choreography.utils import get_task, create_task
        
        # Mock pipeline to raise VideoGenerationError
        mock_instance = Mock()
        mock_pipeline.return_value = mock_instance
        
        async def mock_generate(*args, **kwargs):
            raise VideoGenerationError(
                message="FFmpeg encoding failed"
            )
        
        mock_instance.generate_choreography = mock_generate
        
        # Create task
        task_id = str(uuid.uuid4())
        create_task(task_id, django_user.id)
        
        # Run background function
        generate_choreography_background(
            task_id=task_id,
            user_id=django_user.id,
            audio_input="Amor.mp3",
            difficulty="beginner",
            auto_save=False
        )
        
        # Check task status
        task_data = get_task(task_id)
        assert task_data['status'] == 'failed'
        assert 'Video generation failed' in task_data['error']
    
    @patch('choreography.views.ChoreoGenerationPipeline')
    def test_unexpected_error(self, mock_pipeline, django_user):
        """Test background task handles unexpected errors"""
        from choreography.views import generate_choreography_background
        from choreography.utils import get_task, create_task
        
        # Mock pipeline to raise unexpected error
        mock_instance = Mock()
        mock_pipeline.return_value = mock_instance
        
        async def mock_generate(*args, **kwargs):
            raise RuntimeError("Unexpected error occurred")
        
        mock_instance.generate_choreography = mock_generate
        
        # Create task
        task_id = str(uuid.uuid4())
        create_task(task_id, django_user.id)
        
        # Run background function
        generate_choreography_background(
            task_id=task_id,
            user_id=django_user.id,
            audio_input="Amor.mp3",
            difficulty="beginner",
            auto_save=False
        )
        
        # Check task status
        task_data = get_task(task_id)
        assert task_data['status'] == 'failed'
        assert 'Unexpected error' in task_data['error']
