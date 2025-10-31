"""
Embedding Validator

Validates embeddings for NaN/Inf values and correct dimensions.
Provides comprehensive validation for all embedding types in the system.

Requirements: 10.3, 10.4
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EmbeddingValidator:
    """
    Validates embeddings for quality and correctness.
    
    Checks:
    - NaN values
    - Inf values
    - Correct dimensionality
    - Value ranges
    """
    
    # Expected dimensions for each embedding type
    EXPECTED_DIMENSIONS = {
        'lead_embedding': 512,
        'follow_embedding': 512,
        'interaction_embedding': 256,
        'text_embedding': 384,
        'audio_embedding': 128,
    }
    
    def __init__(self):
        """Initialize embedding validator."""
        logger.info("EmbeddingValidator initialized")
    
    def validate_embedding(self, embedding: np.ndarray, 
                          embedding_type: str,
                          check_normalized: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Validate a single embedding.
        
        Args:
            embedding: Embedding array to validate
            embedding_type: Type of embedding (e.g., 'lead_embedding', 'audio_embedding')
            check_normalized: Whether to check if embedding is L2-normalized
        
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if embedding is valid
            - error_message: None if valid, error description if invalid
        """
        # Check if embedding is numpy array
        if not isinstance(embedding, np.ndarray):
            return False, f"{embedding_type}: Not a numpy array (type: {type(embedding)})"
        
        # Check for NaN values
        if np.any(np.isnan(embedding)):
            nan_count = np.sum(np.isnan(embedding))
            return False, f"{embedding_type}: Contains {nan_count} NaN values"
        
        # Check for Inf values
        if np.any(np.isinf(embedding)):
            inf_count = np.sum(np.isinf(embedding))
            return False, f"{embedding_type}: Contains {inf_count} Inf values"
        
        # Check dimensionality
        expected_dim = self.EXPECTED_DIMENSIONS.get(embedding_type)
        if expected_dim is not None:
            if embedding.shape != (expected_dim,):
                return False, (
                    f"{embedding_type}: Invalid dimension. "
                    f"Expected ({expected_dim},), got {embedding.shape}"
                )
        
        # Check if normalized (optional)
        if check_normalized:
            norm = np.linalg.norm(embedding)
            if not np.isclose(norm, 1.0, atol=1e-5):
                return False, (
                    f"{embedding_type}: Not L2-normalized. "
                    f"Norm is {norm:.6f}, expected 1.0"
                )
        
        # All checks passed
        return True, None
    
    def validate_all_embeddings(self, embedding_document: Dict,
                               check_normalized: bool = False) -> Tuple[bool, List[str]]:
        """
        Validate all embeddings in a document.
        
        Args:
            embedding_document: Dictionary containing all embeddings
            check_normalized: Whether to check if embeddings are L2-normalized
        
        Returns:
            Tuple of (all_valid, error_messages)
            - all_valid: True if all embeddings are valid
            - error_messages: List of error messages (empty if all valid)
        """
        errors = []
        
        # Validate each embedding type
        for embedding_type in self.EXPECTED_DIMENSIONS.keys():
            if embedding_type in embedding_document:
                embedding = embedding_document[embedding_type]
                
                # Convert to numpy array if it's a list
                if isinstance(embedding, list):
                    embedding = np.array(embedding, dtype=np.float32)
                
                is_valid, error_msg = self.validate_embedding(
                    embedding, embedding_type, check_normalized
                )
                
                if not is_valid:
                    errors.append(error_msg)
                    logger.error(f"✗ Validation failed: {error_msg}")
                else:
                    logger.debug(f"✓ {embedding_type} validated successfully")
            else:
                logger.warning(f"⚠ {embedding_type} not found in document")
        
        all_valid = len(errors) == 0
        
        if all_valid:
            logger.info("✓ All embeddings validated successfully")
        else:
            logger.error(f"✗ Validation failed with {len(errors)} errors")
        
        return all_valid, errors
    
    def validate_batch(self, embedding_documents: List[Dict],
                      check_normalized: bool = False) -> Tuple[int, int, List[Dict]]:
        """
        Validate a batch of embedding documents.
        
        Args:
            embedding_documents: List of embedding documents
            check_normalized: Whether to check if embeddings are L2-normalized
        
        Returns:
            Tuple of (valid_count, invalid_count, invalid_documents)
            - valid_count: Number of valid documents
            - invalid_count: Number of invalid documents
            - invalid_documents: List of invalid documents with error details
        """
        valid_count = 0
        invalid_count = 0
        invalid_documents = []
        
        logger.info(f"Validating batch of {len(embedding_documents)} documents...")
        
        for doc in embedding_documents:
            clip_id = doc.get('clip_id', 'unknown')
            
            is_valid, errors = self.validate_all_embeddings(doc, check_normalized)
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                invalid_documents.append({
                    'clip_id': clip_id,
                    'errors': errors
                })
                logger.warning(f"⚠ Document {clip_id} failed validation: {errors}")
        
        logger.info(
            f"Batch validation complete: "
            f"{valid_count} valid, {invalid_count} invalid"
        )
        
        return valid_count, invalid_count, invalid_documents
    
    def get_embedding_statistics(self, embedding: np.ndarray) -> Dict:
        """
        Get statistics about an embedding.
        
        Args:
            embedding: Embedding array
        
        Returns:
            Dictionary containing statistics
        """
        return {
            'shape': embedding.shape,
            'dtype': str(embedding.dtype),
            'min': float(np.min(embedding)),
            'max': float(np.max(embedding)),
            'mean': float(np.mean(embedding)),
            'std': float(np.std(embedding)),
            'norm': float(np.linalg.norm(embedding)),
            'has_nan': bool(np.any(np.isnan(embedding))),
            'has_inf': bool(np.any(np.isinf(embedding))),
            'zero_count': int(np.sum(embedding == 0)),
        }
    
    def log_embedding_statistics(self, embedding_document: Dict):
        """
        Log statistics for all embeddings in a document.
        
        Args:
            embedding_document: Dictionary containing all embeddings
        """
        clip_id = embedding_document.get('clip_id', 'unknown')
        
        logger.info(f"\nEmbedding Statistics for {clip_id}:")
        logger.info("=" * 60)
        
        for embedding_type in self.EXPECTED_DIMENSIONS.keys():
            if embedding_type in embedding_document:
                embedding = embedding_document[embedding_type]
                
                # Convert to numpy array if it's a list
                if isinstance(embedding, list):
                    embedding = np.array(embedding, dtype=np.float32)
                
                stats = self.get_embedding_statistics(embedding)
                
                logger.info(f"\n{embedding_type}:")
                logger.info(f"  Shape: {stats['shape']}")
                logger.info(f"  Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
                logger.info(f"  Mean: {stats['mean']:.4f}, Std: {stats['std']:.4f}")
                logger.info(f"  Norm: {stats['norm']:.4f}")
                logger.info(f"  Zero count: {stats['zero_count']}")
                
                if stats['has_nan']:
                    logger.warning(f"  ⚠ Contains NaN values!")
                if stats['has_inf']:
                    logger.warning(f"  ⚠ Contains Inf values!")
        
        logger.info("=" * 60)
    
    def reject_invalid_embedding(self, embedding_document: Dict,
                                errors: List[str]) -> None:
        """
        Reject an invalid embedding with clear error messages.
        
        Args:
            embedding_document: Invalid embedding document
            errors: List of error messages
        
        Raises:
            ValueError: Always raises with detailed error information
        """
        clip_id = embedding_document.get('clip_id', 'unknown')
        video_path = embedding_document.get('video_path', 'unknown')
        
        error_msg = (
            f"Invalid embeddings detected for clip '{clip_id}' ({video_path}):\n"
            + "\n".join(f"  - {error}" for error in errors)
            + "\n\nThe embedding has been rejected and will not be indexed."
        )
        
        logger.error(f"✗ {error_msg}")
        raise ValueError(error_msg)


# Convenience function for quick validation
def validate_embedding_document(embedding_document: Dict,
                               check_normalized: bool = False,
                               raise_on_error: bool = True) -> bool:
    """
    Convenience function to validate an embedding document.
    
    Args:
        embedding_document: Dictionary containing all embeddings
        check_normalized: Whether to check if embeddings are L2-normalized
        raise_on_error: Whether to raise exception on validation failure
    
    Returns:
        True if valid, False otherwise (if raise_on_error=False)
    
    Raises:
        ValueError: If validation fails and raise_on_error=True
    """
    validator = EmbeddingValidator()
    is_valid, errors = validator.validate_all_embeddings(
        embedding_document, check_normalized
    )
    
    if not is_valid and raise_on_error:
        validator.reject_invalid_embedding(embedding_document, errors)
    
    return is_valid
