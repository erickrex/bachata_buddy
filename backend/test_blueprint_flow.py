"""
Integration tests for blueprint-based choreography generation flow.

Tests both user paths:
- Path 1: Select Song (/api/choreography/generate-from-song)
- Path 2: Describe Choreo (/api/choreography/generate-with-ai)

Tests complete API → Job flow including:
- Blueprint generation
- Job execution
- Storage operations (local and GCS)
- Error scenarios
"""
import json
import uuid
import os
import sys
from unittest.mock import patch, MagicMock, Mock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.choreography.models import ChoreographyTask, Song, Blueprint

# Mock music_analyzer module since it's in the job container
sys.modules['music_analyzer'] = MagicMock()

User = get_user_model()


class BlueprintFlowPath1Tests(TestCase):
    """Test Path 1: Select Song → Blueprint Generation → Job Execution"""
    
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
                    "transition_type": "cut"
                }
            ],
            "total_duration": 180.0,
            "difficulty_level": "intermediate",
            "generation_parameters": {
                "energy_level": "medium",
                "style": "modern",
                "user_id": self.user.id
            },
            "output_config": {
                "output_path": "data/output/choreography_test.mp4",
                "output_format": "mp4"
            }
        }
    
    @patch('services.blueprint_generator.BlueprintGenerator')
    def test_path1_complete_flow_success(self, mock_blueprint_gen_class):
        """Test complete Path 1 flow: song selection → blueprint → job"""
        # Setup mock blueprint generator
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = self.mock_blueprint
        
        # Make request
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
        self.assertIn('song', response.data)
        self.assertEqual(response.data['song']['id'], self.song.id)
        self.assertEqual(response.data['status'], 'started')
        
        # Verify task created
        task_id = response.data['task_id']
        task = ChoreographyTask.objects.get(task_id=task_id)
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.song, self.song)
        self.assertEqual(task.status, 'started')
        
        # Verify blueprint created
        blueprint = Blueprint.objects.get(task=task)
        self.assertIsNotNone(blueprint.blueprint_json)
        self.assertEqual(blueprint.blueprint_json['audio_path'], 'data/songs/test.mp3')
        
        # Verify job execution name was stored
        self.assertIsNotNone(task.job_execution_name)
        self.assertIn('local-dev-execution', task.job_execution_name)
    
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.gemini_service.GeminiService')
    @patch('services.vector_search_service.VectorSearchService')
    def test_path1_blueprint_generation_failure(self, mock_vector_search, mock_gemini, mock_blueprint_gen_class):
        """Test Path 1 handles blueprint generation failure"""
        # Mock blueprint generation failure
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.side_effect = Exception("Blueprint generation failed")
        
        # Make request
        data = {
            'song_id': self.song.id,
            'difficulty': 'intermediate'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        # Verify error response
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
        
        # Verify task marked as failed
        tasks = ChoreographyTask.objects.filter(user=self.user)
        self.assertEqual(tasks.count(), 1)
        task = tasks.first()
        self.assertEqual(task.status, 'failed')
        self.assertIn('Blueprint generation failed', task.error)
    
    @patch('services.jobs_service.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.gemini_service.GeminiService')
    @patch('services.vector_search_service.VectorSearchService')
    
    def test_path1_job_submission_failure(self, mock_vector_search, mock_gemini, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test Path 1 handles job submission failure"""
        # Mock successful blueprint generation
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = self.mock_blueprint
        
        # Mock job submission failure
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.side_effect = Exception("Job submission failed")
        
        # Make request
        data = {
            'song_id': self.song.id,
            'difficulty': 'beginner'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        # Verify error response
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
        
        # Verify task marked as failed
        tasks = ChoreographyTask.objects.filter(user=self.user)
        task = tasks.first()
        self.assertEqual(task.status, 'failed')
        self.assertIn('Job submission failed', task.error)
    
    def test_path1_invalid_song_id(self):
        """Test Path 1 with non-existent song ID"""
        data = {
            'song_id': 99999,
            'difficulty': 'intermediate'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('song_id', response.data)
    
    @patch('services.jobs_service.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.gemini_service.GeminiService')
    @patch('services.vector_search_service.VectorSearchService')
    
    def test_path1_blueprint_schema_validation(self, mock_vector_search, mock_gemini, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test Path 1 generates valid blueprint schema"""
        # Mock blueprint generation with complete schema
        complete_blueprint = {
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
        
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = complete_blueprint
        
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution"
        
        # Make request
        data = {
            'song_id': self.song.id,
            'difficulty': 'intermediate'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        # Verify blueprint has required fields
        task_id = response.data['task_id']
        task = ChoreographyTask.objects.get(task_id=task_id)
        blueprint = Blueprint.objects.get(task=task)
        
        # Validate blueprint schema
        bp = blueprint.blueprint_json
        self.assertIn('task_id', bp)
        self.assertIn('audio_path', bp)
        self.assertIn('moves', bp)
        self.assertIn('output_config', bp)
        self.assertIsInstance(bp['moves'], list)


class BlueprintFlowPath2Tests(TestCase):
    """Test Path 2: Describe Choreo → Query Parsing → Blueprint Generation → Job Execution"""
    
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
                    "transition_type": "cut"
                }
            ],
            "total_duration": 180.0,
            "difficulty_level": "beginner",
            "generation_parameters": {
                "energy_level": "low",
                "style": "romantic",
                "user_id": self.user.id,
                "ai_mode": True,
                "original_query": "Create a romantic beginner choreography"
            },
            "output_config": {
                "output_path": "data/output/choreography_test.mp4",
                "output_format": "mp4"
            }
        }
    
    @patch('apps.choreography.views.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.gemini_service.GeminiService')
    @patch('services.vector_search_service.VectorSearchService')
    
    def test_path2_complete_flow_success(self, mock_vector_search_class, mock_gemini_class, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test complete Path 2 flow: query → parsing → blueprint → job"""
        # Mock query parsing
        mock_gemini = mock_gemini_class.return_value
        mock_parsed = MagicMock()
        mock_parsed.to_dict.return_value = {
            'difficulty': 'beginner',
            'energy_level': 'low',
            'style': 'romantic',
            'tempo': 'slow'
        }
        mock_gemini.parse_choreography_request.return_value = mock_parsed
        
        # Mock blueprint generation
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = self.mock_blueprint
        
        # Mock job service
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution-name"
        
        # Make request
        data = {
            'query': 'Create a romantic beginner choreography'
        }
        response = self.client.post('/api/choreography/generate-with-ai/', data, format='json')
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task_id', response.data)
        self.assertEqual(response.data['status'], 'started')
        
        # Verify task created
        task_id = response.data['task_id']
        task = ChoreographyTask.objects.get(task_id=task_id)
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.status, 'started')
        
        # Verify blueprint created with AI metadata
        blueprint = Blueprint.objects.get(task=task)
        self.assertIsNotNone(blueprint.blueprint_json)
        bp = blueprint.blueprint_json
        self.assertTrue(bp['generation_parameters']['ai_mode'])
        self.assertEqual(bp['generation_parameters']['original_query'], 'Create a romantic beginner choreography')
        
        # Verify job execution called
        mock_jobs_service.create_job_execution.assert_called_once()
    
    @patch('services.gemini_service.GeminiService')
    def test_path2_query_parsing_failure(self, mock_gemini_class):
        """Test Path 2 handles query parsing failure"""
        # Mock query parsing failure
        mock_gemini = mock_gemini_class.return_value
        mock_gemini.parse_choreography_request.side_effect = Exception("Could not parse query")
        
        # Make request
        data = {
            'query': 'Invalid query that cannot be parsed'
        }
        response = self.client.post('/api/choreography/generate-with-ai/', data, format='json')
        
        # Verify error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.gemini_service.GeminiService')
    @patch('services.vector_search_service.VectorSearchService')
    
    def test_path2_blueprint_generation_failure(self, mock_vector_search_class, mock_gemini_class, mock_blueprint_gen_class):
        """Test Path 2 handles blueprint generation failure"""
        # Mock successful query parsing
        mock_gemini = mock_gemini_class.return_value
        mock_parsed = MagicMock()
        mock_parsed.to_dict.return_value = {
            'difficulty': 'intermediate',
            'energy_level': 'medium',
            'style': 'modern'
        }
        mock_gemini.parse_choreography_request.return_value = mock_parsed
        
        # Mock blueprint generation failure
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.side_effect = Exception("Blueprint generation failed")
        
        # Make request
        data = {
            'query': 'Create an intermediate choreography'
        }
        response = self.client.post('/api/choreography/generate-with-ai/', data, format='json')
        
        # Verify error response
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
        
        # Verify task marked as failed
        tasks = ChoreographyTask.objects.filter(user=self.user)
        task = tasks.first()
        self.assertEqual(task.status, 'failed')
        self.assertIn('Blueprint generation failed', task.error)
    
    def test_path2_empty_query(self):
        """Test Path 2 with empty query"""
        data = {
            'query': ''
        }
        response = self.client.post('/api/choreography/generate-with-ai/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('query', response.data)


class BlueprintSchemaConsistencyTests(TestCase):
    """Test that both paths generate the same blueprint schema"""
    
    def setUp(self):
        """Set up test client, user, and song"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.song = Song.objects.create(
            title='Test Song',
            artist='Test Artist',
            duration=180.0,
            bpm=120,
            genre='bachata',
            audio_path='data/songs/test.mp3'
        )
        
        # Standard mock blueprint with complete schema
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
                "audio_codec": "aac",
                "video_bitrate": "2M",
                "audio_bitrate": "128k",
                "frame_rate": 30,
                "transition_duration": 0.5,
                "fade_duration": 0.3,
                "add_audio_overlay": True,
                "normalize_audio": True
            }
        }
    
    def _validate_blueprint_schema(self, blueprint, path_name):
        """
        Validate that a blueprint conforms to the expected schema.
        
        Args:
            blueprint: Blueprint JSON to validate
            path_name: Name of the path (for error messages)
        """
        # Required top-level fields
        required_fields = [
            'task_id',
            'audio_path',
            'moves',
            'total_duration',
            'difficulty_level',
            'generation_timestamp',
            'generation_parameters',
            'output_config'
        ]
        
        for field in required_fields:
            self.assertIn(
                field, 
                blueprint,
                f"{path_name}: Missing required field '{field}'"
            )
        
        # Validate types
        self.assertIsInstance(blueprint['task_id'], str, f"{path_name}: task_id must be string")
        self.assertIsInstance(blueprint['audio_path'], str, f"{path_name}: audio_path must be string")
        self.assertIsInstance(blueprint['moves'], list, f"{path_name}: moves must be list")
        self.assertIsInstance(blueprint['total_duration'], (int, float), f"{path_name}: total_duration must be number")
        self.assertIsInstance(blueprint['difficulty_level'], str, f"{path_name}: difficulty_level must be string")
        self.assertIsInstance(blueprint['generation_parameters'], dict, f"{path_name}: generation_parameters must be dict")
        self.assertIsInstance(blueprint['output_config'], dict, f"{path_name}: output_config must be dict")
        
        # Validate moves array is not empty
        self.assertGreater(len(blueprint['moves']), 0, f"{path_name}: moves array cannot be empty")
        
        # Validate each move has required fields
        required_move_fields = [
            'clip_id',
            'video_path',
            'start_time',
            'duration',
            'transition_type'
        ]
        
        for i, move in enumerate(blueprint['moves']):
            for field in required_move_fields:
                self.assertIn(
                    field,
                    move,
                    f"{path_name}: Move {i} missing required field '{field}'"
                )
            
            # Validate move field types
            self.assertIsInstance(move['clip_id'], str, f"{path_name}: Move {i} clip_id must be string")
            self.assertIsInstance(move['video_path'], str, f"{path_name}: Move {i} video_path must be string")
            self.assertIsInstance(move['start_time'], (int, float), f"{path_name}: Move {i} start_time must be number")
            self.assertIsInstance(move['duration'], (int, float), f"{path_name}: Move {i} duration must be number")
            self.assertIsInstance(move['transition_type'], str, f"{path_name}: Move {i} transition_type must be string")
            
            # Validate transition type is valid
            valid_transitions = ['cut', 'crossfade', 'fade_black', 'fade_white']
            self.assertIn(
                move['transition_type'],
                valid_transitions,
                f"{path_name}: Move {i} has invalid transition_type '{move['transition_type']}'"
            )
        
        # Validate output_config has required fields
        self.assertIn('output_path', blueprint['output_config'], f"{path_name}: output_config missing output_path")
        self.assertIsInstance(blueprint['output_config']['output_path'], str, f"{path_name}: output_path must be string")
        
        # Validate generation_parameters structure
        self.assertIn('energy_level', blueprint['generation_parameters'], f"{path_name}: generation_parameters missing energy_level")
        self.assertIn('style', blueprint['generation_parameters'], f"{path_name}: generation_parameters missing style")
    
    def _compare_blueprint_schemas(self, bp1, bp2, ignore_fields=None):
        """
        Compare two blueprints to ensure they have the same schema structure.
        
        Args:
            bp1: First blueprint
            bp2: Second blueprint
            ignore_fields: List of fields to ignore in comparison (e.g., AI-specific metadata)
        """
        ignore_fields = ignore_fields or []
        
        # Get all keys from both blueprints
        keys1 = set(bp1.keys()) - set(ignore_fields)
        keys2 = set(bp2.keys()) - set(ignore_fields)
        
        # Both should have the same top-level keys (excluding ignored fields)
        self.assertEqual(
            keys1,
            keys2,
            f"Blueprints have different top-level keys. Path1: {keys1}, Path2: {keys2}"
        )
        
        # Compare types of all fields
        for key in keys1:
            self.assertEqual(
                type(bp1[key]),
                type(bp2[key]),
                f"Field '{key}' has different types: {type(bp1[key])} vs {type(bp2[key])}"
            )
        
        # Compare move structures
        if bp1['moves'] and bp2['moves']:
            move1 = bp1['moves'][0]
            move2 = bp2['moves'][0]
            
            move_keys1 = set(move1.keys())
            move_keys2 = set(move2.keys())
            
            self.assertEqual(
                move_keys1,
                move_keys2,
                f"Moves have different keys. Path1: {move_keys1}, Path2: {move_keys2}"
            )
            
            for key in move_keys1:
                self.assertEqual(
                    type(move1[key]),
                    type(move2[key]),
                    f"Move field '{key}' has different types: {type(move1[key])} vs {type(move2[key])}"
                )
        
        # Compare output_config structures
        output_keys1 = set(bp1['output_config'].keys())
        output_keys2 = set(bp2['output_config'].keys())
        
        self.assertEqual(
            output_keys1,
            output_keys2,
            f"output_config has different keys. Path1: {output_keys1}, Path2: {output_keys2}"
        )
    
    @patch('services.jobs_service.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.gemini_service.GeminiService')
    @patch('services.vector_search_service.VectorSearchService')
    
    def test_both_paths_generate_same_schema(self, mock_vector_search, mock_gemini_class, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test that Path 1 and Path 2 generate blueprints with the same schema"""
        # Setup mocks
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = self.mock_blueprint.copy()
        
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution"
        
        # Mock query parsing for Path 2
        mock_gemini = mock_gemini_class.return_value
        mock_parsed = MagicMock()
        mock_parsed.to_dict.return_value = {
            'difficulty': 'intermediate',
            'energy_level': 'medium',
            'style': 'modern'
        }
        mock_gemini.parse_choreography_request.return_value = mock_parsed
        
        # Test Path 1: Select Song
        data1 = {
            'song_id': self.song.id,
            'difficulty': 'intermediate',
            'energy_level': 'medium',
            'style': 'modern'
        }
        response1 = self.client.post('/api/choreography/generate-from-song/', data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_202_ACCEPTED)
        
        task1 = ChoreographyTask.objects.get(task_id=response1.data['task_id'])
        blueprint1 = Blueprint.objects.get(task=task1)
        bp1 = blueprint1.blueprint_json
        
        # Test Path 2: Describe Choreo
        data2 = {
            'query': 'Create an intermediate modern choreography with medium energy'
        }
        response2 = self.client.post('/api/choreography/generate-with-ai/', data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_202_ACCEPTED)
        
        task2 = ChoreographyTask.objects.get(task_id=response2.data['task_id'])
        blueprint2 = Blueprint.objects.get(task=task2)
        bp2 = blueprint2.blueprint_json
        
        # Validate both blueprints conform to schema
        self._validate_blueprint_schema(bp1, "Path 1 (Select Song)")
        self._validate_blueprint_schema(bp2, "Path 2 (Describe Choreo)")
        
        # Compare schemas (ignore AI-specific fields that only Path 2 adds)
        # Path 2 adds 'ai_mode' and 'original_query' to generation_parameters
        # We'll compare the structure but allow these extra fields
        
        # Both should have same core top-level fields
        core_fields = [
            'task_id',
            'audio_path',
            'audio_tempo',
            'moves',
            'total_duration',
            'difficulty_level',
            'generation_timestamp',
            'generation_parameters',
            'output_config'
        ]
        
        for field in core_fields:
            self.assertIn(field, bp1, f"Path 1 missing field: {field}")
            self.assertIn(field, bp2, f"Path 2 missing field: {field}")
            
            # Verify same type
            self.assertEqual(
                type(bp1[field]),
                type(bp2[field]),
                f"Field '{field}' has different types: Path1={type(bp1[field])}, Path2={type(bp2[field])}"
            )
        
        # Both should have same move structure
        self.assertGreater(len(bp1['moves']), 0, "Path 1 has no moves")
        self.assertGreater(len(bp2['moves']), 0, "Path 2 has no moves")
        
        move1 = bp1['moves'][0]
        move2 = bp2['moves'][0]
        
        move_fields = [
            'clip_id',
            'video_path',
            'start_time',
            'duration',
            'transition_type',
            'original_duration',
            'trim_start',
            'trim_end',
            'volume_adjustment'
        ]
        
        for field in move_fields:
            self.assertIn(field, move1, f"Path 1 move missing field: {field}")
            self.assertIn(field, move2, f"Path 2 move missing field: {field}")
            
            # Verify same type
            self.assertEqual(
                type(move1[field]),
                type(move2[field]),
                f"Move field '{field}' has different types: Path1={type(move1[field])}, Path2={type(move2[field])}"
            )
        
        # Both should have same output_config structure
        output_fields = [
            'output_path',
            'output_format',
            'video_codec',
            'audio_codec',
            'video_bitrate',
            'audio_bitrate',
            'frame_rate',
            'transition_duration',
            'fade_duration',
            'add_audio_overlay',
            'normalize_audio'
        ]
        
        for field in output_fields:
            self.assertIn(field, bp1['output_config'], f"Path 1 output_config missing field: {field}")
            self.assertIn(field, bp2['output_config'], f"Path 2 output_config missing field: {field}")
            
            # Verify same type
            self.assertEqual(
                type(bp1['output_config'][field]),
                type(bp2['output_config'][field]),
                f"output_config field '{field}' has different types: Path1={type(bp1['output_config'][field])}, Path2={type(bp2['output_config'][field])}"
            )
        
        # Verify generation_parameters has common fields
        common_gen_params = ['energy_level', 'style', 'user_id']
        for field in common_gen_params:
            self.assertIn(field, bp1['generation_parameters'], f"Path 1 generation_parameters missing field: {field}")
            self.assertIn(field, bp2['generation_parameters'], f"Path 2 generation_parameters missing field: {field}")
        
        # Path 2 should have AI-specific fields
        self.assertIn('ai_mode', bp2['generation_parameters'], "Path 2 should have ai_mode in generation_parameters")
        self.assertIn('original_query', bp2['generation_parameters'], "Path 2 should have original_query in generation_parameters")
        self.assertTrue(bp2['generation_parameters']['ai_mode'], "Path 2 ai_mode should be True")
        
        print("\n✓ Both paths generate blueprints with the same schema structure")
        print(f"✓ Path 1 blueprint has {len(bp1['moves'])} moves")
        print(f"✓ Path 2 blueprint has {len(bp2['moves'])} moves")
        print(f"✓ Both blueprints conform to the expected schema")
    
    @patch('services.jobs_service.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.gemini_service.GeminiService')
    @patch('services.vector_search_service.VectorSearchService')
    
    def test_schema_consistency_with_different_parameters(self, mock_vector_search, mock_gemini_class, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test that schema remains consistent even with different parameters"""
        # Setup mocks
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        
        # Create different blueprints for different parameters
        beginner_blueprint = self.mock_blueprint.copy()
        beginner_blueprint['difficulty_level'] = 'beginner'
        beginner_blueprint['generation_parameters']['energy_level'] = 'low'
        
        advanced_blueprint = self.mock_blueprint.copy()
        advanced_blueprint['difficulty_level'] = 'advanced'
        advanced_blueprint['generation_parameters']['energy_level'] = 'high'
        
        mock_blueprint_gen.generate_blueprint.side_effect = [beginner_blueprint, advanced_blueprint]
        
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution"
        
        # Mock query parsing for Path 2
        mock_gemini = mock_gemini_class.return_value
        mock_parsed1 = MagicMock()
        mock_parsed1.to_dict.return_value = {
            'difficulty': 'beginner',
            'energy_level': 'low',
            'style': 'romantic'
        }
        mock_parsed2 = MagicMock()
        mock_parsed2.to_dict.return_value = {
            'difficulty': 'advanced',
            'energy_level': 'high',
            'style': 'energetic'
        }
        mock_gemini.parse_choreography_request.side_effect = [mock_parsed1, mock_parsed2]
        
        # Test Path 1 with beginner difficulty
        data1 = {
            'song_id': self.song.id,
            'difficulty': 'beginner',
            'energy_level': 'low',
            'style': 'romantic'
        }
        response1 = self.client.post('/api/choreography/generate-from-song/', data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_202_ACCEPTED)
        
        task1 = ChoreographyTask.objects.get(task_id=response1.data['task_id'])
        blueprint1 = Blueprint.objects.get(task=task1)
        bp1 = blueprint1.blueprint_json
        
        # Test Path 2 with advanced difficulty
        data2 = {
            'query': 'Create an advanced energetic choreography with high energy'
        }
        response2 = self.client.post('/api/choreography/generate-with-ai/', data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_202_ACCEPTED)
        
        task2 = ChoreographyTask.objects.get(task_id=response2.data['task_id'])
        blueprint2 = Blueprint.objects.get(task=task2)
        bp2 = blueprint2.blueprint_json
        
        # Validate both blueprints have the same schema structure
        self._validate_blueprint_schema(bp1, "Path 1 (Beginner)")
        self._validate_blueprint_schema(bp2, "Path 2 (Advanced)")
        
        # Verify they have the same keys (structure) even with different values
        core_keys1 = set(bp1.keys())
        core_keys2 = set(bp2.keys()) - {'generation_parameters'}  # Path 2 has extra AI fields
        
        # Add back generation_parameters for comparison
        core_keys2.add('generation_parameters')
        
        # Both should have the same core structure
        expected_keys = {
            'task_id',
            'audio_path',
            'audio_tempo',
            'moves',
            'total_duration',
            'difficulty_level',
            'generation_timestamp',
            'generation_parameters',
            'output_config'
        }
        
        self.assertTrue(expected_keys.issubset(core_keys1), "Path 1 missing expected keys")
        self.assertTrue(expected_keys.issubset(core_keys2), "Path 2 missing expected keys")
        
        print("\n✓ Schema remains consistent across different parameters")
        print(f"✓ Beginner blueprint: difficulty={bp1['difficulty_level']}, energy={bp1['generation_parameters']['energy_level']}")
        print(f"✓ Advanced blueprint: difficulty={bp2['difficulty_level']}, energy={bp2['generation_parameters']['energy_level']}")


class StorageModeTests(TestCase):
    """Test blueprint flow with different storage modes"""
    
    def setUp(self):
        """Set up test client, user, and song"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('services.jobs_service.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.gemini_service.GeminiService')
    @patch('services.vector_search_service.VectorSearchService')
    
    def test_local_storage_mode(self, mock_vector_search, mock_gemini, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test blueprint generation with local storage paths"""
        # Create song with local path
        song = Song.objects.create(
            title='Local Song',
            artist='Test Artist',
            duration=180.0,
            bpm=120,
            genre='bachata',
            audio_path='data/songs/local-test.mp3'
        )
        
        # Mock blueprint with local paths
        mock_blueprint = {
            "task_id": "test-task-id",
            "audio_path": "data/songs/local-test.mp3",
            "moves": [
                {
                    "clip_id": "move_1",
                    "video_path": "data/Bachata_steps/basic_steps/basic_1.mp4",
                    "start_time": 0.0,
                    "duration": 8.0,
                    "transition_type": "cut"
                }
            ],
            "output_config": {
                "output_path": "data/output/choreography_test.mp4"
            }
        }
        
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = mock_blueprint
        
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution"
        
        # Make request
        data = {
            'song_id': song.id,
            'difficulty': 'intermediate'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        # Verify blueprint uses local paths
        task = ChoreographyTask.objects.get(task_id=response.data['task_id'])
        blueprint = Blueprint.objects.get(task=task)
        bp = blueprint.blueprint_json
        
        self.assertTrue(bp['audio_path'].startswith('data/'))
        self.assertTrue(bp['moves'][0]['video_path'].startswith('data/'))
        self.assertTrue(bp['output_config']['output_path'].startswith('data/'))
    
    @patch('services.jobs_service.CloudRunJobsService')
    @patch('services.blueprint_generator.BlueprintGenerator')
    @patch('services.gemini_service.GeminiService')
    @patch('services.vector_search_service.VectorSearchService')
    
    def test_gcs_storage_mode(self, mock_vector_search, mock_gemini, mock_blueprint_gen_class, mock_jobs_service_class):
        """Test blueprint generation with GCS storage paths"""
        # Create song with GCS path
        song = Song.objects.create(
            title='GCS Song',
            artist='Test Artist',
            duration=180.0,
            bpm=120,
            genre='bachata',
            audio_path='gs://bachata-buddy-bucket/songs/gcs-test.mp3'
        )
        
        # Mock blueprint with GCS paths
        mock_blueprint = {
            "task_id": "test-task-id",
            "audio_path": "gs://bachata-buddy-bucket/songs/gcs-test.mp3",
            "moves": [
                {
                    "clip_id": "move_1",
                    "video_path": "gs://bachata-buddy-bucket/Bachata_steps/basic_steps/basic_1.mp4",
                    "start_time": 0.0,
                    "duration": 8.0,
                    "transition_type": "cut"
                }
            ],
            "output_config": {
                "output_path": "gs://bachata-buddy-bucket/output/choreography_test.mp4"
            }
        }
        
        mock_blueprint_gen = mock_blueprint_gen_class.return_value
        mock_blueprint_gen.generate_blueprint.return_value = mock_blueprint
        
        mock_jobs_service = mock_jobs_service_class.return_value
        mock_jobs_service.create_job_execution.return_value = "test-execution"
        
        # Make request
        data = {
            'song_id': song.id,
            'difficulty': 'intermediate'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        # Verify blueprint uses GCS paths
        task = ChoreographyTask.objects.get(task_id=response.data['task_id'])
        blueprint = Blueprint.objects.get(task=task)
        bp = blueprint.blueprint_json
        
        self.assertTrue(bp['audio_path'].startswith('gs://'))
        self.assertTrue(bp['moves'][0]['video_path'].startswith('gs://'))
        self.assertTrue(bp['output_config']['output_path'].startswith('gs://'))


class ErrorScenarioTests(TestCase):
    """Test error handling in blueprint flow"""
    
    def setUp(self):
        """Set up test client, user, and song"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.song = Song.objects.create(
            title='Test Song',
            artist='Test Artist',
            duration=180.0,
            bpm=120,
            genre='bachata',
            audio_path='data/songs/test.mp3'
        )
    
    def test_authentication_required(self):
        """Test that authentication is required for blueprint generation"""
        self.client.force_authenticate(user=None)
        
        data = {
            'song_id': self.song.id,
            'difficulty': 'intermediate'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
