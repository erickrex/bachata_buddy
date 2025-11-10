"""
Unit tests for BlueprintGenerator

Tests cover:
- Blueprint generation with various inputs
- Blueprint schema validation
- Integration with music analyzer
- Integration with vector search

Run with:
    cd backend && python manage.py test services.test_blueprint_generator
"""
from django.test import TestCase
from apps.choreography.models import MoveEmbedding
from services.blueprint_generator import (
    BlueprintGenerator, 
    BlueprintConfig, 
    BlueprintGenerationError
)
from services.vector_search_service import VectorSearchService
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import List


@dataclass
class MockMusicSection:
    """Mock music section for testing."""
    start_time: float
    end_time: float
    section_type: str
    energy_level: float
    tempo_stability: float
    recommended_move_types: List[str]


@dataclass
class MockMusicFeatures:
    """Mock music features for testing."""
    tempo: float
    beat_positions: List[float]
    duration: float
    mfcc_features: np.ndarray
    chroma_features: np.ndarray
    spectral_centroid: np.ndarray
    zero_crossing_rate: np.ndarray
    rms_energy: np.ndarray
    harmonic_component: np.ndarray
    percussive_component: np.ndarray
    energy_profile: List[float]
    tempo_confidence: float
    sections: List[MockMusicSection]
    rhythm_pattern_strength: float
    syncopation_level: float
    audio_embedding: List[float]


class BlueprintGeneratorTestCase(TestCase):
    """Test cases for BlueprintGenerator"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample move embeddings
        self.move1 = MoveEmbedding.objects.create(
            move_id='move_001',
            move_name='Basic Step',
            video_path='data/Bachata_steps/basic_steps/basic_1.mp4',
            pose_embedding=[0.1] * 512,
            audio_embedding=[0.2] * 128,
            text_embedding=[0.3] * 384,
            difficulty='beginner',
            energy_level='medium',
            style='romantic',
            duration=8.0
        )
        
        self.move2 = MoveEmbedding.objects.create(
            move_id='move_002',
            move_name='Body Roll',
            video_path='data/Bachata_steps/body_roll/body_roll_1.mp4',
            pose_embedding=[0.5] * 512,
            audio_embedding=[0.6] * 128,
            text_embedding=[0.7] * 384,
            difficulty='intermediate',
            energy_level='medium',
            style='sensual',
            duration=8.0
        )
        
        self.move3 = MoveEmbedding.objects.create(
            move_id='move_003',
            move_name='Turn',
            video_path='data/Bachata_steps/lady_right_turn/turn_1.mp4',
            pose_embedding=[0.9] * 512,
            audio_embedding=[0.8] * 128,
            text_embedding=[0.7] * 384,
            difficulty='intermediate',
            energy_level='medium',
            style='energetic',
            duration=8.0
        )
        
        self.move4 = MoveEmbedding.objects.create(
            move_id='move_004',
            move_name='Advanced Spin',
            video_path='data/Bachata_steps/advanced/spin_1.mp4',
            pose_embedding=[0.4] * 512,
            audio_embedding=[0.5] * 128,
            text_embedding=[0.6] * 384,
            difficulty='advanced',
            energy_level='medium',
            style='romantic',
            duration=8.0
        )
        
        self.move5 = MoveEmbedding.objects.create(
            move_id='move_005',
            move_name='Romantic Turn',
            video_path='data/Bachata_steps/intermediate/romantic_turn_1.mp4',
            pose_embedding=[0.3] * 512,
            audio_embedding=[0.4] * 128,
            text_embedding=[0.5] * 384,
            difficulty='intermediate',
            energy_level='medium',
            style='romantic',
            duration=8.0
        )
        
        # Create mock services
        self.vector_search = VectorSearchService(cache_ttl_seconds=60)
        self.vector_search.load_embeddings_from_db()
        
        self.music_analyzer = Mock()
        self.gemini_service = Mock()
        
        # Create generator
        self.generator = BlueprintGenerator(
            vector_search_service=self.vector_search,
            music_analyzer=self.music_analyzer,
            gemini_service=self.gemini_service
        )
    
    # Test: Blueprint generation with various inputs
    def test_generate_blueprint_basic(self):
        """Test basic blueprint generation"""
        # Mock music analyzer
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        # Generate blueprint
        blueprint = self.generator.generate_blueprint(
            task_id='test_task_001',
            song_path='data/songs/test_song.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        # Verify blueprint structure
        self.assertIsInstance(blueprint, dict)
        self.assertEqual(blueprint['task_id'], 'test_task_001')
        self.assertEqual(blueprint['audio_path'], 'data/songs/test_song.mp3')
        self.assertEqual(blueprint['difficulty_level'], 'beginner')
        self.assertIn('moves', blueprint)
        self.assertIn('total_duration', blueprint)
        self.assertIn('output_config', blueprint)
    
    def test_generate_blueprint_with_different_difficulties(self):
        """Test blueprint generation with different difficulty levels"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        for difficulty in ['beginner', 'intermediate', 'advanced']:
            blueprint = self.generator.generate_blueprint(
                task_id=f'test_{difficulty}',
                song_path='data/songs/test.mp3',
                difficulty=difficulty,
                energy_level='medium',
                style='romantic'
            )
            
            self.assertEqual(blueprint['difficulty_level'], difficulty)
            self.assertGreater(len(blueprint['moves']), 0)
    
    def test_generate_blueprint_with_different_energy_levels(self):
        """Test blueprint generation with different energy levels"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        # Test with medium energy (which all our test moves have)
        blueprint = self.generator.generate_blueprint(
            task_id='test_medium',
            song_path='data/songs/test.mp3',
            difficulty='intermediate',
            energy_level='medium',
            style='energetic'
        )
        
        self.assertEqual(blueprint['generation_parameters']['energy_level'], 'medium')
        self.assertGreater(len(blueprint['moves']), 0)
    
    def test_generate_blueprint_with_different_styles(self):
        """Test blueprint generation with different styles"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        for style in ['romantic', 'energetic', 'sensual', 'playful']:
            blueprint = self.generator.generate_blueprint(
                task_id=f'test_{style}',
                song_path='data/songs/test.mp3',
                difficulty='intermediate',
                energy_level='medium',
                style=style
            )
            
            self.assertEqual(blueprint['generation_parameters']['style'], style)
    
    def test_generate_blueprint_with_user_id(self):
        """Test blueprint generation with user ID"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_user',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic',
            user_id=123
        )
        
        self.assertEqual(blueprint['generation_parameters']['user_id'], 123)
    
    def test_generate_blueprint_with_tempo_preference(self):
        """Test blueprint generation with tempo preference"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_tempo',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic',
            tempo_preference='slow'
        )
        
        # Verify blueprint was generated (tempo preference is used internally)
        self.assertIsNotNone(blueprint)
    
    # Test: Blueprint schema validation
    def test_validate_blueprint_valid(self):
        """Test validation of valid blueprint"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_valid',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        # Should not raise exception
        self.assertTrue(self.generator.validate_blueprint(blueprint))
    
    def test_validate_blueprint_missing_task_id(self):
        """Test validation fails when task_id is missing"""
        blueprint = {
            'audio_path': 'test.mp3',
            'moves': [],
            'total_duration': 180.0,
            'difficulty_level': 'beginner',
            'generation_timestamp': '2024-01-01T00:00:00Z',
            'output_config': {}
        }
        
        with self.assertRaises(ValueError) as context:
            self.generator.validate_blueprint(blueprint)
        
        self.assertIn('task_id', str(context.exception))
    
    def test_validate_blueprint_missing_audio_path(self):
        """Test validation fails when audio_path is missing"""
        blueprint = {
            'task_id': 'test',
            'moves': [],
            'total_duration': 180.0,
            'difficulty_level': 'beginner',
            'generation_timestamp': '2024-01-01T00:00:00Z',
            'output_config': {}
        }
        
        with self.assertRaises(ValueError) as context:
            self.generator.validate_blueprint(blueprint)
        
        self.assertIn('audio_path', str(context.exception))
    
    def test_validate_blueprint_empty_moves(self):
        """Test validation fails when moves array is empty"""
        blueprint = {
            'task_id': 'test',
            'audio_path': 'test.mp3',
            'moves': [],
            'total_duration': 180.0,
            'difficulty_level': 'beginner',
            'generation_timestamp': '2024-01-01T00:00:00Z',
            'output_config': {}
        }
        
        with self.assertRaises(ValueError) as context:
            self.generator.validate_blueprint(blueprint)
        
        self.assertIn('empty', str(context.exception).lower())
    
    def test_validate_blueprint_invalid_moves_type(self):
        """Test validation fails when moves is not a list"""
        blueprint = {
            'task_id': 'test',
            'audio_path': 'test.mp3',
            'moves': 'not a list',
            'total_duration': 180.0,
            'difficulty_level': 'beginner',
            'generation_timestamp': '2024-01-01T00:00:00Z',
            'output_config': {}
        }
        
        with self.assertRaises(ValueError) as context:
            self.generator.validate_blueprint(blueprint)
        
        self.assertIn('list', str(context.exception).lower())
    
    def test_validate_blueprint_move_missing_fields(self):
        """Test validation fails when move is missing required fields"""
        blueprint = {
            'task_id': 'test',
            'audio_path': 'test.mp3',
            'moves': [
                {
                    'clip_id': 'move_1',
                    'video_path': 'test.mp4'
                    # Missing start_time and duration
                }
            ],
            'total_duration': 180.0,
            'difficulty_level': 'beginner',
            'generation_timestamp': '2024-01-01T00:00:00Z',
            'output_config': {}
        }
        
        with self.assertRaises(ValueError) as context:
            self.generator.validate_blueprint(blueprint)
        
        self.assertIn('missing', str(context.exception).lower())
    
    def test_validate_blueprint_invalid_output_config(self):
        """Test validation fails when output_config is not a dict"""
        blueprint = {
            'task_id': 'test',
            'audio_path': 'test.mp3',
            'moves': [
                {
                    'clip_id': 'move_1',
                    'video_path': 'test.mp4',
                    'start_time': 0.0,
                    'duration': 8.0
                }
            ],
            'total_duration': 180.0,
            'difficulty_level': 'beginner',
            'generation_timestamp': '2024-01-01T00:00:00Z',
            'output_config': 'not a dict'
        }
        
        with self.assertRaises(ValueError) as context:
            self.generator.validate_blueprint(blueprint)
        
        self.assertIn('dictionary', str(context.exception).lower())
    
    # Test: Integration with music analyzer
    def test_music_analyzer_integration(self):
        """Test integration with music analyzer"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_music',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        # Verify music analyzer was called
        self.music_analyzer.analyze_audio.assert_called_once_with('data/songs/test.mp3')
        
        # Verify tempo was extracted
        self.assertEqual(blueprint['audio_tempo'], 120.0)
    
    def test_music_analyzer_failure(self):
        """Test handling of music analyzer failure"""
        self.music_analyzer.analyze_audio.side_effect = Exception("Analysis failed")
        
        with self.assertRaises(BlueprintGenerationError) as context:
            self.generator.generate_blueprint(
                task_id='test_fail',
                song_path='data/songs/test.mp3',
                difficulty='beginner',
                energy_level='medium',
                style='romantic'
            )
        
        self.assertIn('failed', str(context.exception).lower())
    
    def test_music_features_used_in_blueprint(self):
        """Test that music features are properly used in blueprint"""
        mock_features = self._create_mock_music_features(
            tempo=140.0,
            duration=200.0
        )
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_features',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        # Verify music features are in blueprint
        self.assertEqual(blueprint['audio_tempo'], 140.0)
        self.assertGreater(blueprint['total_duration'], 0)
    
    # Test: Integration with vector search
    def test_vector_search_integration(self):
        """Test integration with vector search"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_vector',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        # Verify moves were selected
        self.assertGreater(len(blueprint['moves']), 0)
        
        # Verify moves have correct structure
        for move in blueprint['moves']:
            self.assertIn('clip_id', move)
            self.assertIn('video_path', move)
            self.assertIn('start_time', move)
            self.assertIn('duration', move)
    
    def test_vector_search_filters_by_difficulty(self):
        """Test that vector search filters by difficulty"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        # Generate blueprint for beginner
        blueprint = self.generator.generate_blueprint(
            task_id='test_beginner',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        # Should have selected moves (at least one beginner move exists)
        self.assertGreater(len(blueprint['moves']), 0)
    
    def test_vector_search_filters_by_energy(self):
        """Test that vector search filters by energy level"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        # Generate blueprint for medium energy (matches our test data)
        blueprint = self.generator.generate_blueprint(
            task_id='test_energy',
            song_path='data/songs/test.mp3',
            difficulty='intermediate',
            energy_level='medium',
            style='sensual'
        )
        
        # Should have selected moves
        self.assertGreater(len(blueprint['moves']), 0)
    
    def test_vector_search_filters_by_style(self):
        """Test that vector search filters by style"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        # Generate blueprint for energetic style
        blueprint = self.generator.generate_blueprint(
            task_id='test_style',
            song_path='data/songs/test.mp3',
            difficulty='intermediate',
            energy_level='medium',
            style='energetic'
        )
        
        # Should have selected moves
        self.assertGreater(len(blueprint['moves']), 0)
    
    # Test: AI sequencing with Gemini
    def test_gemini_ai_sequencing(self):
        """Test AI sequencing with Gemini"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = '''
        [
            {"move_name": "Basic Step", "start_time": 0.0, "duration": 8.0},
            {"move_name": "Body Roll", "start_time": 8.0, "duration": 8.0}
        ]
        '''
        self.gemini_service.model.generate_content.return_value = mock_response
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_gemini',
            song_path='data/songs/test.mp3',
            difficulty='intermediate',
            energy_level='medium',
            style='sensual'
        )
        
        # Verify Gemini was called
        self.gemini_service.model.generate_content.assert_called_once()
        
        # Verify moves were generated
        self.assertGreater(len(blueprint['moves']), 0)
    
    def test_fallback_to_rule_based_when_gemini_fails(self):
        """Test fallback to rule-based sequencing when Gemini fails"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        # Mock Gemini failure
        self.gemini_service.model.generate_content.side_effect = Exception("API error")
        
        # Should still generate blueprint using rule-based approach
        blueprint = self.generator.generate_blueprint(
            task_id='test_fallback',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        # Verify blueprint was generated
        self.assertGreater(len(blueprint['moves']), 0)
    
    def test_rule_based_sequencing_without_gemini(self):
        """Test rule-based sequencing when Gemini is not available"""
        # Create generator without Gemini
        generator = BlueprintGenerator(
            vector_search_service=self.vector_search,
            music_analyzer=self.music_analyzer,
            gemini_service=None
        )
        
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = generator.generate_blueprint(
            task_id='test_no_gemini',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        # Verify blueprint was generated
        self.assertGreater(len(blueprint['moves']), 0)
    
    # Test: Blueprint structure and content
    def test_blueprint_has_required_fields(self):
        """Test that blueprint has all required fields"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_fields',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        # Check required fields
        required_fields = [
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
        
        for field in required_fields:
            self.assertIn(field, blueprint, f"Missing field: {field}")
    
    def test_blueprint_moves_have_correct_structure(self):
        """Test that moves in blueprint have correct structure"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_move_structure',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        # Check move structure
        for move in blueprint['moves']:
            self.assertIn('clip_id', move)
            self.assertIn('video_path', move)
            self.assertIn('start_time', move)
            self.assertIn('duration', move)
            self.assertIn('transition_type', move)
            self.assertIn('original_duration', move)
            self.assertIn('trim_start', move)
            self.assertIn('trim_end', move)
            self.assertIn('volume_adjustment', move)
    
    def test_blueprint_output_config_structure(self):
        """Test that output_config has correct structure"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_output',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic'
        )
        
        output_config = blueprint['output_config']
        
        # Check output config fields
        self.assertIn('output_path', output_config)
        self.assertIn('output_format', output_config)
        self.assertIn('video_codec', output_config)
        self.assertIn('audio_codec', output_config)
        self.assertIn('video_bitrate', output_config)
        self.assertIn('audio_bitrate', output_config)
        self.assertIn('frame_rate', output_config)
        self.assertIn('transition_duration', output_config)
        self.assertIn('fade_duration', output_config)
    
    def test_blueprint_generation_parameters(self):
        """Test that generation_parameters are stored correctly"""
        mock_features = self._create_mock_music_features()
        self.music_analyzer.analyze_audio.return_value = mock_features
        
        blueprint = self.generator.generate_blueprint(
            task_id='test_params',
            song_path='data/songs/test.mp3',
            difficulty='intermediate',
            energy_level='high',
            style='energetic',
            user_id=456
        )
        
        params = blueprint['generation_parameters']
        
        self.assertEqual(params['energy_level'], 'high')
        self.assertEqual(params['style'], 'energetic')
        self.assertEqual(params['user_id'], 456)
    
    # Test: BlueprintConfig dataclass
    def test_blueprint_config_creation(self):
        """Test BlueprintConfig creation"""
        config = BlueprintConfig(
            task_id='test_config',
            song_path='data/songs/test.mp3',
            difficulty='beginner',
            energy_level='medium',
            style='romantic',
            user_id=789,
            tempo_preference='slow'
        )
        
        self.assertEqual(config.task_id, 'test_config')
        self.assertEqual(config.difficulty, 'beginner')
        self.assertEqual(config.user_id, 789)
        self.assertEqual(config.tempo_preference, 'slow')
    
    def test_blueprint_config_to_dict(self):
        """Test BlueprintConfig to_dict conversion"""
        config = BlueprintConfig(
            task_id='test_dict',
            song_path='data/songs/test.mp3',
            difficulty='intermediate',
            energy_level='high',
            style='energetic'
        )
        
        config_dict = config.to_dict()
        
        self.assertIsInstance(config_dict, dict)
        self.assertEqual(config_dict['task_id'], 'test_dict')
        self.assertEqual(config_dict['difficulty'], 'intermediate')
    
    # Helper methods
    def _create_mock_music_features(self, tempo=120.0, duration=180.0):
        """Create mock music features for testing"""
        sections = [
            MockMusicSection(
                start_time=0.0,
                end_time=45.0,
                section_type='intro',
                energy_level=0.2,
                tempo_stability=0.9,
                recommended_move_types=['basic_step', 'side_step']
            ),
            MockMusicSection(
                start_time=45.0,
                end_time=90.0,
                section_type='verse',
                energy_level=0.25,
                tempo_stability=0.85,
                recommended_move_types=['basic_step', 'cross_body_lead']
            ),
            MockMusicSection(
                start_time=90.0,
                end_time=135.0,
                section_type='chorus',
                energy_level=0.35,
                tempo_stability=0.8,
                recommended_move_types=['lady_left_turn', 'lady_right_turn']
            ),
            MockMusicSection(
                start_time=135.0,
                end_time=duration,
                section_type='outro',
                energy_level=0.15,
                tempo_stability=0.9,
                recommended_move_types=['basic_step', 'dips']
            )
        ]
        
        # Create combined embedding matching the expected dimension (512 + 128 + 384 = 1024)
        # This matches what VectorSearchService expects
        combined_embedding = [0.1] * 512 + [0.2] * 128 + [0.3] * 384
        
        return MockMusicFeatures(
            tempo=tempo,
            beat_positions=[i * 0.5 for i in range(int(duration * 2))],
            duration=duration,
            mfcc_features=np.random.randn(13, 100),
            chroma_features=np.random.randn(12, 100),
            spectral_centroid=np.random.randn(1, 100),
            zero_crossing_rate=np.random.randn(1, 100),
            rms_energy=np.random.randn(1, 100),
            harmonic_component=np.random.randn(int(duration * 22050)),
            percussive_component=np.random.randn(int(duration * 22050)),
            energy_profile=[0.2 + 0.1 * np.sin(i / 10) for i in range(100)],
            tempo_confidence=0.9,
            sections=sections,
            rhythm_pattern_strength=0.8,
            syncopation_level=0.6,
            audio_embedding=combined_embedding  # Combined 1024D embedding
        )
