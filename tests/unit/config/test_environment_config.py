"""
Tests for environment configuration.

Tests both local (.env) and cloud (Secret Manager) configuration loading,
as well as validation of configuration parameters.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from common.config.environment_config import EnvironmentConfig, ElasticsearchConfig, YOLOv8Config


class TestEnvironmentConfigLocal:
    """Tests for local environment configuration."""
    
    @pytest.fixture(autouse=True)
    def setup_local_env(self, monkeypatch):
        """Set up local environment variables for testing."""
        monkeypatch.setenv("ENVIRONMENT", "local")
        monkeypatch.setenv("ELASTICSEARCH_HOST", "localhost")
        monkeypatch.setenv("ELASTICSEARCH_PORT", "9200")
        monkeypatch.setenv("ELASTICSEARCH_INDEX", "test_index")
        monkeypatch.setenv("YOLOV8_MODEL", "yolov8n-pose.pt")
        monkeypatch.setenv("YOLOV8_CONFIDENCE", "0.3")
    
    def test_load_local_config(self):
        """Test loading local configuration from .env."""
        config = EnvironmentConfig()
        
        assert config.environment == "local"
        assert config.elasticsearch.host == "localhost"
        assert config.elasticsearch.port == 9200
        assert config.elasticsearch.index_name == "test_index"
        assert config.yolov8.model_name == "yolov8n-pose.pt"
        assert config.yolov8.confidence_threshold == 0.3
        assert config.yolov8.device == "cpu"
    
    def test_elasticsearch_defaults(self, monkeypatch):
        """Test Elasticsearch default values."""
        monkeypatch.delenv("ELASTICSEARCH_INDEX", raising=False)
        
        config = EnvironmentConfig()
        
        assert config.elasticsearch.index_name == "bachata_move_embeddings"
        assert config.elasticsearch.use_ssl is False
        assert config.elasticsearch.verify_certs is True
        assert config.elasticsearch.max_connections == 10
        assert config.elasticsearch.timeout == 30
    
    def test_yolov8_defaults(self, monkeypatch):
        """Test YOLOv8 default values."""
        monkeypatch.delenv("YOLOV8_CONFIDENCE", raising=False)
        monkeypatch.delenv("YOLOV8_MODEL", raising=False)
        
        config = EnvironmentConfig()
        
        assert config.yolov8.confidence_threshold == 0.3
        assert config.yolov8.model_name == "yolov8n-pose.pt"
        assert config.yolov8.device == "cpu"
    
    def test_ssl_configuration(self, monkeypatch):
        """Test SSL configuration."""
        monkeypatch.setenv("ELASTICSEARCH_USE_SSL", "true")
        monkeypatch.setenv("ELASTICSEARCH_VERIFY_CERTS", "false")
        
        config = EnvironmentConfig()
        
        assert config.elasticsearch.use_ssl is True
        assert config.elasticsearch.verify_certs is False


class TestEnvironmentConfigValidation:
    """Tests for configuration validation."""
    
    def test_invalid_environment(self, monkeypatch):
        """Test that invalid environment raises ValueError."""
        monkeypatch.setenv("ENVIRONMENT", "invalid")
        
        with pytest.raises(ValueError, match="Invalid ENVIRONMENT"):
            EnvironmentConfig()
    
    def test_missing_elasticsearch_host(self, monkeypatch):
        """Test that missing Elasticsearch host raises ValueError."""
        monkeypatch.setenv("ENVIRONMENT", "local")
        monkeypatch.setenv("ELASTICSEARCH_HOST", "")
        monkeypatch.setenv("ELASTICSEARCH_PORT", "9200")
        monkeypatch.setenv("YOLOV8_MODEL", "yolov8n-pose.pt")
        
        with pytest.raises(ValueError, match="Elasticsearch connection is required"):
            EnvironmentConfig()
    
    def test_invalid_elasticsearch_port(self, monkeypatch):
        """Test that invalid Elasticsearch port raises ValueError."""
        monkeypatch.setenv("ENVIRONMENT", "local")
        monkeypatch.setenv("ELASTICSEARCH_HOST", "localhost")
        monkeypatch.setenv("ELASTICSEARCH_PORT", "-1")
        monkeypatch.setenv("YOLOV8_MODEL", "yolov8n-pose.pt")
        
        with pytest.raises(ValueError, match="port must be a positive integer"):
            EnvironmentConfig()
    
    def test_invalid_confidence_threshold_high(self, monkeypatch):
        """Test that confidence threshold > 1.0 raises ValueError."""
        monkeypatch.setenv("ENVIRONMENT", "local")
        monkeypatch.setenv("ELASTICSEARCH_HOST", "localhost")
        monkeypatch.setenv("ELASTICSEARCH_PORT", "9200")
        monkeypatch.setenv("YOLOV8_MODEL", "yolov8n-pose.pt")
        monkeypatch.setenv("YOLOV8_CONFIDENCE", "1.5")
        
        with pytest.raises(ValueError, match="confidence threshold must be between 0.0 and 1.0"):
            EnvironmentConfig()
    
    def test_invalid_confidence_threshold_low(self, monkeypatch):
        """Test that confidence threshold < 0.0 raises ValueError."""
        monkeypatch.setenv("ENVIRONMENT", "local")
        monkeypatch.setenv("ELASTICSEARCH_HOST", "localhost")
        monkeypatch.setenv("ELASTICSEARCH_PORT", "9200")
        monkeypatch.setenv("YOLOV8_MODEL", "yolov8n-pose.pt")
        monkeypatch.setenv("YOLOV8_CONFIDENCE", "-0.1")
        
        with pytest.raises(ValueError, match="confidence threshold must be between 0.0 and 1.0"):
            EnvironmentConfig()
    
    def test_missing_yolov8_model(self, monkeypatch):
        """Test that missing YOLOv8 model uses default."""
        monkeypatch.setenv("ENVIRONMENT", "local")
        monkeypatch.setenv("ELASTICSEARCH_HOST", "localhost")
        monkeypatch.setenv("ELASTICSEARCH_PORT", "9200")
        monkeypatch.delenv("YOLOV8_MODEL", raising=False)
        
        config = EnvironmentConfig()
        assert config.yolov8.model_name == "yolov8n-pose.pt"


class TestEnvironmentConfigCloud:
    """Tests for cloud environment configuration."""
    
    @patch('common.config.environment_config.secretmanager.SecretManagerServiceClient')
    def test_load_cloud_config(self, mock_secret_client, monkeypatch):
        """Test loading cloud configuration from Secret Manager."""
        monkeypatch.setenv("ENVIRONMENT", "cloud")
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
        
        # Mock secret manager responses
        mock_client = MagicMock()
        mock_secret_client.return_value = mock_client
        
        def mock_access_secret(request):
            secret_id = request["name"].split("/")[-3]
            mock_response = MagicMock()
            
            secrets = {
                "elasticsearch-host": "es.cloud.example.com",
                "elasticsearch-port": "9243",
                "elasticsearch-username": "elastic",
                "elasticsearch-password": "secret123",
                "yolov8-model-name": "yolov8n-pose.pt"
            }
            
            mock_response.payload.data.decode.return_value = secrets.get(secret_id, "")
            return mock_response
        
        mock_client.access_secret_version = mock_access_secret
        
        config = EnvironmentConfig()
        
        assert config.environment == "cloud"
        assert config.elasticsearch.host == "es.cloud.example.com"
        assert config.elasticsearch.port == 9243
        assert config.elasticsearch.username == "elastic"
        assert config.elasticsearch.password == "secret123"
        assert config.elasticsearch.use_ssl is True
        assert config.yolov8.model_name == "yolov8n-pose.pt"
    
    def test_missing_gcp_project_id(self, monkeypatch):
        """Test that missing GCP_PROJECT_ID raises ValueError."""
        monkeypatch.setenv("ENVIRONMENT", "cloud")
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        
        with pytest.raises(ValueError, match="GCP_PROJECT_ID environment variable required"):
            EnvironmentConfig()


class TestDataClasses:
    """Tests for configuration dataclasses."""
    
    def test_elasticsearch_config_creation(self):
        """Test ElasticsearchConfig creation."""
        config = ElasticsearchConfig(
            host="localhost",
            port=9200,
            index_name="test_index",
            username="user",
            password="pass",
            use_ssl=True
        )
        
        assert config.host == "localhost"
        assert config.port == 9200
        assert config.index_name == "test_index"
        assert config.username == "user"
        assert config.password == "pass"
        assert config.use_ssl is True
        assert config.verify_certs is True  # default
        assert config.max_connections == 10  # default
    
    def test_yolov8_config_creation(self):
        """Test YOLOv8Config creation."""
        config = YOLOv8Config(
            model_name="yolov8n-pose.pt",
            confidence_threshold=0.5,
            device="cpu"
        )
        
        assert config.model_name == "yolov8n-pose.pt"
        assert config.confidence_threshold == 0.5
        assert config.device == "cpu"
