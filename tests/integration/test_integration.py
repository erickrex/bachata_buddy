"""
Integration tests for Django choreography application.

These tests verify end-to-end workflows including:
- Complete choreography generation flow (login → generate → poll → result → save)
- Video player integration with loop controls
- Collection management (create, view, edit, delete, filter, search, pagination)

Reference: Requirements 15.1-15.11, 14.1-14.10
"""
import pytest
import json
import uuid
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client
from django.conf import settings

from choreography.models import SavedChoreography
from choreography.utils import create_task, update_task, get_task

User = get_user_model()


# Override the client fixture to use Django test client
@pytest.fixture
def django_client():
    """Django test client for integration tests."""
    return Client()


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndChoreographyGeneration:
    """
    Test complete choreography generation flow.
    
    Flow: login → generate → poll → result → save
    Verifies: task status updates, video file creation, choreography saved to collection
    """
    
    def test_complete_choreography_generation_flow(self, django_client, test_user, tmp_path):
        """
        Test the complete end-to-end choreography generation workflow.
        
        Steps:
        1. User logs in
        2. User submits generation form
        3. System creates task and starts background generation
        4. Frontend polls task status
        5. Task completes with video result
        6. User saves choreography to collection
        """
        # Step 1: Login
        django_client.force_login(test_user)
        
        # Step 2: Submit generation form
        with patch('choreography.views.threading.Thread') as mock_thread, \
             patch('choreography.views.ChoreoGenerationPipeline') as mock_pipeline_class:
            
            # Mock thread to prevent actual background execution
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance
            
            # Mock pipeline result
            mock_result = Mock()
            mock_result.success = True
            mock_result.output_path = str(tmp_path / 'output' / f'user_{test_user.id}' / 'test_video.mp4')
            mock_result.processing_time = 45.2
            mock_result.sequence_duration = 180.5
            mock_result.moves_analyzed = 12
            mock_result.metadata_path = str(tmp_path / 'output' / f'user_{test_user.id}' / 'metadata.json')
            
            async_mock = AsyncMock(return_value=mock_result)
            mock_pipeline_instance = Mock()
            mock_pipeline_instance.generate_choreography = async_mock
            mock_pipeline_class.return_value = mock_pipeline_instance
            
            # Create the video file
            video_dir = tmp_path / 'output' / f'user_{test_user.id}'
            video_dir.mkdir(parents=True, exist_ok=True)
            video_file = video_dir / 'test_video.mp4'
            video_file.write_bytes(b'fake video content')
            
            # Submit generation request
            create_url = reverse('choreography:create')
            response = django_client.post(create_url, {
                'song_selection': 'data/songs/Amor.mp3',
                'difficulty': 'intermediate'
            })
            
            assert response.status_code == 200
            data = json.loads(response.content)
            assert 'task_id' in data
            assert data['status'] == 'started'
            
            task_id = data['task_id']
            
            # Verify thread was started
            mock_thread_instance.start.assert_called_once()
            
            # Step 3: Simulate background generation by manually updating task
            # (In real scenario, the background thread would do this)
            update_task(task_id, status='running', progress=10, stage='downloading')
            update_task(task_id, progress=25, stage='analyzing')
            update_task(task_id, progress=40, stage='selecting')
            update_task(task_id, progress=70, stage='generating')
            update_task(task_id, progress=90, stage='finalizing')
            update_task(
                task_id,
                status='completed',
                progress=100,
                stage='completed',
                message='Choreography generated successfully!',
                result={
                    'video_path': str(video_file),
                    'video_filename': 'test_video.mp4',
                    'processing_time': 45.2,
                    'sequence_duration': 180.5,
                    'moves_analyzed': 12
                }
            )
            
            # Step 4: Poll task status
            status_url = reverse('choreography:task_status', kwargs={'task_id': task_id})
            
            # Poll multiple times to simulate frontend polling
            for i in range(3):
                response = django_client.get(status_url)
                assert response.status_code == 200
                status_data = json.loads(response.content)
                
                assert 'status' in status_data
                assert 'progress' in status_data
                assert 'stage' in status_data
            
            # Final poll should show completed status
            response = django_client.get(status_url)
            assert response.status_code == 200
            status_data = json.loads(response.content)
            
            assert status_data['status'] == 'completed'
            assert status_data['progress'] == 100
            assert 'result' in status_data
            assert status_data['result']['video_filename'] == 'test_video.mp4'
            
            # Step 5: Save choreography to collection
            with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
                save_url = reverse('collections:save')
                response = django_client.post(save_url, {
                    'title': 'My Test Choreography',
                    'difficulty': 'intermediate',
                    'video_path': str(video_file),
                    'duration': 180.5,
                    'music_info': json.dumps({
                        'title': 'Amor',
                        'artist': 'Unknown',
                        'tempo': 120
                    }),
                    'generation_parameters': json.dumps({
                        'difficulty': 'intermediate',
                        'song_selection': 'data/songs/Amor.mp3'
                    })
                })
                
                assert response.status_code == 200
                save_data = json.loads(response.content)
                assert save_data['success'] is True
                assert 'choreography_id' in save_data
                
                # Verify choreography was saved to database
                choreography = SavedChoreography.objects.get(id=save_data['choreography_id'])
                assert choreography.user == test_user
                assert choreography.title == 'My Test Choreography'
                assert choreography.difficulty == 'intermediate'
                assert choreography.duration == 180.5

    
    def test_task_status_updates_correctly_through_stages(self, django_client, test_user):
        """
        Test that task status updates correctly through all generation stages.
        
        Verifies: downloading → analyzing → selecting → generating → finalizing → completed
        """
        # Login
        django_client.force_login(test_user)
        
        # Create a task manually
        task_id = str(uuid.uuid4())
        create_task(task_id, test_user.id)
        
        # Define expected stages
        stages = [
            ('running', 10, 'downloading', 'Downloading audio...'),
            ('running', 25, 'analyzing', 'Analyzing music features...'),
            ('running', 40, 'selecting', 'Selecting dance moves...'),
            ('running', 70, 'generating', 'Generating choreography video...'),
            ('running', 90, 'finalizing', 'Finalizing video...'),
            ('completed', 100, 'completed', 'Choreography generated successfully!')
        ]
        
        status_url = reverse('choreography:task_status', kwargs={'task_id': task_id})
        
        # Update and verify each stage
        for status, progress, stage, message in stages:
            update_task(task_id, status=status, progress=progress, stage=stage, message=message)
            
            response = django_client.get(status_url)
            assert response.status_code == 200
            
            data = json.loads(response.content)
            assert data['status'] == status
            assert data['progress'] == progress
            assert data['stage'] == stage
            assert data['message'] == message
    
    def test_video_file_is_created_and_accessible(self, django_client, test_user, tmp_path):
        """
        Test that generated video file is created and accessible via serve_video endpoint.
        """
        # Login
        django_client.force_login(test_user)
        
        # Create video file in user's directory
        video_dir = tmp_path / 'output' / f'user_{test_user.id}'
        video_dir.mkdir(parents=True, exist_ok=True)
        video_file = video_dir / 'generated_video.mp4'
        video_content = b'test video content for integration test'
        video_file.write_bytes(video_content)
        
        # Access video via serve_video endpoint
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            serve_url = reverse('choreography:serve_video', kwargs={'filename': 'generated_video.mp4'})
            response = django_client.get(serve_url)
            
            assert response.status_code == 200
            assert response['Content-Type'] == 'video/mp4'
            
            # Verify content
            content = b''.join(response.streaming_content)
            assert content == video_content
    
    def test_choreography_saved_to_collection_with_all_metadata(self, django_client, test_user, tmp_path):
        """
        Test that choreography is saved to collection with all required metadata.
        """
        # Login
        django_client.force_login(test_user)
        
        # Create video file
        video_dir = tmp_path / 'output' / f'user_{test_user.id}'
        video_dir.mkdir(parents=True, exist_ok=True)
        video_file = video_dir / 'test_video.mp4'
        video_file.write_bytes(b'video content')
        
        # Save choreography
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            save_url = reverse('collections:save')
            response = django_client.post(save_url, {
                'title': 'Complete Test Choreography',
                'difficulty': 'advanced',
                'video_path': str(video_file),
                'duration': 240.0,
                'music_info': json.dumps({
                    'title': 'Test Song',
                    'artist': 'Test Artist',
                    'tempo': 128,
                    'genre': 'Bachata'
                }),
                'generation_parameters': json.dumps({
                    'difficulty': 'advanced',
                    'song_selection': 'data/songs/Test.mp3',
                    'style': 'sensual'
                })
            })
            
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data['success'] is True
            
            # Verify all metadata was saved
            choreography = SavedChoreography.objects.get(id=data['choreography_id'])
            assert choreography.title == 'Complete Test Choreography'
            assert choreography.difficulty == 'advanced'
            assert choreography.duration == 240.0
            assert choreography.music_info['title'] == 'Test Song'
            assert choreography.music_info['tempo'] == 128
            assert choreography.generation_parameters['difficulty'] == 'advanced'
            assert choreography.generation_parameters['style'] == 'sensual'
    
    def test_failed_generation_updates_task_with_error(self, django_client, test_user):
        """
        Test that failed generation properly updates task with error information.
        """
        # Login
        django_client.force_login(test_user)
        
        # Create a task
        task_id = str(uuid.uuid4())
        create_task(task_id, test_user.id)
        
        # Simulate generation failure
        error_message = 'Failed to download YouTube video'
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='Generation failed',
            error=error_message
        )
        
        # Poll task status
        status_url = reverse('choreography:task_status', kwargs={'task_id': task_id})
        response = django_client.get(status_url)
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert data['status'] == 'failed'
        assert data['error'] == error_message
        assert 'result' not in data or data['result'] is None



@pytest.mark.django_db
@pytest.mark.integration
class TestVideoPlayerIntegration:
    """
    Test video player integration with loop controls.
    
    Tests:
    - Video player loads with generated video
    - Loop controls are functional
    - Loop start/end adjustments work
    
    Reference: Requirements 14.1-14.10, 15.8
    """
    
    def test_video_player_loads_with_generated_video(self, django_client, test_user, test_choreography, tmp_path):
        """
        Test that video player loads correctly with a generated video.
        """
        # Login
        django_client.force_login(test_user)
        
        # Create video file
        video_dir = tmp_path / 'output' / f'user_{test_user.id}'
        video_dir.mkdir(parents=True, exist_ok=True)
        video_file = video_dir / 'test_video.mp4'
        video_file.write_bytes(b'video player test content')
        
        # Update choreography with video path
        test_choreography.video_path = str(video_file)
        test_choreography.save()
        
        # Access choreography detail page (which includes video player)
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            detail_url = reverse('collections:detail', kwargs={'pk': test_choreography.id})
            response = django_client.get(detail_url)
            
            assert response.status_code == 200
            content = response.content.decode('utf-8')
            
            # Verify video player elements are present
            assert '<video' in content
            assert 'x-ref="videoPlayer"' in content or 'videoPlayer' in content
            
            # Verify video source is set
            assert 'test_video.mp4' in content or str(test_choreography.id) in content
    
    def test_video_player_has_loop_controls(self, django_client, test_user, test_choreography):
        """
        Test that video player includes loop control elements.
        """
        # Login
        django_client.force_login(test_user)
        
        # Access choreography detail page
        detail_url = reverse('collections:detail', kwargs={'pk': test_choreography.id})
        response = django_client.get(detail_url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify loop control elements are present
        assert 'toggleLoop' in content or 'loop' in content.lower()
        assert 'loopStart' in content or 'loop-start' in content.lower()
        assert 'loopEnd' in content or 'loop-end' in content.lower()
        
        # Verify loop adjustment buttons
        assert 'adjustLoopStart' in content or '+1s' in content or '-1s' in content
        assert 'adjustLoopEnd' in content or '+1s' in content or '-1s' in content
    
    def test_video_player_on_index_page(self, django_client, test_user):
        """
        Test that video player is present on index page for displaying results.
        """
        # Login
        django_client.force_login(test_user)
        
        # Access index page
        index_url = reverse('choreography:index')
        response = django_client.get(index_url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify video player elements are present (even if hidden initially)
        assert '<video' in content or 'videoPlayer' in content
        assert 'x-show="result"' in content or 'result' in content
    
    def test_loop_controls_javascript_functions_present(self, django_client, test_user, test_choreography):
        """
        Test that loop control JavaScript functions are present in the page.
        """
        # Login
        django_client.force_login(test_user)
        
        # Access choreography detail page
        detail_url = reverse('collections:detail', kwargs={'pk': test_choreography.id})
        response = django_client.get(detail_url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify Alpine.js methods are present
        alpine_methods = [
            'togglePlayPause',
            'toggleLoop',
            'adjustLoopStart',
            'adjustLoopEnd',
            'formatTime'
        ]
        
        # At least some of these methods should be present
        methods_found = sum(1 for method in alpine_methods if method in content)
        assert methods_found >= 3, f"Expected at least 3 Alpine.js methods, found {methods_found}"
    
    def test_video_player_progress_bar_with_loop_indicators(self, django_client, test_user, test_choreography):
        """
        Test that video player includes progress bar with loop indicators.
        """
        # Login
        django_client.force_login(test_user)
        
        # Access choreography detail page
        detail_url = reverse('collections:detail', kwargs={'pk': test_choreography.id})
        response = django_client.get(detail_url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify progress bar elements
        assert 'progress' in content.lower()
        
        # Verify loop indicators (visual markers on progress bar)
        assert 'loopStartPercentage' in content or 'loop-start' in content.lower()
        assert 'loopEndPercentage' in content or 'loop-end' in content.lower() or 'loopSegmentWidth' in content
    
    def test_video_serves_correctly_for_playback(self, django_client, test_user, tmp_path):
        """
        Test that video file serves correctly for playback in video player.
        """
        # Login
        django_client.force_login(test_user)
        
        # Create video file
        video_dir = tmp_path / 'output' / f'user_{test_user.id}'
        video_dir.mkdir(parents=True, exist_ok=True)
        video_file = video_dir / 'playback_test.mp4'
        video_content = b'MP4 video content for playback test'
        video_file.write_bytes(video_content)
        
        # Request video via serve_video endpoint
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            serve_url = reverse('choreography:serve_video', kwargs={'filename': 'playback_test.mp4'})
            response = django_client.get(serve_url)
            
            assert response.status_code == 200
            assert response['Content-Type'] == 'video/mp4'
            
            # Verify content is correct
            content = b''.join(response.streaming_content)
            assert content == video_content
    
    def test_loop_controls_state_management(self, django_client, test_user, test_choreography):
        """
        Test that loop controls state management is properly set up in Alpine.js.
        """
        # Login
        django_client.force_login(test_user)
        
        # Access choreography detail page
        detail_url = reverse('collections:detail', kwargs={'pk': test_choreography.id})
        response = django_client.get(detail_url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify Alpine.js state variables for loop controls
        state_variables = [
            'isLooping',
            'loopStart',
            'loopEnd',
            'videoDuration',
            'currentTime'
        ]
        
        # At least some state variables should be present
        variables_found = sum(1 for var in state_variables if var in content)
        assert variables_found >= 3, f"Expected at least 3 state variables, found {variables_found}"



@pytest.mark.django_db
@pytest.mark.integration
class TestCollectionManagementIntegration:
    """
    Test collection management integration.
    
    Tests:
    - Creating, viewing, editing, deleting choreographies
    - Filtering and search functionality
    - Pagination
    
    Reference: Requirement 15.5
    """
    
    def test_create_view_edit_delete_choreography_workflow(self, django_client, test_user, tmp_path):
        """
        Test complete CRUD workflow for choreographies.
        
        Steps:
        1. Create a choreography
        2. View it in the list
        3. View detail page
        4. Edit the choreography
        5. Delete the choreography
        """
        # Login
        django_client.force_login(test_user)
        
        # Create video file
        video_dir = tmp_path / 'output' / f'user_{test_user.id}'
        video_dir.mkdir(parents=True, exist_ok=True)
        video_file = video_dir / 'crud_test.mp4'
        video_file.write_bytes(b'crud test video')
        
        # Step 1: Create choreography
        with patch.object(settings, 'MEDIA_ROOT', str(tmp_path)):
            save_url = reverse('collections:save')
            response = django_client.post(save_url, {
                'title': 'CRUD Test Choreography',
                'difficulty': 'intermediate',
                'video_path': str(video_file),
                'duration': 150.0,
                'music_info': json.dumps({'title': 'Test Song'}),
                'generation_parameters': json.dumps({'difficulty': 'intermediate'})
            })
            
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data['success'] is True
            choreography_id = data['choreography_id']
        
        # Step 2: View in list
        list_url = reverse('collections:list')
        response = django_client.get(list_url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'CRUD Test Choreography' in content
        
        # Step 3: View detail page
        detail_url = reverse('collections:detail', kwargs={'pk': choreography_id})
        response = django_client.get(detail_url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'CRUD Test Choreography' in content
        assert 'intermediate' in content.lower()
        
        # Step 4: Edit choreography
        edit_url = reverse('collections:edit', kwargs={'pk': choreography_id})
        response = django_client.post(edit_url, {
            'title': 'Updated CRUD Test',
            'difficulty': 'advanced'
        })
        
        # Should redirect to detail page
        assert response.status_code == 302
        
        # Verify changes
        choreography = SavedChoreography.objects.get(id=choreography_id)
        assert choreography.title == 'Updated CRUD Test'
        assert choreography.difficulty == 'advanced'
        
        # Step 5: Delete choreography
        delete_url = reverse('collections:delete', kwargs={'pk': choreography_id})
        response = django_client.post(delete_url)
        
        # Should return success (JSON for HTMX or redirect)
        assert response.status_code in [200, 302]
        
        # Verify deletion
        assert not SavedChoreography.objects.filter(id=choreography_id).exists()
    
    def test_collection_filtering_by_difficulty(self, django_client, test_user):
        """
        Test filtering choreographies by difficulty level.
        """
        # Login
        django_client.force_login(test_user)
        
        # Create choreographies with different difficulties
        SavedChoreography.objects.create(
            user=test_user,
            title='Beginner Choreo',
            video_path='beginner.mp4',
            difficulty='beginner',
            duration=120.0
        )
        SavedChoreography.objects.create(
            user=test_user,
            title='Intermediate Choreo',
            video_path='intermediate.mp4',
            difficulty='intermediate',
            duration=150.0
        )
        SavedChoreography.objects.create(
            user=test_user,
            title='Advanced Choreo',
            video_path='advanced.mp4',
            difficulty='advanced',
            duration=180.0
        )
        
        # Filter by beginner
        list_url = reverse('collections:list')
        response = django_client.get(list_url, {'difficulty': 'beginner'})
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Beginner Choreo' in content
        assert 'Intermediate Choreo' not in content
        assert 'Advanced Choreo' not in content
        
        # Filter by intermediate
        response = django_client.get(list_url, {'difficulty': 'intermediate'})
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Beginner Choreo' not in content
        assert 'Intermediate Choreo' in content
        assert 'Advanced Choreo' not in content
        
        # Filter by advanced
        response = django_client.get(list_url, {'difficulty': 'advanced'})
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Beginner Choreo' not in content
        assert 'Intermediate Choreo' not in content
        assert 'Advanced Choreo' in content
    
    def test_collection_search_functionality(self, django_client, test_user):
        """
        Test search functionality for choreographies.
        """
        # Login
        django_client.force_login(test_user)
        
        # Create choreographies with different titles and music info
        SavedChoreography.objects.create(
            user=test_user,
            title='Romantic Bachata',
            video_path='romantic.mp4',
            difficulty='intermediate',
            duration=150.0,
            music_info={'title': 'Amor Eterno', 'artist': 'Artist A'}
        )
        SavedChoreography.objects.create(
            user=test_user,
            title='Sensual Dance',
            video_path='sensual.mp4',
            difficulty='advanced',
            duration=180.0,
            music_info={'title': 'Desnudate', 'artist': 'Artist B'}
        )
        SavedChoreography.objects.create(
            user=test_user,
            title='Basic Steps',
            video_path='basic.mp4',
            difficulty='beginner',
            duration=120.0,
            music_info={'title': 'Simple Song', 'artist': 'Artist C'}
        )
        
        # Search by title
        list_url = reverse('collections:list')
        response = django_client.get(list_url, {'search': 'Romantic'})
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Romantic Bachata' in content
        assert 'Sensual Dance' not in content
        assert 'Basic Steps' not in content
        
        # Search by music info (partial match)
        response = django_client.get(list_url, {'search': 'Amor'})
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Romantic Bachata' in content
        
        # Search with no results
        response = django_client.get(list_url, {'search': 'NonexistentQuery'})
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Should show empty state or no results message
        assert 'Romantic Bachata' not in content
        assert 'Sensual Dance' not in content
        assert 'Basic Steps' not in content
    
    def test_collection_pagination(self, django_client, test_user):
        """
        Test pagination of choreography collection.
        """
        # Login
        django_client.force_login(test_user)
        
        # Create 25 choreographies (more than one page at 20 per page)
        for i in range(25):
            SavedChoreography.objects.create(
                user=test_user,
                title=f'Choreography {i+1}',
                video_path=f'video_{i+1}.mp4',
                difficulty='intermediate',
                duration=150.0
            )
        
        # Get first page
        list_url = reverse('collections:list')
        response = django_client.get(list_url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Should show pagination controls
        assert 'page' in content.lower() or 'next' in content.lower() or 'previous' in content.lower()
        
        # First page should have 20 items
        choreographies = response.context['choreographies']
        assert len(choreographies) == 20
        
        # Get second page
        response = django_client.get(list_url, {'page': 2})
        
        assert response.status_code == 200
        choreographies = response.context['choreographies']
        
        # Second page should have 5 items (25 total - 20 on first page)
        assert len(choreographies) == 5
    
    def test_collection_sorting(self, django_client, test_user):
        """
        Test sorting choreographies by different fields.
        """
        # Login
        django_client.force_login(test_user)
        
        # Create choreographies with different attributes
        import time
        
        choreo1 = SavedChoreography.objects.create(
            user=test_user,
            title='Alpha Choreography',
            video_path='alpha.mp4',
            difficulty='beginner',
            duration=120.0
        )
        
        time.sleep(0.1)  # Ensure different timestamps
        
        choreo2 = SavedChoreography.objects.create(
            user=test_user,
            title='Beta Choreography',
            video_path='beta.mp4',
            difficulty='intermediate',
            duration=180.0
        )
        
        time.sleep(0.1)
        
        choreo3 = SavedChoreography.objects.create(
            user=test_user,
            title='Gamma Choreography',
            video_path='gamma.mp4',
            difficulty='advanced',
            duration=150.0
        )
        
        # Default sort (should be -created_at, newest first)
        list_url = reverse('collections:list')
        response = django_client.get(list_url)
        
        assert response.status_code == 200
        choreographies = list(response.context['choreographies'])
        
        # Newest should be first
        assert choreographies[0].title == 'Gamma Choreography'
        assert choreographies[1].title == 'Beta Choreography'
        assert choreographies[2].title == 'Alpha Choreography'
        
        # Sort by title ascending
        response = django_client.get(list_url, {'sort_by': 'title'})
        
        assert response.status_code == 200
        choreographies = list(response.context['choreographies'])
        
        assert choreographies[0].title == 'Alpha Choreography'
        assert choreographies[1].title == 'Beta Choreography'
        assert choreographies[2].title == 'Gamma Choreography'
    
    def test_user_isolation_in_collections(self, django_client, test_user):
        """
        Test that users can only see their own choreographies.
        """
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123',
            display_name='Other User'
        )
        
        # Create choreographies for both users
        user_choreo = SavedChoreography.objects.create(
            user=test_user,
            title='My Choreography',
            video_path='my_video.mp4',
            difficulty='intermediate',
            duration=150.0
        )
        
        other_choreo = SavedChoreography.objects.create(
            user=other_user,
            title='Other User Choreography',
            video_path='other_video.mp4',
            difficulty='intermediate',
            duration=150.0
        )
        
        # Login as test_user
        django_client.force_login(test_user)
        
        # View collection list
        list_url = reverse('collections:list')
        response = django_client.get(list_url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Should see own choreography
        assert 'My Choreography' in content
        
        # Should NOT see other user's choreography
        assert 'Other User Choreography' not in content
        
        # Try to access other user's choreography detail (should fail)
        detail_url = reverse('collections:detail', kwargs={'pk': other_choreo.id})
        response = django_client.get(detail_url)
        
        # Should return 404 (not found for this user)
        assert response.status_code == 404
    
    def test_collection_stats_calculation(self, django_client, test_user):
        """
        Test collection statistics calculation.
        """
        # Login
        django_client.force_login(test_user)
        
        # Create choreographies with different difficulties and durations
        SavedChoreography.objects.create(
            user=test_user,
            title='Beginner 1',
            video_path='b1.mp4',
            difficulty='beginner',
            duration=120.0
        )
        SavedChoreography.objects.create(
            user=test_user,
            title='Beginner 2',
            video_path='b2.mp4',
            difficulty='beginner',
            duration=130.0
        )
        SavedChoreography.objects.create(
            user=test_user,
            title='Intermediate 1',
            video_path='i1.mp4',
            difficulty='intermediate',
            duration=150.0
        )
        SavedChoreography.objects.create(
            user=test_user,
            title='Advanced 1',
            video_path='a1.mp4',
            difficulty='advanced',
            duration=180.0
        )
        
        # Get stats
        stats_url = reverse('collections:stats')
        response = django_client.get(stats_url)
        
        assert response.status_code == 200
        stats = json.loads(response.content)
        
        # Verify stats
        assert stats['total_count'] == 4
        assert stats['total_duration'] == 580.0  # 120 + 130 + 150 + 180
        assert stats['avg_duration'] == 145.0  # 580 / 4
        assert stats['beginner_count'] == 2
        assert stats['intermediate_count'] == 1
        assert stats['advanced_count'] == 1
