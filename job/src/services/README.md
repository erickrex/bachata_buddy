# Job Services

This directory contains service modules for the video processing job.

## Database Service

The `database.py` module provides database connection and update functions for the job.

### Key Features

- **Connection Pooling**: Efficient connection management with psycopg2 ThreadedConnectionPool
- **Dual Mode Support**: Works in both local development (TCP/IP) and Cloud Run (Unix socket)
- **Schema Compatibility**: Writes to the same `choreography_tasks` table as the original app
- **Error Handling**: Comprehensive error handling with logging
- **Context Manager**: Safe cursor management with automatic cleanup

### Usage

#### Test Database Connection

```python
from services.database import test_connection

if test_connection():
    print("Database connection successful")
else:
    print("Database connection failed")
```

#### Update Task Status

```python
from services.database import update_task_status

# Update task to running
success = update_task_status(
    task_id='abc-123-def-456',
    status='running',
    progress=50,
    stage='processing',
    message='Processing video...'
)

# Update task to completed with result
success = update_task_status(
    task_id='abc-123-def-456',
    status='completed',
    progress=100,
    stage='completed',
    message='Choreography generated successfully!',
    result={
        'video_url': 'gs://bucket/choreographies/2024/11/video.mp4',
        'duration': 180.5,
        'moves_count': 12
    }
)

# Update task to failed with error
success = update_task_status(
    task_id='abc-123-def-456',
    status='failed',
    progress=0,
    stage='failed',
    message='Video processing failed',
    error='FFmpeg error: Invalid codec'
)
```

#### Get Task Status

```python
from services.database import get_task_status

task_data = get_task_status('abc-123-def-456')
if task_data:
    print(f"Status: {task_data['status']}")
    print(f"Progress: {task_data['progress']}%")
    print(f"Message: {task_data['message']}")
```

#### Close Connection Pool

```python
from services.database import close_connection_pool

# Call when job is shutting down
close_connection_pool()
```

### Status Values

The job MUST use these exact status values to match the original app:

- `'started'` - Task has been created and queued
- `'running'` - Task is currently being processed
- `'completed'` - Task completed successfully
- `'failed'` - Task failed with an error

### Environment Variables

The database service requires these environment variables:

**Local Development (TCP/IP):**
- `DB_HOST` - Database host (e.g., 'db' for Docker Compose)
- `DB_PORT` - Database port (default: 5432)
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password

**Cloud Run Production (Unix Socket):**
- `K_SERVICE` - Set by Cloud Run (indicates Cloud Run environment)
- `CLOUD_SQL_CONNECTION_NAME` - Cloud SQL connection name (e.g., 'project:region:instance')
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password

### Database Schema

The job writes to the `choreography_tasks` table with this schema:

```sql
CREATE TABLE choreography_tasks (
    task_id VARCHAR(36) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'started',
    progress INTEGER NOT NULL DEFAULT 0,
    stage VARCHAR(50) NOT NULL DEFAULT 'initializing',
    message TEXT NOT NULL DEFAULT 'Starting choreography generation...',
    result JSONB,
    error TEXT,
    job_execution_name VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### Testing

Run the test script to verify database connection:

```bash
# Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=bachata_buddy
export DB_USER=postgres
export DB_PASSWORD=postgres

# Run tests
uv run python test_database_connection.py

# Test with a specific task (optional)
export TEST_TASK_ID=abc-123-def-456
uv run python test_database_connection.py
```

### Error Handling

The database service handles these error scenarios:

1. **Connection Failures**: Logs error and raises exception
2. **Invalid Status**: Raises `ValueError` for invalid status values
3. **Invalid Progress**: Raises `ValueError` for progress outside 0-100 range
4. **Task Not Found**: Returns `False` (does not raise exception)
5. **Database Errors**: Logs error and returns `False`

### Logging

The database service logs all operations with structured logging:

- **INFO**: Successful operations (connection, updates, queries)
- **WARNING**: Non-critical issues (task not found)
- **ERROR**: Database errors, connection failures
- **DEBUG**: Detailed operation information

### Connection Pooling

The service uses a connection pool with these settings:

- **Min Connections**: 1
- **Max Connections**: 5
- **Connection Timeout**: 10 seconds
- **Thread-Safe**: Yes (ThreadedConnectionPool)

Connections are automatically managed:
- Acquired from pool when needed
- Returned to pool after use
- Closed when pool is shut down

### Best Practices

1. **Always close the pool**: Call `close_connection_pool()` when job completes
2. **Use context manager**: Use `get_db_cursor()` for automatic cleanup
3. **Validate inputs**: Status and progress values are validated automatically
4. **Handle failures**: Check return values from `update_task_status()`
5. **Log operations**: All operations are logged automatically

## Service Architecture

The job services are organized into specialized modules:

### 1. Database Service (`database.py`) ✅ IMPLEMENTED

Handles database operations for task status updates.

**Status**: Fully implemented with connection pooling and error handling.

### 2. Video Generator Service (`video_generator.py`) 📝 SKELETON

Generates choreography videos by combining training video clips.

**Key Features** (to be implemented):
- Process video files with FFmpeg
- Combine multiple video clips into sequences
- Apply transitions and effects
- Generate final output videos

**Status**: Skeleton created, implementation pending in task 2.3.

### 3. Music Analyzer Service (`music_analyzer.py`) 📝 SKELETON

Analyzes music to extract features for choreography generation.

**Key Features** (to be implemented):
- Analyze audio features (tempo, energy, structure)
- Detect beats and musical sections
- Extract rhythm patterns using Librosa
- Provide music metadata for move matching

**Status**: Skeleton created, implementation pending in task 2.3.

### 4. Pose Detector Service (`pose_detector.py`) 📝 SKELETON

Detects and analyzes human poses in dance videos.

**Key Features** (to be implemented):
- Detect poses using YOLOv8
- Extract pose keypoints and features
- Analyze dance movements
- Generate pose embeddings for similarity matching

**Status**: Skeleton created, implementation pending in task 2.3.

### 5. Elasticsearch Service (`elasticsearch_service.py`) 📝 SKELETON

Handles Elasticsearch queries for dance move matching.

**Key Features** (to be implemented):
- Query Elasticsearch for matching moves
- Search by music features (tempo, energy, style)
- Retrieve move metadata and video references
- Perform similarity searches using embeddings

**Status**: Skeleton created, implementation pending in task 2.3.

### 6. Storage Service (`storage_service.py`) ✅ IMPLEMENTED

Handles file storage operations for both local and cloud environments.

**Key Features**:
- Upload/download files from Google Cloud Storage
- Generate signed URLs for file access
- Support local filesystem for development
- Automatic retry logic with exponential backoff
- Progress tracking for large files

**Status**: Fully implemented with comprehensive test coverage (13/13 tests passing).

See [STORAGE_SERVICE_IMPLEMENTATION.md](../../STORAGE_SERVICE_IMPLEMENTATION.md) for detailed documentation.

## Service Integration

These services will be integrated in the choreography pipeline (task 2.4):

```python
from services import (
    MusicAnalyzer,
    ElasticsearchService,
    VideoGenerator,
    PoseDetector,
    StorageService,
    update_task_status
)

# Pipeline flow:
# 1. Download audio (StorageService)
# 2. Analyze music (MusicAnalyzer)
# 3. Query matching moves (ElasticsearchService)
# 4. Download training videos (StorageService)
# 5. Detect poses (PoseDetector)
# 6. Generate choreography video (VideoGenerator)
# 7. Upload result (StorageService)
# 8. Update task status (database)
```

## Implementation Status

| Service | Status | Task | Tests |
|---------|--------|------|-------|
| database.py | ✅ Complete | 2.2 | ✅ Passing |
| elasticsearch_service.py | ✅ Complete | 2.3 | ✅ Passing |
| music_analyzer.py | ✅ Complete | 2.3 | ✅ Passing |
| pose_detector.py | ✅ Complete | 2.3 | ✅ Passing |
| video_generator.py | ✅ Complete | 2.3 | ✅ Passing |
| storage_service.py | ✅ Complete | 2.3 | ✅ Passing (13/13) |
