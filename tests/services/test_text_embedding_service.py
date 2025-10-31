"""
Tests for Text Embedding Service.

These tests verify:
- Text embedding model initialization
- Natural language description generation from annotations
- 384D text embedding generation
- L2 normalization
- Error handling for missing annotations
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from ai_services.services.text_embedding_service import TextEmbeddingService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_annotation():
    """Create a sample annotation."""
    return {
        "move_label": "cross_body_lead",
        "difficulty": "intermediate",
        "energy_level": "high",
        "lead_follow_roles": "both",
        "estimated_tempo": 120.0,
        "notes": "A fundamental turn pattern where the follow crosses in front of the lead"
    }


@pytest.fixture
def incomplete_annotation():
    """Create an incomplete annotation (missing notes)."""
    return {
        "move_label": "basic_step",
        "difficulty": "beginner",
        "energy_level": "medium",
        "lead_follow_roles": "both",
        "estimated_tempo": 110.0
    }


# ============================================================================
# Unit Tests
# ============================================================================

class TestTextEmbeddingService:
    """Unit tests for TextEmbeddingService."""
    
    def test_initialization(self):
        """Test service initialization."""
        with patch('ai_services.services.text_embedding_service.SentenceTransformer') as mock_st:
            service = TextEmbeddingService()
            
            # Verify model was loaded
            mock_st.assert_called_once_with('all-MiniLM-L6-v2')
            assert service.model is not None
    
    def test_create_text_description_complete(self, sample_annotation):
        """Test text description generation with complete annotation."""
        with patch('ai_services.services.text_embedding_service.SentenceTransformer'):
            service = TextEmbeddingService()
            
            description = service.create_text_description(sample_annotation)
            
            # Verify all fields are included
            assert "Dance move: Cross Body Lead" in description
            assert "Difficulty: intermediate" in description
            assert "Energy: high" in description
            assert "Role focus: both" in description
            assert "Tempo: 120.0 BPM" in description
            assert "Description: A fundamental turn pattern" in description
    
    def test_create_text_description_incomplete(self, incomplete_annotation):
        """Test text description generation with incomplete annotation."""
        with patch('ai_services.services.text_embedding_service.SentenceTransformer'):
            service = TextEmbeddingService()
            
            description = service.create_text_description(incomplete_annotation)
            
            # Verify required fields are included
            assert "Dance move: Basic Step" in description
            assert "Difficulty: beginner" in description
            assert "Energy: medium" in description
            assert "Role focus: both" in description
            assert "Tempo: 110.0 BPM" in description
            # Notes should not be included
            assert "Description:" not in description
    
    def test_move_label_formatting(self):
        """Test move label formatting (underscores to spaces, title case)."""
        with patch('ai_services.services.text_embedding_service.SentenceTransformer'):
            service = TextEmbeddingService()
            
            annotation = {
                "move_label": "double_cross_body_lead",
                "difficulty": "advanced",
                "energy_level": "high",
                "lead_follow_roles": "both",
                "estimated_tempo": 130.0
            }
            
            description = service.create_text_description(annotation)
            
            assert "Dance move: Double Cross Body Lead" in description
    
    def test_generate_text_embedding_dimensions(self, sample_annotation):
        """Test that generated embeddings have correct dimensions (384D)."""
        with patch('ai_services.services.text_embedding_service.SentenceTransformer') as mock_st:
            # Mock the model to return a 384D embedding
            mock_model = MagicMock()
            mock_embedding = np.random.randn(384).astype(np.float32)
            mock_model.encode.return_value = mock_embedding
            mock_st.return_value = mock_model
            
            service = TextEmbeddingService()
            embedding = service.generate_embedding_from_annotation(sample_annotation)
            
            assert embedding.shape == (384,)
            assert embedding.dtype == np.float32
    
    def test_generate_text_embedding_normalization(self, sample_annotation):
        """Test that embeddings are L2 normalized."""
        with patch('ai_services.services.text_embedding_service.SentenceTransformer') as mock_st:
            # Mock the model to return a normalized embedding (as the real model would)
            mock_model = MagicMock()
            # Create a normalized vector
            vec = np.array([3.0, 4.0] + [0.0] * 382, dtype=np.float32)
            normalized_vec = vec / np.linalg.norm(vec)
            mock_model.encode.return_value = normalized_vec
            mock_st.return_value = mock_model
            
            service = TextEmbeddingService()
            embedding = service.generate_embedding_from_annotation(sample_annotation)
            
            # Verify L2 norm is 1.0 (normalized)
            norm = np.linalg.norm(embedding)
            assert np.isclose(norm, 1.0, atol=1e-5)
    
    def test_generate_text_embedding_calls_encode(self, sample_annotation):
        """Test that generate_embedding_from_annotation calls model.encode with correct parameters."""
        with patch('ai_services.services.text_embedding_service.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_embedding = np.random.randn(384).astype(np.float32)
            mock_model.encode.return_value = mock_embedding
            mock_st.return_value = mock_model
            
            service = TextEmbeddingService()
            service.generate_embedding_from_annotation(sample_annotation)
            
            # Verify encode was called with normalize_embeddings=True
            mock_model.encode.assert_called_once()
            call_args = mock_model.encode.call_args
            assert call_args.kwargs.get('normalize_embeddings') is True
    
    def test_handle_missing_fields_gracefully(self):
        """Test handling of annotations with missing fields."""
        with patch('ai_services.services.text_embedding_service.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_embedding = np.random.randn(384).astype(np.float32)
            mock_model.encode.return_value = mock_embedding
            mock_st.return_value = mock_model
            
            service = TextEmbeddingService()
            
            # Annotation with minimal fields
            minimal_annotation = {
                "move_label": "test_move",
                "difficulty": "beginner"
            }
            
            # Should not raise an error
            embedding = service.generate_embedding_from_annotation(minimal_annotation)
            assert embedding.shape == (384,)
    
    def test_model_caching(self):
        """Test that model is cached and reused."""
        with patch('ai_services.services.text_embedding_service.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_st.return_value = mock_model
            
            service = TextEmbeddingService()
            
            # Verify model was loaded once
            assert mock_st.call_count == 1
            
            # Multiple calls should use the same model instance
            assert service.model is mock_model
    
    def test_batch_processing_efficiency(self, sample_annotation):
        """Test that service can process multiple annotations efficiently."""
        with patch('ai_services.services.text_embedding_service.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_embedding = np.random.randn(384).astype(np.float32)
            mock_model.encode.return_value = mock_embedding
            mock_st.return_value = mock_model
            
            service = TextEmbeddingService()
            
            # Process multiple annotations
            annotations = [sample_annotation] * 38
            embeddings = [service.generate_embedding_from_annotation(ann) for ann in annotations]
            
            # Verify all embeddings were generated
            assert len(embeddings) == 38
            
            # Verify model was loaded only once (cached)
            assert mock_st.call_count == 1
            
            # Verify encode was called 38 times
            assert mock_model.encode.call_count == 38


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = pytest.mark.unit
