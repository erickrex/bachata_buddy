"""
Integration tests for embedding pipeline.

These tests verify end-to-end functionality:
- Elasticsearch connectivity
- Text embedding generation and storage
- Recommendation engine with real embeddings
- Processing time validation

Note: Requires running Elasticsearch instance.
Run: docker run -p 9200:9200 -e "discovery.type=single-node" elasticsearch:9.1.0
"""

import pytest
import numpy as np
from pathlib import Path

from core.config.environment_config import EnvironmentConfig, ElasticsearchConfig
from core.services.elasticsearch_service import ElasticsearchService
from core.services.text_embedding_service import TextEmbeddingService
from core.services.recommendation_engine import RecommendationEngine


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def es_config():
    """Create test Elasticsearch configuration."""
    return ElasticsearchConfig(
        host="localhost",
        port=9200,
        index_name="test_integration_embeddings",
        use_ssl=False,
        verify_certs=False
    )


@pytest.fixture
def es_service(es_config):
    """Create Elasticsearch service for testing."""
    try:
        service = ElasticsearchService(es_config)
        
        # Clean up before test
        if service.index_exists():
            service.delete_index()
        
        yield service
        
        # Clean up after test
        if service.index_exists():
            service.delete_index()
        
        service.close()
    except Exception as e:
        pytest.skip(f"Elasticsearch not available: {e}")


@pytest.fixture
def text_service():
    """Create text embedding service."""
    return TextEmbeddingService()


@pytest.fixture
def sample_annotations():
    """Create sample annotations for testing."""
    return [
        {
            "clip_id": "basic_step_1",
            "move_label": "basic_step",
            "difficulty": "beginner",
            "energy_level": "medium",
            "lead_follow_roles": "both",
            "estimated_tempo": 110.0,
            "notes": "Fundamental step pattern"
        },
        {
            "clip_id": "cross_body_lead_1",
            "move_label": "cross_body_lead",
            "difficulty": "intermediate",
            "energy_level": "high",
            "lead_follow_roles": "both",
            "estimated_tempo": 120.0,
            "notes": "Turn pattern where follow crosses"
        },
        {
            "clip_id": "body_roll_1",
            "move_label": "body_roll",
            "difficulty": "advanced",
            "energy_level": "high",
            "lead_follow_roles": "follow_focus",
            "estimated_tempo": 115.0,
            "notes": "Sensual body movement"
        }
    ]


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestEmbeddingPipelineIntegration:
    """Integration tests for complete embedding pipeline."""
    
    def test_elasticsearch_connectivity(self, es_service):
        """Test that Elasticsearch is accessible."""
        assert es_service.client.ping()
    
    def test_create_index_with_mappings(self, es_service):
        """Test index creation with proper vector mappings."""
        es_service.create_index()
        
        assert es_service.index_exists()
        
        # Verify mappings
        mapping = es_service.client.indices.get_mapping(index=es_service.index_name)
        properties = mapping[es_service.index_name]["mappings"]["properties"]
        
        # Check all embedding fields exist
        assert "text_embedding" in properties
        assert "audio_embedding" in properties
        assert "lead_embedding" in properties
        assert "follow_embedding" in properties
        assert "interaction_embedding" in properties
    
    def test_text_embedding_generation(self, text_service, sample_annotations):
        """Test text embedding generation from annotations."""
        embeddings = []
        
        for annotation in sample_annotations:
            embedding = text_service.generate_embedding_from_annotation(annotation)
            embeddings.append(embedding)
        
        # Verify all embeddings generated
        assert len(embeddings) == 3
        
        # Verify dimensions
        for emb in embeddings:
            assert emb.shape == (384,)
            assert emb.dtype == np.float32
            
            # Verify normalized
            norm = np.linalg.norm(emb)
            assert np.isclose(norm, 1.0, atol=1e-5)
    
    def test_store_and_retrieve_embeddings(self, es_service, text_service, sample_annotations):
        """Test storing and retrieving embeddings from Elasticsearch."""
        # Create index
        es_service.create_index()
        
        # Generate and store embeddings
        documents = []
        for annotation in sample_annotations:
            text_emb = text_service.generate_embedding_from_annotation(annotation)
            
            # Create mock embeddings for other modalities
            doc = {
                "clip_id": annotation["clip_id"],
                "text_embedding": text_emb,
                "audio_embedding": np.random.randn(128).astype(np.float32),
                "lead_embedding": np.random.randn(512).astype(np.float32),
                "follow_embedding": np.random.randn(512).astype(np.float32),
                "interaction_embedding": np.random.randn(256).astype(np.float32),
                "move_label": annotation["move_label"],
                "difficulty": annotation["difficulty"],
                "energy_level": annotation["energy_level"],
                "quality_score": 0.85,
                "detection_rate": 0.90,
                "version": "mmpose_v1"
            }
            documents.append(doc)
        
        # Bulk index
        es_service.bulk_index_embeddings(documents)
        
        # Retrieve all
        retrieved = es_service.get_all_embeddings()
        
        assert len(retrieved) == 3
        
        # Verify structure
        for doc in retrieved:
            assert "clip_id" in doc
            assert "text_embedding" in doc
            assert doc["text_embedding"].shape == (384,)
    
    def test_retrieve_by_id(self, es_service, text_service, sample_annotations):
        """Test retrieving specific embedding by ID."""
        # Setup
        es_service.create_index()
        
        annotation = sample_annotations[0]
        text_emb = text_service.generate_embedding_from_annotation(annotation)
        
        doc = {
            "clip_id": annotation["clip_id"],
            "text_embedding": text_emb,
            "audio_embedding": np.random.randn(128).astype(np.float32),
            "lead_embedding": np.random.randn(512).astype(np.float32),
            "follow_embedding": np.random.randn(512).astype(np.float32),
            "interaction_embedding": np.random.randn(256).astype(np.float32),
            "move_label": annotation["move_label"],
            "difficulty": annotation["difficulty"]
        }
        
        es_service.bulk_index_embeddings([doc])
        
        # Retrieve by ID
        retrieved = es_service.get_embedding_by_id("basic_step_1")
        
        assert retrieved is not None
        assert retrieved["clip_id"] == "basic_step_1"
        assert retrieved["move_label"] == "basic_step"
    
    def test_filter_by_difficulty(self, es_service, text_service, sample_annotations):
        """Test filtering embeddings by metadata."""
        # Setup
        es_service.create_index()
        
        documents = []
        for annotation in sample_annotations:
            text_emb = text_service.generate_embedding_from_annotation(annotation)
            doc = {
                "clip_id": annotation["clip_id"],
                "text_embedding": text_emb,
                "audio_embedding": np.random.randn(128).astype(np.float32),
                "lead_embedding": np.random.randn(512).astype(np.float32),
                "follow_embedding": np.random.randn(512).astype(np.float32),
                "interaction_embedding": np.random.randn(256).astype(np.float32),
                "move_label": annotation["move_label"],
                "difficulty": annotation["difficulty"]
            }
            documents.append(doc)
        
        es_service.bulk_index_embeddings(documents)
        
        # Filter for beginner
        beginner_moves = es_service.get_all_embeddings(filters={"difficulty": "beginner"})
        
        assert len(beginner_moves) == 1
        assert beginner_moves[0]["difficulty"] == "beginner"
    
    def test_recommendation_engine_integration(self, es_service, text_service, sample_annotations):
        """Test recommendation engine with real embeddings."""
        # Setup
        es_service.create_index()
        
        documents = []
        for annotation in sample_annotations:
            text_emb = text_service.generate_embedding_from_annotation(annotation)
            doc = {
                "clip_id": annotation["clip_id"],
                "text_embedding": text_emb,
                "audio_embedding": np.random.randn(128).astype(np.float32),
                "lead_embedding": np.random.randn(512).astype(np.float32),
                "follow_embedding": np.random.randn(512).astype(np.float32),
                "interaction_embedding": np.random.randn(256).astype(np.float32),
                "move_label": annotation["move_label"],
                "difficulty": annotation["difficulty"]
            }
            documents.append(doc)
        
        es_service.bulk_index_embeddings(documents)
        
        # Create recommendation engine
        rec_engine = RecommendationEngine(elasticsearch_service=es_service)
        
        # Create query embeddings (use first annotation)
        query_annotation = sample_annotations[0]
        query_text_emb = text_service.generate_embedding_from_annotation(query_annotation)
        
        query_embeddings = {
            "text_embedding": query_text_emb,
            "audio_embedding": np.random.randn(128).astype(np.float32),
            "lead_embedding": np.random.randn(512).astype(np.float32),
            "follow_embedding": np.random.randn(512).astype(np.float32),
            "interaction_embedding": np.random.randn(256).astype(np.float32)
        }
        
        # Get recommendations
        recommendations = rec_engine.get_recommendations(query_embeddings, top_k=3)
        
        # Verify recommendations
        assert len(recommendations) == 3
        
        # Verify structure
        for rec in recommendations:
            assert "clip_id" in rec
            assert "overall_similarity" in rec
            assert "text_similarity" in rec
            assert "audio_similarity" in rec
            assert "lead_similarity" in rec
            assert "follow_similarity" in rec
            assert "interaction_similarity" in rec
            
            # Verify similarity scores are in valid range
            assert -1.0 <= rec["overall_similarity"] <= 1.0
    
    def test_processing_time_validation(self, text_service, sample_annotations):
        """Test that text embedding generation is fast (<5 seconds for 38 clips)."""
        import time
        
        # Simulate 38 clips
        annotations = sample_annotations * 13  # 3 * 13 = 39, close to 38
        
        start_time = time.time()
        
        embeddings = []
        for annotation in annotations:
            emb = text_service.generate_embedding_from_annotation(annotation)
            embeddings.append(emb)
        
        elapsed_time = time.time() - start_time
        
        # Should complete in <5 seconds
        assert elapsed_time < 5.0, f"Processing took {elapsed_time:.2f}s, expected <5s"
        
        # Verify all embeddings generated
        assert len(embeddings) == len(annotations)


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = pytest.mark.integration
