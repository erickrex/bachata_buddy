"""
Tests for Elasticsearch hybrid search functionality.

Tests:
- Vector search accuracy
- Text search accuracy
- Combined hybrid search
- Metadata filtering
- Weighted similarity computation
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch

from ai_services.services.elasticsearch_service import ElasticsearchService
from ai_services.services.recommendation_engine import RecommendationEngine, RecommendationRequest
from common.config.environment_config import ElasticsearchConfig


@pytest.fixture
def mock_es_config():
    """Create mock Elasticsearch configuration."""
    return ElasticsearchConfig(
        host="localhost",
        port=9200,
        index_name="test_bachata_embeddings",
        username="elastic",
        password="test",
        use_ssl=False,
        verify_certs=False,
        timeout=30
    )


@pytest.fixture
def mock_es_client():
    """Create mock Elasticsearch client."""
    client = MagicMock()
    client.ping.return_value = True
    return client


@pytest.fixture
def es_service_with_mock(mock_es_config, mock_es_client):
    """Create ElasticsearchService with mocked client."""
    with patch('ai_services.services.elasticsearch_service.Elasticsearch', return_value=mock_es_client):
        service = ElasticsearchService(mock_es_config)
        service.client = mock_es_client
        return service


class TestVectorSearch:
    """Test vector similarity search functionality."""
    
    def test_vector_search_single_embedding(self, es_service_with_mock):
        """Test vector search with single embedding type."""
        # Mock search response
        es_service_with_mock.client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_score": 0.95,
                        "fields": {
                            "clip_id": ["clip_001"],
                            "move_label": ["cross_body_lead"],
                            "difficulty": ["intermediate"],
                            "audio_embedding": list(np.random.rand(128)),
                            "lead_embedding": list(np.random.rand(512)),
                            "follow_embedding": list(np.random.rand(512)),
                            "interaction_embedding": list(np.random.rand(256)),
                            "text_embedding": list(np.random.rand(384)),
                            "quality_score": [0.85]
                        }
                    }
                ]
            }
        }
        
        # Execute vector search
        query_audio = np.random.rand(128).astype(np.float32)
        results = es_service_with_mock.hybrid_search(
            query_embeddings={'audio': query_audio},
            top_k=5
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]['clip_id'] == 'clip_001'
        assert results[0]['score'] == 0.95
        assert 'audio_embedding' in results[0]
    
    def test_vector_search_multiple_embeddings(self, es_service_with_mock):
        """Test vector search with multiple embedding types."""
        # Mock search response
        es_service_with_mock.client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_score": 0.92,
                        "fields": {
                            "clip_id": ["clip_002"],
                            "move_label": ["basic_step"],
                            "difficulty": ["beginner"],
                            "audio_embedding": list(np.random.rand(128)),
                            "lead_embedding": list(np.random.rand(512)),
                            "follow_embedding": list(np.random.rand(512)),
                            "interaction_embedding": list(np.random.rand(256)),
                            "text_embedding": list(np.random.rand(384)),
                            "quality_score": [0.90]
                        }
                    }
                ]
            }
        }
        
        # Execute vector search with multiple embeddings
        query_embeddings = {
            'audio': np.random.rand(128).astype(np.float32),
            'text': np.random.rand(384).astype(np.float32),
            'lead': np.random.rand(512).astype(np.float32)
        }
        
        results = es_service_with_mock.hybrid_search(
            query_embeddings=query_embeddings,
            top_k=5
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]['clip_id'] == 'clip_002'
        assert results[0]['score'] == 0.92


class TestTextSearch:
    """Test text search functionality."""
    
    def test_text_search_move_label(self, es_service_with_mock):
        """Test text search on move_label field."""
        # Mock search response
        es_service_with_mock.client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_score": 0.88,
                        "fields": {
                            "clip_id": ["clip_003"],
                            "move_label": ["cross_body_lead"],
                            "difficulty": ["intermediate"],
                            "audio_embedding": list(np.random.rand(128)),
                            "lead_embedding": list(np.random.rand(512)),
                            "follow_embedding": list(np.random.rand(512)),
                            "interaction_embedding": list(np.random.rand(256)),
                            "text_embedding": list(np.random.rand(384)),
                            "quality_score": [0.80]
                        }
                    }
                ]
            }
        }
        
        # Execute text search
        results = es_service_with_mock.hybrid_search(
            query_text="cross body lead",
            top_k=5
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]['clip_id'] == 'clip_003'
        assert results[0]['move_label'] == 'cross_body_lead'
    
    def test_text_search_with_boost(self, es_service_with_mock):
        """Test text search with custom boost factor."""
        # Mock search response
        es_service_with_mock.client.search.return_value = {
            "hits": {"hits": []}
        }
        
        # Execute text search with boost
        es_service_with_mock.hybrid_search(
            query_text="romantic",
            text_boost=2.0,
            top_k=5
        )
        
        # Verify boost was applied in search call
        call_args = es_service_with_mock.client.search.call_args
        assert call_args is not None


class TestHybridSearch:
    """Test combined vector + text hybrid search."""
    
    def test_hybrid_search_combined(self, es_service_with_mock):
        """Test hybrid search combining vector and text."""
        # Mock search response
        es_service_with_mock.client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_score": 0.93,
                        "fields": {
                            "clip_id": ["clip_004"],
                            "move_label": ["romantic_turn"],
                            "difficulty": ["intermediate"],
                            "energy_level": ["medium"],
                            "audio_embedding": list(np.random.rand(128)),
                            "lead_embedding": list(np.random.rand(512)),
                            "follow_embedding": list(np.random.rand(512)),
                            "interaction_embedding": list(np.random.rand(256)),
                            "text_embedding": list(np.random.rand(384)),
                            "quality_score": [0.88]
                        }
                    }
                ]
            }
        }
        
        # Execute hybrid search
        query_embeddings = {
            'audio': np.random.rand(128).astype(np.float32),
            'text': np.random.rand(384).astype(np.float32)
        }
        
        results = es_service_with_mock.hybrid_search(
            query_embeddings=query_embeddings,
            query_text="romantic turn",
            top_k=5
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]['clip_id'] == 'clip_004'
        assert results[0]['move_label'] == 'romantic_turn'
        assert results[0]['score'] == 0.93
    
    def test_hybrid_search_no_results(self, es_service_with_mock):
        """Test hybrid search with no matching results."""
        # Mock empty search response
        es_service_with_mock.client.search.return_value = {
            "hits": {"hits": []}
        }
        
        # Execute hybrid search
        query_embeddings = {'audio': np.random.rand(128).astype(np.float32)}
        results = es_service_with_mock.hybrid_search(
            query_embeddings=query_embeddings,
            query_text="nonexistent_move",
            top_k=5
        )
        
        # Verify empty results
        assert len(results) == 0


class TestMetadataFiltering:
    """Test metadata filtering in hybrid search."""
    
    def test_filter_by_difficulty(self, es_service_with_mock):
        """Test filtering by difficulty level."""
        # Mock search response
        es_service_with_mock.client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_score": 0.90,
                        "fields": {
                            "clip_id": ["clip_005"],
                            "move_label": ["basic_step"],
                            "difficulty": ["beginner"],
                            "audio_embedding": list(np.random.rand(128)),
                            "lead_embedding": list(np.random.rand(512)),
                            "follow_embedding": list(np.random.rand(512)),
                            "interaction_embedding": list(np.random.rand(256)),
                            "text_embedding": list(np.random.rand(384)),
                            "quality_score": [0.85]
                        }
                    }
                ]
            }
        }
        
        # Execute search with difficulty filter
        query_embeddings = {'audio': np.random.rand(128).astype(np.float32)}
        results = es_service_with_mock.hybrid_search(
            query_embeddings=query_embeddings,
            filters={'difficulty': 'beginner'},
            top_k=5
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]['difficulty'] == 'beginner'
    
    def test_filter_by_multiple_fields(self, es_service_with_mock):
        """Test filtering by multiple metadata fields."""
        # Mock search response
        es_service_with_mock.client.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_score": 0.87,
                        "fields": {
                            "clip_id": ["clip_006"],
                            "move_label": ["energetic_turn"],
                            "difficulty": ["advanced"],
                            "energy_level": ["high"],
                            "audio_embedding": list(np.random.rand(128)),
                            "lead_embedding": list(np.random.rand(512)),
                            "follow_embedding": list(np.random.rand(512)),
                            "interaction_embedding": list(np.random.rand(256)),
                            "text_embedding": list(np.random.rand(384)),
                            "quality_score": [0.92]
                        }
                    }
                ]
            }
        }
        
        # Execute search with multiple filters
        query_embeddings = {'audio': np.random.rand(128).astype(np.float32)}
        results = es_service_with_mock.hybrid_search(
            query_embeddings=query_embeddings,
            filters={
                'difficulty': 'advanced',
                'energy_level': 'high'
            },
            top_k=5
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]['difficulty'] == 'advanced'
        assert results[0]['energy_level'] == 'high'


class TestWeightedSimilarity:
    """Test weighted similarity computation."""
    
    def test_custom_embedding_weights(self, es_service_with_mock):
        """Test hybrid search with custom embedding weights."""
        # Mock search response
        es_service_with_mock.client.search.return_value = {
            "hits": {"hits": []}
        }
        
        # Execute search with custom weights
        query_embeddings = {
            'audio': np.random.rand(128).astype(np.float32),
            'text': np.random.rand(384).astype(np.float32)
        }
        
        custom_weights = {
            'audio': 0.5,
            'text': 0.5,
            'lead': 0.0,
            'follow': 0.0,
            'interaction': 0.0
        }
        
        es_service_with_mock.hybrid_search(
            query_embeddings=query_embeddings,
            embedding_weights=custom_weights,
            top_k=5
        )
        
        # Verify search was called
        assert es_service_with_mock.client.search.called
    
    def test_default_weights(self, es_service_with_mock):
        """Test hybrid search with default equal weights."""
        # Mock search response
        es_service_with_mock.client.search.return_value = {
            "hits": {"hits": []}
        }
        
        # Execute search without custom weights (should use defaults)
        query_embeddings = {'audio': np.random.rand(128).astype(np.float32)}
        
        es_service_with_mock.hybrid_search(
            query_embeddings=query_embeddings,
            top_k=5
        )
        
        # Verify search was called
        assert es_service_with_mock.client.search.called


class TestRecommendationEngineHybridSearch:
    """Test RecommendationEngine integration with hybrid search."""
    
    @patch('ai_services.services.recommendation_engine.ElasticsearchService')
    def test_recommendation_with_hybrid_search(self, mock_es_class):
        """Test recommendations using hybrid search."""
        # Mock Elasticsearch service
        mock_es = MagicMock()
        mock_es_class.return_value = mock_es
        
        # Mock hybrid search response
        mock_es.hybrid_search.return_value = [
            {
                'clip_id': 'clip_007',
                'move_label': 'cross_body_lead',
                'difficulty': 'intermediate',
                'energy_level': 'medium',
                'audio_embedding': np.random.rand(128).astype(np.float32),
                'lead_embedding': np.random.rand(512).astype(np.float32),
                'follow_embedding': np.random.rand(512).astype(np.float32),
                'interaction_embedding': np.random.rand(256).astype(np.float32),
                'text_embedding': np.random.rand(384).astype(np.float32),
                'video_path': 'data/videos/clip_007.mp4',
                'quality_score': 0.85,
                'detection_rate': 0.90,
                'estimated_tempo': 120.0,
                'lead_follow_roles': 'both',
                'frame_count': 100,
                'processing_time': 5.0,
                'version': 'v1',
                'score': 0.92
            }
        ]
        
        # Create recommendation engine
        engine = RecommendationEngine(elasticsearch_service=mock_es)
        
        # Create recommendation request
        request = RecommendationRequest(
            query_audio_embedding=np.random.rand(128).astype(np.float32),
            query_text_embedding=np.random.rand(384).astype(np.float32),
            difficulty='intermediate'
        )
        
        # Get recommendations
        results = engine.recommend_moves(request, top_k=5, use_hybrid_search=True)
        
        # Verify hybrid search was called
        assert mock_es.hybrid_search.called
        
        # Verify results
        assert len(results) > 0
        assert results[0].move_candidate.clip_id == 'clip_007'
    
    @patch('ai_services.services.recommendation_engine.ElasticsearchService')
    def test_recommendation_fallback_to_get_all(self, mock_es_class):
        """Test fallback to get_all_embeddings when hybrid search fails."""
        # Mock Elasticsearch service
        mock_es = MagicMock()
        mock_es_class.return_value = mock_es
        
        # Mock hybrid search to raise exception
        mock_es.hybrid_search.side_effect = Exception("Hybrid search failed")
        
        # Mock get_all_embeddings response
        mock_es.get_all_embeddings.return_value = [
            {
                'clip_id': 'clip_008',
                'move_label': 'basic_step',
                'difficulty': 'beginner',
                'energy_level': 'low',
                'audio_embedding': np.random.rand(128).astype(np.float32),
                'lead_embedding': np.random.rand(512).astype(np.float32),
                'follow_embedding': np.random.rand(512).astype(np.float32),
                'interaction_embedding': np.random.rand(256).astype(np.float32),
                'text_embedding': np.random.rand(384).astype(np.float32),
                'video_path': 'data/videos/clip_008.mp4',
                'quality_score': 0.80,
                'detection_rate': 0.85,
                'estimated_tempo': 110.0,
                'lead_follow_roles': 'both',
                'frame_count': 90,
                'processing_time': 4.5,
                'version': 'v1'
            }
        ]
        
        # Create recommendation engine
        engine = RecommendationEngine(elasticsearch_service=mock_es)
        
        # Create recommendation request
        request = RecommendationRequest(
            query_audio_embedding=np.random.rand(128).astype(np.float32),
            difficulty='beginner'
        )
        
        # Get recommendations (should fallback to get_all_embeddings)
        results = engine.recommend_moves(request, top_k=5, use_hybrid_search=True)
        
        # Verify fallback was used
        assert mock_es.get_all_embeddings.called
        
        # Verify results
        assert len(results) > 0
        assert results[0].move_candidate.clip_id == 'clip_008'


class TestErrorHandling:
    """Test error handling in hybrid search."""
    
    def test_missing_query_parameters(self, es_service_with_mock):
        """Test error when no query parameters provided."""
        with pytest.raises(ValueError, match="Must provide either query_embeddings or query_text"):
            es_service_with_mock.hybrid_search(top_k=5)
    
    def test_retry_on_connection_error(self, es_service_with_mock):
        """Test retry logic on connection errors."""
        from elasticsearch.exceptions import ConnectionError
        
        # Mock search to fail twice then succeed
        es_service_with_mock.client.search.side_effect = [
            ConnectionError("Connection failed"),
            ConnectionError("Connection failed"),
            {
                "hits": {
                    "hits": [
                        {
                            "_score": 0.85,
                            "fields": {
                                "clip_id": ["clip_009"],
                                "move_label": ["test_move"],
                                "audio_embedding": list(np.random.rand(128)),
                                "lead_embedding": list(np.random.rand(512)),
                                "follow_embedding": list(np.random.rand(512)),
                                "interaction_embedding": list(np.random.rand(256)),
                                "text_embedding": list(np.random.rand(384)),
                                "quality_score": [0.80]
                            }
                        }
                    ]
                }
            }
        ]
        
        # Execute search (should retry and succeed)
        query_embeddings = {'audio': np.random.rand(128).astype(np.float32)}
        results = es_service_with_mock.hybrid_search(
            query_embeddings=query_embeddings,
            top_k=5,
            max_retries=3
        )
        
        # Verify results after retry
        assert len(results) == 1
        assert results[0]['clip_id'] == 'clip_009'
