"""
Tests for RecommendationEngine service.

Tests multimodal recommendation system with Elasticsearch integration.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from core.services.recommendation_engine import (
    RecommendationEngine,
    MoveCandidate,
    RecommendationScore,
    RecommendationRequest
)


@pytest.fixture
def mock_es_service():
    """Create mock Elasticsearch service."""
    mock_es = Mock()
    mock_es.get_all_embeddings = Mock(return_value=[])
    return mock_es


@pytest.fixture
def engine(mock_es_service):
    """Create recommendation engine with mock ES."""
    return RecommendationEngine(elasticsearch_service=mock_es_service)


@pytest.fixture
def sample_move_candidate():
    """Create sample MoveCandidate."""
    return MoveCandidate(
        clip_id='test_move_1',
        video_path='data/Bachata_steps/basic/basic_1.mp4',
        move_label='basic_step',
        audio_embedding=np.random.rand(128).astype(np.float32),
        lead_embedding=np.random.rand(512).astype(np.float32),
        follow_embedding=np.random.rand(512).astype(np.float32),
        interaction_embedding=np.random.rand(256).astype(np.float32),
        text_embedding=np.random.rand(384).astype(np.float32),
        energy_level='medium',
        difficulty='intermediate',
        estimated_tempo=120.0,
        lead_follow_roles='both',
        quality_score=0.85,
        detection_rate=0.95
    )


@pytest.fixture
def sample_embedding_doc():
    """Create sample embedding document from Elasticsearch."""
    return {
        'clip_id': 'test_move_1',
        'video_path': 'Bachata_steps/basic/basic_1.mp4',  # Without data/ prefix
        'move_label': 'basic_step',
        'audio_embedding': np.random.rand(128).tolist(),
        'lead_embedding': np.random.rand(512).tolist(),
        'follow_embedding': np.random.rand(512).tolist(),
        'interaction_embedding': np.random.rand(256).tolist(),
        'text_embedding': np.random.rand(384).tolist(),
        'energy_level': 'medium',
        'difficulty': 'intermediate',
        'estimated_tempo': 120.0,
        'lead_follow_roles': 'both',
        'quality_score': 0.85,
        'detection_rate': 0.95
    }


class TestRecommendationEngine:
    """Test suite for RecommendationEngine."""
    
    def test_initialization(self, engine):
        """Test engine initializes correctly."""
        assert engine.es_service is not None
        assert engine.default_weights == {
            'text': 0.35,
            'audio': 0.35,
            'lead': 0.10,
            'follow': 0.10,
            'interaction': 0.10
        }
    
    def test_initialization_without_es_service(self):
        """Test engine creates ES service if not provided."""
        with patch('core.services.recommendation_engine.EnvironmentConfig'):
            with patch('core.services.recommendation_engine.ElasticsearchService'):
                engine = RecommendationEngine()
                assert engine.es_service is not None
    
    def test_recommend_moves_empty_results(self, engine, mock_es_service):
        """Test recommendation with no candidates."""
        mock_es_service.get_all_embeddings.return_value = []
        
        request = RecommendationRequest(
            query_audio_embedding=np.random.rand(128),
            difficulty='intermediate'
        )
        
        recommendations = engine.recommend_moves(request, top_k=10)
        
        assert recommendations == []
    
    def test_recommend_moves_with_candidates(self, engine, mock_es_service, sample_embedding_doc):
        """Test recommendation with candidates."""
        # Setup mock to return candidates
        mock_es_service.get_all_embeddings.return_value = [
            sample_embedding_doc,
            {**sample_embedding_doc, 'clip_id': 'test_move_2', 'move_label': 'turn'},
            {**sample_embedding_doc, 'clip_id': 'test_move_3', 'move_label': 'dip'}
        ]
        
        request = RecommendationRequest(
            query_audio_embedding=np.random.rand(128),
            query_text_embedding=np.random.rand(384),
            difficulty='intermediate'
        )
        
        recommendations = engine.recommend_moves(request, top_k=3)
        
        assert len(recommendations) <= 3
        assert all(isinstance(r, RecommendationScore) for r in recommendations)
        # Should be sorted by score descending
        if len(recommendations) > 1:
            assert recommendations[0].overall_score >= recommendations[1].overall_score
    
    def test_recommend_moves_with_filters(self, engine, mock_es_service, sample_embedding_doc):
        """Test recommendation with metadata filters."""
        mock_es_service.get_all_embeddings.return_value = [sample_embedding_doc]
        
        request = RecommendationRequest(
            query_audio_embedding=np.random.rand(128),
            difficulty='intermediate',
            energy_level='medium',
            move_label='basic_step'
        )
        
        recommendations = engine.recommend_moves(request, top_k=10)
        
        # Verify filters were passed to ES
        mock_es_service.get_all_embeddings.assert_called_once()
        call_args = mock_es_service.get_all_embeddings.call_args
        assert call_args[1]['filters'] is not None
    
    def test_recommend_moves_quality_filtering(self, engine, mock_es_service, sample_embedding_doc):
        """Test recommendation with quality score filtering."""
        # Create candidates with different quality scores
        candidates = [
            {**sample_embedding_doc, 'clip_id': f'move_{i}', 'quality_score': 0.5 + i*0.1}
            for i in range(5)
        ]
        mock_es_service.get_all_embeddings.return_value = candidates
        
        request = RecommendationRequest(
            query_audio_embedding=np.random.rand(128),
            min_quality_score=0.7
        )
        
        recommendations = engine.recommend_moves(request, top_k=10)
        
        # Should only include candidates with quality >= 0.7
        assert all(r.move_candidate.quality_score >= 0.7 for r in recommendations)
    
    def test_embedding_to_candidate(self, engine, sample_embedding_doc):
        """Test converting ES document to MoveCandidate."""
        candidate = engine._embedding_to_candidate(sample_embedding_doc)
        
        assert isinstance(candidate, MoveCandidate)
        assert candidate.clip_id == 'test_move_1'
        # Should add data/ prefix to video path
        assert candidate.video_path.startswith('data/')
        assert candidate.move_label == 'basic_step'
        assert candidate.audio_embedding.shape == (128,)
        assert candidate.lead_embedding.shape == (512,)
        assert candidate.follow_embedding.shape == (512,)
        assert candidate.interaction_embedding.shape == (256,)
        assert candidate.text_embedding.shape == (384,)
    
    def test_embedding_to_candidate_path_normalization(self, engine):
        """Test video path normalization."""
        # Path without data/ prefix
        doc1 = {'clip_id': 'test', 'video_path': 'Bachata_steps/move.mp4',
                'move_label': 'test', 'audio_embedding': np.zeros(128).tolist(),
                'lead_embedding': np.zeros(512).tolist(),
                'follow_embedding': np.zeros(512).tolist(),
                'interaction_embedding': np.zeros(256).tolist(),
                'text_embedding': np.zeros(384).tolist()}
        
        candidate1 = engine._embedding_to_candidate(doc1)
        assert candidate1.video_path == 'data/Bachata_steps/move.mp4'
        
        # Path with data/ prefix already
        doc2 = {**doc1, 'video_path': 'data/Bachata_steps/move.mp4'}
        candidate2 = engine._embedding_to_candidate(doc2)
        assert candidate2.video_path == 'data/Bachata_steps/move.mp4'
    
    def test_compute_multimodal_similarity(self, engine, sample_move_candidate):
        """Test multimodal similarity computation."""
        request = RecommendationRequest(
            query_audio_embedding=np.random.rand(128),
            query_text_embedding=np.random.rand(384),
            query_lead_embedding=np.random.rand(512),
            query_follow_embedding=np.random.rand(512),
            query_interaction_embedding=np.random.rand(256)
        )
        
        weights = engine.default_weights
        score = engine._compute_multimodal_similarity(request, sample_move_candidate, weights)
        
        assert isinstance(score, RecommendationScore)
        assert 0 <= score.overall_score <= 1
        assert 0 <= score.text_similarity <= 1
        assert 0 <= score.audio_similarity <= 1
        assert 0 <= score.lead_similarity <= 1
        assert 0 <= score.follow_similarity <= 1
        assert 0 <= score.interaction_similarity <= 1
        assert score.weights == weights
    
    def test_compute_similarity_with_missing_embeddings(self, engine, sample_move_candidate):
        """Test similarity computation with some missing query embeddings."""
        request = RecommendationRequest(
            query_audio_embedding=np.random.rand(128),
            # Other embeddings are None
        )
        
        weights = engine.default_weights
        score = engine._compute_multimodal_similarity(request, sample_move_candidate, weights)
        
        assert isinstance(score, RecommendationScore)
        # Should handle missing embeddings gracefully
        assert score.text_similarity == 0.0
        assert score.audio_similarity > 0.0
    
    def test_cosine_similarity(self, engine):
        """Test cosine similarity calculation."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        
        similarity = engine._cosine_similarity(vec1, vec2)
        
        assert abs(similarity - 1.0) < 0.001  # Should be 1.0 for identical vectors
    
    def test_cosine_similarity_orthogonal(self, engine):
        """Test cosine similarity for orthogonal vectors."""
        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([0.0, 1.0])
        
        similarity = engine._cosine_similarity(vec1, vec2)
        
        assert abs(similarity) < 0.001  # Should be 0.0 for orthogonal vectors
    
    def test_custom_weights(self, engine, mock_es_service, sample_embedding_doc):
        """Test recommendation with custom weights."""
        mock_es_service.get_all_embeddings.return_value = [sample_embedding_doc]
        
        custom_weights = {
            'text': 0.5,
            'audio': 0.3,
            'lead': 0.1,
            'follow': 0.05,
            'interaction': 0.05
        }
        
        request = RecommendationRequest(
            query_audio_embedding=np.random.rand(128),
            query_text_embedding=np.random.rand(384),
            weights=custom_weights
        )
        
        recommendations = engine.recommend_moves(request, top_k=1)
        
        if recommendations:
            assert recommendations[0].weights == custom_weights


class TestMoveCandidate:
    """Test MoveCandidate dataclass."""
    
    def test_creation(self):
        """Test creating MoveCandidate."""
        candidate = MoveCandidate(
            clip_id='test_1',
            video_path='data/test.mp4',
            move_label='basic',
            audio_embedding=np.zeros(128),
            lead_embedding=np.zeros(512),
            follow_embedding=np.zeros(512),
            interaction_embedding=np.zeros(256),
            text_embedding=np.zeros(384),
            energy_level='medium',
            difficulty='intermediate',
            estimated_tempo=120.0,
            lead_follow_roles='both',
            quality_score=0.8,
            detection_rate=0.9
        )
        
        assert candidate.clip_id == 'test_1'
        assert candidate.energy_level == 'medium'
        assert candidate.difficulty == 'intermediate'
        assert candidate.quality_score == 0.8


class TestRecommendationScore:
    """Test RecommendationScore dataclass."""
    
    def test_creation(self, sample_move_candidate):
        """Test creating RecommendationScore."""
        score = RecommendationScore(
            move_candidate=sample_move_candidate,
            overall_score=0.85,
            text_similarity=0.9,
            audio_similarity=0.8,
            lead_similarity=0.85,
            follow_similarity=0.82,
            interaction_similarity=0.88,
            difficulty_match=True,
            energy_match=True,
            tempo_difference=5.0,
            weights={'text': 0.35, 'audio': 0.35, 'lead': 0.1, 'follow': 0.1, 'interaction': 0.1}
        )
        
        assert score.overall_score == 0.85
        assert score.difficulty_match is True
        assert score.tempo_difference == 5.0


class TestRecommendationRequest:
    """Test RecommendationRequest dataclass."""
    
    def test_creation_minimal(self):
        """Test creating minimal RecommendationRequest."""
        request = RecommendationRequest()
        
        assert request.query_audio_embedding is None
        assert request.difficulty is None
        assert request.weights is None
    
    def test_creation_full(self):
        """Test creating full RecommendationRequest."""
        request = RecommendationRequest(
            query_audio_embedding=np.zeros(128),
            query_text_embedding=np.zeros(384),
            query_lead_embedding=np.zeros(512),
            query_follow_embedding=np.zeros(512),
            query_interaction_embedding=np.zeros(256),
            difficulty='intermediate',
            energy_level='medium',
            move_label='basic',
            lead_follow_roles='both',
            min_quality_score=0.7,
            weights={'text': 0.5, 'audio': 0.5, 'lead': 0, 'follow': 0, 'interaction': 0}
        )
        
        assert request.difficulty == 'intermediate'
        assert request.energy_level == 'medium'
        assert request.min_quality_score == 0.7
        assert request.weights['text'] == 0.5
