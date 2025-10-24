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
        client_args = {
            "request_timeout": config.timeout,
        }
        
        # Build connection URL
        scheme = "https" if config.use_ssl else "http"
        url = f"{scheme}://{config.host}:{config.port}"
        client_args["hosts"] = [url]
        
        # Authentication
        if config.api_key:
            # Serverless mode (API key authentication)
            client_args["api_key"] = config.api_key
            connection_info = f"Serverless: {config.host}:{config.port}"
            logger.info("Using Elasticsearch Serverless (API key authentication)")
        elif config.username and config.password:
            # Local mode with basic auth
            client_args["basic_auth"] = (config.username, config.password)
            connection_info = f"Local: {config.host}:{config.port} (basic auth)"
            logger.info("Using local Elasticsearch (basic auth)")
        else:
            # Local mode without auth
            connection_info = f"Local: {config.host}:{config.port}"
            logger.info("Using local Elasticsearch (no auth)")
        
        # SSL settings
        if config.use_ssl:
            client_args["verify_certs"] = config.verify_certs
        
        self.client = Elasticsearch(**client_args)
        self.index_name = config.index_name
        
        # Verify connection
        self._verify_connection()
        
        logger.info(
            f"Elasticsearch service initialized. "
            f"{connection_info}, Index: {config.index_name}"
        )
    
    def _verify_connection(self):
        """
        Verify connection to Elasticsearch.
        
        Raises:
            ConnectionError: If cannot connect to Elasticsearch
        """
        try:
            if not self.client.ping():
                connection_info = f"{self.config.host}:{self.config.port}"
                raise ConnectionError(
                    f"Cannot connect to Elasticsearch at {connection_info}. "
                    f"Please ensure Elasticsearch is running and accessible."
                )
            logger.info("Elasticsearch connection verified successfully")
        except Exception as e:
            connection_info = f"{self.config.host}:{self.config.port}"
            raise ConnectionError(
                f"Failed to connect to Elasticsearch at {connection_info}. "
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
            }
        }
        
        # Add settings only for non-serverless (local) mode
        if not self.config.api_key:
            mapping["settings"] = {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "-1"  # Disable auto-refresh for bulk indexing
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
            audio_emb = self._to_list(emb.get("audio_embedding"))
            lead_emb = self._to_list(emb.get("lead_embedding"))
            follow_emb = self._to_list(emb.get("follow_embedding"))
            interaction_emb = self._to_list(emb.get("interaction_embedding"))
            text_emb = self._to_list(emb.get("text_embedding"))
            
            # Debug: Log first embedding to verify data
            if len(actions) == 0:
                logger.info(f"First embedding - clip_id: {emb['clip_id']}")
                logger.info(f"  audio_embedding: {type(audio_emb)}, len={len(audio_emb) if audio_emb else 'None'}")
                logger.info(f"  lead_embedding: {type(lead_emb)}, len={len(lead_emb) if lead_emb else 'None'}")
                logger.info(f"  follow_embedding: {type(follow_emb)}, len={len(follow_emb) if follow_emb else 'None'}")
                logger.info(f"  interaction_embedding: {type(interaction_emb)}, len={len(interaction_emb) if interaction_emb else 'None'}")
                logger.info(f"  text_embedding: {type(text_emb)}, len={len(text_emb) if text_emb else 'None'}")
            
            # Format for client.bulk() API
            actions.append({"index": {"_index": self.index_name, "_id": emb["clip_id"]}})
            actions.append({
                # Embeddings (convert numpy arrays to lists)
                "audio_embedding": audio_emb,
                "lead_embedding": lead_emb,
                "follow_embedding": follow_emb,
                "interaction_embedding": interaction_emb,
                "text_embedding": text_emb,
                
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
            })
        
        # Bulk index - use direct client call to see full response
        try:
            # Use direct bulk API to get full response
            response = self.client.bulk(operations=actions)
            
            # Check for errors in response
            if response.get('errors'):
                logger.error("Bulk indexing had errors!")
                for item in response.get('items', [])[:3]:
                    if 'error' in item.get('index', {}):
                        logger.error(f"  Error: {item['index']['error']}")
            
            success = len([item for item in response.get('items', []) if item.get('index', {}).get('status') in [200, 201]])
            failed = len([item for item in response.get('items', []) if item.get('index', {}).get('status') not in [200, 201]])
            
            logger.info(f"Bulk indexing complete. Success: {success}, Failed: {failed}")
            
            # Single refresh to make all embeddings searchable
            self.client.indices.refresh(index=self.index_name)
            logger.info(f"Index '{self.index_name}' refreshed")
            
        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            raise TransportError(f"Failed to bulk index embeddings: {e}")
    
    def hybrid_search(
        self,
        query_embeddings: Optional[Dict[str, np.ndarray]] = None,
        query_text: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        embedding_weights: Optional[Dict[str, float]] = None,
        text_boost: float = 1.0,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity and text search.
        
        This method combines:
        1. kNN vector search on multiple embedding fields (audio, lead, follow, interaction, text)
        2. Text search on move_label and description fields
        3. Metadata filtering (difficulty, energy_level, style)
        
        Args:
            query_embeddings: Dict of embedding type to numpy array:
                - 'audio': 128D audio embedding
                - 'lead': 512D lead pose embedding
                - 'follow': 512D follow pose embedding
                - 'interaction': 256D interaction embedding
                - 'text': 384D text embedding
            query_text: Optional text query for move_label search
            filters: Optional metadata filters (difficulty, energy_level, etc.)
            top_k: Number of results to return
            embedding_weights: Optional weights for each embedding type (default: equal weights)
            text_boost: Boost factor for text search score (default: 1.0)
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of results with combined scores, sorted by relevance
            
        Raises:
            TransportError: If search fails after all retries
        """
        if not query_embeddings and not query_text:
            raise ValueError("Must provide either query_embeddings or query_text")
        
        # Default embedding weights (equal weights)
        if embedding_weights is None:
            embedding_weights = {
                'audio': 0.2,
                'lead': 0.2,
                'follow': 0.2,
                'interaction': 0.2,
                'text': 0.2
            }
        
        # Build query
        query_clauses = []
        
        # Add kNN vector searches for each embedding type
        if query_embeddings:
            for emb_type, emb_array in query_embeddings.items():
                if emb_array is not None and len(emb_array) > 0:
                    field_name = f"{emb_type}_embedding"
                    weight = embedding_weights.get(emb_type, 0.2)
                    
                    # kNN query for this embedding type
                    # Ensure num_candidates >= k (Elasticsearch requirement)
                    k_value = top_k * 2
                    num_candidates_value = max(k_value, min(100, top_k * 10))
                    
                    knn_query = {
                        "field": field_name,
                        "query_vector": emb_array.tolist() if isinstance(emb_array, np.ndarray) else emb_array,
                        "k": k_value,  # Get more candidates for better ranking
                        "num_candidates": num_candidates_value,  # Search space (must be >= k)
                        "boost": weight
                    }
                    
                    # Add filters to kNN query if provided
                    if filters:
                        filter_clauses = []
                        for key, value in filters.items():
                            if value is not None:
                                filter_clauses.append({"term": {key: value}})
                        if filter_clauses:
                            knn_query["filter"] = {"bool": {"must": filter_clauses}}
                    
                    query_clauses.append({"knn": knn_query})
        
        # Add text search if provided
        if query_text:
            text_query = {
                "multi_match": {
                    "query": query_text,
                    "fields": ["move_label^2", "difficulty", "energy_level"],  # Boost move_label
                    "type": "best_fields",
                    "boost": text_boost
                }
            }
            query_clauses.append({"query": text_query})
        
        # Combine queries with should (OR logic, scores are summed)
        if len(query_clauses) == 1:
            # Single query type
            if "knn" in query_clauses[0]:
                search_body = {"knn": query_clauses[0]["knn"]}
            else:
                search_body = {"query": query_clauses[0]["query"]}
        else:
            # Multiple query types - use bool should for score combination
            search_body = {
                "query": {
                    "bool": {
                        "should": [q.get("query") for q in query_clauses if "query" in q]
                    }
                }
            }
            # Add kNN queries separately (Elasticsearch 8.x syntax)
            if any("knn" in q for q in query_clauses):
                search_body["knn"] = [q["knn"] for q in query_clauses if "knn" in q]
        
        # Add metadata filters to query if not already in kNN
        if filters and "knn" not in search_body:
            filter_clauses = []
            for key, value in filters.items():
                if value is not None:
                    filter_clauses.append({"term": {key: value}})
            
            if filter_clauses:
                if "query" in search_body:
                    # Add filter to existing query
                    if "bool" not in search_body["query"]:
                        search_body["query"] = {"bool": {"must": [search_body["query"]]}}
                    search_body["query"]["bool"]["filter"] = filter_clauses
                else:
                    # Create query with just filters
                    search_body["query"] = {"bool": {"filter": filter_clauses}}
        
        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                # Execute search
                response = self.client.search(
                    index=self.index_name,
                    body={
                        **search_body,
                        "fields": [
                            "clip_id", "audio_embedding", "lead_embedding", "follow_embedding",
                            "interaction_embedding", "text_embedding", "move_label", "difficulty",
                            "energy_level", "lead_follow_roles", "estimated_tempo", "video_path",
                            "quality_score", "detection_rate", "frame_count", "processing_time", "version"
                        ],
                        "_source": False,
                        "size": top_k
                    }
                )
                
                # Convert response to list of results
                results = []
                for hit in response["hits"]["hits"]:
                    fields = hit["fields"]
                    
                    def get_scalar_field(name):
                        val = fields.get(name, [None])
                        return val[0] if isinstance(val, list) and len(val) > 0 else val
                    
                    def get_vector_field(name):
                        return fields.get(name, [])
                    
                    result = {
                        "clip_id": get_scalar_field("clip_id"),
                        "audio_embedding": np.array(get_vector_field("audio_embedding"), dtype=np.float32),
                        "lead_embedding": np.array(get_vector_field("lead_embedding"), dtype=np.float32),
                        "follow_embedding": np.array(get_vector_field("follow_embedding"), dtype=np.float32),
                        "interaction_embedding": np.array(get_vector_field("interaction_embedding"), dtype=np.float32),
                        "text_embedding": np.array(get_vector_field("text_embedding"), dtype=np.float32),
                        
                        # Metadata
                        "move_label": get_scalar_field("move_label"),
                        "difficulty": get_scalar_field("difficulty"),
                        "energy_level": get_scalar_field("energy_level"),
                        "lead_follow_roles": get_scalar_field("lead_follow_roles"),
                        "estimated_tempo": get_scalar_field("estimated_tempo"),
                        "video_path": get_scalar_field("video_path"),
                        "quality_score": get_scalar_field("quality_score"),
                        "detection_rate": get_scalar_field("detection_rate"),
                        "frame_count": get_scalar_field("frame_count"),
                        "processing_time": get_scalar_field("processing_time"),
                        "version": get_scalar_field("version"),
                        
                        # Search score
                        "score": hit["_score"]
                    }
                    results.append(result)
                
                logger.info(f"Hybrid search returned {len(results)} results")
                
                # CRITICAL DEBUG: Log unique video paths from Elasticsearch
                unique_paths_from_es = set(r["video_path"] for r in results)
                logger.info("=" * 80)
                logger.info(f"CRITICAL DEBUG - ELASTICSEARCH RESULTS:")
                logger.info(f"  Total results: {len(results)}")
                logger.info(f"  Unique video paths: {len(unique_paths_from_es)}")
                for i, result in enumerate(results[:10]):
                    logger.info(f"  [{i}] {result['clip_id']}: {result['video_path']} (ES score: {result['score']:.3f})")
                logger.info("=" * 80)
                
                return results
                
            except (ConnectionError, TransportError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Hybrid search failed (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s... Error: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Hybrid search failed after {max_retries} attempts: {e}")
                    raise TransportError(
                        f"Failed to execute hybrid search after {max_retries} attempts: {e}"
                    )
    
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
                # Use fields API to retrieve dense_vector fields (excluded from _source in Serverless)
                response = self.client.search(
                    index=self.index_name,
                    body={
                        "query": query,
                        "fields": [
                            "clip_id", "audio_embedding", "lead_embedding", "follow_embedding",
                            "interaction_embedding", "text_embedding", "move_label", "difficulty",
                            "energy_level", "lead_follow_roles", "estimated_tempo", "video_path",
                            "quality_score", "detection_rate", "frame_count", "processing_time", "version"
                        ],
                        "_source": False  # Don't need _source since we're using fields
                    },
                    size=100  # More than enough for 38 videos
                )
                
                # Convert response to list of embeddings
                embeddings = []
                for hit in response["hits"]["hits"]:
                    fields = hit["fields"]
                    
                    # Fields API returns single values in arrays, extract first element for scalars
                    # But dense_vector fields are already lists, so keep them as-is
                    def get_scalar_field(name):
                        val = fields.get(name, [None])
                        return val[0] if isinstance(val, list) and len(val) > 0 else val
                    
                    def get_vector_field(name):
                        # Dense vector fields are returned as lists directly
                        return fields.get(name, [])
                    
                    # Convert embedding lists back to numpy arrays
                    embedding = {
                        "clip_id": get_scalar_field("clip_id"),
                        "audio_embedding": np.array(get_vector_field("audio_embedding"), dtype=np.float32),
                        "lead_embedding": np.array(get_vector_field("lead_embedding"), dtype=np.float32),
                        "follow_embedding": np.array(get_vector_field("follow_embedding"), dtype=np.float32),
                        "interaction_embedding": np.array(get_vector_field("interaction_embedding"), dtype=np.float32),
                        "text_embedding": np.array(get_vector_field("text_embedding"), dtype=np.float32),
                        
                        # Metadata
                        "move_label": get_scalar_field("move_label"),
                        "difficulty": get_scalar_field("difficulty"),
                        "energy_level": get_scalar_field("energy_level"),
                        "lead_follow_roles": get_scalar_field("lead_follow_roles"),
                        "estimated_tempo": get_scalar_field("estimated_tempo"),
                        "video_path": get_scalar_field("video_path"),
                        "quality_score": get_scalar_field("quality_score"),
                        "detection_rate": get_scalar_field("detection_rate"),
                        "frame_count": get_scalar_field("frame_count"),
                        "processing_time": get_scalar_field("processing_time"),
                        "version": get_scalar_field("version")
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
                # Use fields API to retrieve dense_vector fields
                response = self.client.search(
                    index=self.index_name,
                    body={
                        "query": {"term": {"clip_id": clip_id}},
                        "fields": [
                            "clip_id", "audio_embedding", "lead_embedding", "follow_embedding",
                            "interaction_embedding", "text_embedding", "move_label", "difficulty",
                            "energy_level", "lead_follow_roles", "estimated_tempo", "video_path",
                            "quality_score", "detection_rate", "frame_count", "processing_time", "version"
                        ],
                        "_source": False
                    },
                    size=1
                )
                
                if not response["hits"]["hits"]:
                    logger.warning(f"Embedding not found for clip_id: {clip_id}")
                    return None
                
                fields = response["hits"]["hits"][0]["fields"]
                
                # Fields API returns single values in arrays, extract first element for scalars
                def get_scalar_field(name):
                    val = fields.get(name, [None])
                    return val[0] if isinstance(val, list) and len(val) > 0 else val
                
                def get_vector_field(name):
                    # Dense vector fields are returned as lists directly
                    return fields.get(name, [])
                
                # Convert embedding lists back to numpy arrays
                embedding = {
                    "clip_id": get_scalar_field("clip_id"),
                    "audio_embedding": np.array(get_vector_field("audio_embedding"), dtype=np.float32),
                    "lead_embedding": np.array(get_vector_field("lead_embedding"), dtype=np.float32),
                    "follow_embedding": np.array(get_vector_field("follow_embedding"), dtype=np.float32),
                    "interaction_embedding": np.array(get_vector_field("interaction_embedding"), dtype=np.float32),
                    "text_embedding": np.array(get_vector_field("text_embedding"), dtype=np.float32),
                    
                    # Metadata
                    "move_label": get_scalar_field("move_label"),
                    "difficulty": get_scalar_field("difficulty"),
                    "energy_level": get_scalar_field("energy_level"),
                    "lead_follow_roles": get_scalar_field("lead_follow_roles"),
                    "estimated_tempo": get_scalar_field("estimated_tempo"),
                    "video_path": get_scalar_field("video_path"),
                    "quality_score": get_scalar_field("quality_score"),
                    "detection_rate": get_scalar_field("detection_rate"),
                    "frame_count": get_scalar_field("frame_count"),
                    "processing_time": get_scalar_field("processing_time"),
                    "version": get_scalar_field("version")
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
