"""
Environment-specific configuration management for Bachata Buddy.

Supports two environments:
- local: Uses .env files for configuration
- cloud: Uses Google Cloud Secret Manager for configuration
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class ElasticsearchConfig:
    """Elasticsearch connection configuration."""
    host: str
    port: int
    index_name: str
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = False
    verify_certs: bool = True
    max_connections: int = 10
    timeout: int = 30
    retry_on_timeout: bool = True


@dataclass
class MMPoseConfig:
    """MMPose model configuration."""
    model_checkpoint_path: str
    confidence_threshold: float = 0.3
    enable_hand_detection: bool = True
    device: str = "cpu"  # Always CPU


class EnvironmentConfig:
    """
    Environment-specific configuration manager.
    
    Supports two environments:
    - local: Uses .env files
    - cloud: Uses Google Cloud Secret Manager
    
    Usage:
        config = EnvironmentConfig()
        es_config = config.elasticsearch
        mmpose_config = config.mmpose
    """
    
    def __init__(self):
        """Initialize configuration based on ENVIRONMENT variable."""
        self.environment = os.getenv("ENVIRONMENT", "local")
        
        if self.environment == "local":
            self._load_local_config()
        elif self.environment == "cloud":
            self._load_cloud_config()
        else:
            raise ValueError(
                f"Invalid ENVIRONMENT: {self.environment}. "
                f"Must be 'local' or 'cloud'"
            )
        
        # Validate configuration after loading
        self._validate_config()
    
    def _load_local_config(self):
        """Load configuration from .env file."""
        from dotenv import load_dotenv
        
        load_dotenv()
        
        self.elasticsearch = ElasticsearchConfig(
            host=os.getenv("ELASTICSEARCH_HOST", "localhost"),
            port=int(os.getenv("ELASTICSEARCH_PORT", "9200")),
            index_name=os.getenv("ELASTICSEARCH_INDEX", "bachata_move_embeddings"),
            username=os.getenv("ELASTICSEARCH_USERNAME"),
            password=os.getenv("ELASTICSEARCH_PASSWORD"),
            use_ssl=os.getenv("ELASTICSEARCH_USE_SSL", "false").lower() == "true",
            verify_certs=os.getenv("ELASTICSEARCH_VERIFY_CERTS", "true").lower() == "true",
            max_connections=int(os.getenv("ELASTICSEARCH_MAX_CONNECTIONS", "10")),
            timeout=int(os.getenv("ELASTICSEARCH_TIMEOUT", "30")),
            retry_on_timeout=os.getenv("ELASTICSEARCH_RETRY_ON_TIMEOUT", "true").lower() == "true"
        )
        
        self.mmpose = MMPoseConfig(
            model_checkpoint_path=os.getenv("MMPOSE_CHECKPOINT_PATH", "./checkpoints"),
            confidence_threshold=float(os.getenv("MMPOSE_CONFIDENCE", "0.3")),
            enable_hand_detection=os.getenv("MMPOSE_HAND_DETECTION", "true").lower() == "true",
            device="cpu"  # Always CPU
        )
    
    def _load_cloud_config(self):
        """Load configuration from Google Cloud Secret Manager."""
        from google.cloud import secretmanager
        
        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            raise ValueError(
                "GCP_PROJECT_ID environment variable required for cloud environment. "
                "Please set GCP_PROJECT_ID to your Google Cloud project ID."
            )
        
        client = secretmanager.SecretManagerServiceClient()
        
        # Load Elasticsearch config from secrets
        es_host = self._get_secret(client, project_id, "elasticsearch-host")
        es_port = int(self._get_secret(client, project_id, "elasticsearch-port"))
        es_username = self._get_secret(client, project_id, "elasticsearch-username")
        es_password = self._get_secret(client, project_id, "elasticsearch-password")
        
        self.elasticsearch = ElasticsearchConfig(
            host=es_host,
            port=es_port,
            index_name="bachata_move_embeddings",
            username=es_username,
            password=es_password,
            use_ssl=True,
            verify_certs=True,
            max_connections=10,
            timeout=30,
            retry_on_timeout=True
        )
        
        # MMPose config
        checkpoint_path = self._get_secret(client, project_id, "mmpose-checkpoint-path")
        
        self.mmpose = MMPoseConfig(
            model_checkpoint_path=checkpoint_path,
            confidence_threshold=0.3,
            enable_hand_detection=True,
            device="cpu"  # Always CPU
        )
    
    def _get_secret(self, client, project_id: str, secret_id: str) -> str:
        """
        Retrieve secret from Google Cloud Secret Manager.
        
        Args:
            client: SecretManagerServiceClient instance
            project_id: Google Cloud project ID
            secret_id: Secret identifier
            
        Returns:
            Secret value as string
            
        Raises:
            Exception: If secret cannot be retrieved
        """
        try:
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            raise Exception(
                f"Failed to retrieve secret '{secret_id}' from Google Cloud Secret Manager. "
                f"Ensure the secret exists and the service account has access. Error: {e}"
            )
    
    def _validate_config(self):
        """
        Validate configuration after loading.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate Elasticsearch configuration
        if not self.elasticsearch.host:
            raise ValueError(
                f"Elasticsearch host is required. "
                f"Environment: {self.environment}. "
                f"Please set ELASTICSEARCH_HOST in .env file (local) or Secret Manager (cloud)."
            )
        
        if not isinstance(self.elasticsearch.port, int) or self.elasticsearch.port <= 0:
            raise ValueError(
                f"Elasticsearch port must be a positive integer. "
                f"Environment: {self.environment}. "
                f"Got: {self.elasticsearch.port}"
            )
        
        if not self.elasticsearch.index_name:
            raise ValueError(
                f"Elasticsearch index name is required. "
                f"Environment: {self.environment}. "
                f"Please set ELASTICSEARCH_INDEX in .env file (local) or use default."
            )
        
        # Validate MMPose configuration
        if not self.mmpose.model_checkpoint_path:
            raise ValueError(
                f"MMPose checkpoint path is required. "
                f"Environment: {self.environment}. "
                f"Please set MMPOSE_CHECKPOINT_PATH in .env file (local) or Secret Manager (cloud)."
            )
        
        if not (0.0 <= self.mmpose.confidence_threshold <= 1.0):
            raise ValueError(
                f"MMPose confidence threshold must be between 0.0 and 1.0. "
                f"Environment: {self.environment}. "
                f"Got: {self.mmpose.confidence_threshold}"
            )
        
        if self.mmpose.device != "cpu":
            raise ValueError(
                f"MMPose device must be 'cpu' (GPU not supported). "
                f"Environment: {self.environment}. "
                f"Got: {self.mmpose.device}"
            )
