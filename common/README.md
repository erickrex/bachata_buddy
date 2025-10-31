# Common App

## Purpose

The `common` app provides shared utilities, configuration management, and exception handling used across all other Django apps in the Bachata Buddy project. It contains truly foundational code with no domain-specific logic, ensuring it can be safely imported by any other app without creating circular dependencies.

This app was created as part of the core app refactoring to separate concerns and improve code organization.

## Architecture

The `common` app follows a strict dependency rule:
- **MUST NOT** depend on `video_processing`, `ai_services`, or any domain-specific apps
- **MAY** depend on Django core and third-party libraries
- **IS DEPENDED ON** by all other apps in the project

This ensures a clean dependency hierarchy and prevents circular imports.

## Services

### Resource Manager (`services/resource_manager.py`)

Manages system resources, file cleanup, and monitoring for the application.

**Key Features:**
- Automatic cleanup of temporary files based on age
- Cache directory size management
- System resource monitoring (memory, disk usage)
- Background monitoring with configurable intervals
- Graceful shutdown with cleanup

**Usage:**
```python
from common import resource_manager

# Get current system resources
resources = resource_manager.get_system_resources()
print(f"Memory usage: {resources['memory']['percent_used']}%")

# Clean up temporary files
stats = await resource_manager.cleanup_temporary_files()
print(f"Removed {stats['files_removed']} files")

# Start background monitoring
await resource_manager.start_monitoring()

# Schedule periodic cleanup (every 6 hours)
await resource_manager.schedule_cleanup(interval_hours=6)

# Shutdown gracefully
await resource_manager.shutdown()
```

**Configuration:**
- `max_temp_age_hours`: Files older than this are cleaned (default: 24 hours)
- `max_cache_size_gb`: Maximum cache size before cleanup (default: 5 GB)
- `memory_warning_threshold`: Memory usage % to trigger warnings (default: 85%)
- `disk_warning_threshold`: Disk usage % to trigger warnings (default: 90%)

### Temp File Manager (`services/temp_file_manager.py`)

Provides context managers for temporary files and directories with automatic cleanup.

**Key Features:**
- Automatic cleanup of temporary files when context exits
- User-specific temporary directories
- Tracking of active temporary files
- Bulk cleanup operations

**Usage:**
```python
from common import temp_file_manager

# Create a temporary file
async with temp_file_manager.temp_file(suffix=".mp4", user_id="123") as temp_path:
    # Use the temporary file
    with open(temp_path, 'wb') as f:
        f.write(video_data)
    # File is automatically cleaned up when context exits

# Create a temporary directory
async with temp_file_manager.temp_directory(prefix="processing_", user_id="123") as temp_dir:
    # Use the temporary directory
    output_file = temp_dir / "output.mp4"
    # Directory and all contents are automatically cleaned up

# Clean up all files for a specific user
await temp_file_manager.cleanup_user_temp_files(user_id="123")

# Get user-specific temp directory
user_temp_dir = temp_file_manager.get_user_temp_directory(user_id="123")
```

### Performance Monitor (`services/performance_monitor.py`)

**Status:** Stub implementation (planned but not yet implemented)

Intended for monitoring system performance metrics, A/B testing, and user feedback tracking.

**Planned Features:**
- Performance metrics collection (accuracy, precision, recall, F1 score, latency)
- Recommendation decision logging
- User feedback tracking
- A/B test configuration and analysis

### Directory Organizer (`services/directory_organizer.py`)

**Status:** Stub implementation (planned but not yet implemented)

Intended for organizing and managing directory structures for training data.

## Configuration

### Environment Config (`config/environment_config.py`)

Manages environment-specific configuration for local and cloud deployments.

**Supported Environments:**
- `local`: Uses `.env` files for configuration
- `cloud`: Uses Google Cloud Secret Manager for configuration

**Configuration Classes:**

#### `EnvironmentConfig`
Main configuration manager that loads settings based on the `ENVIRONMENT` variable.

**Usage:**
```python
from common import EnvironmentConfig

# Initialize configuration (reads ENVIRONMENT variable)
config = EnvironmentConfig()

# Access Elasticsearch configuration
es_config = config.elasticsearch
print(f"Elasticsearch host: {es_config.host}:{es_config.port}")

# Access YOLOv8 configuration
yolo_config = config.yolov8
print(f"YOLOv8 model: {yolo_config.model_name}")
```

#### `ElasticsearchConfig`
Configuration for Elasticsearch connections (supports both local and serverless).

**Attributes:**
- `host`: Elasticsearch host
- `port`: Elasticsearch port
- `index_name`: Index name for embeddings
- `username`: Username for basic auth (optional)
- `password`: Password for basic auth (optional)
- `api_key`: API key for serverless (optional)
- `use_ssl`: Whether to use SSL
- `verify_certs`: Whether to verify SSL certificates
- `max_connections`: Maximum connection pool size
- `timeout`: Request timeout in seconds
- `retry_on_timeout`: Whether to retry on timeout

**Usage:**
```python
from common import ElasticsearchConfig

# Create custom configuration
es_config = ElasticsearchConfig(
    host="localhost",
    port=9200,
    index_name="my_index",
    use_ssl=False
)
```

#### `YOLOv8Config`
Configuration for YOLOv8 pose detection model.

**Attributes:**
- `model_name`: Model file name (default: 'yolov8n-pose.pt')
- `confidence_threshold`: Minimum confidence for detections (default: 0.3)
- `device`: Device to run on ('cpu' or 'cuda', default: 'cpu')
- `iou_threshold`: IoU threshold for NMS (default: 0.5)
- `max_det`: Maximum number of detections (default: 10)

**Usage:**
```python
from common import YOLOv8Config

# Create custom configuration
yolo_config = YOLOv8Config(
    model_name='yolov8m-pose.pt',
    confidence_threshold=0.5,
    device='cuda'
)
```

**Environment Variables:**

For local development (`.env` file):
```bash
# Environment
ENVIRONMENT=local

# Elasticsearch (Local)
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=bachata_move_embeddings
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=changeme
ELASTICSEARCH_USE_SSL=false

# Elasticsearch (Serverless)
ELASTICSEARCH_HOST=https://my-deployment.es.us-central1.gcp.cloud.es.io
ELASTICSEARCH_API_KEY=your_api_key_here
ELASTICSEARCH_INDEX=bachata_move_embeddings

# YOLOv8
YOLOV8_MODEL=yolov8n-pose.pt
YOLOV8_CONFIDENCE=0.3
YOLOV8_DEVICE=cpu
YOLOV8_IOU_THRESHOLD=0.5
YOLOV8_MAX_DET=10
```

For cloud deployment:
```bash
ENVIRONMENT=cloud
GCP_PROJECT_ID=your-project-id
# Secrets are loaded from Google Cloud Secret Manager
```

## Exceptions

### Exception Hierarchy

All custom exceptions inherit from `ChoreographyGenerationError`, which provides:
- `message`: Human-readable error message
- `error_code`: Machine-readable error code
- `details`: Optional dictionary with additional context

**Available Exceptions:**

#### `ChoreographyGenerationError`
Base exception for all choreography-related errors.

```python
from common import ChoreographyGenerationError

raise ChoreographyGenerationError(
    message="Failed to generate choreography",
    error_code="GENERATION_ERROR",
    details={"step": "music_analysis", "duration": 120}
)
```

#### `YouTubeDownloadError`
Raised when YouTube download fails.

```python
from common import YouTubeDownloadError

raise YouTubeDownloadError(
    message="Video is unavailable",
    url="https://youtube.com/watch?v=...",
    details={"reason": "video_removed"}
)
```

#### `MusicAnalysisError`
Raised when music analysis fails.

```python
from common import MusicAnalysisError

raise MusicAnalysisError(
    message="Audio file is corrupted",
    audio_path="/path/to/audio.mp3",
    details={"file_size": 0}
)
```

#### `MoveAnalysisError`
Raised when move analysis fails.

```python
from common import MoveAnalysisError

raise MoveAnalysisError(
    message="Pose detection failed",
    video_path="/path/to/video.mp4",
    details={"frames_processed": 0}
)
```

#### `VideoGenerationError`
Raised when video generation fails.

```python
from common import VideoGenerationError

raise VideoGenerationError(
    message="FFmpeg encoding failed",
    details={"exit_code": 1, "stderr": "..."}
)
```

#### `ValidationError`
Raised when input validation fails.

```python
from common import ValidationError

raise ValidationError(
    message="Invalid difficulty level",
    field="difficulty",
    value="expert",
    details={"allowed_values": ["beginner", "intermediate", "advanced"]}
)
```

#### `ResourceError`
Raised when system resources are insufficient.

```python
from common import ResourceError

raise ResourceError(
    message="Insufficient memory",
    resource_type="memory",
    details={"required_mb": 2048, "available_mb": 512}
)
```

#### `ServiceUnavailableError`
Raised when a required service is unavailable.

```python
from common import ServiceUnavailableError

raise ServiceUnavailableError(
    message="Elasticsearch is not responding",
    service_name="elasticsearch",
    details={"timeout": 30}
)
```

### User-Friendly Error Messages

The `get_user_friendly_message()` function provides user-friendly error messages for display in the UI.

**Usage:**
```python
from common import get_user_friendly_message, YouTubeDownloadError

try:
    # ... download video
    pass
except YouTubeDownloadError as e:
    user_message = get_user_friendly_message(e.error_code, "video_unavailable")
    # Display user_message in the UI
```

**Available Error Types:**
- `YOUTUBE_DOWNLOAD_ERROR`: invalid_url, video_unavailable, restricted_content, network_error, format_error
- `MUSIC_ANALYSIS_ERROR`: file_not_found, unsupported_format, corrupted_file, too_short, too_long, analysis_failed
- `MOVE_ANALYSIS_ERROR`: video_not_found, pose_detection_failed, insufficient_frames, analysis_timeout
- `VIDEO_GENERATION_ERROR`: ffmpeg_error, insufficient_moves, sync_error, output_error
- `VALIDATION_ERROR`: invalid_difficulty, invalid_quality, invalid_url_format, missing_required_field
- `RESOURCE_ERROR`: insufficient_memory, disk_space_full, cpu_overload
- `SERVICE_UNAVAILABLE_ERROR`: youtube_service, analysis_service, generation_service

## Dependencies

### Required Packages
- `django`: Web framework
- `psutil`: System resource monitoring
- `python-dotenv`: Environment variable loading (local development)
- `google-cloud-secret-manager`: Secret management (cloud deployment)
- `pydantic`: Data validation (for performance monitor)

### Internal Dependencies
- **Depends on:** None (foundational app)
- **Used by:** 
  - `video_processing`: Uses configuration, exceptions, and resource management
  - `ai_services`: Uses configuration and exceptions
  - `choreography`: Uses exceptions for error handling
  - `users`: Uses exceptions for error handling
  - `instructors`: Uses exceptions for error handling
  - `user_collections`: Uses exceptions for error handling

## Import Examples

### Importing Configuration
```python
from common import EnvironmentConfig, ElasticsearchConfig, YOLOv8Config

# Load environment-specific configuration
config = EnvironmentConfig()
es_config = config.elasticsearch
yolo_config = config.yolov8
```

### Importing Exceptions
```python
from common import (
    ChoreographyGenerationError,
    YouTubeDownloadError,
    MusicAnalysisError,
    VideoGenerationError,
    ValidationError,
    get_user_friendly_message
)
```

### Importing Services
```python
from common import (
    resource_manager,
    temp_file_manager,
    ResourceManager,
    TempFileManager,
    PerformanceMonitor,
    DirectoryOrganizer
)
```

### Importing Everything
```python
from common import *  # Not recommended, but available
```

## Testing

Tests for the `common` app are located in `tests/unit/config/` and `tests/services/`.

**Run tests:**
```bash
# Run all common app tests
uv run pytest tests/unit/config/ tests/services/test_resource_manager.py -v

# Run specific test file
uv run pytest tests/unit/config/test_environment_config.py -v
```

## Migration Notes

This app was created during the core app refactoring (see `.kiro/specs/core-app-refactoring/`). Services and configuration were moved from the monolithic `core` app to improve code organization and maintainability.

**Previous Import Paths:**
```python
# Old (deprecated)
from core.config.environment_config import EnvironmentConfig
from core.exceptions import ChoreographyGenerationError
from core.services.resource_manager import resource_manager

# New (current)
from common import EnvironmentConfig
from common import ChoreographyGenerationError
from common import resource_manager
```

## Contributing

When adding new utilities to the `common` app:

1. **Ensure it's truly shared**: Only add code that is used by multiple apps
2. **Avoid domain logic**: Keep domain-specific code in domain apps
3. **Maintain zero dependencies**: Don't import from `video_processing`, `ai_services`, or domain apps
4. **Export in `__init__.py`**: Add new classes/functions to `__all__` for easy importing
5. **Document thoroughly**: Update this README with usage examples
6. **Write tests**: Add unit tests for all new functionality

## License

See the main project LICENSE file.
