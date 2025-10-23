"""
Minimal unit tests for Elasticsearch Serverless integration.

Tests core functionality with proper mocking.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from core.config.environment_config import ElasticsearchConfig
from core.services.elasticsearch_service import ElasticsearchService


@pytest.fixture
def serverless_config():
    """Create Serverless Elasticsearch configuration."""
    return ElasticsearchConfig(
        host="test-project.es.us-central1.gcp.elastic.cloud",
        port=443,
        index_name="test_index",
        api_key="test-api-key",
        use_ssl=True,
        verify_certs=True
    )


@pytest.fixture
def mock_es_client():
    """Create properly mocked Elasticsearch client."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.indices.exists.return_value = True
    mock_client.indices.create.return_value = {'acknowledged': True}
    mock_client.indices.delete.return_value = {'acknowledged': True}
    mock_client.count.return_value = {'count': 38}
    return mock_client


class TestServerlessConfiguration:
    """Test Serverless configuration detection."""
    
    def test_serverless_mode_detected_with_api_key(self, serverless_config):
        """Test that API key presence indicates Serverless mode."""
        assert serverless_config.api_key is not None
        assert serverless_config.use_ssl is True
        assert serverless_config.port == 443
    
    def test_local_mode_without_api_key(self):
        """Test local mode configuration."""
        local_config = ElasticsearchConfig(
            host="localhost",
            port=9200,
            index_name="test_index",
            api_key=None,
            use_ssl=False
        )
        assert local_config.api_key is None
        assert local_config.use_ssl is False


class TestElasticsearchService:
    """Test ElasticsearchService with mocked client."""
    
    def test_initialization_serverless(self, serverless_config, mock_es_client):
        """Test service initializes with Serverless config."""
        with patch('core.services.elasticsearch_service.Elasticsearch', return_value=mock_es_client):
            service = ElasticsearchService(serverless_config)
            
            assert service.config == serverless_config
            assert service.index_name == "test_index"
            mock_es_client.ping.assert_called_once()
    
    def test_index_exists(self, serverless_config, mock_es_client):
        """Test checking if index exists."""
        with patch('core.services.elasticsearch_service.Elasticsearch', return_value=mock_es_client):
            service = ElasticsearchService(serverless_config)
            
            assert service.index_exists() is True
            mock_es_client.indices.exists.assert_called_with(index="test_index")
    
    def test_create_index_serverless(self, serverless_config, mock_es_client):
        """Test index creation for Serverless (no shard/replica settings)."""
        mock_es_client.indices.exists.return_value = False
        
        with patch('core.services.elasticsearch_service.Elasticsearch', return_value=mock_es_client):
            service = ElasticsearchService(serverless_config)
            service.create_index()
            
            # Verify create was called
            mock_es_client.indices.create.assert_called_once()
            call_args = mock_es_client.indices.create.call_args
            
            # Verify no settings for Serverless (shards/replicas not allowed)
            mapping = call_args[1]['body']
            assert 'settings' not in mapping or mapping.get('settings') is None
    
    def test_count_documents(self, serverless_config, mock_es_client):
        """Test counting documents."""
        with patch('core.services.elasticsearch_service.Elasticsearch', return_value=mock_es_client):
            service = ElasticsearchService(serverless_config)
            count = service.count_documents()
            
            assert count == 38
            mock_es_client.count.assert_called_with(index="test_index")


class TestFieldsAPI:
    """Test fields API for retrieving dense_vector fields."""
    
    def test_get_all_embeddings_with_fields_api(self, serverless_config, mock_es_client):
        """Test that get_all_embeddings uses fields API and parses correctly."""
        # Mock response with fields API format
        mock_es_client.search.return_value = {
            'hits': {
                'hits': [
                    {
                        'fields': {
                            'clip_id': ['test_clip_1'],
                            'audio_embedding': [0.1] * 128,
                            'lead_embedding': [0.2] * 512,
                            'follow_embedding': [0.3] * 512,
                            'interaction_embedding': [0.4] * 256,
                            'text_embedding': [0.5] * 384,
                            'move_label': ['basic_step'],
                            'difficulty': ['beginner']
                        }
                    },
                    {
                        'fields': {
                            'clip_id': ['test_clip_2'],
                            'audio_embedding': [0.6] * 128,
                            'lead_embedding': [0.7] * 512,
                            'follow_embedding': [0.8] * 512,
                            'interaction_embedding': [0.9] * 256,
                            'text_embedding': [1.0] * 384,
                            'move_label': ['turn'],
                            'difficulty': ['intermediate']
                        }
                    }
                ]
            }
        }
        
        with patch('core.services.elasticsearch_service.Elasticsearch', return_value=mock_es_client):
            service = ElasticsearchService(serverless_config)
            embeddings = service.get_all_embeddings()
            
            # Verify results
            assert len(embeddings) == 2
            
            # Check first embedding
            assert embeddings[0]['clip_id'] == 'test_clip_1'
            assert embeddings[0]['move_label'] == 'basic_step'
            assert embeddings[0]['difficulty'] == 'beginner'
            
            # Verify embeddings are numpy arrays with correct shapes
            assert isinstance(embeddings[0]['audio_embedding'], np.ndarray)
            assert embeddings[0]['audio_embedding'].shape == (128,)
            assert embeddings[0]['lead_embedding'].shape == (512,)
            assert embeddings[0]['follow_embedding'].shape == (512,)
            assert embeddings[0]['interaction_embedding'].shape == (256,)
            assert embeddings[0]['text_embedding'].shape == (384,)
            
            # Check second embedding
            assert embeddings[1]['clip_id'] == 'test_clip_2'
            assert embeddings[1]['move_label'] == 'turn'
    
    def test_get_all_embeddings_with_filters(self, serverless_config, mock_es_client):
        """Test get_all_embeddings with metadata filters."""
        mock_es_client.search.return_value = {'hits': {'hits': []}}
        
        with patch('core.services.elasticsearch_service.Elasticsearch', return_value=mock_es_client):
            service = ElasticsearchService(serverless_config)
            service.get_all_embeddings(filters={'difficulty': 'beginner'})
            
            # Verify search was called with filters
            call_args = mock_es_client.search.call_args
            query = call_args[1]['body']['query']
            
            assert 'bool' in query
            assert 'must' in query['bool']


class TestBulkIndexing:
    """Test bulk indexing with proper format."""
    
    def test_bulk_index_format(self, serverless_config, mock_es_client):
        """Test bulk indexing uses correct format for client.bulk()."""
        mock_es_client.bulk.return_value = {
            'errors': False,
            'items': [
                {'index': {'status': 201}},
                {'index': {'status': 201}}
            ]
        }
        
        embeddings = [
            {
                'clip_id': 'test_1',
                'audio_embedding': [0.1] * 128,
                'lead_embedding': [0.2] * 512,
                'follow_embedding': [0.3] * 512,
                'interaction_embedding': [0.4] * 256,
                'text_embedding': [0.5] * 384,
                'move_label': 'basic_step',
                'difficulty': 'beginner'
            },
            {
                'clip_id': 'test_2',
                'audio_embedding': [0.6] * 128,
                'lead_embedding': [0.7] * 512,
                'follow_embedding': [0.8] * 512,
                'interaction_embedding': [0.9] * 256,
                'text_embedding': [1.0] * 384,
                'move_label': 'turn',
                'difficulty': 'intermediate'
            }
        ]
        
        with patch('core.services.elasticsearch_service.Elasticsearch', return_value=mock_es_client):
            service = ElasticsearchService(serverless_config)
            service.bulk_index_embeddings(embeddings)
            
            # Verify bulk was called
            mock_es_client.bulk.assert_called_once()
            
            # Verify format: alternating action/document
            call_args = mock_es_client.bulk.call_args
            operations = call_args[1]['operations']
            
            # Should have 4 items (2 embeddings * 2 lines each)
            assert len(operations) == 4
            
            # First should be action metadata
            assert 'index' in operations[0]
            assert operations[0]['index']['_id'] == 'test_1'
            
            # Second should be document
            assert 'clip_id' in operations[1]
            assert operations[1]['clip_id'] == 'test_1'
            
            # Verify refresh was called
            mock_es_client.indices.refresh.assert_called_once()


class TestErrorHandling:
    """Test error handling."""
    
    def test_connection_failure(self, serverless_config):
        """Test handling of connection failures."""
        mock_client = MagicMock()
        mock_client.ping.return_value = False
        
        with patch('core.services.elasticsearch_service.Elasticsearch', return_value=mock_client):
            from elasticsearch.exceptions import ConnectionError as ESConnectionError
            
            with pytest.raises(ESConnectionError):
                ElasticsearchService(serverless_config)
    
    def test_empty_embeddings_list(self, serverless_config, mock_es_client):
        """Test bulk indexing with empty list."""
        with patch('core.services.elasticsearch_service.Elasticsearch', return_value=mock_es_client):
            service = ElasticsearchService(serverless_config)
            
            # Should not raise, just log warning
            service.bulk_index_embeddings([])
            
            # Bulk should not be called
            mock_es_client.bulk.assert_not_called()
