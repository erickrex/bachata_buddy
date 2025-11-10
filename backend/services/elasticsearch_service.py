"""
Elasticsearch Service

Handles search queries for dance moves.
"""
import os
import logging

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Service for Elasticsearch queries"""
    
    def __init__(self):
        self.url = os.environ.get('ELASTICSEARCH_URL', 'http://elasticsearch:9200')
        
        try:
            from elasticsearch import Elasticsearch
            self.client = Elasticsearch([self.url])
        except ImportError:
            logger.warning("elasticsearch not installed")
            self.client = None
    
    def search_moves(self, query, difficulty=None, limit=10):
        """
        Search for dance moves
        
        Args:
            query: Search query string
            difficulty: Optional difficulty filter
            limit: Maximum number of results
        
        Returns:
            List of matching moves
        """
        if not self.client:
            logger.warning("Elasticsearch not configured")
            return []
        
        try:
            # Build search query
            body = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"description": query}}
                        ]
                    }
                },
                "size": limit
            }
            
            # Add difficulty filter if provided
            if difficulty:
                body["query"]["bool"]["filter"] = [
                    {"term": {"difficulty": difficulty}}
                ]
            
            # Execute search
            response = self.client.search(index="dance_moves", body=body)
            
            # Extract results
            hits = response.get('hits', {}).get('hits', [])
            moves = [hit['_source'] for hit in hits]
            
            logger.info(f"Found {len(moves)} moves for query: {query}")
            return moves
            
        except Exception as e:
            logger.error(f"Elasticsearch search failed: {e}")
            return []
