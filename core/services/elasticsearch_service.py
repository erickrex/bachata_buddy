"""
Elasticsearch service for embedding storage and retrieval.

Features:
- Bulk indexing for efficient batch operations
- kNN vector similarity search
- Metadata filtering
- Connection pooling
- Retry logic with exponential backoff
"""

from typing import List, Dict, Optional, Any
import numpy as np
import logging
import time
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, TransportError
from elasticsearch.helpers import bulk

from core.config.environment_config import ElasticsearchConfig


logger = logging.getLogger(__name__)


class ElasticsearchService:
    """
    Elasticsearch service for embedding storage and retrieval.
    
    This service manages all interactions with Elasticsearch for storing
    and retrieving multimodal embeddings (audio, lead, follow, interaction, text).
    
    Features:
    - Connection pooling for efficient queries
    - Bulk indexing with single refresh
    - Retry logic with exponential backoff
    - Metadata filtering support
    """
    
    def __init__(self, config: ElasticsearchConfig):
        """
        Initialize Elasticsearch client with connection pool.
        
        Args:
            config: Elasticsearch configuration
            
        Raises:
            ConnectionError: If cannot connect to Elasticsearch
        """
        self.config = config
        
        # Create client with connection pooling
        # Note: Elasticsearch 9.x requires full URL with scheme
        scheme = "https" if config.use_ssl else "http"
        url = f"{scheme}://{config.host}:{config.port}"
        
        client_args = {
            "hosts": [url],
            "request_timeout": config.timeout,
        }
        
        # Add authentication if provided
        if config.username and config.password:
            client_args["basic_auth"] = (config.username, config.password)
        
        # Add SSL settings
        if config.use_ssl:
            client_args["verify_certs"] = config.verify_certs
        
        self.client = Elasticsearch(**client_args)
        self.index_name = config.index_name
        
        # Verify connection
        self._verify_connection()
        
        logger.info(
            f"Elasticsearch service initialized. "
            f"Host: {config.host}:{config.port}, Index: {config.index_name}"
        )
    
    def _verify_connection(self):
        """
        Verify connection to Elasticsearch.
        
        Raises:
            ConnectionError: If cannot connect to Elasticsearch
        """
        try:
            if not self.client.ping():
                raise ConnectionError(
                    f"Cannot connect to Elasticsearch at {self.config.host}:{self.config.port}. "
                    f"Please ensure Elasticsearch is running and accessible."
                )
            logger.info("Elasticsearch connection verified successfully")
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Elasticsearch at {self.config.host}:{self.config.port}. "
                f"Error: {e}"
            )
    
    def create_index(self):
        """
        Create index with dense_vector mappings for all 5 embedding types.
        
        Total dimensions: 1792D
        - audio_embedding: 128D
        - lead_embedding: 512D
        - follow_embedding: 512D
        - interaction_embedding: 256D
        - text_embedding: 384D
        
        Also defines metadata fields for filtering and quality tracking.
        """
        mapping = {
            "mappings": {
                "properties": {
                    # Embedding fields (stored individually, no combined embedding)
                    "audio_embedding": {
                        "type": "dense_vector",
                        "dims": 128,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "lead_embedding": {
                        "type": "dense_vector",
                        "dims": 512,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "follow_embedding": {
                        "type": "dense_vector",
                        "dims": 512,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "interaction_embedding": {
                        "type": "dense_vector",
                        "dims": 256,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "text_embedding": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine"
                    },
                    
                    # Metadata fields
                    "clip_id": {"type": "keyword"},
                    "move_label": {"type": "keyword"},
                    "difficulty": {"type": "keyword"},
                    "energy_level": {"type": "keyword"},
                    "lead_follow_roles": {"type": "keyword"},
                    "estimated_tempo": {"type": "float"},
                    "video_path": {"type": "text"},
                    "quality_score": {"type": "float"},
                    "detection_rate": {"type": "float"},
                    "frame_count": {"type": "integer"},
                    "processing_time": {"type": "float"},
                    "version": {"type": "keyword"},
                    "created_at": {"type": "date"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,  # Can increase for production
                "refresh_interval": "-1"  # Disable auto-refresh for bulk indexing
            }
        }
        
        # Check if index already exists
        if self.client.indices.exists(index=self.index_name):
            logger.info(f"Index '{self.index_name}' already exists")
            return
        
        # Create index
        self.client.indices.create(index=self.index_name, body=mapping)
        logger.info(f"Created index '{self.index_name}' with dense_vector mappings (1792D total)")
    
    def bulk_index_embeddings(self, embeddings: List[Dict[str, Any]]):
        """
        Bulk index embeddings with single refresh at end.
        
        This method uses Elasticsearch's bulk API for efficient batch operations.
        After all embeddings are indexed, a single refresh is performed to make
        them searchable.
        
        Args:
            embeddings: List of embedding documents, each containing:
                - clip_id: Unique identifier
                - audio_embedding: 128D numpy array
                - lead_embedding: 512D numpy array
                - follow_embedding: 512D numpy array
                - interaction_embedding: 256D numpy array
                - text_embedding: 384D numpy array
                - metadata fields (move_label, difficulty, etc.)
                
        Raises:
            TransportError: If bulk indexing fails
        """
        if not embeddings:
            logger.warning("No embeddings to index")
            return
        
        logger.info(f"Bulk indexing {len(embeddings)} embeddings...")
        
        # Prepare bulk actions
        actions = []
        for emb in embeddings:
            # Convert numpy arrays to lists for JSON serialization
            action = {
                "_index": self.index_name,
                "_id": emb["clip_id"],
                "_source": {
                    # Embeddings (convert numpy arrays to lists)
                    "audio_embedding": self._to_list(emb.get("audio_embedding")),
                    "lead_embedding": self._to_list(emb.get("lead_embedding")),
                    "follow_embedding": self._to_list(emb.get("follow_embedding")),
                    "interaction_embedding": self._to_list(emb.get("interaction_embedding")),
                    "text_embedding": self._to_list(emb.get("text_embedding")),
                    
                    # Metadata
                    "clip_id": emb["clip_id"],
                    "move_label": emb.get("move_label"),
                    "difficulty": emb.get("difficulty"),
                    "energy_level": emb.get("energy_level"),
                    "lead_follow_roles": emb.get("lead_follow_roles"),
                    "estimated_tempo": emb.get("estimated_tempo"),
                    "video_path": emb.get("video_path"),
                    "quality_score": emb.get("quality_score"),
                    "detection_rate": emb.get("detection_rate"),
                    "frame_count": emb.get("frame_count"),
                    "processing_time": emb.get("processing_time"),
                    "version": emb.get("version", "mmpose_v1"),
                    "created_at": emb.get("created_at")
                }
            }
            actions.append(action)
        
        # Bulk index
        try:
            success, failed = bulk(
                self.client,
                actions,
                raise_on_error=False,
                raise_on_exception=False
            )
            
            logger.info(f"Bulk indexing complete. Success: {success}, Failed: {len(failed)}")
            
            if failed:
                logger.error(f"Failed to index {len(failed)} documents: {failed}")
            
            # Single refresh to make all embeddings searchable
            self.client.indices.refresh(index=self.index_name)
            logger.info(f"Index '{self.index_name}' refreshed")
            
        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            raise TransportError(f"Failed to bulk index embeddings: {e}")
    
    def get_all_embeddings(
        self,
        filters: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all embeddings for similarity computation.
        
        With only 38 videos, we retrieve all and compute weighted similarity in Python.
        This is faster and more flexible than Elasticsearch kNN on multiple fields.
        
        Args:
            filters: Optional metadata filters (difficulty, energy_level, move_label, etc.)
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of all embeddings with metadata
            
        Raises:
            TransportError: If retrieval fails after all retries
        """
        query = {"match_all": {}}
        
        # Add filters if provided
        if filters:
            must_clauses = []
            for key, value in filters.items():
                if value is not None:
                    must_clauses.append({"term": {key: value}})
            
            if must_clauses:
                query = {
                    "bool": {
                        "must": must_clauses
                    }
                }
        
        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                response = self.client.search(
                    index=self.index_name,
                    body={"query": query},
                    size=100  # More than enough for 38 videos
                )
                
                # Convert response to list of embeddings
                embeddings = []
                for hit in response["hits"]["hits"]:
                    source = hit["_source"]
                    
                    # Convert embedding lists back to numpy arrays
                    embedding = {
                        "clip_id": source["clip_id"],
                        "audio_embedding": np.array(source["audio_embedding"], dtype=np.float32),
                        "lead_embedding": np.array(source["lead_embedding"], dtype=np.float32),
                        "follow_embedding": np.array(source["follow_embedding"], dtype=np.float32),
                        "interaction_embedding": np.array(source["interaction_embedding"], dtype=np.float32),
                        "text_embedding": np.array(source["text_embedding"], dtype=np.float32),
                        
                        # Metadata
                        "move_label": source.get("move_label"),
                        "difficulty": source.get("difficulty"),
                        "energy_level": source.get("energy_level"),
                        "lead_follow_roles": source.get("lead_follow_roles"),
                        "estimated_tempo": source.get("estimated_tempo"),
                        "video_path": source.get("video_path"),
                        "quality_score": source.get("quality_score"),
                        "detection_rate": source.get("detection_rate"),
                        "frame_count": source.get("frame_count"),
                        "processing_time": source.get("processing_time"),
                        "version": source.get("version")
                    }
                    embeddings.append(embedding)
                
                logger.info(f"Retrieved {len(embeddings)} embeddings from Elasticsearch")
                return embeddings
                
            except (ConnectionError, TransportError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Elasticsearch query failed (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s... Error: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Elasticsearch query failed after {max_retries} attempts: {e}")
                    raise TransportError(
                        f"Failed to retrieve embeddings after {max_retries} attempts: {e}"
                    )
    
    def get_embedding_by_id(
        self,
        clip_id: str,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single embedding by clip_id.
        
        Args:
            clip_id: Unique clip identifier
            max_retries: Maximum number of retry attempts
            
        Returns:
            Embedding document with all fields, or None if not found
            
        Raises:
            TransportError: If retrieval fails after all retries
        """
        for attempt in range(max_retries):
            try:
                response = self.client.get(
                    index=self.index_name,
                    id=clip_id
                )
                
                source = response["_source"]
                
                # Convert embedding lists back to numpy arrays
                embedding = {
                    "clip_id": source["clip_id"],
                    "audio_embedding": np.array(source["audio_embedding"], dtype=np.float32),
                    "lead_embedding": np.array(source["lead_embedding"], dtype=np.float32),
                    "follow_embedding": np.array(source["follow_embedding"], dtype=np.float32),
                    "interaction_embedding": np.array(source["interaction_embedding"], dtype=np.float32),
                    "text_embedding": np.array(source["text_embedding"], dtype=np.float32),
                    
                    # Metadata
                    "move_label": source.get("move_label"),
                    "difficulty": source.get("difficulty"),
                    "energy_level": source.get("energy_level"),
                    "lead_follow_roles": source.get("lead_follow_roles"),
                    "estimated_tempo": source.get("estimated_tempo"),
                    "video_path": source.get("video_path"),
                    "quality_score": source.get("quality_score"),
                    "detection_rate": source.get("detection_rate"),
                    "frame_count": source.get("frame_count"),
                    "processing_time": source.get("processing_time"),
                    "version": source.get("version")
                }
                
                logger.debug(f"Retrieved embedding for clip_id: {clip_id}")
                return embedding
                
            except Exception as e:
                if "not_found" in str(e).lower():
                    logger.warning(f"Embedding not found for clip_id: {clip_id}")
                    return None
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Elasticsearch get failed (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s... Error: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Elasticsearch get failed after {max_retries} attempts: {e}")
                    raise TransportError(
                        f"Failed to retrieve embedding after {max_retries} attempts: {e}"
                    )
    
    def index_exists(self) -> bool:
        """
        Check if the index exists.
        
        Returns:
            True if index exists, False otherwise
        """
        return self.client.indices.exists(index=self.index_name)
    
    def delete_index(self):
        """
        Delete the index.
        
        Warning: This will delete all embeddings!
        """
        if self.index_exists():
            self.client.indices.delete(index=self.index_name)
            logger.warning(f"Deleted index '{self.index_name}'")
        else:
            logger.info(f"Index '{self.index_name}' does not exist")
    
    def count_documents(self) -> int:
        """
        Count the number of documents in the index.
        
        Returns:
            Number of documents
        """
        if not self.index_exists():
            return 0
        
        response = self.client.count(index=self.index_name)
        count = response["count"]
        logger.info(f"Index '{self.index_name}' contains {count} documents")
        return count
    
    def _to_list(self, arr: Optional[np.ndarray]) -> Optional[List[float]]:
        """
        Convert numpy array to list for JSON serialization.
        
        Args:
            arr: Numpy array or None
            
        Returns:
            List of floats or None
        """
        if arr is None:
            return None
        if isinstance(arr, np.ndarray):
            return arr.tolist()
        return arr
    
    def close(self):
        """Close the Elasticsearch client connection."""
        self.client.close()
        logger.info("Elasticsearch connection closed")
