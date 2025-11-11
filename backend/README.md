# Django REST API Backend

This directory contains the Django REST Framework API for the Bachata Buddy microservices architecture.

## Overview

The API service handles:
- JWT authentication
- User management
- Choreography task management
- Cloud Run Jobs creation
- Collections CRUD operations
- Elasticsearch integration for move search

## Development Setup

### ⚠️ IMPORTANT: Always Use UV for Python Operations

This backend project uses **UV** as the package manager for all Python operations. UV is a fast Python package installer and resolver that replaces pip.

**Key Commands:**
- `uv sync` - Install all dependencies from pyproject.toml
- `uv add <package>` - Add a new dependency
- `uv run python <script>` - Run Python scripts
- `uv run python manage.py <command>` - Run Django management commands

**DO NOT USE:**
- ❌ `pip install` - Use `uv add` or `uv sync` instead
- ❌ `python manage.py` - Use `uv run python manage.py` instead
- ❌ Direct `python` commands - Use `uv run python` instead

### Using Docker Compose (Recommended)

**Quick Start:**

```bash
# From the bachata_buddy directory

# 1. Start the API (includes database and Elasticsearch)
docker-compose --profile microservices up -d

# 2. Run migrations
docker-compose exec api uv run python manage.py migrate

# 3. Create superuser (optional)
docker-compose exec api uv run python manage.py createsuperuser

# 4. Access the API
# API: http://localhost:8001
# Swagger UI: http://localhost:8001/api/docs/
# OpenAPI Schema: http://localhost:8001/api/schema/
```

**Common Commands:**

```bash
# View logs
docker-compose logs -f api

# Stop services
docker-compose --profile microservices down

# Restart API
docker-compose restart api

# Run tests
docker-compose exec api uv run pytest
```

**Note:** The API runs on port **8001** (not 8000) to avoid conflicts with the legacy monolithic app.

### Native Development

```bash
# Install UV (if not already installed)
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or with Homebrew:
brew install uv

# Navigate to backend directory
cd backend

# Install dependencies using UV
uv sync

# Set environment variables
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bachata_vibes
export ELASTICSEARCH_URL=http://localhost:9200
export DJANGO_SECRET_KEY=local-dev-secret-key
export DEBUG=True

# Run migrations using UV
uv run python manage.py migrate

# Start development server using UV
uv run python manage.py runserver
```

### Adding New Dependencies

**ALWAYS use UV to add dependencies:**

```bash
# Add a new dependency
cd backend
uv add django-cors-headers

# Add a development dependency
uv add --dev pytest-django

# Install all dependencies after pulling changes
uv sync
```

This will automatically update `backend/pyproject.toml` and install the package.

## Docker Images

### Dockerfile (Production - CPU)

The standard `Dockerfile` is optimized for Cloud Run deployment:

- **Multi-stage build**: Separate build and runtime stages for smaller image size
- **Python 3.12**: Latest stable Python version
- **Gunicorn**: Production WSGI server with 1 worker, 8 threads
- **Health checks**: Built-in health check endpoint
- **Size**: ~500MB

### Dockerfile.gpu (Production - GPU)

The `Dockerfile.gpu` is optimized for GPU-accelerated Cloud Run deployment:

- **NVIDIA CUDA 12.2**: Base image with CUDA runtime
- **FAISS GPU**: GPU-accelerated vector similarity search
- **PyTorch with CUDA**: GPU-accelerated audio processing
- **Multi-stage build**: Optimized for smaller image size
- **Size**: ~3GB (includes CUDA libraries)

**Build GPU image:**
```bash
# Set your project ID
export GCP_PROJECT_ID=your-project-id

# Build and push
./build_gpu_image.sh
```

**Deploy to Cloud Run with GPU:**
```bash
gcloud run deploy bachata-api \
  --image gcr.io/PROJECT_ID/bachata-api-gpu:latest \
  --region europe-west1 \
  --platform managed \
  --memory 16Gi \
  --cpu 4 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --set-env-vars USE_GPU=true,FAISS_USE_GPU=true,AUDIO_USE_GPU=true
```

### Dockerfile.dev (Development)

The `Dockerfile.dev` is optimized for local development:

- **Lightweight**: Only includes dependencies needed for the API (no FFmpeg, YOLOv8, etc.)
- **Hot-reload**: Code changes are reflected immediately via volume mounts
- **Fast builds**: Uses UV for dependency management
- **Port 8000**: Standard Django development port

### Image Comparison

| Feature | Dockerfile | Dockerfile.gpu | Dockerfile.dev |
|---------|-----------|---------------|----------------|
| Base Image | python:3.12-slim | nvidia/cuda:12.2.0 | python:3.12-slim |
| GPU Support | ❌ | ✅ CUDA 12.2 | ❌ |
| FAISS | CPU | GPU | CPU |
| PyTorch | ❌ | ✅ with CUDA | ❌ |
| Size | ~500MB | ~3GB | ~500MB |
| Purpose | Production (CPU) | Production (GPU) | Development |

## Database Connection

The API automatically detects the environment and configures the database connection:

### Local Development (TCP/IP)
```bash
DB_NAME=bachata_buddy
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db              # For Docker Compose
# DB_HOST=localhost     # For native development
DB_PORT=5432
```

### Cloud Run Production (Unix Socket)
```bash
CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME
DB_NAME=bachata_buddy
DB_USER=postgres
DB_PASSWORD=your-secure-password  # From Secret Manager
```

The connection automatically switches based on the `K_SERVICE` environment variable (set by Cloud Run).

**Verify Connection:**
```bash
# Local development
uv run --directory backend python verify_cloud_sql_connection.py

# Cloud Run (via logs)
gcloud run logs read bachata-api --limit=50
```

See [CLOUD_SQL_SETUP.md](./CLOUD_SQL_SETUP.md) for detailed configuration instructions.

## Environment Variables

### Quick Setup

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Update the Google API key:**
   ```bash
   # Edit .env and replace:
   GOOGLE_API_KEY=your-actual-gemini-api-key-here
   ```

3. **Verify configuration:**
   ```bash
   uv run python test_env.py
   ```

### Required Variables

The following environment variables are required for local development:

```bash
# Django Configuration
DJANGO_SECRET_KEY=local-dev-secret-key-change-in-production
DEBUG=True
DJANGO_SETTINGS_MODULE=api.settings
ENVIRONMENT=local

# Database (PostgreSQL)
DB_NAME=bachata_vibes
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db              # For Docker Compose
DB_PORT=5432

# Vector Search Configuration
MOVE_EMBEDDINGS_CACHE_TTL=3600    # Cache TTL in seconds (1 hour)
VECTOR_SEARCH_TOP_K=50            # Number of similar moves to return
FAISS_USE_GPU=false               # Enable GPU acceleration (requires FAISS-GPU)
FAISS_NPROBE=10                   # Search accuracy for IVF indices

# GPU Acceleration Configuration (Optional)
USE_GPU=false                     # Global GPU enable/disable flag
FFMPEG_USE_NVENC=false           # FFmpeg NVENC for video encoding (job container)
AUDIO_USE_GPU=false              # Audio GPU processing with torchaudio
GPU_MEMORY_FRACTION=0.8          # GPU memory allocation (0.0-1.0)
GPU_FALLBACK_ENABLED=true        # Enable CPU fallback on GPU errors
GPU_TIMEOUT_SECONDS=30           # GPU operation timeout
GPU_RETRY_COUNT=3                # Retry count for transient GPU errors

# Google Cloud
GCP_PROJECT_ID=local-dev
GCP_REGION=us-central1
CLOUD_RUN_JOB_NAME=video-processor
GOOGLE_API_KEY=your-gemini-api-key-here

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=7

# Logging
LOG_LEVEL=DEBUG
DJANGO_LOG_LEVEL=INFO
```

### Environment Files

- **`.env.example`** - Template with all available variables and documentation
- **`.env`** - Your local configuration (not committed to git)
- **`.env.local`** - Alternative template with working defaults

### Detailed Documentation

For comprehensive environment variable documentation, including:
- Complete variable reference
- Production setup (Cloud Run)
- Security best practices
- Troubleshooting

See [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md)

### CORS Configuration

The API is configured to accept requests from the React frontend. CORS settings are automatically configured based on the environment:

**Local Development:**
- Allows requests from `http://localhost:5173` (Vite default)
- Allows requests from `http://localhost:3000` (Create React App default)
- Allows credentials (cookies, authorization headers)

**Production (Cloud Run):**
- Set `CORS_ALLOWED_ORIGINS` environment variable with your frontend URL
- Example: `CORS_ALLOWED_ORIGINS=https://your-frontend.run.app`
- Multiple origins can be comma-separated

**Allowed Headers:**
- `Authorization` (for JWT tokens)
- `Content-Type`
- `Accept`
- `X-CSRFToken`
- Standard CORS headers

**Configuration Location:** `backend/api/settings.py`

## GPU Acceleration (Optional)

The backend supports GPU acceleration for improved performance when running on NVIDIA GPUs (e.g., L4 on Cloud Run).

### GPU Features

1. **FAISS GPU** - Vector similarity search acceleration (10-50x speedup)
2. **FFmpeg NVENC** - Video encoding acceleration (6-8x speedup, job container only)
3. **Audio GPU** - Audio processing with torchaudio (3-5x speedup)

### Requirements

- NVIDIA GPU with CUDA support (e.g., L4, T4, A100)
- CUDA 12.2 or later
- GPU-enabled Docker image (see `Dockerfile.gpu`)
- Cloud Run with GPU support (europe-west1 or europe-west4)

### Configuration

GPU acceleration is controlled via environment variables:

```bash
# Enable GPU globally
USE_GPU=true

# Per-service GPU flags (override USE_GPU)
FAISS_USE_GPU=true          # Vector search GPU
FFMPEG_USE_NVENC=true       # Video encoding GPU (job container)
AUDIO_USE_GPU=true          # Audio processing GPU

# GPU settings
GPU_MEMORY_FRACTION=0.8     # GPU memory allocation (80%)
GPU_FALLBACK_ENABLED=true   # Auto-fallback to CPU on errors
GPU_TIMEOUT_SECONDS=30      # Operation timeout
```

### GPU Detection

The backend automatically detects GPU availability at runtime:

```python
from services.gpu_utils import get_gpu_info

# Get GPU information
gpu_info = get_gpu_info()
print(gpu_info)
# {
#   'cuda_available': True,
#   'faiss_gpu_available': True,
#   'nvenc_available': True,
#   'device_name': 'NVIDIA L4',
#   ...
# }
```

### Graceful Fallback

If GPU is unavailable or encounters errors, the backend automatically falls back to CPU:

- FAISS GPU → FAISS CPU
- FFmpeg NVENC → FFmpeg libx264
- torchaudio GPU → librosa CPU

This ensures the application works in all environments without code changes.

### Local Development

GPU features are disabled by default for local development. To test GPU features locally:

1. Ensure you have an NVIDIA GPU with CUDA installed
2. Install GPU-enabled packages: `uv add faiss-gpu torch torchaudio`
3. Set `USE_GPU=true` in your `.env` file
4. Restart the API server

### Cloud Run Deployment

To deploy with GPU support:

```bash
gcloud run deploy bachata-api \
  --image gcr.io/PROJECT_ID/bachata-api:gpu \
  --region europe-west1 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --memory 16Gi \
  --cpu 4 \
  --set-env-vars USE_GPU=true,FAISS_USE_GPU=true,AUDIO_USE_GPU=true
```

See the GPU acceleration spec for detailed implementation guide.

## API Endpoints

See the OpenAPI documentation at `/api/docs` when the server is running.

Key endpoints:
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - Login (returns JWT tokens)
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user profile
- `POST /api/choreography/generate` - Start choreography generation
- `GET /api/choreography/tasks/{id}` - Get task status
- `GET /api/collections` - List saved choreographies

## Local Development with Sample Songs

### Setting Up Sample Songs

The song template workflow requires sample audio files for local development:

**1. Sample Song Fixtures:**

```bash
# Load sample song metadata into database
docker-compose exec api uv run python manage.py loaddata songs

# Native development
cd backend
uv run python manage.py loaddata songs
```

This loads sample songs from `backend/fixtures/songs.json` with metadata like:
- Title, artist, duration, BPM, genre
- Local file paths (e.g., `songs/bachata-rosa.mp3`)

**2. Adding Audio Files:**

Place MP3 files in `backend/data/songs/` directory:

```bash
# Create directory if it doesn't exist
mkdir -p backend/data/songs

# Add your MP3 files
cp ~/Music/bachata-rosa.mp3 backend/data/songs/
cp ~/Music/obsesion.mp3 backend/data/songs/
```

**3. Verify Setup:**

```bash
# List songs via API
curl http://localhost:8001/api/choreography/songs/ \
  -H "Authorization: Bearer $TOKEN"

# Check audio file exists
ls -lh backend/data/songs/
```

See `backend/data/songs/README.md` for detailed instructions on adding sample audio files.

### Local vs GCS Storage

The API supports dual storage modes for flexibility:

**Local Storage (Development):**
- Audio files stored in: `backend/data/songs/`
- Database paths: `songs/filename.mp3` (relative paths)
- No cloud dependencies required
- Fast iteration and testing

**GCS Storage (Production):**
- Audio files stored in: `gs://bachata-buddy-bucket/songs/`
- Database paths: `gs://bucket/songs/filename.mp3` (GCS URIs)
- Automatic detection based on environment
- Scalable and reliable

**Environment Detection:**

The system automatically detects storage mode:

```python
# In Cloud Run (production)
K_SERVICE=bachata-api  # Set by Cloud Run
→ Uses GCS storage

# In local development
K_SERVICE not set
→ Uses local file system
```

**Migration to Production:**

When ready to deploy, upload songs to GCS:

```bash
# Upload all local songs to GCS
gsutil -m cp -r backend/data/songs/* gs://bachata-buddy-bucket/songs/

# Update database paths (if needed)
# The API handles both local and GCS paths automatically
```

**Storage Configuration:**

```bash
# .env for local development
USE_LOCAL_STORAGE=True
SONGS_DIRECTORY=backend/data/songs

# Cloud Run environment variables
GCS_BUCKET=bachata-buddy-bucket
GCS_SONGS_PREFIX=songs/
```

## Testing

### Unit Tests

```bash
# Run tests (using UV)
docker-compose exec api uv run pytest

# Run with coverage (using UV)
docker-compose exec api uv run pytest --cov=apps --cov-report=html

# Native development
cd backend
uv run pytest
```

### Local Job Testing

For testing the choreography generation flow locally without Cloud Run infrastructure:

```bash
# Run the mock job service test (using UV)
docker-compose exec api uv run python test_mock_job_service.py

# Native development
cd backend
uv run python test_mock_job_service.py
```

**Documentation:**
- **[JOB_TESTING_DOCS_INDEX.md](./JOB_TESTING_DOCS_INDEX.md)** - Documentation index (START HERE)
- **[LOCAL_JOB_TESTING_WORKFLOW.md](./LOCAL_JOB_TESTING_WORKFLOW.md)** - Step-by-step workflow guide
- **[LOCAL_JOB_TESTING.md](./LOCAL_JOB_TESTING.md)** - Detailed technical documentation
- **[MOCK_JOB_QUICK_REFERENCE.md](./MOCK_JOB_QUICK_REFERENCE.md)** - Quick command reference
- **[TASK_STATUS_UPDATER_GUIDE.md](./TASK_STATUS_UPDATER_GUIDE.md)** - Task status updater API

## Production Deployment

For production deployment to Cloud Run, use the production Dockerfile (not Dockerfile.dev):

```bash
# Build production image
docker build -t gcr.io/PROJECT_ID/bachata-api:latest .

# Push to Container Registry
docker push gcr.io/PROJECT_ID/bachata-api:latest

# Deploy to Cloud Run
gcloud run deploy bachata-api \
  --image gcr.io/PROJECT_ID/bachata-api:latest \
  --region us-central1 \
  --platform managed
```

## Architecture

This API service is part of a microservices architecture:

```
React Frontend (Cloud Run)
    ↓
Django REST API (Cloud Run) ← You are here
    ↓
Cloud Run Job (Video Processing)
    ↓
Shared Services (Cloud SQL, Elasticsearch, GCS)
```

See the main [design document](../.kiro/specs/microservices-migration/design.md) for more details.


---

## API Documentation

### Complete Endpoint Reference

The API provides 35 endpoints organized into 4 main categories. All endpoints except registration and login require JWT authentication.

#### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register/` | Register new user | No |
| POST | `/api/auth/login/` | Login and get JWT tokens | No |
| POST | `/api/auth/refresh/` | Refresh access token | No |
| GET | `/api/auth/profile/` | Get user profile | Yes |
| PUT | `/api/auth/profile/` | Update user profile | Yes |
| GET | `/api/auth/preferences/` | Get user preferences | Yes |
| PUT | `/api/auth/preferences/` | Update user preferences | Yes |

**User Preferences:**
- `auto_save_choreographies` (boolean) - Auto-save completed choreographies
- `default_difficulty` (string) - Default difficulty level (beginner/intermediate/advanced)
- `email_notifications` (boolean) - Enable email notifications

#### Choreography Generation Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/choreography/songs/` | List available song templates | Yes |
| GET | `/api/choreography/songs/{id}/` | Get song details | Yes |
| POST | `/api/choreography/generate-from-song/` | Generate from song template | Yes |
| GET | `/api/choreography/tasks/` | List user's tasks | Yes |
| GET | `/api/choreography/tasks/{id}/` | Get task status | Yes |
| POST | `/api/choreography/tasks/{id}/cancel/` | Cancel running task | Yes |
| POST | `/api/choreography/parse-query/` | Parse natural language query | Yes |
| POST | `/api/choreography/generate-with-ai/` | Generate with AI explanations | Yes |

**Song Template Workflow:**
1. List songs with filtering (genre, BPM range, search)
2. Select a song and view details
3. Generate choreography with chosen difficulty

**Natural Language AI Workflow:**
- "Create a romantic beginner choreography with slow tempo"
- "Generate an energetic advanced dance"
- "Make a sensual intermediate routine"

#### Collections Management Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/collections/` | List saved choreographies | Yes |
| GET | `/api/collections/{id}/` | Get choreography detail | Yes |
| PUT | `/api/collections/{id}/` | Update choreography | Yes |
| DELETE | `/api/collections/{id}/` | Delete choreography | Yes |
| POST | `/api/collections/save/` | Save from completed task | Yes |
| GET | `/api/collections/stats/` | Get collection statistics | Yes |
| POST | `/api/collections/delete-all/` | Bulk delete all | Yes |
| POST | `/api/collections/cleanup/` | Remove orphaned records | Yes |

**Filtering & Search:**
- `?difficulty=beginner` - Filter by difficulty
- `?search=romantic` - Search in title
- `?ordering=-created_at` - Sort by date (descending)
- `?page=1&page_size=20` - Pagination

#### Instructor Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/instructors/class-plans/` | List class plans | Yes (Instructor) |
| POST | `/api/instructors/class-plans/` | Create class plan | Yes (Instructor) |
| GET | `/api/instructors/class-plans/{id}/` | Get class plan detail | Yes (Instructor) |
| PUT | `/api/instructors/class-plans/{id}/` | Update class plan | Yes (Instructor) |
| DELETE | `/api/instructors/class-plans/{id}/` | Delete class plan | Yes (Instructor) |
| POST | `/api/instructors/class-plans/{id}/add-sequence/` | Add choreography sequence | Yes (Instructor) |
| DELETE | `/api/instructors/class-plans/{id}/sequences/{seq_id}/` | Delete sequence | Yes (Instructor) |
| PUT | `/api/instructors/class-plans/{id}/sequences/{seq_id}/` | Update sequence | Yes (Instructor) |
| POST | `/api/instructors/class-plans/{id}/reorder-sequences/` | Reorder sequences | Yes (Instructor) |
| POST | `/api/instructors/class-plans/{id}/duplicate/` | Duplicate class plan | Yes (Instructor) |
| GET | `/api/instructors/class-plans/{id}/summary/` | Get class plan summary | Yes (Instructor) |
| GET | `/api/instructors/class-plans/{id}/export/` | Export as HTML | Yes (Instructor) |
| GET | `/api/instructors/stats/` | Get instructor statistics | Yes (Instructor) |

### Interactive API Documentation

**Swagger UI:** http://localhost:8001/api/docs/

Features:
- Try out endpoints directly from your browser
- See request/response examples
- View authentication requirements
- Test with your JWT token

**OpenAPI Schema:** http://localhost:8001/api/schema/

Download the schema for:
- Postman/Insomnia import
- Code generation (TypeScript, Python, etc.)
- API testing tools

**Note:** The API runs on port **8001** in Docker Compose to avoid conflicts with the legacy monolithic app.

### Usage Examples

#### 1. Authentication Flow

```bash
# Register
curl -X POST http://localhost:8001/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "dancer123",
    "email": "dancer@example.com",
    "password": "SecurePass123!"
  }'

# Login
curl -X POST http://localhost:8001/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "dancer123",
    "password": "SecurePass123!"
  }'

# Response:
# {
#   "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "user": {
#     "id": 1,
#     "username": "dancer123",
#     "email": "dancer@example.com"
#   }
# }

# Use token in subsequent requests
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."
```

#### 2. Song Template Workflow (Recommended)

The primary workflow for generating choreography uses pre-existing song templates.

```bash
# Step 1: List available songs
curl -X GET "http://localhost:8001/api/choreography/songs/?genre=bachata&bpm_min=110&bpm_max=130" \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "count": 5,
#   "next": null,
#   "previous": null,
#   "results": [
#     {
#       "id": 1,
#       "title": "Bachata Rosa",
#       "artist": "Juan Luis Guerra",
#       "duration": 245.5,
#       "bpm": 120,
#       "genre": "bachata",
#       "created_at": "2025-11-08T10:00:00Z"
#     }
#   ]
# }

# Step 2: Get song details
curl -X GET http://localhost:8001/api/choreography/songs/1/ \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "id": 1,
#   "title": "Bachata Rosa",
#   "artist": "Juan Luis Guerra",
#   "duration": 245.5,
#   "bpm": 120,
#   "genre": "bachata",
#   "audio_path": "songs/bachata-rosa.mp3",
#   "created_at": "2025-11-08T10:00:00Z",
#   "updated_at": "2025-11-08T10:00:00Z"
# }

# Step 3: Generate choreography from song
curl -X POST http://localhost:8001/api/choreography/generate-from-song/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "song_id": 1,
    "difficulty": "intermediate",
    "energy_level": "medium",
    "style": "romantic"
  }'

# Response:
# {
#   "task_id": "550e8400-e29b-41d4-a716-446655440000",
#   "song": {
#     "id": 1,
#     "title": "Bachata Rosa",
#     "artist": "Juan Luis Guerra"
#   },
#   "status": "pending",
#   "message": "Choreography generation started",
#   "poll_url": "/api/choreography/tasks/550e8400-e29b-41d4-a716-446655440000"
# }

# Step 4: Poll for status
curl -X GET http://localhost:8001/api/choreography/tasks/550e8400-e29b-41d4-a716-446655440000/ \
  -H "Authorization: Bearer $TOKEN"

# Step 5: When completed, save to collection
curl -X POST http://localhost:8001/api/collections/save/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "My Romantic Dance"
  }'
```

#### 3. Song Endpoint Examples

**List Songs with Filtering:**

```bash
# List all songs
curl -X GET http://localhost:8001/api/choreography/songs/ \
  -H "Authorization: Bearer $TOKEN"

# Filter by genre
curl -X GET "http://localhost:8001/api/choreography/songs/?genre=bachata" \
  -H "Authorization: Bearer $TOKEN"

# Filter by BPM range
curl -X GET "http://localhost:8001/api/choreography/songs/?bpm_min=110&bpm_max=130" \
  -H "Authorization: Bearer $TOKEN"

# Search by title or artist
curl -X GET "http://localhost:8001/api/choreography/songs/?search=rosa" \
  -H "Authorization: Bearer $TOKEN"

# Combine filters with pagination
curl -X GET "http://localhost:8001/api/choreography/songs/?genre=bachata&bpm_min=115&page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Get Song Details:**

```bash
# Get specific song by ID
curl -X GET http://localhost:8001/api/choreography/songs/1/ \
  -H "Authorization: Bearer $TOKEN"

# Response includes audio_path for processing
# {
#   "id": 1,
#   "title": "Bachata Rosa",
#   "artist": "Juan Luis Guerra",
#   "duration": 245.5,
#   "bpm": 120,
#   "genre": "bachata",
#   "audio_path": "songs/bachata-rosa.mp3",
#   "created_at": "2025-11-08T10:00:00Z",
#   "updated_at": "2025-11-08T10:00:00Z"
# }
```

**Generate from Song:**

```bash
# Basic generation with song ID and difficulty
curl -X POST http://localhost:8001/api/choreography/generate-from-song/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "song_id": 1,
    "difficulty": "beginner"
  }'

# Advanced generation with style and energy
curl -X POST http://localhost:8001/api/choreography/generate-from-song/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "song_id": 1,
    "difficulty": "intermediate",
    "energy_level": "high",
    "style": "modern"
  }'

# Response (202 Accepted):
# {
#   "task_id": "550e8400-e29b-41d4-a716-446655440000",
#   "song": {
#     "id": 1,
#     "title": "Bachata Rosa",
#     "artist": "Juan Luis Guerra"
#   },
#   "status": "pending",
#   "message": "Choreography generation started",
#   "poll_url": "/api/choreography/tasks/550e8400-e29b-41d4-a716-446655440000"
# }
```

#### 4. Natural Language AI Workflow

```bash
# Parse natural language query
curl -X POST http://localhost:8001/api/choreography/parse-query/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a romantic beginner choreography with slow tempo"
  }'

# Response:
# {
#   "parameters": {
#     "difficulty": "beginner",
#     "style": "romantic",
#     "energy_level": "low",
#     "tempo": "slow"
#   },
#   "confidence": 0.95,
#   "query": "Create a romantic beginner choreography with slow tempo"
# }

# Generate with AI
curl -X POST http://localhost:8001/api/choreography/generate-with-ai/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a romantic beginner choreography",
    "parameters": {
      "difficulty": "beginner",
      "style": "romantic"
    }
  }'
```

#### 5. Collection Management

```bash
# List collections with filtering
curl -X GET "http://localhost:8001/api/collections/?difficulty=intermediate&search=romantic&ordering=-created_at" \
  -H "Authorization: Bearer $TOKEN"

# Get statistics
curl -X GET http://localhost:8001/api/collections/stats/ \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "total_count": 15,
#   "total_duration": 675.5,
#   "by_difficulty": {
#     "beginner": 5,
#     "intermediate": 7,
#     "advanced": 3
#   },
#   "recent_count": 3
# }

# Bulk delete all
curl -X POST http://localhost:8001/api/collections/delete-all/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirmation": true}'
```

#### 6. Instructor Workflow

```bash
# Create class plan
curl -X POST http://localhost:8001/api/instructors/class-plans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Beginner Workshop",
    "description": "Introduction to bachata basics",
    "difficulty_level": "beginner",
    "estimated_duration": 60
  }'

# Add sequence to class plan
curl -X POST http://localhost:8001/api/instructors/class-plans/{plan_id}/add-sequence/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "choreography_id": "choreo-uuid",
    "notes": "Start with this",
    "estimated_time": 10
  }'

# Get class plan summary
curl -X GET http://localhost:8001/api/instructors/class-plans/{plan_id}/summary/ \
  -H "Authorization: Bearer $TOKEN"

# Export as HTML
curl -X GET http://localhost:8001/api/instructors/class-plans/{plan_id}/export/ \
  -H "Authorization: Bearer $TOKEN" \
  > class_plan.html
```

### Feature Highlights

#### ✅ Complete Feature Parity with Legacy App

All features from the legacy Django monolith are available via REST API:

- **User Management**
  - Registration and authentication
  - Profile management
  - User preferences (auto-save, default difficulty, notifications)

- **Choreography Generation (Two Workflows)**
  
  **Workflow 1: Song Template (Recommended)**
  - Browse pre-existing songs with metadata (title, artist, BPM, genre)
  - Filter by genre, BPM range, or search by title/artist
  - Select a song and generate choreography with chosen difficulty
  - Supports local storage (development) and GCS (production)
  - Fast and reliable - no external dependencies
  
  **Workflow 2: AI Natural Language**
  - Describe choreography in natural language ("create a romantic beginner dance")
  - AI parses query and extracts parameters (difficulty, style, energy)
  - AI-generated explanations for move selections
  - Powered by Google Gemini
  
  **Both workflows:**
  - Async task processing with real-time status updates
  - Poll task status endpoint for progress
  - Save completed choreographies to collections

- **Collection Management**
  - Save generated choreographies
  - Filter by difficulty, search by title
  - Pagination and sorting
  - Collection statistics dashboard
  - Bulk operations (delete all, cleanup orphaned)

- **Instructor Features**
  - Create and manage class plans
  - Add choreographies in sequence
  - Drag-and-drop reordering
  - Duplicate class plans
  - Generate structured summaries
  - Export to HTML for printing
  - Instructor dashboard with statistics

#### 🔒 Security Features

- JWT authentication with access/refresh tokens
- Permission-based access control (IsAuthenticated, IsInstructor)
- Resource ownership validation
- CORS configuration
- Input validation and sanitization
- Rate limiting support

#### 📊 Performance Features

- Database query optimization (select_related, prefetch_related)
- Indexed fields for fast filtering
- Pagination for large datasets
- Async task processing via Cloud Run Jobs
- Caching support (ready to enable)

#### 🧪 Testing

- Comprehensive unit tests for all endpoints
- Integration tests for complete workflows
- 100% endpoint coverage
- Automated test suite

### Frontend Integration

The API is designed for seamless React frontend integration:

1. **TypeScript Client Generation**
   ```bash
   npx @openapitools/openapi-generator-cli generate \
     -i http://localhost:8001/api/schema/ \
     -g typescript-axios \
     -o frontend/src/api
   ```

2. **Authentication State Management**
   - Store JWT tokens in localStorage or secure cookies
   - Implement token refresh logic
   - Handle 401 responses with automatic re-authentication

3. **Real-time Updates**
   - Poll task status endpoints for choreography generation progress
   - Update UI based on task status (queued, running, completed, failed)

4. **Error Handling**
   - All endpoints return consistent error format
   - HTTP status codes follow REST conventions
   - Detailed error messages for debugging

### Deployment

See `DEPLOYMENT.md` for production deployment instructions including:
- Cloud Run configuration
- Cloud SQL setup
- Environment variables
- Secrets management
- CI/CD pipeline

---

## Additional Documentation

- **API Feature Parity:** `FEATURE_PARITY_CHECKLIST.md` - Complete endpoint inventory
- **Endpoint Status:** `ENDPOINT_STATUS.md` - Implementation status
- **Integration Tests:** `INTEGRATION_TESTS_SUMMARY.md` - Test coverage
- **OpenAPI Documentation:** `API_DOCUMENTATION_UPDATE.md` - Documentation details
- **OpenAPI Schema:** `schema.yml` - Machine-readable API specification
