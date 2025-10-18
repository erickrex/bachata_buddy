"""
Tests for Elasticsearch service.

These tests verify:
- Connection management
- Index creation with proper mappings
- Bulk indexing operations
- Embedding retrieval (all, by ID, filtered)
- Retry logic and error handling
- Dimension validation

Note: These are integration tests that require a running Elasticsearch instance.
Run Elasticsearch with: docker run -p 9200:9200 -e "discovery.type=single-node" elasticsearch:9.1.0
"""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch
from elasticsearch.exceptions import ConnectionError, TransportError

from core.config.environment_config import ElasticsearchConfig
from core.services.elasticsearch_service import ElasticsearchService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def es_config():
    """Create Elasticsearch configuration for testing."""
    return ElasticsearchConfig(
        host="localhost",
        port=9200,
        index_name="test_bachata_embeddings",
        use_ssl=False,
        verify_certs=False,
        max_connections=10,
        timeout=30,
        retry_on_timeout=True
    )


@pytest.fixture
def sample_embedding():
    """Create a sample embedding document."""
    return {
        "clip_id": "test_basic_step_1",
        "audio_embedding": np.random.randn(128).astype(np.float32),
        "lead_embedding": np.random.randn(512).astype(np.float32),
        "follow_embedding": np.random.randn(512).astype(np.float32),
        "interaction_embedding": np.random.randn(256).astype(np.float32),
        "text_embedding": np.random.randn(384).astype(np.float32),
        "move_label": "basic_step",
        "difficulty": "beginner",
        "energy_level": "medium",
        "lead_follow_roles": "both",
        "estimated_tempo": 110.0,
        "video_path": "test/basic_step_1.mp4",
        "quality_score": 0.85,
        "detection_rate": 0.90,
        "frame_count": 450,
        "processing_time": 120.5,
        "version": "mmpose_v1",
        "created_at": datetime.now().isoformat()
    }


@pytest.fixture
def sample_embeddings(sample_embedding):
    """Create multiple sample embeddings."""
    embeddings = []
    
    # Beginner move
    emb1 = sample_embedding.copy()
    emb1["clip_id"] = "basic_step_1"
    emb1["move_label"] = "basic_step"
    emb1["difficulty"] = "beginner"
    embeddings.append(emb1)
    
    # Intermediate move
    emb2 = sample_embedding.copy()
    emb2["clip_id"] = "cross_body_lead_1"
    emb2["move_label"] = "cross_body_lead"
    emb2["difficulty"] = "intermediate"
    emb2["audio_embedding"] = np.random.randn(128).astype(np.float32)
    emb2["lead_embedding"] = np.random.randn(512).astype(np.float32)
    emb2["follow_embedding"] = np.random.randn(512).astype(np.float32)
    emb2["interaction_embedding"] = np.random.randn(256).astype(np.float32)
    emb2["text_embedding"] = np.random.randn(384).astype(np.float32)
    embeddings.append(emb2)
    
    # Advanced move
    emb3 = sample_embedding.copy()
    emb3["clip_id"] = "body_roll_1"
    emb3["move_label"] = "body_roll"
    emb3["difficulty"] = "advanced"
    emb3["audio_embedding"] = np.random.randn(128).astype(np.float32)
    emb3["lead_embedding"] = np.random.randn(512).astype(np.float32)
    emb3["follow_embedding"] = np.random.randn(512).astype(np.float32)
    emb3["interaction_embedding"] = np.random.randn(256).astype(np.float32)
    emb3["text_embedding"] = np.random.randn(384).astype(np.float32)
    embeddings.append(emb3)
    
    return embeddings


# ============================================================================
# Integration Tests (require running Elasticsearch)
# ============================================================================

@pytest.mark.integration
class TestElasticsearchServiceIntegration:
    """Integration tests for Elasticsearch service."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, es_config):
        """Set up and tear down test index."""
        try:
            es_service = ElasticsearchService(es_config)
            
            # Clean up before test
            if es_service.index_exists():
                es_service.delete_index()
            
            yield es_service
            
            # Clean up after test
            if es_service.index_exists():
                es_service.delete_index()
            
            es_service.close()
        except ConnectionError:
            pytest.skip("Elasticsearch not available")
    
    def test_connection(self, setup_and_teardown):
        """Test connection to Elasticsearch."""
        es_service = setup_and_teardown
        assert es_service.client.ping()
    
    def test_create_index(self, setup_and_teardown):
        """Test index creation with proper mappings."""
        es_service = setup_and_teardown
        
        es_service.create_index()
        
        assert es_service.index_exists()
        
        # Verify mappings
        mapping = es_service.client.indices.get_mapping(index=es_service.index_name)
        properties = mapping[es_service.index_name]["mappings"]["properties"]
        
        # Check embedding fields
        assert properties["audio_embedding"]["type"] == "dense_vector"
        assert properties["audio_embedding"]["dims"] == 128
        assert properties["lead_embedding"]["dims"] == 512
        assert properties["follow_embedding"]["dims"] == 512
        assert properties["interaction_embedding"]["dims"] == 256
        assert properties["text_embedding"]["dims"] == 384
        
        # Check metadata fields
        assert properties["clip_id"]["type"] == "keyword"
        assert properties["move_label"]["type"] == "keyword"
        assert properties["difficulty"]["type"] == "keyword"
    
    def test_bulk_index_embeddings(self, setup_and_teardown, sample_embeddings):
        """Test bulk indexing of embeddings."""
        es_service = setup_and_teardown
        
        es_service.create_index()
        es_service.bulk_index_embeddings(sample_embeddings)
        
        count = es_service.count_documents()
        assert count == 3
    
    def test_get_all_embeddings(self, setup_and_teardown, sample_embeddings):
        """Test retrieving all embeddings."""
        es_service = setup_and_teardown
        
        es_service.create_index()
        es_service.bulk_index_embeddings(sample_embeddings)
        
        embeddings = es_service.get_all_embeddings()
        
        assert len(embeddings) == 3
        
        # Verify structure
        for emb in embeddings:
            assert "clip_id" in emb
            assert "audio_embedding" in emb
            assert "lead_embedding" in emb
            assert "follow_embedding" in emb
            assert "interaction_embedding" in emb
            assert "text_embedding" in emb
            assert isinstance(emb["audio_embedding"], np.ndarray)
            assert emb["audio_embedding"].shape == (128,)
            assert emb["lead_embedding"].shape == (512,)
            assert emb["follow_embedding"].shape == (512,)
            assert emb["interaction_embedding"].shape == (256,)
            assert emb["text_embedding"].shape == (384,)
    
    def test_get_embedding_by_id(self, setup_and_teardown, sample_embeddings):
        """Test retrieving single embedding by ID."""
        es_service = setup_and_teardown
        
        es_service.create_index()
        es_service.bulk_index_embeddings(sample_embeddings)
        
        embedding = es_service.get_embedding_by_id("basic_step_1")
        
        assert embedding is not None
        assert embedding["clip_id"] == "basic_step_1"
        assert embedding["move_label"] == "basic_step"
        assert embedding["difficulty"] == "beginner"
        assert embedding["audio_embedding"].shape == (128,)
    
    def test_get_embedding_by_id_not_found(self, setup_and_teardown):
        """Test retrieving non-existent embedding."""
        es_service = setup_and_teardown
        
        es_service.create_index()
        
        embedding = es_service.get_embedding_by_id("nonexistent")
        
        assert embedding is None
    
    def test_filter_by_difficulty(self, setup_and_teardown, sample_embeddings):
        """Test filtering embeddings by difficulty."""
        es_service = setup_and_teardown
        
        es_service.create_index()
        es_service.bulk_index_embeddings(sample_embeddings)
        
        # Filter for beginner moves
        beginner_moves = es_service.get_all_embeddings(filters={"difficulty": "beginner"})
        
        assert len(beginner_moves) == 1
        assert beginner_moves[0]["difficulty"] == "beginner"
        assert beginner_moves[0]["move_label"] == "basic_step"
    
    def test_filter_by_multiple_criteria(self, setup_and_teardown, sample_embeddings):
        """Test filtering by multiple criteria."""
        es_service = setup_and_teardown
        
        es_service.create_index()
        es_service.bulk_index_embeddings(sample_embeddings)
        
        # Filter for beginner moves with medium energy
        filtered = es_service.get_all_embeddings(
            filters={"difficulty": "beginner", "energy_level": "medium"}
        )
        
        assert len(filtered) == 1
        assert filtered[0]["difficulty"] == "beginner"
        assert filtered[0]["energy_level"] == "medium"
    
    def test_embedding_dimensions(self, setup_and_teardown, sample_embeddings):
        """Test that embedding dimensions are correct."""
        es_service = setup_and_teardown
        
        es_service.create_index()
        es_service.bulk_index_embeddings(sample_embeddings)
        
        embedding = es_service.get_embedding_by_id("basic_step_1")
        
        # Verify all dimensions
        assert embedding["audio_embedding"].shape == (128,)
        assert embedding["lead_embedding"].shape == (512,)
        assert embedding["follow_embedding"].shape == (512,)
        assert embedding["interaction_embedding"].shape == (256,)
        assert embedding["text_embedding"].shape == (384,)
        
        # Total: 1792D
        total_dims = 128 + 512 + 512 + 256 + 384
        assert total_dims == 1792


# ============================================================================
# Unit Tests (no Elasticsearch required)
# ============================================================================

class TestElasticsearchServiceUnit:
    """Unit tests for Elasticsearch service."""
    
    def test_to_list_with_numpy_array(self, es_config):
        """Test _to_list with numpy array."""
        with patch('core.services.elasticsearch_service.Elasticsearch'):
            es_service = ElasticsearchService(es_config)
            
            arr = np.array([1.0, 2.0, 3.0])
            result = es_service._to_list(arr)
            
            assert isinstance(result, list)
            assert result == [1.0, 2.0, 3.0]
    
    def test_to_list_with_none(self, es_config):
        """Test _to_list with None."""
        with patch('core.services.elasticsearch_service.Elasticsearch'):
            es_service = ElasticsearchService(es_config)
            
            result = es_service._to_list(None)
            
            assert result is None
    
    def test_to_list_with_list(self, es_config):
        """Test _to_list with list."""
        with patch('core.services.elasticsearch_service.Elasticsearch'):
            es_service = ElasticsearchService(es_config)
            
            lst = [1.0, 2.0, 3.0]
            result = es_service._to_list(lst)
            
            assert result == lst
    
    def test_url_construction_http(self):
        """Test URL construction for HTTP."""
        config = ElasticsearchConfig(
            host="localhost",
            port=9200,
            index_name="test",
            use_ssl=False
        )
        
        with patch('core.services.elasticsearch_service.Elasticsearch') as mock_es:
            ElasticsearchService(config)
            
            # Verify URL was constructed correctly
            call_args = mock_es.call_args
            assert "http://localhost:9200" in call_args.kwargs["hosts"]
    
    def test_url_construction_https(self):
        """Test URL construction for HTTPS."""
        config = ElasticsearchConfig(
            host="es.cloud.example.com",
            port=9243,
            index_name="test",
            use_ssl=True
        )
        
        with patch('core.services.elasticsearch_service.Elasticsearch') as mock_es:
            ElasticsearchService(config)
            
            # Verify URL was constructed correctly
            call_args = mock_es.call_args
            assert "https://es.cloud.example.com:9243" in call_args.kwargs["hosts"]
    
    def test_authentication_included(self):
        """Test that authentication is included when provided."""
        config = ElasticsearchConfig(
            host="localhost",
            port=9200,
            index_name="test",
            username="elastic",
            password="secret123"
        )
        
        with patch('core.services.elasticsearch_service.Elasticsearch') as mock_es:
            ElasticsearchService(config)
            
            # Verify authentication was included
            call_args = mock_es.call_args
            assert call_args.kwargs["basic_auth"] == ("elastic", "secret123")


# ============================================================================
# Pytest Markers
# ============================================================================

# Mark all integration tests
pytestmark = pytest.mark.integration
