# Environment Configuration

This module provides environment-specific configuration management for the Bachata Buddy application, supporting both local development and Google Cloud production environments.

## Features

- **Local Development**: Uses `.env` files for configuration
- **Google Cloud Production**: Uses Google Cloud Secret Manager for secure credential storage
- **Automatic Validation**: Validates all configuration parameters on load
- **Type Safety**: Uses dataclasses for type-safe configuration objects

## Usage

### Local Development

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your local settings:
```bash
ENVIRONMENT=local
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
MMPOSE_CHECKPOINT_PATH=./checkpoints
```

3. Use the configuration in your code:
```python
from core.config.environment_config import EnvironmentConfig

config = EnvironmentConfig()

# Access Elasticsearch configuration
print(config.elasticsearch.host)
print(config.elasticsearch.port)

# Access MMPose configuration
print(config.mmpose.model_checkpoint_path)
print(config.mmpose.confidence_threshold)
```

### Google Cloud Production

1. Set the environment variable:
```bash
export ENVIRONMENT=cloud
export GCP_PROJECT_ID=your-project-id
```

2. Create secrets in Google Cloud Secret Manager:
```bash
# Elasticsearch secrets
echo -n "your-es-host.es.gcp.cloud.es.io" | \
    gcloud secrets create elasticsearch-host --data-file=-

echo -n "9243" | \
    gcloud secrets create elasticsearch-port --data-file=-

echo -n "elastic" | \
    gcloud secrets create elasticsearch-username --data-file=-

echo -n "your-password" | \
    gcloud secrets create elasticsearch-password --data-file=-

# MMPose secrets
echo -n "gs://your-bucket/checkpoints" | \
    gcloud secrets create mmpose-checkpoint-path --data-file=-
```

3. Grant access to the service account:
```bash
gcloud secrets add-iam-policy-binding elasticsearch-host \
    --member="serviceAccount:your-project@appspot.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

4. Use the same code as local development - the configuration will automatically load from Secret Manager.

## Configuration Objects

### ElasticsearchConfig

```python
@dataclass
class ElasticsearchConfig:
    host: str                      # Elasticsearch host
    port: int                      # Elasticsearch port
    index_name: str                # Index name for embeddings
    username: Optional[str]        # Username (optional)
    password: Optional[str]        # Password (optional)
    use_ssl: bool                  # Use SSL/TLS
    verify_certs: bool             # Verify SSL certificates
    max_connections: int           # Connection pool size
    timeout: int                   # Request timeout (seconds)
    retry_on_timeout: bool         # Retry on timeout
```

### MMPoseConfig

```python
@dataclass
class MMPoseConfig:
    model_checkpoint_path: str     # Path to model checkpoints
    confidence_threshold: float    # Confidence threshold (0.0-1.0)
    enable_hand_detection: bool    # Enable hand keypoint detection
    device: str                    # Device (always "cpu")
```

## Validation

The configuration system automatically validates:

- **Elasticsearch**:
  - Host is not empty
  - Port is a positive integer
  - Index name is not empty

- **MMPose**:
  - Checkpoint path is not empty
  - Confidence threshold is between 0.0 and 1.0
  - Device is set to "cpu"

If validation fails, a `ValueError` is raised with a clear error message indicating:
- What went wrong
- Which environment is being used
- How to fix the issue

## Testing

Run the configuration tests:

```bash
# Test basic configuration loading
python test_config.py

# Test validation
python test_config_validation.py
```

## Environment Variables

### Required for Local Development

- `ENVIRONMENT=local`
- `ELASTICSEARCH_HOST` (default: localhost)
- `ELASTICSEARCH_PORT` (default: 9200)
- `MMPOSE_CHECKPOINT_PATH` (default: ./checkpoints)

### Required for Google Cloud

- `ENVIRONMENT=cloud`
- `GCP_PROJECT_ID` (your Google Cloud project ID)

### Optional

- `ELASTICSEARCH_INDEX` (default: bachata_move_embeddings)
- `ELASTICSEARCH_USERNAME`
- `ELASTICSEARCH_PASSWORD`
- `ELASTICSEARCH_USE_SSL` (default: false for local, true for cloud)
- `ELASTICSEARCH_VERIFY_CERTS` (default: true)
- `ELASTICSEARCH_MAX_CONNECTIONS` (default: 10)
- `ELASTICSEARCH_TIMEOUT` (default: 30)
- `ELASTICSEARCH_RETRY_ON_TIMEOUT` (default: true)
- `MMPOSE_CONFIDENCE` (default: 0.3)
- `MMPOSE_HAND_DETECTION` (default: true)

## Error Messages

The configuration system provides clear error messages:

```
Invalid ENVIRONMENT: production. Must be 'local' or 'cloud'
```

```
GCP_PROJECT_ID environment variable required for cloud environment. 
Please set GCP_PROJECT_ID to your Google Cloud project ID.
```

```
Elasticsearch port must be a positive integer. Environment: local. Got: -1
```

```
MMPose confidence threshold must be between 0.0 and 1.0. Environment: local. Got: 1.5
```

## Security Notes

- **Never commit `.env` files** - they are in `.gitignore`
- **Use Secret Manager in production** - never hardcode credentials
- **Rotate secrets regularly** - especially in production
- **Use least privilege** - grant only necessary IAM permissions
