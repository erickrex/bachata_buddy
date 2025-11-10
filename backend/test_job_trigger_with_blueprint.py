#!/usr/bin/env python
"""
Test: Both Paths Successfully Trigger Job Container with BLUEPRINT_JSON

This test verifies that:
1. Path 1 (Select Song) generates a blueprint and triggers the job with BLUEPRINT_JSON
2. Path 2 (Describe Choreo) generates a blueprint and triggers the job with BLUEPRINT_JSON
3. The job container receives the BLUEPRINT_JSON environment variable
4. The BLUEPRINT_JSON contains all required fields for video assembly

Usage:
    # Run with pytest
    cd bachata_buddy/backend
    uv run pytest test_job_trigger_with_blueprint.py -v

    # Run standalone
    uv run --directory bachata_buddy/backend python test_job_trigger_with_blueprint.py
"""
import os
import sys
import json
import uuid
from unittest.mock import patch, MagicMock, call
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

# Mock music_analyzer module before Django setup (it's in job container, not backend)
sys.modules['music_analyzer'] = MagicMock()

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
import django
django.setup()

from apps.choreography.models import ChoreographyTask, Song, Blueprint

User = get_user_model()


class JobTriggerWithBlueprintTests(TestCase):
    """Test that both paths successfully trigger job container with BLUEPRINT_JSON"""
    
    def setUp(self):
        """Set up test client, user, and song"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test song
        self.song = Song.objects.create(
            title='Test Song',
            artist='Test Artist',
            duration=180.0,
            bpm=120,
            genre='bachata',
            audio_path='data/songs/test.mp3'
        )
        
        # Standard mock blueprint
        self.mock_blueprint = {
            "task_id": "test-task-id",
            "audio_path": "data/songs/test.mp3",
            "audio_tempo": 120,
            "moves": [
                {
                    "clip_id": "move_1",
                    "video_path": "data/Bachata_steps/basic_steps/basic_1.mp4",
                    "start_time": 0.0,
                    "duration": 8.0,
                    "transition_type": "cut",
                    "original_duration": 8.0,
                    "trim_start": 0.0,
                    "trim_end": 0.0,
                    "volume_adjustment": 1.0
                }
            ],
            "total_duration": 180.0,
            "difficulty_level": "intermediate",
            "generation_timestamp": "2025-11-09T00:00:00Z",
            "generation_parameters": {
                "energy_level": "medium",
                "style": "modern",
                "user_id": self.user.id
            },
            "output_config": {
                "output_path": "data/output/choreography_test.mp4",
                "output_format": "mp4",
                "video_codec": "libx264",
                "audio_codec": "aac"
            }
        }
    
    def _validate_blueprint_json_env_var(self, blueprint_json_str: str) -> dict:
        """
        Validate that BLUEPRINT_JSON environment variable contains valid JSON
        with all required fields
        
        Args:
            blueprint_json_str: The BLUEPRINT_JSON string passed to job
        
        Returns:
            Parsed blueprint dict
        """
        # Parse JSON
        try:
            blueprint = json.loads(blueprint_json_str)
        except json.JSONDecodeError as e:
            self.fail(f"BLUEPRINT_JSON is not valid JSON: {e}")
        
        # Validate required fields
        required_fields = [
            'task_id',
            'audio_path',
            'audio_tempo',
            'moves',
            'total_duration',
            'difficulty_level',
            'generation_parameters',
            'output_config'
        ]
        
        for field in required_fields:
            self.assertIn(field, blueprint, f"BLUEPRINT_JSON missing required field: {field}")
        
        # Validate moves array
        self.assertIsInstance(blueprint['moves'], list, "moves must be a list")
        self.assertGreater(len(blueprint['moves']), 0, "moves array cannot be empty")
        
        # Validate first move has required fields
        move = blueprint['moves'][0]
        required_move_fields = ['clip_id', 'video_path', 'start_time', 'duration', 'transition_type']
        for field in required_move_fields:
            self.assertIn(field, move, f"Move missing required field: {field}")
        
        # Validate output_config
        self.assertIn('output_path', blueprint['output_config'], "output_config missing output_path")
        
        return blueprint
    
    @patch('apps.choreography.views.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.vector_search_service.VectorSearchService')
    @patch('services.gemini_service.GeminiService')
    def test_path1_triggers_job_with_blueprint_json(self, mock_gemini_class, mock_vector_class, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test Path 1 (Select Song) triggers job with BLUEPRINT_JSON environment variable"""
        # Setup mocks
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = self.mock_blueprint.copy()
        
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution-path1"
        
        # Make request to Path 1 endpoint
        data = {
            'song_id': self.song.id,
            'difficulty': 'intermediate',
            'energy_level': 'medium',
            'style': 'modern'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task_id', response.data)
        
        # Verify job service was called
        mock_jobs_service.create_job_execution.assert_called_once()
        
        # Get the call arguments
        call_args = mock_jobs_service.create_job_execution.call_args
        task_id = call_args[1]['task_id']
        user_id = call_args[1]['user_id']
        parameters = call_args[1]['parameters']
        
        # Verify task_id and user_id
        self.assertEqual(user_id, self.user.id)
        self.assertIsNotNone(task_id)
        
        # Verify parameters contains blueprint_json
        self.assertIn('blueprint_json', parameters, "parameters missing blueprint_json")
        
        # Validate BLUEPRINT_JSON content
        blueprint = self._validate_blueprint_json_env_var(parameters['blueprint_json'])
        
        # Verify blueprint matches expected structure
        self.assertEqual(blueprint['audio_path'], 'data/songs/test.mp3')
        self.assertEqual(blueprint['difficulty_level'], 'intermediate')
        self.assertEqual(blueprint['generation_parameters']['energy_level'], 'medium')
        self.assertEqual(blueprint['generation_parameters']['style'], 'modern')
        
        print("✅ Path 1 successfully triggers job with BLUEPRINT_JSON")
        print(f"   Task ID: {task_id}")
        print(f"   Blueprint size: {len(parameters['blueprint_json'])} bytes")
        print(f"   Moves count: {len(blueprint['moves'])}")
    
    @patch('apps.choreography.views.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.vector_search_service.VectorSearchService')
    @patch('services.gemini_service.GeminiService')
    def test_path2_triggers_job_with_blueprint_json(self, mock_gemini_class, mock_vector_class, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test Path 2 (Describe Choreo) triggers job with BLUEPRINT_JSON environment variable"""
        # Setup mocks
        mock_gemini = mock_gemini_class.return_value
        mock_parsed = MagicMock()
        mock_parsed.to_dict.return_value = {
            'difficulty': 'beginner',
            'energy_level': 'low',
            'style': 'romantic'
        }
        mock_gemini.parse_choreography_request.return_value = mock_parsed
        
        # Create blueprint with AI metadata
        ai_blueprint = self.mock_blueprint.copy()
        ai_blueprint['difficulty_level'] = 'beginner'
        ai_blueprint['generation_parameters'] = {
            'energy_level': 'low',
            'style': 'romantic',
            'user_id': self.user.id,
            'ai_mode': True,
            'original_query': 'Create a romantic beginner choreography'
        }
        
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = ai_blueprint
        
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution-path2"
        
        # Make request to Path 2 endpoint
        data = {
            'query': 'Create a romantic beginner choreography'
        }
        response = self.client.post('/api/choreography/generate-with-ai/', data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task_id', response.data)
        
        # Verify job service was called
        mock_jobs_service.create_job_execution.assert_called_once()
        
        # Get the call arguments
        call_args = mock_jobs_service.create_job_execution.call_args
        task_id = call_args[1]['task_id']
        user_id = call_args[1]['user_id']
        parameters = call_args[1]['parameters']
        
        # Verify task_id and user_id
        self.assertEqual(user_id, self.user.id)
        self.assertIsNotNone(task_id)
        
        # Verify parameters contains blueprint_json
        self.assertIn('blueprint_json', parameters, "parameters missing blueprint_json")
        
        # Validate BLUEPRINT_JSON content
        blueprint = self._validate_blueprint_json_env_var(parameters['blueprint_json'])
        
        # Verify blueprint matches expected structure
        self.assertEqual(blueprint['audio_path'], 'data/songs/test.mp3')
        self.assertEqual(blueprint['difficulty_level'], 'beginner')
        self.assertEqual(blueprint['generation_parameters']['energy_level'], 'low')
        self.assertEqual(blueprint['generation_parameters']['style'], 'romantic')
        
        # Verify AI-specific metadata
        self.assertTrue(blueprint['generation_parameters']['ai_mode'])
        self.assertEqual(blueprint['generation_parameters']['original_query'], 'Create a romantic beginner choreography')
        
        print("✅ Path 2 successfully triggers job with BLUEPRINT_JSON")
        print(f"   Task ID: {task_id}")
        print(f"   Blueprint size: {len(parameters['blueprint_json'])} bytes")
        print(f"   Moves count: {len(blueprint['moves'])}")
        print(f"   AI mode: {blueprint['generation_parameters']['ai_mode']}")
    
    @patch('apps.choreography.views.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.vector_search_service.VectorSearchService')
    @patch('services.gemini_service.GeminiService')
    def test_both_paths_use_same_blueprint_format(self, mock_gemini_class, mock_vector_class, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test that both paths pass BLUEPRINT_JSON in the same format"""
        # Setup mocks
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = self.mock_blueprint.copy()
        
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution"
        
        # Test Path 1
        data1 = {
            'song_id': self.song.id,
            'difficulty': 'intermediate'
        }
        response1 = self.client.post('/api/choreography/generate-from-song/', data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_202_ACCEPTED)
        
        # Get Path 1 blueprint_json
        call_args1 = mock_jobs_service.create_job_execution.call_args
        blueprint_json1 = call_args1[1]['parameters']['blueprint_json']
        blueprint1 = json.loads(blueprint_json1)
        
        # Reset mock
        mock_jobs_service.create_job_execution.reset_mock()
        
        # Test Path 2 (setup Gemini mock for AI query parsing)
        mock_gemini = mock_gemini_class.return_value
        mock_parsed = MagicMock()
        mock_parsed.to_dict.return_value = {
            'difficulty': 'intermediate',
            'energy_level': 'medium',
            'style': 'modern'
        }
        mock_gemini.parse_choreography_request.return_value = mock_parsed
        
        data2 = {
            'query': 'Create an intermediate choreography'
        }
        response2 = self.client.post('/api/choreography/generate-with-ai/', data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_202_ACCEPTED)
        
        # Get Path 2 blueprint_json
        call_args2 = mock_jobs_service.create_job_execution.call_args
        blueprint_json2 = call_args2[1]['parameters']['blueprint_json']
        blueprint2 = json.loads(blueprint_json2)
        
        # Compare blueprint structures (ignore AI-specific fields)
        core_fields = [
            'task_id',
            'audio_path',
            'audio_tempo',
            'moves',
            'total_duration',
            'difficulty_level',
            'generation_parameters',
            'output_config'
        ]
        
        for field in core_fields:
            self.assertIn(field, blueprint1, f"Path 1 missing field: {field}")
            self.assertIn(field, blueprint2, f"Path 2 missing field: {field}")
            
            # Verify same type
            self.assertEqual(
                type(blueprint1[field]),
                type(blueprint2[field]),
                f"Field '{field}' has different types between paths"
            )
        
        # Verify move structure is the same
        move1 = blueprint1['moves'][0]
        move2 = blueprint2['moves'][0]
        
        move_fields = set(move1.keys())
        self.assertEqual(move_fields, set(move2.keys()), "Move structures differ between paths")
        
        print("✅ Both paths use the same BLUEPRINT_JSON format")
        print(f"   Common fields: {len(core_fields)}")
        print(f"   Move fields: {len(move_fields)}")
    
    @patch('apps.choreography.views.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.vector_search_service.VectorSearchService')
    @patch('services.gemini_service.GeminiService')
    def test_blueprint_json_is_valid_json_string(self, mock_gemini_class, mock_vector_class, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test that BLUEPRINT_JSON is passed as a valid JSON string (not dict)"""
        # Setup mocks
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = self.mock_blueprint.copy()
        
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution"
        
        # Make request
        data = {
            'song_id': self.song.id,
            'difficulty': 'intermediate'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        
        # Get blueprint_json
        call_args = mock_jobs_service.create_job_execution.call_args
        blueprint_json = call_args[1]['parameters']['blueprint_json']
        
        # Verify it's a string
        self.assertIsInstance(blueprint_json, str, "BLUEPRINT_JSON must be a string")
        
        # Verify it's valid JSON
        try:
            parsed = json.loads(blueprint_json)
            self.assertIsInstance(parsed, dict, "Parsed BLUEPRINT_JSON must be a dict")
        except json.JSONDecodeError as e:
            self.fail(f"BLUEPRINT_JSON is not valid JSON: {e}")
        
        print("✅ BLUEPRINT_JSON is passed as a valid JSON string")
        print(f"   String length: {len(blueprint_json)} bytes")
        print(f"   Parsed successfully: {len(parsed)} top-level fields")
    
    @patch('apps.choreography.views.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.vector_search_service.VectorSearchService')
    @patch('services.gemini_service.GeminiService')
    def test_job_receives_all_required_env_vars(self, mock_gemini_class, mock_vector_class, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test that job receives all required environment variables"""
        # Setup mocks
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = self.mock_blueprint.copy()
        
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution"
        
        # Make request
        data = {
            'song_id': self.song.id,
            'difficulty': 'intermediate'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        
        # Verify job service was called with correct parameters
        call_args = mock_jobs_service.create_job_execution.call_args
        task_id = call_args[1]['task_id']
        user_id = call_args[1]['user_id']
        parameters = call_args[1]['parameters']
        
        # Verify all required parameters are present
        self.assertIsNotNone(task_id, "task_id is required")
        self.assertIsNotNone(user_id, "user_id is required")
        self.assertIn('blueprint_json', parameters, "blueprint_json is required")
        
        # Verify no old parameters are passed
        old_params = ['audio_input', 'difficulty', 'energy_level', 'style', 'ai_mode']
        for param in old_params:
            self.assertNotIn(param, parameters, f"Old parameter '{param}' should not be passed")
        
        print("✅ Job receives all required environment variables")
        print(f"   TASK_ID: {task_id}")
        print(f"   USER_ID: {user_id}")
        print(f"   BLUEPRINT_JSON: {len(parameters['blueprint_json'])} bytes")
        print(f"   Old parameters removed: {', '.join(old_params)}")


def run_tests():
    """Run tests standalone"""
    import unittest
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(JobTriggerWithBlueprintTests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 80)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        print("\n✅ Both paths successfully trigger job container with BLUEPRINT_JSON")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
