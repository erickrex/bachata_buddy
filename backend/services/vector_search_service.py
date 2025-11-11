"""
Vector search service for finding similar dance moves using FAISS.

This service provides in-memory vector similarity search using FAISS (Facebook AI Similarity Search)
for efficient nearest neighbor search. It loads move embeddings from the database, builds a FAISS
index, and provides fast similarity search with metadata filtering.

Features:
- FAISS-based similarity search with IndexFlatIP (inner product for cosine similarity)
- In-memory caching of embeddings and FAISS index (1-hour TTL)
- Metadata filtering (difficulty, energy_level, style)
- Fallback to NumPy-based search if FAISS fails
- Automatic embedding normalization for cosine similarity
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

logger = logging.getLogger(__name__)


@dataclass
class MoveResult:
    """Result from vector search."""
    move_id: str
    move_name: str
    video_path: str
    similarity_score: float
    difficulty: str
    energy_level: str
    style: str
    duration: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'move_id': self.move_id,
            'move_name': self.move_name,
            'video_path': self.video_path,
            'similarity_score': float(self.similarity_score),
            'difficulty': self.difficulty,
            'energy_level': self.energy_level,
            'style': self.style,
            'duration': self.duration,
        }


class VectorSearchService:
    """
    In-memory vector search service using FAISS.
    
    This service loads move embeddings from the database into memory and builds
    a FAISS index for fast similarity search. The index is cached for 1 hour to
    avoid repeated database queries and index building.
    
    FAISS IndexFlatIP is used for exact inner product search, which with normalized
    embeddings gives us cosine similarity.
    """
    
    # Embedding dimensions (from generation pipeline)
    POSE_EMBEDDING_DIM = 512
    AUDIO_EMBEDDING_DIM = 128  # Music analyzer generates 128-dim embeddings
    TEXT_EMBEDDING_DIM = 384
    
    # Embedding weights
    POSE_WEIGHT = 0.35
    AUDIO_WEIGHT = 0.35
    TEXT_WEIGHT = 0.30
    
    @staticmethod
    def combine_embeddings_weighted(
        pose_embedding: Optional[np.ndarray],
        audio_embedding: Optional[np.ndarray],
        text_embedding: Optional[np.ndarray],
        pose_weight: float = 0.35,
        audio_weight: float = 0.35,
        text_weight: float = 0.30
    ) -> np.ndarray:
        """
        Combine multiple embeddings with weighted normalization.
        
        This method ensures consistent embedding combination for both
        stored move embeddings and query embeddings.
        
        Process:
        1. Normalize each embedding to unit length
        2. Apply the specified weight to each
        3. Concatenate the weighted embeddings
        
        Args:
            pose_embedding: Pose embedding vector (or None)
            audio_embedding: Audio embedding vector (or None)
            text_embedding: Text embedding vector (or None)
            pose_weight: Weight for pose component (default: 0.35)
            audio_weight: Weight for audio component (default: 0.35)
            text_weight: Weight for text component (default: 0.30)
        
        Returns:
            Combined weighted embedding vector
        
        Raises:
            ValueError: If all embeddings are None
        """
        # Validate at least one embedding is provided
        if pose_embedding is None and audio_embedding is None and text_embedding is None:
            raise ValueError("At least one embedding must be provided")
        
        # Handle None embeddings by creating zero vectors
        if pose_embedding is None:
            pose_embedding = np.zeros(VectorSearchService.POSE_EMBEDDING_DIM, dtype=np.float32)
            logger.debug("Using zero vector for pose embedding")
        else:
            pose_embedding = np.array(pose_embedding, dtype=np.float32)
        
        if audio_embedding is None:
            audio_embedding = np.zeros(VectorSearchService.AUDIO_EMBEDDING_DIM, dtype=np.float32)
            logger.debug("Using zero vector for audio embedding")
        else:
            audio_embedding = np.array(audio_embedding, dtype=np.float32)
        
        if text_embedding is None:
            text_embedding = np.zeros(VectorSearchService.TEXT_EMBEDDING_DIM, dtype=np.float32)
            logger.debug("Using zero vector for text embedding")
        else:
            text_embedding = np.array(text_embedding, dtype=np.float32)
        
        # Normalize each embedding to unit length
        pose_norm = np.linalg.norm(pose_embedding)
        audio_norm = np.linalg.norm(audio_embedding)
        text_norm = np.linalg.norm(text_embedding)
        
        # Avoid division by zero
        pose_emb_normalized = pose_embedding / (pose_norm + 1e-8)
        audio_emb_normalized = audio_embedding / (audio_norm + 1e-8)
        text_emb_normalized = text_embedding / (text_norm + 1e-8)
        
        # Apply weights to normalized embeddings
        weighted_pose = pose_emb_normalized * pose_weight
        weighted_audio = audio_emb_normalized * audio_weight
        weighted_text = text_emb_normalized * text_weight
        
        # Concatenate weighted embeddings
        combined_emb = np.concatenate([weighted_pose, weighted_audio, weighted_text])
        
        logger.debug(
            f"Combined embedding: pose_dim={len(pose_embedding)}, "
            f"audio_dim={len(audio_embedding)}, text_dim={len(text_embedding)}, "
            f"combined_dim={len(combined_emb)}"
        )
        
        return combined_emb
    
    def __init__(self, cache_ttl_seconds: int = 3600, use_gpu: Optional[bool] = None):
        """
        Initialize vector search service.
        
        Args:
            cache_ttl_seconds: Time-to-live for cached embeddings and index (default: 1 hour)
            use_gpu: Whether to use GPU acceleration (None = auto-detect)
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        self.faiss_index = None
        self.move_metadata = []
        self.embeddings = None
        self.embedding_dimension = None
        self.cache_timestamp = None
        self.use_faiss = FAISS_AVAILABLE
        
        # GPU configuration
        self.use_gpu = self._should_use_gpu(use_gpu)
        self.gpu_resources = None
        
        if not FAISS_AVAILABLE:
            logger.warning(
                "FAISS is not available. Falling back to NumPy-based search. "
                "Install FAISS for better performance: pip install faiss-cpu"
            )
        
        # Initialize GPU resources if needed
        if self.use_gpu:
            self._init_gpu_resources()
        
        logger.info(
            f"VectorSearchService initialized (FAISS: {self.use_faiss}, GPU: {self.use_gpu})"
        )
    
    def _should_use_gpu(self, use_gpu: Optional[bool]) -> bool:
        """
        Determine if GPU should be used for FAISS.
        
        Args:
            use_gpu: Explicit GPU preference (None = auto-detect)
        
        Returns:
            True if GPU should be used, False otherwise
        """
        # If explicitly set, use that value
        if use_gpu is not None:
            if use_gpu and not FAISS_AVAILABLE:
                logger.warning("GPU requested but FAISS not available")
                return False
            return use_gpu
        
        # Auto-detect from configuration
        try:
            from services.gpu_utils import GPUConfig, check_faiss_gpu_available
            
            config = GPUConfig()
            if not config.faiss_gpu:
                logger.debug("FAISS GPU disabled in configuration")
                return False
            
            # Check if FAISS GPU is actually available
            gpu_available = check_faiss_gpu_available()
            if gpu_available:
                logger.info("FAISS GPU detected and enabled")
            else:
                logger.info("FAISS GPU not available, using CPU")
            
            return gpu_available
            
        except Exception as e:
            logger.warning(f"Error checking GPU availability: {e}")
            return False
    
    def _init_gpu_resources(self) -> None:
        """
        Initialize GPU resources for FAISS.
        
        This method sets up the GPU resources needed for FAISS GPU operations.
        If initialization fails, it falls back to CPU mode.
        """
        if not FAISS_AVAILABLE:
            logger.warning("Cannot initialize GPU resources: FAISS not available")
            self.use_gpu = False
            return
        
        try:
            # Check if FAISS has GPU support
            if not hasattr(faiss, 'StandardGpuResources'):
                logger.warning("FAISS GPU not available (faiss-cpu installed?)")
                self.use_gpu = False
                return
            
            # Initialize GPU resources
            self.gpu_resources = faiss.StandardGpuResources()
            
            # Configure GPU memory
            try:
                from services.gpu_utils import GPUConfig
                config = GPUConfig()
                
                # Set memory fraction (FAISS uses bytes, not fraction)
                # We'll let FAISS manage memory automatically
                logger.info(
                    f"GPU resources initialized (memory fraction: {config.memory_fraction})"
                )
            except Exception as e:
                logger.warning(f"Could not load GPU config: {e}")
            
            logger.info("FAISS GPU resources initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GPU resources: {e}")
            logger.info("Falling back to CPU mode")
            self.use_gpu = False
            self.gpu_resources = None
    
    def load_embeddings_from_db(self) -> None:
        """
        Load all move embeddings from database into memory.
        
        This method queries the MoveEmbedding model and loads all embeddings
        into memory. It also builds the FAISS index for fast similarity search.
        
        The embeddings are cached for cache_ttl_seconds to avoid repeated
        database queries.
        
        Raises:
            ImportError: If MoveEmbedding model cannot be imported
            ValueError: If no embeddings found in database
        """
        # Check if cache is still valid
        if self._is_cache_valid():
            logger.debug("Using cached embeddings")
            return
        
        logger.info("Loading embeddings from database...")
        
        try:
            # Import here to avoid circular dependencies
            from apps.choreography.models import MoveEmbedding
        except ImportError:
            logger.error("MoveEmbedding model not found. Has it been created yet?")
            raise ImportError(
                "MoveEmbedding model not found. "
                "Please ensure the model is created and migrations are run."
            )
        
        # Query all move embeddings
        move_embeddings = MoveEmbedding.objects.all()
        
        if not move_embeddings.exists():
            logger.warning("No move embeddings found in database")
            raise ValueError(
                "No move embeddings found in database. "
                "Please run the embedding generation script first."
            )
        
        # Extract embeddings and metadata
        embeddings_list = []
        metadata_list = []
        
        for move_emb in move_embeddings:
            # Use the centralized weighted combination method
            combined_emb = self.combine_embeddings_weighted(
                pose_embedding=move_emb.pose_embedding,
                audio_embedding=move_emb.audio_embedding,
                text_embedding=move_emb.text_embedding
            )
            embeddings_list.append(combined_emb)
            
            # Store metadata
            metadata_list.append({
                'move_id': move_emb.move_id,
                'move_name': move_emb.move_name,
                'video_path': move_emb.video_path,
                'difficulty': move_emb.difficulty,
                'energy_level': move_emb.energy_level,
                'style': move_emb.style,
                'duration': move_emb.duration,
            })
        
        # Convert to numpy array
        self.embeddings = np.array(embeddings_list, dtype=np.float32)
        self.move_metadata = metadata_list
        self.embedding_dimension = self.embeddings.shape[1]
        
        logger.info(
            f"Loaded {len(self.move_metadata)} move embeddings "
            f"(dimension: {self.embedding_dimension})"
        )
        
        # Build FAISS index
        if self.use_faiss:
            self.build_faiss_index(self.embeddings)
        
        # Update cache timestamp
        self.cache_timestamp = datetime.now()
    
    def build_faiss_index(self, embeddings: np.ndarray) -> None:
        """
        Build FAISS index from embeddings.
        
        Uses IndexFlatIP (inner product) for exact search. Embeddings are
        normalized to unit length so that inner product equals cosine similarity.
        
        If GPU is enabled, the index is transferred to GPU for faster search.
        
        Args:
            embeddings: numpy array of shape (n_moves, embedding_dim)
        
        Raises:
            ValueError: If FAISS is not available
        """
        if not FAISS_AVAILABLE:
            raise ValueError("FAISS is not available. Cannot build index.")
        
        logger.info(f"Building FAISS index (GPU: {self.use_gpu})...")
        
        # Normalize embeddings for cosine similarity
        # After normalization, inner product = cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create CPU index first
        dimension = embeddings.shape[1]
        cpu_index = faiss.IndexFlatIP(dimension)
        
        # Add embeddings to CPU index
        cpu_index.add(embeddings)
        
        # Transfer to GPU if enabled
        if self.use_gpu and self.gpu_resources is not None:
            try:
                self.faiss_index = self._index_cpu_to_gpu(cpu_index)
                logger.info(
                    f"FAISS GPU index built with {self.faiss_index.ntotal} vectors "
                    f"(dimension: {dimension})"
                )
            except Exception as e:
                logger.error(f"Failed to transfer index to GPU: {e}")
                logger.info("Falling back to CPU index")
                self.faiss_index = cpu_index
                self.use_gpu = False
        else:
            self.faiss_index = cpu_index
            logger.info(
                f"FAISS CPU index built with {self.faiss_index.ntotal} vectors "
                f"(dimension: {dimension})"
            )
    
    def _index_cpu_to_gpu(self, cpu_index: 'faiss.Index') -> 'faiss.Index':
        """
        Transfer FAISS index from CPU to GPU.
        
        Args:
            cpu_index: CPU-based FAISS index
        
        Returns:
            GPU-based FAISS index
        
        Raises:
            RuntimeError: If GPU transfer fails
        """
        if not self.use_gpu or self.gpu_resources is None:
            raise RuntimeError("GPU resources not initialized")
        
        try:
            # Transfer index to GPU (device 0)
            gpu_index = faiss.index_cpu_to_gpu(self.gpu_resources, 0, cpu_index)
            
            logger.info("Successfully transferred FAISS index to GPU")
            return gpu_index
            
        except Exception as e:
            logger.error(f"Failed to transfer index to GPU: {e}")
            raise RuntimeError(f"GPU index transfer failed: {e}")
    
    def search_similar_moves(
        self,
        query_embedding: np.ndarray,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[MoveResult]:
        """
        Find similar moves using FAISS similarity search.
        
        This method performs vector similarity search using FAISS (or NumPy fallback).
        It first searches for the top candidates, then filters by metadata criteria.
        
        Args:
            query_embedding: Query vector (will be normalized)
            filters: Metadata filters (difficulty, energy_level, style)
            top_k: Number of results to return
        
        Returns:
            List of MoveResult objects sorted by similarity score
        
        Example:
            >>> query_emb = np.random.randn(1024).astype(np.float32)
            >>> filters = {'difficulty': 'intermediate', 'energy_level': 'high'}
            >>> results = service.search_similar_moves(query_emb, filters, top_k=10)
        """
        # Ensure embeddings are loaded
        if self.embeddings is None or not self._is_cache_valid():
            self.load_embeddings_from_db()
        
        # Validate query embedding
        query_embedding = np.array(query_embedding, dtype=np.float32)
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        if query_embedding.shape[1] != self.embedding_dimension:
            raise ValueError(
                f"Query embedding dimension {query_embedding.shape[1]} "
                f"does not match index dimension {self.embedding_dimension}"
            )
        
        # Use FAISS if available, otherwise fallback to NumPy
        if self.use_faiss and self.faiss_index is not None:
            try:
                results = self._faiss_search(query_embedding, filters, top_k)
            except Exception as e:
                logger.warning(f"FAISS search failed: {e}. Falling back to NumPy.")
                results = self._numpy_search(query_embedding, filters, top_k)
        else:
            results = self._numpy_search(query_embedding, filters, top_k)
        
        return results
    
    def _faiss_search(
        self,
        query_embedding: np.ndarray,
        filters: Optional[Dict[str, Any]],
        top_k: int
    ) -> List[MoveResult]:
        """
        Perform FAISS-based similarity search.
        
        Supports both CPU and GPU indices. Automatically falls back to CPU
        if GPU search fails.
        
        Args:
            query_embedding: Normalized query vector
            filters: Metadata filters
            top_k: Number of results to return
        
        Returns:
            List of MoveResult objects
        """
        try:
            # Normalize query for cosine similarity
            faiss.normalize_L2(query_embedding)
            
            # Search for more candidates than needed to allow for filtering
            search_k = min(top_k * 5, self.faiss_index.ntotal)
            
            # Perform FAISS search (works on both CPU and GPU indices)
            distances, indices = self.faiss_index.search(query_embedding, search_k)
            
            # Convert to results
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue
                
                metadata = self.move_metadata[idx]
                
                # Apply metadata filters
                if filters and not self._matches_filters(metadata, filters):
                    continue
                
                results.append(MoveResult(
                    move_id=metadata['move_id'],
                    move_name=metadata['move_name'],
                    video_path=metadata['video_path'],
                    similarity_score=float(dist),  # Inner product = cosine similarity
                    difficulty=metadata['difficulty'],
                    energy_level=metadata['energy_level'],
                    style=metadata['style'],
                    duration=metadata['duration'],
                ))
                
                # Stop when we have enough results
                if len(results) >= top_k:
                    break
            
            search_type = "GPU" if self.use_gpu else "CPU"
            logger.debug(f"FAISS {search_type} search returned {len(results)} results")
            return results
            
        except Exception as e:
            # If GPU search fails, try to rebuild with CPU
            if self.use_gpu:
                logger.error(f"GPU search failed: {e}")
                logger.info("Attempting to rebuild index on CPU")
                
                try:
                    # Disable GPU and rebuild index
                    self.use_gpu = False
                    self.gpu_resources = None
                    
                    # Rebuild index on CPU
                    if self.embeddings is not None:
                        self.build_faiss_index(self.embeddings)
                        
                        # Retry search on CPU
                        return self._faiss_search(query_embedding, filters, top_k)
                    else:
                        raise RuntimeError("No embeddings available for CPU fallback")
                        
                except Exception as fallback_error:
                    logger.error(f"CPU fallback also failed: {fallback_error}")
                    raise
            else:
                # Already on CPU, re-raise the error
                raise
    
    def _numpy_search(
        self,
        query_embedding: np.ndarray,
        filters: Optional[Dict[str, Any]],
        top_k: int
    ) -> List[MoveResult]:
        """
        Fallback to NumPy-based cosine similarity search.
        
        This is slower than FAISS but doesn't require additional dependencies.
        
        Args:
            query_embedding: Query vector
            filters: Metadata filters
            top_k: Number of results to return
        
        Returns:
            List of MoveResult objects
        """
        logger.debug("Using NumPy-based similarity search")
        
        # Normalize query and embeddings
        query_norm = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
        embeddings_norm = self.embeddings / np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        
        # Compute cosine similarity
        similarities = np.dot(embeddings_norm, query_norm.T).flatten()
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1]
        
        # Convert to results with filtering
        results = []
        for idx in top_indices:
            metadata = self.move_metadata[idx]
            
            # Apply metadata filters
            if filters and not self._matches_filters(metadata, filters):
                continue
            
            results.append(MoveResult(
                move_id=metadata['move_id'],
                move_name=metadata['move_name'],
                video_path=metadata['video_path'],
                similarity_score=float(similarities[idx]),
                difficulty=metadata['difficulty'],
                energy_level=metadata['energy_level'],
                style=metadata['style'],
                duration=metadata['duration'],
            ))
            
            # Stop when we have enough results
            if len(results) >= top_k:
                break
        
        logger.debug(f"NumPy search returned {len(results)} results")
        return results
    
    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if metadata matches filter criteria.
        
        Args:
            metadata: Move metadata dictionary
            filters: Filter criteria dictionary
        
        Returns:
            True if metadata matches all filters
        """
        for key, value in filters.items():
            if key in metadata and metadata[key] != value:
                return False
        return True
    
    def _is_cache_valid(self) -> bool:
        """
        Check if cached embeddings are still valid.
        
        Returns:
            True if cache is valid, False otherwise
        """
        if self.cache_timestamp is None or self.embeddings is None:
            return False
        
        age = datetime.now() - self.cache_timestamp
        return age < timedelta(seconds=self.cache_ttl_seconds)
    
    def clear_cache(self) -> None:
        """Clear cached embeddings and FAISS index."""
        logger.info("Clearing vector search cache")
        self.faiss_index = None
        self.move_metadata = []
        self.embeddings = None
        self.cache_timestamp = None
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the current cache state.
        
        Returns:
            Dictionary with cache information
        """
        if self.cache_timestamp is None:
            return {
                'cached': False,
                'num_moves': 0,
                'embedding_dimension': None,
                'cache_age_seconds': None,
                'cache_valid': False,
                'using_gpu': False,
            }
        
        age = datetime.now() - self.cache_timestamp
        
        info = {
            'cached': True,
            'num_moves': len(self.move_metadata),
            'embedding_dimension': self.embedding_dimension,
            'cache_age_seconds': age.total_seconds(),
            'cache_valid': self._is_cache_valid(),
            'using_faiss': self.use_faiss and self.faiss_index is not None,
            'using_gpu': self.use_gpu,
        }
        
        # Add GPU memory info if available
        if self.use_gpu and self.gpu_resources is not None:
            try:
                # Get GPU memory usage
                import torch
                if torch.cuda.is_available():
                    info['gpu_memory_allocated'] = torch.cuda.memory_allocated(0)
                    info['gpu_memory_reserved'] = torch.cuda.memory_reserved(0)
            except Exception as e:
                logger.debug(f"Could not get GPU memory info: {e}")
        
        return info
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """
        Get GPU-specific information.
        
        Returns:
            Dictionary with GPU information
        """
        info = {
            'gpu_enabled': self.use_gpu,
            'gpu_resources_initialized': self.gpu_resources is not None,
        }
        
        if self.use_gpu:
            try:
                from services.gpu_utils import get_gpu_info
                gpu_details = get_gpu_info()
                info.update(gpu_details)
            except Exception as e:
                logger.warning(f"Could not get GPU info: {e}")
        
        return info


# Global instance for reuse across requests
_vector_search_service = None


def get_vector_search_service(use_gpu: Optional[bool] = None) -> VectorSearchService:
    """
    Get or create the global vector search service instance.
    
    This ensures we reuse the same service instance (and its cache)
    across multiple requests.
    
    Args:
        use_gpu: Whether to use GPU acceleration (None = auto-detect from config)
    
    Returns:
        VectorSearchService instance
    """
    global _vector_search_service
    
    if _vector_search_service is None:
        # Get cache TTL from environment variable
        cache_ttl = int(os.getenv('MOVE_EMBEDDINGS_CACHE_TTL', '3600'))
        _vector_search_service = VectorSearchService(
            cache_ttl_seconds=cache_ttl,
            use_gpu=use_gpu
        )
    
    return _vector_search_service
