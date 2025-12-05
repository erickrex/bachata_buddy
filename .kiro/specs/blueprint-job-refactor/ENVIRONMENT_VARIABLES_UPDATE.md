# Environment Variables Update Summary

## Overview

This document summarizes the environment variable changes made as part of the blueprint-based architecture refactor (Task 15).

## Changes Made

### 1. Removed Elasticsearch Variables

The following Elasticsearch-related variables have been removed from all environment files:

**Root `.env.example`:**
- `ELASTICSEARCH_URL`
- `ELASTICSEARCH_HOST`
- `ELASTICSEARCH_API_KEY`
- `ELASTICSEARCH_INDEX`

**Backend `.env.example`:**
- `ELASTICSEARCH_URL`
- `ELASTICSEARCH_HOST`
- `ELASTICSEARCH_API_KEY`
- `ELASTICSEARCH_INDEX`

**Job `.env.example`:**
- `ELASTICSEARCH_HOST`
- `ELASTICSEARCH_PORT`
- `ELASTICSEARCH_API_KEY`
- `ELASTICSEARCH_INDEX`

### 2. Added Vector Search Variables (Backend/API)

New variables for FAISS-based vector search in the backend:

| Variable | Default | Description |
|----------|---------|-------------|
| `MOVE_EMBEDDINGS_CACHE_TTL` | 3600 | Cache TTL for FAISS index in seconds (1 hour) |
| `VECTOR_SEARCH_TOP_K` | 50 | Number of top similar moves to return |
| `FAISS_USE_GPU` | false | Enable GPU acceleration (requires FAISS-GPU) |
| `FAISS_NPROBE` | 10 | Number of cells to visit for IVF indices (higher = more accurate but slower) |

**Added to:**
- `bachata_buddy/.env.example`
- `bachata_buddy/backend/.env.example`
- `bachata_buddy/docker-compose.yml` (api service)

### 3. Added Blueprint Variable (Job Container)

New variable for blueprint-based video assembly:

| Variable | Description |
|----------|-------------|
| `BLUEPRINT_JSON` | Blueprint JSON containing all choreography parameters and move selections |

**Blueprint Structure:**
```json
{
  "task_id": "uuid-string",
  "song": {
    "audio_path": "/app/data/songs/test.mp3",
    "duration": 180.5,
    "bpm": 120,
    "key": "C major"
  },
  "moves_used": [
    {
      "move_id": "basic_step_001",
      "move_name": "Basic Step",
      "video_path": "/app/data/moves/basic_step.mp4",
      "start_time": 0.0,
      "duration": 8.0,
      "transition": "crossfade"
    }
  ],
  "video_output": {
    "path": "/app/output/choreography.mp4",
    "format": "mp4",
    "resolution": "1920x1080"
  }
}
```

**Added to:**
- `bachata_buddy/job/.env.example`
- `bachata_buddy/docker-compose.yml` (job service)

### 4. Removed Job Container Variables

The following variables are no longer needed in the job container (intelligence moved to backend):

**Removed from `job/.env.example` and `docker-compose.yml`:**
- `AUDIO_INPUT` - Now in blueprint
- `DIFFICULTY` - Now in blueprint
- `ENERGY_LEVEL` - Now in blueprint
- `STYLE` - Now in blueprint
- `GOOGLE_API_KEY` - No longer needed (AI in backend)
- `YOLOV8_MODEL` - No longer needed (no pose detection)
- `YOLOV8_CONFIDENCE` - No longer needed
- `YOLOV8_DEVICE` - No longer needed
- `YOLOV8_IOU_THRESHOLD` - No longer needed
- `YOLOV8_MAX_DET` - No longer needed

**Kept in job container:**
- `TASK_ID` - Task identifier
- `USER_ID` - User identifier
- `BLUEPRINT_JSON` - All choreography data
- `DB_*` - Database connection
- `GCP_*` - Cloud configuration
- `GCS_BUCKET_NAME` - Storage configuration
- `VIDEO_*` - FFmpeg configuration
- `AUDIO_*` - FFmpeg configuration
- `LOG_LEVEL` - Logging configuration

## Docker Compose Changes

### API Service

Added vector search environment variables:
```yaml
environment:
  # ... existing vars ...
  # Vector Search Configuration
  - MOVE_EMBEDDINGS_CACHE_TTL=${MOVE_EMBEDDINGS_CACHE_TTL:-3600}
  - VECTOR_SEARCH_TOP_K=${VECTOR_SEARCH_TOP_K:-50}
  - FAISS_USE_GPU=${FAISS_USE_GPU:-false}
  - FAISS_NPROBE=${FAISS_NPROBE:-10}
```

### Job Service

Simplified to blueprint-based approach:
```yaml
environment:
  # Task information
  - TASK_ID=${TASK_ID:-test-task-id}
  - USER_ID=${USER_ID:-1}
  
  # Blueprint JSON (contains all choreography parameters)
  - BLUEPRINT_JSON=${BLUEPRINT_JSON:-}
  
  # Database, Cloud, FFmpeg configs remain
  # Removed: AUDIO_INPUT, DIFFICULTY, ENERGY_LEVEL, STYLE, YOLOV8_*, GOOGLE_API_KEY
```

## Documentation Updates

### Updated Files

1. **`bachata_buddy/.env.example`**
   - Removed Elasticsearch section
   - Added Vector Search Configuration section
   - Updated job configuration to use BLUEPRINT_JSON

2. **`bachata_buddy/backend/.env.example`**
   - Removed Elasticsearch section
   - Added Vector Search Configuration section

3. **`bachata_buddy/job/.env.example`**
   - Removed Elasticsearch section
   - Removed individual choreography parameters
   - Added Blueprint Configuration section with example structure

4. **`bachata_buddy/docker-compose.yml`**
   - Updated api service with vector search vars
   - Simplified job service to blueprint-based approach

5. **`bachata_buddy/job/README.md`**
   - Updated overview to describe blueprint-based architecture
   - Removed Elasticsearch configuration section
   - Removed individual choreography parameter sections
   - Added Blueprint Configuration section
   - Removed YOLOV8 and GOOGLE_API_KEY documentation

6. **`bachata_buddy/backend/README.md`**
   - Added Vector Search Configuration section
   - Documented new environment variables

## Migration Guide

### For Local Development

1. **Update your `.env` file:**
   ```bash
   # Remove old Elasticsearch variables
   # Add new vector search variables (optional, defaults provided)
   MOVE_EMBEDDINGS_CACHE_TTL=3600
   VECTOR_SEARCH_TOP_K=50
   FAISS_USE_GPU=false
   FAISS_NPROBE=10
   ```

2. **Restart services:**
   ```bash
   docker-compose down
   docker-compose --profile microservices up -d
   ```

### For Production (Cloud Run)

1. **Backend API - Add new environment variables:**
   ```bash
   gcloud run services update bachata-api \
     --set-env-vars MOVE_EMBEDDINGS_CACHE_TTL=3600 \
     --set-env-vars VECTOR_SEARCH_TOP_K=50 \
     --set-env-vars FAISS_USE_GPU=false \
     --set-env-vars FAISS_NPROBE=10
   ```

2. **Job Container - Remove old variables, add BLUEPRINT_JSON:**
   ```bash
   # BLUEPRINT_JSON is passed dynamically by the API
   # Remove these from Cloud Run Job template:
   # - ELASTICSEARCH_HOST
   # - ELASTICSEARCH_PORT
   # - ELASTICSEARCH_API_KEY
   # - ELASTICSEARCH_INDEX
   # - AUDIO_INPUT
   # - DIFFICULTY
   # - ENERGY_LEVEL
   # - STYLE
   # - GOOGLE_API_KEY
   # - YOLOV8_*
   ```

3. **Update Cloud Run Job template:**
   ```bash
   gcloud run jobs update video-processor \
     --clear-env-vars ELASTICSEARCH_HOST,ELASTICSEARCH_PORT,ELASTICSEARCH_API_KEY,ELASTICSEARCH_INDEX,AUDIO_INPUT,DIFFICULTY,ENERGY_LEVEL,STYLE,GOOGLE_API_KEY
   ```

## Testing

### Verify Vector Search Configuration

```bash
# Check API has vector search variables
docker-compose exec api env | grep -E "(MOVE_EMBEDDINGS|VECTOR_SEARCH|FAISS)"

# Expected output:
# MOVE_EMBEDDINGS_CACHE_TTL=3600
# VECTOR_SEARCH_TOP_K=50
# FAISS_USE_GPU=false
# FAISS_NPROBE=10
```

### Verify Job Container Configuration

```bash
# Check job has blueprint variable
docker-compose --profile job run --rm job env | grep BLUEPRINT_JSON

# Check old variables are removed
docker-compose --profile job run --rm job env | grep -E "(ELASTICSEARCH|AUDIO_INPUT|DIFFICULTY|YOLOV8)"
# Should return nothing
```

## Rollback Plan

If issues arise, you can temporarily revert by:

1. **Restore Elasticsearch variables** in `.env` files
2. **Restore old job variables** (AUDIO_INPUT, DIFFICULTY, etc.)
3. **Remove new variables** (MOVE_EMBEDDINGS_CACHE_TTL, etc.)
4. **Restart services**

Keep old environment file backups:
```bash
cp .env .env.backup
cp backend/.env.example backend/.env.example.backup
cp job/.env.example job/.env.example.backup
```

## Related Tasks

- Task 1: Backend vector search service (uses these variables)
- Task 2: Backend blueprint generator (uses these variables)
- Task 6: Job container main.py (uses BLUEPRINT_JSON)
- Task 14: Jobs service update (passes BLUEPRINT_JSON)

## References

- Requirements: 1.2 (Blueprint-based architecture)
- Design: Blueprint schema specification
- Tasks: Task 15 (this document)
