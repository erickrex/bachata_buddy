"""
Environment-specific configuration management for Bachata Buddy.

Supports two environments:
- local: Uses .env files for configuration
- cloud: Uses Google Cloud Secret Manager for configuration
"""

from dataclasses import dataclass
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


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
    # Serverless API key authentication
    api_key: Optional[str] = None


@dataclass
class YOLOv8Config:
    """YOLOv8-Pose model configuration."""
    model_name: str = 'yolov8n-pose.pt'
    confidence_threshold: float = 0.3
    device: str = 'cpu'
    iou_threshold: float = 0.5
    max_det: int = 10


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
        
        # Elasticsearch configuration
        # Serverless (host + api_key) or Local (host + port)
        
        api_key = os.getenv("ELASTICSEARCH_API_KEY")
        host = os.getenv("ELASTICSEARCH_HOST", "localhost")
        port_str = os.getenv("ELASTICSEARCH_PORT", "443" if api_key else "9200")
        
        # Parse port
        try:
            port = int(port_str) if port_str else 443
        except ValueError:
            port = 443 if api_key else 9200
        
        if api_key:
            # Serverless mode (endpoint URL + API key)
            self.elasticsearch = ElasticsearchConfig(
                host=host,
                port=port,
                index_name=os.getenv("ELASTICSEARCH_INDEX", "bachata_move_embeddings"),
                api_key=api_key,
                use_ssl=True,  # Always true for serverless
                verify_certs=True,
                max_connections=int(os.getenv("ELASTICSEARCH_MAX_CONNECTIONS", "10")),
                timeout=int(os.getenv("ELASTICSEARCH_TIMEOUT", "30")),
                retry_on_timeout=os.getenv("ELASTICSEARCH_RETRY_ON_TIMEOUT", "true").lower() == "true"
            )
        else:
            # Local mode (host + port, optional basic auth)
            self.elasticsearch = ElasticsearchConfig(
                host=host,
                port=port,
                index_name=os.getenv("ELASTICSEARCH_INDEX", "bachata_move_embeddings"),
                username=os.getenv("ELASTICSEARCH_USERNAME"),
                password=os.getenv("ELASTICSEARCH_PASSWORD"),
                use_ssl=os.getenv("ELASTICSEARCH_USE_SSL", "false").lower() == "true",
                verify_certs=os.getenv("ELASTICSEARCH_VERIFY_CERTS", "true").lower() == "true",
                max_connections=int(os.getenv("ELASTICSEARCH_MAX_CONNECTIONS", "10")),
                timeout=int(os.getenv("ELASTICSEARCH_TIMEOUT", "30")),
                retry_on_timeout=os.getenv("ELASTICSEARCH_RETRY_ON_TIMEOUT", "true").lower() == "true"
            )
        
        self.yolov8 = YOLOv8Config(
            model_name=os.getenv("YOLOV8_MODEL", "yolov8n-pose.pt"),
            confidence_threshold=float(os.getenv("YOLOV8_CONFIDENCE", "0.3")),
            device=os.getenv("YOLOV8_DEVICE", "cpu"),
            iou_threshold=float(os.getenv("YOLOV8_IOU_THRESHOLD", "0.5")),
            max_det=int(os.getenv("YOLOV8_MAX_DET", "10"))
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
        
        # Initialize Secret Manager client (may not be used if env vars are set)
        client = None
        try:
            client = secretmanager.SecretManagerServiceClient()
        except Exception as e:
            logger.warning(f"Failed to initialize Secret Manager client: {e}")
        
        # Try environment variables first, then Secret Manager
        es_host = os.getenv("ELASTICSEARCH_HOST")
        es_api_key = os.getenv("ELASTICSEARCH_API_KEY")
        
        if not es_host or not es_api_key:
            # Fallback to Secret Manager
            if client:
                try:
                    es_host = es_host or self._get_secret(client, project_id, "elasticsearch-host")
                    es_port = int(self._get_secret(client, project_id, "elasticsearch-port", default="443"))
                    es_username = self._get_secret(client, project_id, "elasticsearch-username", default="")
                    es_password = self._get_secret(client, project_id, "elasticsearch-password", default="")
                except Exception as e:
                    logger.warning(f"Failed to load from Secret Manager, using defaults: {e}")
                    es_port = 443
                    es_username = ""
                    es_password = ""
            else:
                logger.warning("Secret Manager client not available, using defaults")
                es_port = 443
                es_username = ""
                es_password = ""
        else:
            # Using environment variables (Elasticsearch Serverless with API key)
            es_port = 443
            es_username = ""
            es_password = ""
        
        # Use API key if available (Elasticsearch Serverless), otherwise username/password
        if es_api_key:
            self.elasticsearch = ElasticsearchConfig(
                host=es_host,
                port=es_port,
                index_name=os.getenv("ELASTICSEARCH_INDEX", "bachata_move_embeddings"),
                api_key=es_api_key,
                use_ssl=True,
                verify_certs=True,
                max_connections=10,
                timeout=30,
                retry_on_timeout=True
            )
        else:
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
        
        # YOLOv8 config - try env var first, then Secret Manager, then default
        model_name = os.getenv("YOLOV8_MODEL")
        if not model_name and client:
            try:
                model_name = self._get_secret(client, project_id, "yolov8-model-name", default="yolov8n-pose.pt")
            except:
                model_name = "yolov8n-pose.pt"
        elif not model_name:
            model_name = "yolov8n-pose.pt"
        
        self.yolov8 = YOLOv8Config(
            model_name=model_name,
            confidence_threshold=float(os.getenv("YOLOV8_CONFIDENCE", "0.3")),
            device=os.getenv("YOLOV8_DEVICE", "cpu"),
            iou_threshold=float(os.getenv("YOLOV8_IOU_THRESHOLD", "0.5")),
            max_det=int(os.getenv("YOLOV8_MAX_DET", "10"))
        )
    
    def _get_secret(self, client, project_id: str, secret_id: str, default: Optional[str] = None) -> str:
        """
        Retrieve secret from Google Cloud Secret Manager.
        
        Args:
            client: SecretManagerServiceClient instance
            project_id: Google Cloud project ID
            secret_id: Secret identifier
            default: Default value if secret not found (optional)
            
        Returns:
            Secret value as string
            
        Raises:
            Exception: If secret cannot be retrieved and no default provided
        """
        try:
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            if default is not None:
                logger.warning(f"Secret '{secret_id}' not found, using default: {default}")
                return default
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
                f"Elasticsearch connection is required. "
                f"Environment: {self.environment}. "
                f"Please set:\n"
                f"  - ELASTICSEARCH_HOST + ELASTICSEARCH_API_KEY (Serverless)\n"
                f"  - ELASTICSEARCH_HOST + ELASTICSEARCH_PORT (Local)"
            )
        
        # Port validation
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
        
        # Validate YOLOv8 configuration
        if not self.yolov8.model_name:
            raise ValueError(
                f"YOLOv8 model name is required. "
                f"Environment: {self.environment}. "
                f"Please set YOLOV8_MODEL in .env file (local) or use default."
            )
        
        if not (0.0 <= self.yolov8.confidence_threshold <= 1.0):
            raise ValueError(
                f"YOLOv8 confidence threshold must be between 0.0 and 1.0. "
                f"Environment: {self.environment}. "
                f"Got: {self.yolov8.confidence_threshold}"
            )
        
        if not (0.0 <= self.yolov8.iou_threshold <= 1.0):
            raise ValueError(
                f"YOLOv8 IoU threshold must be between 0.0 and 1.0. "
                f"Environment: {self.environment}. "
                f"Got: {self.yolov8.iou_threshold}"
            )
        
        if self.yolov8.device not in ["cpu", "cuda"]:
            raise ValueError(
                f"YOLOv8 device must be 'cpu' or 'cuda'. "
                f"Environment: {self.environment}. "
                f"Got: {self.yolov8.device}"
            )
