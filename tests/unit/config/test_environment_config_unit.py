"""
Unit tests for Environment Configuration.

These tests verify:
- Local configuration loading from .env files
- Google Cloud configuration loading from Secret Manager
- Configuration validation
- Error handling for missing credentials
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

from common.config.environment_config import (
    ElasticsearchConfig,
    YOLOv8Config,
    EnvironmentConfig
)


# ============================================================================
# Unit Tests for ElasticsearchConfig
# ============================================================================

class TestElasticsearchConfig:
    """Unit tests for ElasticsearchConfig dataclass."""
    
    def test_elasticsearch_config_defaults(self):
        """Test ElasticsearchConfig with default values."""
        config = ElasticsearchConfig(
            host="localhost",
            port=9200,
            index_name="test_index"
        )
        
        assert config.host == "localhost"
        assert config.port == 9200
        assert config.index_name == "test_index"
        assert config.username is None
        assert config.password is None
        assert config.use_ssl is False
        assert config.verify_certs is True
        assert config.max_connections == 10
        assert config.timeout == 30
        assert config.retry_on_timeout is True
    
    def test_elasticsearch_config_with_auth(self):
        """Test ElasticsearchConfig with authentication."""
        config = ElasticsearchConfig(
            host="es.cloud.example.com",
            port=9243,
            index_name="prod_index",
            username="elastic",
            password="secret123",
            use_ssl=True
        )
        
        assert config.username == "elastic"
        assert config.password == "secret123"
        assert config.use_ssl is True
    
    def test_elasticsearch_config_custom_pool_settings(self):
        """Test ElasticsearchConfig with custom connection pool settings."""
        config = ElasticsearchConfig(
            host="localhost",
            port=9200,
            index_name="test_index",
            max_connections=20,
            timeout=60,
            retry_on_timeout=False
        )
        
        assert config.max_connections == 20
        assert config.timeout == 60
        assert config.retry_on_timeout is False


# ============================================================================
# Unit Tests for YOLOv8Config
# ============================================================================

class TestYOLOv8Config:
    """Unit tests for YOLOv8Config dataclass."""
    
    def test_yolov8_config_defaults(self):
        """Test YOLOv8Config with default values."""
        config = YOLOv8Config()
        
        assert config.model_name == "yolov8n-pose.pt"
        assert config.confidence_threshold == 0.3
        assert config.device == "cpu"
        assert config.iou_threshold == 0.5
        assert config.max_det == 10
    
    def test_yolov8_config_custom_values(self):
        """Test YOLOv8Config with custom values."""
        config = YOLOv8Config(
            model_name="yolov8m-pose.pt",
            confidence_threshold=0.5,
            device="cuda",
            iou_threshold=0.7,
            max_det=20
        )
        
        assert config.model_name == "yolov8m-pose.pt"
        assert config.confidence_threshold == 0.5
        assert config.device == "cuda"
        assert config.iou_threshold == 0.7
        assert config.max_det == 20
    
    def test_yolov8_config_cpu_device(self):
        """Test that YOLOv8Config can use CPU device."""
        config = YOLOv8Config(device="cpu")
        
        assert config.device == "cpu"


# ============================================================================
# Unit Tests for EnvironmentConfig - Local
# ============================================================================

class TestEnvironmentConfigLocal:
    """Unit tests for EnvironmentConfig in local mode."""
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "local",
        "ELASTICSEARCH_HOST": "localhost",
        "ELASTICSEARCH_PORT": "9200",
        "ELASTICSEARCH_INDEX": "test_index",
        "ELASTICSEARCH_USERNAME": "test_user",
        "ELASTICSEARCH_PASSWORD": "test_pass",
        "ELASTICSEARCH_USE_SSL": "false",
        "YOLOV8_MODEL": "yolov8n-pose.pt",
        "YOLOV8_CONFIDENCE": "0.5",
        "YOLOV8_DEVICE": "cpu"
    })
    @patch('dotenv.load_dotenv')
    def test_load_local_config(self, mock_load_dotenv):
        """Test loading configuration from local .env file."""
        config = EnvironmentConfig()
        
        # Verify environment was detected
        assert config.environment == "local"
        
        # Verify load_dotenv was called
        mock_load_dotenv.assert_called_once()
        
        # Verify Elasticsearch config
        assert config.elasticsearch.host == "localhost"
        assert config.elasticsearch.port == 9200
        assert config.elasticsearch.index_name == "test_index"
        assert config.elasticsearch.username == "test_user"
        assert config.elasticsearch.password == "test_pass"
        assert config.elasticsearch.use_ssl is False
        
        # Verify YOLOv8 config
        assert config.yolov8.model_name == "yolov8n-pose.pt"
        assert config.yolov8.confidence_threshold == 0.5
        assert config.yolov8.device == "cpu"
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "local",
        "ELASTICSEARCH_HOST": "localhost",
        "ELASTICSEARCH_PORT": "9200"
    }, clear=True)
    @patch('dotenv.load_dotenv')
    def test_load_local_config_defaults(self, mock_load_dotenv):
        """Test loading local configuration with default values."""
        # Set minimal required env vars
        os.environ["ENVIRONMENT"] = "local"
        os.environ["ELASTICSEARCH_HOST"] = "localhost"
        os.environ["ELASTICSEARCH_PORT"] = "9200"
        
        config = EnvironmentConfig()
        
        # Verify defaults are used
        assert config.elasticsearch.index_name == "bachata_move_embeddings"
        assert config.elasticsearch.username is None
        assert config.elasticsearch.password is None
        assert config.yolov8.model_name == "yolov8n-pose.pt"
        assert config.yolov8.confidence_threshold == 0.3
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "local",
        "ELASTICSEARCH_HOST": "localhost",
        "ELASTICSEARCH_PORT": "9200",
        "ELASTICSEARCH_USE_SSL": "true"
    })
    @patch('dotenv.load_dotenv')
    def test_load_local_config_ssl_parsing(self, mock_load_dotenv):
        """Test parsing of boolean SSL flag."""
        config = EnvironmentConfig()
        
        assert config.elasticsearch.use_ssl is True
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "local",
        "ELASTICSEARCH_HOST": "localhost",
        "ELASTICSEARCH_PORT": "9200",
        "YOLOV8_DEVICE": "cuda"
    })
    @patch('dotenv.load_dotenv')
    def test_load_local_config_device_parsing(self, mock_load_dotenv):
        """Test parsing of device configuration."""
        config = EnvironmentConfig()
        
        assert config.yolov8.device == "cuda"


# ============================================================================
# Unit Tests for EnvironmentConfig - Cloud
# ============================================================================

class TestEnvironmentConfigCloud:
    """Unit tests for EnvironmentConfig in cloud mode."""
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "cloud"
    }, clear=True)
    def test_load_cloud_config_missing_project_id(self):
        """Test that missing GCP_PROJECT_ID raises error."""
        # Mock the import to avoid ImportError
        with patch.dict('sys.modules', {'google.cloud.secretmanager': MagicMock()}):
            with pytest.raises(ValueError, match="GCP_PROJECT_ID environment variable required"):
                EnvironmentConfig()


# ============================================================================
# Unit Tests for EnvironmentConfig - Invalid Environment
# ============================================================================

class TestEnvironmentConfigInvalid:
    """Unit tests for EnvironmentConfig with invalid environment."""
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "invalid"
    })
    def test_invalid_environment(self):
        """Test that invalid environment raises error."""
        with pytest.raises(ValueError, match="Invalid ENVIRONMENT: invalid"):
            EnvironmentConfig()
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('dotenv.load_dotenv')
    def test_default_environment_is_local(self, mock_load_dotenv):
        """Test that default environment is 'local'."""
        # Set minimal required env vars for local
        with patch.dict(os.environ, {
            "ELASTICSEARCH_HOST": "localhost",
            "ELASTICSEARCH_PORT": "9200"
        }):
            config = EnvironmentConfig()
            
            assert config.environment == "local"


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = pytest.mark.unit
