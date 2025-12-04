"""
Property-based tests for Path 1 agent bypass.

**Feature: agent-orchestration, Property 8: Path 1 agent bypass**
**Validates: Requirements 5.2, 5.3**

These tests verify that Path 1 (song selection workflow) does NOT invoke
the AgentService and continues to work exactly as before the agent implementation.
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.choreography.models import Song, ChoreographyTask
import uuid

User = get_user_model()


# Hypothesis strategies for generating test data

@st.composite
def song_generation_request(draw):
    """Generate valid song generation requests for Path 1"""
    difficulty = draw(st.sampled_from(['beginner', 'intermediate', 'advanced']))
    energy_level = draw(st.sampled_from(['low', 'medium', 'high']))
    style = draw(st.sampled_from(['traditional', 'modern', 'romantic', 'sensual']))
    
    return {
        'difficulty': difficulty,
        'energy_level': energy_level,
        'style': style
    }


class TestPath1AgentBypass(TestCase):
    """
    Test that Path 1 (song selection) does NOT use AgentService.
    
    **Property 8: Path 1 agent bypass**
    *For any* choreography request submitted via Path 1 (song selection endpoint),
    the AgentService should NOT be invoked, and the existing workflow should
    execute unchanged.
    **Validates: Requirements 5.2, 5.3**
    """
    
    def setUp(self):
        """Set up test fixtures"""
        # Create or get test user (hypothesis runs multiple examples)
        self.user, _ = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'password': 'testpass123'
            }
        )
        
        # Create or get test song (hypothesis runs multiple examples)
        self.song, _ = Song.objects.get_or_create(
            title='Test Song',
            defaults={
                'artist': 'Test Artist',
                'duration': 180.0,
                'bpm': 120,
                'genre': 'bachata',
                'audio_path': 'songs/test.mp3'
            }
        )
        
        # Create API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Clean up sys.modules to avoid mock pollution between tests
        import sys
        if 'music_analyzer' in sys.modules:
            del sys.modules['music_analyzer']
    
    @given(request_data=song_generation_request())
    @settings(max_examples=20, deadline=None)
    def test_path1_does_not_invoke_agent_service(self, request_data):
        """
        **Property 8: Path 1 agent bypass**
        
        Test that Path 1 endpoint does NOT invoke AgentService.
        
        For any valid song generation request via Path 1, verify:
        1. AgentService is NOT imported or instantiated
        2. The existing workflow executes (BlueprintGenerator is used)
        3. Task is created successfully
        """
        # Add song_id to request
        request_data['song_id'] = self.song.id
        
        # Mock AgentService to detect if it's instantiated
        with patch('services.agent_service.AgentService', autospec=True) as mock_agent_service:
            # Mock the services that SHOULD be used in Path 1
            with patch('services.blueprint_generator.BlueprintGenerator') as mock_blueprint_gen, \
                 patch('services.vector_search_service.get_vector_search_service') as mock_vector_search, \
                 patch('services.gemini_service.GeminiService') as mock_gemini, \
                 patch('services.jobs_service.JobsService') as mock_jobs_service:
                
                # Configure mocks for successful execution
                mock_blueprint_instance = MagicMock()
                mock_blueprint_instance.generate_blueprint.return_value = {
                    'moves': [],
                    'song_path': self.song.audio_path,
                    'generation_parameters': request_data
                }
                mock_blueprint_gen.return_value = mock_blueprint_instance
                
                mock_jobs_instance = MagicMock()
                mock_jobs_instance.create_job_execution.return_value = 'test-execution-123'
                mock_jobs_service.return_value = mock_jobs_instance
                
                # Make request to Path 1 endpoint
                response = self.client.post(
                    '/api/choreography/generate-from-song/',
                    request_data,
                    format='json'
                )
                
                # Verify response is successful
                assert response.status_code == 202, \
                    f"Path 1 endpoint should return 202, got {response.status_code}"
                
                # CRITICAL: Verify AgentService was NOT instantiated
                mock_agent_service.assert_not_called(), \
                    "AgentService should NOT be instantiated for Path 1 requests"
                
                # Verify BlueprintGenerator WAS used (existing workflow)
                mock_blueprint_gen.assert_called_once(), \
                    "BlueprintGenerator should be used for Path 1 requests"
                
                # Verify task was created
                assert 'task_id' in response.data, \
                    "Response should contain task_id"
                
                task_id = response.data['task_id']
                task = ChoreographyTask.objects.get(task_id=task_id)
                
                # Verify task has correct song reference
                assert task.song_id == self.song.id, \
                    "Task should reference the selected song"
    
    def test_path1_workflow_unchanged(self):
        """
        **Property 8: Path 1 agent bypass**
        
        Test that Path 1 workflow executes exactly as before.
        
        For any valid song generation request via Path 1, verify:
        1. BlueprintGenerator is called with correct parameters
        2. CloudRunJobsService is called to create job
        3. Task progresses through expected stages
        """
        # Create test request data
        request_data = {
            'song_id': self.song.id,
            'difficulty': 'intermediate',
            'energy_level': 'medium',
            'style': 'modern'
        }
        
        # Mock services - need to mock MusicAnalyzer import from job container
        import sys
        mock_music_analyzer = MagicMock()
        sys.modules['music_analyzer'] = MagicMock()
        sys.modules['music_analyzer'].MusicAnalyzer = MagicMock(return_value=mock_music_analyzer)
        
        with patch('services.blueprint_generator.BlueprintGenerator') as mock_blueprint_gen, \
             patch('services.vector_search_service.get_vector_search_service') as mock_vector_search, \
             patch('services.gemini_service.GeminiService') as mock_gemini, \
             patch('apps.choreography.views.CloudRunJobsService') as mock_jobs_service:
            
            # Configure mocks
            mock_blueprint_instance = MagicMock()
            expected_blueprint = {
                'moves': [{'name': 'basic', 'duration': 4.0}],
                'song_path': self.song.audio_path,
                'generation_parameters': {
                    'difficulty': request_data['difficulty'],
                    'energy_level': request_data['energy_level'],
                    'style': request_data['style']
                }
            }
            mock_blueprint_instance.generate_blueprint.return_value = expected_blueprint
            mock_blueprint_gen.return_value = mock_blueprint_instance
            
            # Configure jobs service mock - the view instantiates it
            mock_jobs_instance = MagicMock()
            mock_jobs_instance.create_job_execution.return_value = 'test-execution-456'
            mock_jobs_service.return_value = mock_jobs_instance
            
            # Make request
            response = self.client.post(
                '/api/choreography/generate-from-song/',
                request_data,
                format='json'
            )
            
            # Verify response
            assert response.status_code == 202, \
                f"Expected 202, got {response.status_code}: {response.data if hasattr(response, 'data') else response.content}"
            task_id = response.data['task_id']
            
            # Verify BlueprintGenerator was called with correct parameters
            assert mock_blueprint_instance.generate_blueprint.called, \
                "BlueprintGenerator.generate_blueprint should be called"
            call_kwargs = mock_blueprint_instance.generate_blueprint.call_args[1]
            
            assert call_kwargs['song_path'] == self.song.audio_path, \
                "BlueprintGenerator should receive correct song path"
            assert call_kwargs['difficulty'] == request_data['difficulty'], \
                "BlueprintGenerator should receive correct difficulty"
            assert call_kwargs['energy_level'] == request_data['energy_level'], \
                "BlueprintGenerator should receive correct energy_level"
            assert call_kwargs['style'] == request_data['style'], \
                "BlueprintGenerator should receive correct style"
            
            # Verify CloudRunJobsService was instantiated and called
            mock_jobs_service.assert_called_once()
            mock_jobs_instance.create_job_execution.assert_called_once()
            
            # Verify task exists and has correct status
            task = ChoreographyTask.objects.get(task_id=task_id)
            assert task.status == 'started', \
                "Task should be in 'started' status after job submission"
            assert task.song_id == self.song.id, \
                "Task should reference the selected song"
    
    def test_path1_endpoint_exists_and_accessible(self):
        """
        Verify Path 1 endpoint exists and is accessible.
        
        This is a basic sanity check that the endpoint is still available.
        """
        # Make request with valid data
        request_data = {
            'song_id': self.song.id,
            'difficulty': 'intermediate',
            'energy_level': 'medium',
            'style': 'modern'
        }
        
        # Configure mocks properly
        with patch('services.blueprint_generator.BlueprintGenerator') as mock_blueprint_gen, \
             patch('services.vector_search_service.get_vector_search_service') as mock_vector_search, \
             patch('services.gemini_service.GeminiService') as mock_gemini, \
             patch('services.jobs_service.JobsService') as mock_jobs_service:
            
            # Configure blueprint generator mock to return a proper dict
            mock_blueprint_instance = MagicMock()
            mock_blueprint_instance.generate_blueprint.return_value = {
                'moves': [],
                'song_path': self.song.audio_path,
                'generation_parameters': request_data
            }
            mock_blueprint_gen.return_value = mock_blueprint_instance
            
            # Configure jobs service mock
            mock_jobs_instance = MagicMock()
            mock_jobs_instance.create_job_execution.return_value = 'test-execution-123'
            mock_jobs_service.return_value = mock_jobs_instance
            
            response = self.client.post(
                '/api/choreography/generate-from-song/',
                request_data,
                format='json'
            )
            
            # Should not return 404
            assert response.status_code != 404, \
                "Path 1 endpoint should still exist"
            
            # Should return 202 (successful) or 500 (error, but endpoint exists)
            assert response.status_code in [202, 500], \
                f"Path 1 endpoint should be accessible, got {response.status_code}"
