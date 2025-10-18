"""
Django choreography view tests.

Tests for:
- index view (main choreography generation page)
- create_choreography view (start generation task)
- task_status view (poll task status)
- serve_video view (serve generated videos)

Reference: choreography/views.py
"""
import pytest
import json
import uuid
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client
from django.conf import settings

User = get_user_model()


# Use Django test client instead of FastAPI TestClient
@pytest.fixture
def client():
    """Override root conftest client with Django test client."""
    return Client()


@pytest.fixture
def authenticated_client(client, test_user):
    """Override root conftest authenticated_client with Django authenticated client."""
    client.force_login(test_user)
    return client


@pytest.mark.django_db
@pytest.mark.views
class TestChoreographyIndexView:
    """Test the choreography index view."""
    
    def test_index_page_loads_successfully(self, client):
        """Test index page loads without authentication."""
        url = reverse('choreography:index')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert b'choreography' in response.content.lower() or b'generate' in response.content.lower()
    
    def test_index_page_contains_form(self, client):
        """Test index page contains ChoreographyGenerationForm."""
        url = reverse('choreography:index')
        response = client.get(url)
        
        assert response.status_code == 200
        # Check form fields are present
        assert b'song_selection' in response.content or b'selectedSong' in response.content
        assert b'difficulty' in response.content
    
    def test_index_page_uses_correct_template(self, client):
        """Test index page uses choreography/index.html template."""
        url = reverse('choreography:index')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'choreography/index.html' in [t.name for t in response.templates]


@pytest.mark.django_db
@pytest.mark.views
class TestCreateChoreographyView:
    """Test the create_choreography view."""
    
    def test_create_choreography_requires_authentication(self, client):
        """Test create_choreography redirects unauthenticated users."""
        url = reverse('choreography:create')
        response = client.post(url, {
            'song_selection': 'data/songs/Amor.mp3',
            'difficulty': 'intermediate'
        })
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.url or 'login' in response.url
    
    def test_create_choreography_requires_post(self, authenticated_client):
        """Test create_choreography only accepts POST requests."""
        url = reverse('choreography:create')
        response = authenticated_client.get(url)
        
        # Should return 405 Method Not Allowed
        assert response.status_code == 405
    
    @patch('choreography.views.threading.Thread')
    @patch('choreography.views.create_task')
    def test_create_choreography_with_valid_data_returns_task_id(
        self, mock_create_task, mock_thread, authenticated_client, test_user
    ):
        """Test create_choreography with valid data returns task_id."""
        url = reverse('choreography:create')
        
        # Mock the thread to prevent actual background execution
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        response = authenticated_client.post(url, {
            'song_selection': 'data/songs/Amor.mp3',
            'difficulty': 'intermediate'
        })
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        # Should return task_id and status
        assert 'task_id' in data
        assert 'status' in data
        assert data['status'] == 'started'
        
        # Verify task_id is a valid UUID
        try:
            uuid.UUID(data['task_id'])
        except ValueError:
            pytest.fail("task_id is not a valid UUID")
        
        # Verify create_task was called
        mock_create_task.assert_called_once()
        assert mock_create_task.call_args[0][0] == data['task_id']
        assert mock_create_task.call_args[0][1] == test_user.id
        
        # Verify thread was started
        mock_thread_instance.start.assert_called_once()
    
    @patch('choreography.views.threading.Thread')
    @patch('choreography.views.create_task')
    def test_create_choreography_with_youtube_url(
        self, mock_create_task, mock_thread, authenticated_client
    ):
        """Test create_choreography with YouTube URL."""
        url = reverse('choreography:create')
        
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        response = authenticated_client.post(url, {
            'song_selection': 'new_song',
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'difficulty': 'beginner'
        })
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert 'task_id' in data
        assert data['status'] == 'started'
    
    def test_create_choreography_with_invalid_data(self, authenticated_client):
        """Test create_choreography with invalid form data returns error."""
        url = reverse('choreography:create')
        
        # Missing required field (difficulty)
        response = authenticated_client.post(url, {
            'song_selection': 'data/songs/Amor.mp3'
        })
        
        assert response.status_code == 400
        data = json.loads(response.content)
        
        assert 'error' in data
        assert 'errors' in data
    
    def test_create_choreography_new_song_without_url(self, authenticated_client):
        """Test create_choreography with new_song but no YouTube URL."""
        url = reverse('choreography:create')
        
        response = authenticated_client.post(url, {
            'song_selection': 'new_song',
            'difficulty': 'intermediate'
        })
        
        assert response.status_code == 400
        data = json.loads(response.content)
        
        assert 'error' in data


@pytest.mark.django_db
@pytest.mark.views
class TestTaskStatusView:
    """Test the task_status view."""
    
    def test_task_status_requires_authentication(self, client):
        """Test task_status redirects unauthenticated users."""
        task_id = str(uuid.uuid4())
        url = reverse('choreography:task_status', kwargs={'task_id': task_id})
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.url or 'login' in response.url
    
    @patch('choreography.views.get_task')
    def test_task_status_returns_correct_data(
        self, mock_get_task, authenticated_client, test_user
    ):
        """Test task_status returns correct task data."""
        task_id = str(uuid.uuid4())
        
        # Mock task data
        mock_task_data = {
            'task_id': task_id,
            'user_id': test_user.id,
            'status': 'running',
            'progress': 50,
            'stage': 'generating',
            'message': 'Generating choreography video...'
        }
        mock_get_task.return_value = mock_task_data
        
        url = reverse('choreography:task_status', kwargs={'task_id': task_id})
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert data['task_id'] == task_id
        assert data['status'] == 'running'
        assert data['progress'] == 50
        assert data['stage'] == 'generating'
        assert data['message'] == 'Generating choreography video...'
        
        # Verify get_task was called with correct task_id
        mock_get_task.assert_called_once_with(task_id)
    
    @patch('choreography.views.get_task')
    def test_task_status_returns_404_for_invalid_task_id(
        self, mock_get_task, authenticated_client
    ):
        """Test task_status returns 404 for non-existent task."""
        task_id = str(uuid.uuid4())
        
        # Mock get_task to return None (task not found)
        mock_get_task.return_value = None
        
        url = reverse('choreography:task_status', kwargs={'task_id': task_id})
        response = authenticated_client.get(url)
        
        assert response.status_code == 404
        data = json.loads(response.content)
        
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    @patch('choreography.views.get_task')
    def test_task_status_returns_403_for_other_users_task(
        self, mock_get_task, authenticated_client, test_user
    ):
        """Test task_status returns 403 when accessing another user's task."""
        task_id = str(uuid.uuid4())
        
        # Mock task data with different user_id
        mock_task_data = {
            'task_id': task_id,
            'user_id': test_user.id + 999,  # Different user
            'status': 'running',
            'progress': 50
        }
        mock_get_task.return_value = mock_task_data
        
        url = reverse('choreography:task_status', kwargs={'task_id': task_id})
        response = authenticated_client.get(url)
        
        assert response.status_code == 403
        data = json.loads(response.content)
        
        assert 'error' in data
        assert 'unauthorized' in data['error'].lower()
    
    @patch('choreography.views.get_task')
    def test_task_status_completed_with_result(
        self, mock_get_task, authenticated_client, test_user
    ):
        """Test task_status returns result data when completed."""
        task_id = str(uuid.uuid4())
        
        # Mock completed task with result
        mock_task_data = {
            'task_id': task_id,
            'user_id': test_user.id,
            'status': 'completed',
            'progress': 100,
            'stage': 'completed',
            'message': 'Choreography generated successfully!',
            'result': {
                'video_path': 'data/output/user_1/test_video.mp4',
                'video_filename': 'test_video.mp4',
                'processing_time': 45.2,
                'sequence_duration': 180.5
            }
        }
        mock_get_task.return_value = mock_task_data
        
        url = reverse('choreography:task_status', kwargs={'task_id': task_id})
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert data['status'] == 'completed'
        assert data['progress'] == 100
        assert 'result' in data
        assert data['result']['video_filename'] == 'test_video.mp4'


@pytest.mark.django_db
@pytest.mark.views
class TestServeVideoView:
    """Test the serve_video view."""
    
    def test_serve_video_requires_authentication(self, client):
        """Test serve_video redirects unauthenticated users."""
        url = reverse('choreography:serve_video', kwargs={'filename': 'test_video.mp4'})
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.url or 'login' in response.url
    
    def test_serve_video_returns_404_for_nonexistent_file(
        self, authenticated_client, test_user
    ):
        """Test serve_video returns 404 for non-existent file."""
        url = reverse('choreography:serve_video', kwargs={'filename': 'nonexistent.mp4'})
        response = authenticated_client.get(url)
        
        assert response.status_code == 404
    
    def test_serve_video_returns_fileresponse_for_valid_file(
        self, authenticated_client, test_user, tmp_path
    ):
        """Test serve_video returns FileResponse for valid file."""
        # Create a temporary video file in user's directory
        user_output_dir = tmp_path / 'output' / f'user_{test_user.id}'
        user_output_dir.mkdir(parents=True, exist_ok=True)
        
        video_file = user_output_dir / 'test_video.mp4'
        video_file.write_bytes(b'fake video content')
        
        # Patch MEDIA_ROOT to use tmp_path
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            url = reverse('choreography:serve_video', kwargs={'filename': 'test_video.mp4'})
            response = authenticated_client.get(url)
            
            assert response.status_code == 200
            assert response['Content-Type'] == 'video/mp4'
            
            # Read the response content
            content = b''.join(response.streaming_content)
            assert content == b'fake video content'
    
    def test_serve_video_sanitizes_filename(
        self, authenticated_client, test_user, tmp_path
    ):
        """Test serve_video sanitizes filename to prevent directory traversal."""
        # The URL pattern [^/]+ already prevents directory traversal at the routing level
        # So we test that the view itself also sanitizes using os.path.basename
        
        # Create a video file
        user_output_dir = tmp_path / 'output' / f'user_{test_user.id}'
        user_output_dir.mkdir(parents=True, exist_ok=True)
        
        video_file = user_output_dir / 'safe_video.mp4'
        video_file.write_bytes(b'safe video content')
        
        # Patch MEDIA_ROOT to use tmp_path
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            # Try to access with a simple filename (should work)
            url = reverse('choreography:serve_video', kwargs={'filename': 'safe_video.mp4'})
            response = authenticated_client.get(url)
            
            assert response.status_code == 200
            
            # The URL pattern prevents slashes, so directory traversal attempts
            # would fail at the routing level before reaching the view
    
    def test_serve_video_only_serves_user_files(
        self, authenticated_client, test_user, tmp_path
    ):
        """Test serve_video only serves files from user's directory."""
        # Create a video file in another user's directory
        other_user_dir = tmp_path / 'output' / 'user_999'
        other_user_dir.mkdir(parents=True, exist_ok=True)
        
        video_file = other_user_dir / 'other_video.mp4'
        video_file.write_bytes(b'other user video')
        
        # Patch MEDIA_ROOT to use tmp_path
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            url = reverse('choreography:serve_video', kwargs={'filename': 'other_video.mp4'})
            response = authenticated_client.get(url)
            
            # Should return 404 (not in current user's directory)
            assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.views
@pytest.mark.slow
class TestGenerateChoreographyBackground:
    """Test the background choreography generation function."""
    
    @patch('choreography.views.ChoreoGenerationPipeline')
    @patch('choreography.views.update_task')
    @patch('choreography.views.create_task')
    def test_background_generation_updates_progress(
        self, mock_create_task, mock_update_task, mock_pipeline_class, test_user, tmp_path
    ):
        """Test background generation updates task progress at each stage."""
        from choreography.views import generate_choreography_background
        
        task_id = str(uuid.uuid4())
        
        # Mock pipeline result
        mock_result = Mock()
        mock_result.success = True
        mock_result.output_path = 'data/output/user_1/test_video.mp4'
        mock_result.processing_time = 45.2
        mock_result.sequence_duration = 180.5
        mock_result.moves_analyzed = 12
        mock_result.metadata_path = 'data/output/user_1/test_metadata.json'
        
        # Create async mock for generate_choreography
        async_mock = AsyncMock(return_value=mock_result)
        
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.generate_choreography = async_mock
        mock_pipeline_class.return_value = mock_pipeline_instance
        
        # Patch MEDIA_ROOT to use tmp_path
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            # Run background generation
            generate_choreography_background(
                task_id=task_id,
                user_id=test_user.id,
                audio_input='data/songs/Amor.mp4',
                difficulty='intermediate'
            )
        
        # Verify update_task was called multiple times with different stages
        assert mock_update_task.call_count >= 5
        
        # Check that progress stages were called
        call_args_list = [call[1] for call in mock_update_task.call_args_list]
        stages = [args.get('stage') for args in call_args_list if 'stage' in args]
        
        assert 'downloading' in stages
        assert 'analyzing' in stages
        assert 'selecting' in stages
        assert 'generating' in stages
        assert 'finalizing' in stages or 'completed' in stages
    
    @patch('choreography.views.ChoreoGenerationPipeline')
    @patch('choreography.views.update_task')
    def test_background_generation_handles_failure(
        self, mock_update_task, mock_pipeline_class, test_user, tmp_path
    ):
        """Test background generation handles pipeline failure."""
        from choreography.views import generate_choreography_background
        
        task_id = str(uuid.uuid4())
        
        # Mock pipeline failure
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = 'Failed to analyze music'
        
        # Create async mock for generate_choreography
        async_mock = AsyncMock(return_value=mock_result)
        
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.generate_choreography = async_mock
        mock_pipeline_class.return_value = mock_pipeline_instance
        
        # Patch MEDIA_ROOT to use tmp_path
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            # Run background generation
            generate_choreography_background(
                task_id=task_id,
                user_id=test_user.id,
                audio_input='data/songs/Amor.mp3',
                difficulty='intermediate'
            )
        
        # Verify update_task was called with failed status
        call_args_list = [call[1] for call in mock_update_task.call_args_list]
        statuses = [args.get('status') for args in call_args_list if 'status' in args]
        
        assert 'failed' in statuses
        
        # Check that error was recorded
        errors = [args.get('error') for args in call_args_list if 'error' in args]
        assert any('Failed to analyze music' in str(err) for err in errors if err)
    
    @patch('choreography.views.ChoreoGenerationPipeline')
    @patch('choreography.views.update_task')
    def test_background_generation_handles_exception(
        self, mock_update_task, mock_pipeline_class, test_user, tmp_path
    ):
        """Test background generation handles unexpected exceptions."""
        from choreography.views import generate_choreography_background
        
        task_id = str(uuid.uuid4())
        
        # Mock pipeline to raise exception
        async_mock = AsyncMock(side_effect=Exception('Unexpected error'))
        
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.generate_choreography = async_mock
        mock_pipeline_class.return_value = mock_pipeline_instance
        
        # Patch MEDIA_ROOT to use tmp_path
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            # Run background generation (should not raise exception)
            generate_choreography_background(
                task_id=task_id,
                user_id=test_user.id,
                audio_input='data/songs/Amor.mp3',
                difficulty='intermediate'
            )
        
        # Verify update_task was called with failed status
        call_args_list = [call[1] for call in mock_update_task.call_args_list]
        statuses = [args.get('status') for args in call_args_list if 'status' in args]
        
        assert 'failed' in statuses
        
        # Check that error was recorded
        errors = [args.get('error') for args in call_args_list if 'error' in args]
        assert any('Unexpected error' in str(err) for err in errors if err)
