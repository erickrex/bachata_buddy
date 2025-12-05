# Simplified Serverless Architecture Design

**Project:** Bachata Buddy - Microservices Migration  
**Date:** November 1, 2025  
**Status:** Design Phase

**⚠️ CRITICAL: This is a MIGRATION project. Backend will use existing Cloud SQL database, starting with existing schema and improving with migrations.**

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Google Cloud Load Balancer                          │
│              (HTTPS, SSL Termination)                            │
└────────────┬────────────────────────┬────────────────────────────┘
             │                        │
             ▼                        ▼
┌────────────────────────┐  ┌────────────────────────┐
│  React Frontend        │  │  Django REST API       │
│  (Cloud Run)           │  │  (Cloud Run)           │
│  ┌──────────────────┐  │  │  ┌──────────────────┐  │
│  │ • React 18.3.1   │  │  │  │ • DRF 3.14       │  │
│  │ • JavaScript     │  │  │  │ • JWT Auth       │  │
│  │ • React Router   │  │  │  │ • CORS           │  │
│  │ • Fetch API      │  │  │  │ • OpenAPI        │  │
│  │ • Tailwind CSS   │  │  │  │ • Jobs API       │  │
│  │ • nginx          │  │  │  │ • Rate Limiting  │  │
│  └──────────────────┘  │  │  └──────────────────┘  │
│                        │  │                        │
│  Port: 8080            │  │  Port: 8080            │
│  Min: 0, Max: 10       │  │  Min: 1, Max: 10       │
└────────────────────────┘  └────────┬───────────────┘
                                     │
                                     │ Creates Job via API
                                     ▼
                         ┌────────────────────────┐
                         │  Cloud Run Job         │
                         │  (video-processor)     │
                         │  ┌──────────────────┐  │
                         │  │ • FFmpeg         │  │
                         │  │ • Librosa        │  │
                         │  │ • YOLOv8         │  │
                         │  │ • Direct DB      │  │
                         │  └──────────────────┘  │
                         │                        │
                         │  Memory: 4GB           │
                         │  CPU: 4                │
                         │  Timeout: 3600s        │
                         │  Max Retries: 3        │
                         └────────┬───────────────┘
                                  │
                                  │ Writes directly
                                  ▼
        ┌─────────────────────────┴─────────────────────────┐
        │                                                    │
        ▼                                                    ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Cloud SQL     │  │  Elasticsearch │  │  Cloud Storage │
│  (PostgreSQL)  │  │  Serverless    │  │  (GCS)         │
│  • Users       │  │  • Move        │  │  • Videos      │
│  • Tasks       │  │    Embeddings  │  │  • Audio       │
│  • Collections │  │  • Vector      │  │  • Generated   │
│                │  │    Search      │  │    Content     │
└────────────────┘  └────────────────┘  └────────────────┘
```

**Key Simplifications:**
- ❌ **No Pub/Sub** - Django directly creates Cloud Run Jobs via API
- ❌ **No Worker Service** - Jobs are triggered on-demand
- ✅ **Direct Database Writes** - Jobs update task status directly in Cloud SQL
- ✅ **Simpler Flow** - React → Django → Job → Database → React polls Django
- ✅ **Reuse Existing Database** - Backend uses same Cloud SQL database as original app
- ✅ **Mirror Existing Models** - Backend models match original app's schema exactly
- ✅ **Local Development First** - Complete system works locally before ANY cloud deployment

---

## Database & Schema Reuse Strategy

### Critical Requirement: Shared Database

**THE BACKEND API WILL USE THE SAME CLOUD SQL DATABASE AS THE ORIGINAL MONOLITHIC APP.**

This is a **migration**, not a greenfield project. We'll start with the existing schema and improve it with migrations.

### Why Shared Database?

1. **Zero Downtime Migration** - Both systems operate simultaneously during cutover
2. **Data Consistency** - No need to sync data between databases
3. **Gradual Migration** - Can migrate features incrementally
4. **Rollback Safety** - Easy to rollback to monolithic app if issues arise
5. **Working System** - Original Django app is working correctly, don't break it
6. **Schema Evolution** - Can improve schema with migrations after initial compatibility

### Schema Strategy (Two-Phase Approach)

**PHASE 1: Initial Compatibility**
- ✅ **Database Tables** - Use existing tables as starting point
- ✅ **Table Names** - Backend models use `db_table` to match original table names
- ✅ **Field Compatibility** - Start with fields that match existing schema
- ✅ **Data Access** - Both systems can read/write existing data
- ✅ **Elasticsearch Index** - Use existing index with existing embeddings
- ✅ **Cloud Storage Bucket** - Use existing GCS bucket with existing videos

**PHASE 2: Schema Improvements (After successful migration)**
- ✅ **Field Type Improvements** - Migrate CharField(36) → UUIDField with data migrations
- ✅ **Better Field Names** - Rename fields for clarity (with migrations)
- ✅ **Normalized Structures** - Improve relationships and constraints
- ✅ **Optimized Indexes** - Add composite indexes based on query patterns
- ✅ **Data Cleanup** - Remove unused fields, add constraints

### Models to Mirror

| Original Model | Original Location | Backend Location | Table Name |
|----------------|-------------------|------------------|------------|
| ChoreographyTask | `choreography/models.py` | `backend/apps/choreography/models.py` | `choreography_tasks` |
| SavedChoreography | `choreography/models.py` | `backend/apps/collections/models.py` | `saved_choreographies` |
| User | Django's built-in | `backend/apps/authentication/models.py` | `auth_user` |

### Example - ChoreographyTask Model Evolution

**Original Model (choreography/models.py):**
```python
class ChoreographyTask(models.Model):
    task_id = models.CharField(max_length=36, primary_key=True)  # CharField storing UUID strings
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='choreography_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    progress = models.IntegerField(default=0)
    stage = models.CharField(max_length=50, default='initializing')
    message = models.TextField(default='Starting choreography generation...')
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'choreography_tasks'
```

**Backend Model Phase 1 (backend/apps/choreography/models.py) - Initial Compatibility:**
```python
class ChoreographyTask(models.Model):
    """Start with compatibility, improve later with migrations"""
    task_id = models.CharField(max_length=36, primary_key=True)  # Start with same type
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='choreography_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    progress = models.IntegerField(default=0)
    stage = models.CharField(max_length=50, default='initializing')
    message = models.TextField(default='Starting choreography generation...')
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    job_execution_name = models.CharField(max_length=500, null=True, blank=True)  # NEW field
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'choreography_tasks'  # Match original
        ordering = ['-created_at']
```

**Backend Model Phase 2 (After Migration) - Improved:**
```python
class ChoreographyTask(models.Model):
    """Improved version after data migration"""
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4)  # Improved to proper UUID
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')  # Cleaner name
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')  # Better naming
    progress = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    stage = models.CharField(max_length=50, default='initializing')
    message = models.TextField(default='Starting choreography generation...')
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    job_execution_name = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'choreography_tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),  # Composite index for common queries
        ]
```

**Key Points:**
- ✅ Phase 1: Start with CharField(36) for compatibility
- ✅ Phase 2: Migrate to UUIDField with data migration
- ✅ Can improve status choices after migration
- ✅ Can add validators and constraints
- ✅ Can optimize indexes based on query patterns

### Schema Changes

**Phase 1 (Initial Compatibility):**
- ✅ Can add new fields to backend models (e.g., `job_execution_name`)
- ✅ New fields must be nullable or have defaults
- ✅ Can add new indexes

**Phase 2 (After Migration):**
- ✅ Can change field types with data migrations
- ✅ Can rename fields with migrations
- ✅ Can add validators and constraints
- ✅ Can optimize schema structure
- ✅ Original app will ignore new fields (no migration needed there)
- ❌ Cannot change existing field types or names
- ❌ Cannot rename tables

### Elasticsearch Reuse

**MUST REUSE:**
- ✅ Existing Elasticsearch index (`bachata_move_embeddings`)
- ✅ Existing embeddings (don't regenerate)
- ✅ Same index schema and mapping
- ✅ Same query patterns

**Why:**
- Embeddings take hours to generate
- Original app's embeddings are working correctly
- Both systems need to query same move database

### Cloud Storage Reuse

**MUST REUSE:**
- ✅ Existing GCS bucket
- ✅ Existing video files
- ✅ Same path structure (`choreographies/%Y/%m/`, `thumbnails/%Y/%m/`)
- ✅ Same file naming conventions

### Testing Requirements

**MUST TEST:**
- ✅ Backend can read data created by original app
- ✅ Original app can read data created by backend
- ✅ No data corruption or conflicts
- ✅ Both systems can run simultaneously
- ✅ Elasticsearch queries return same results
- ✅ Video files accessible from both systems

### Implementation Reference

See `backend/MODEL_REUSE_STRATEGY.md` for detailed implementation guide.

---

## Dependency Management with UV

### Overview

All Python operations in the backend service MUST use **UV** as the package manager. UV is a fast Python package installer and resolver that replaces pip and manages Python environments.

### Why UV?

- ✅ **Faster** - 10-100x faster than pip
- ✅ **Reliable** - Better dependency resolution
- ✅ **Consistent** - Lock file ensures reproducible builds
- ✅ **Simple** - Single tool for all Python operations
- ✅ **Modern** - Built for modern Python workflows

### Backend Dependency Structure

**Location:** `backend/pyproject.toml`

This is the ONLY dependency file for the backend API and video processing job. The root-level `pyproject.toml` is kept only for reference during migration.

```toml
[project]
name = "bachata-buddy-api"
version = "1.0.0"
description = "REST API for Bachata Buddy choreography generation platform"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    # Core Django
    "django>=5.2",
    "djangorestframework>=3.14",
    "djangorestframework-simplejwt>=5.3",
    
    # API Documentation
    "drf-spectacular>=0.27",
    
    # CORS Support
    "django-cors-headers>=4.3",
    
    # Database
    "psycopg2-binary>=2.9",
    
    # Google Cloud
    "google-cloud-run>=0.10",
    "google-cloud-storage>=2.10",
    "google-cloud-secret-manager>=2.16",
    
    # Production Server
    "gunicorn>=21.2",
    
    # Environment Variables
    "python-dotenv>=1.0",
    
    # Elasticsearch Client
    "elasticsearch>=8.11",
    
    # Google AI
    "google-generativeai>=0.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-django>=4.5.0",
    "pytest-cov>=4.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### UV Commands Reference

**Installing UV:**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv

# Or with pip (if you must)
pip install uv
```

**Essential Commands:**

```bash
# Navigate to backend directory
cd backend

# Install all dependencies from pyproject.toml
uv sync

# Add a new dependency
uv add django-cors-headers

# Add a development dependency
uv add --dev pytest-django

# Remove a dependency
uv remove package-name

# Run Python scripts
uv run python manage.py migrate
uv run python manage.py runserver

# Run tests
uv run pytest

# Run any Python command
uv run python script.py
```

### Docker Integration

**Backend Dockerfile with UV:**
```dockerfile
FROM python:3.12-slim

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using UV
RUN uv pip install --system --no-cache .

# Copy application code
COPY . .

# Run with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 api.wsgi:application
```

**Docker Compose with UV:**
```yaml
services:
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: uv run python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
    environment:
      - DEBUG=True
```

### Development Workflow

**1. Initial Setup:**
```bash
# Clone repository
git clone <repo-url>
cd bachata_buddy/backend

# Install dependencies
uv sync

# Run migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser
```

**2. Adding Dependencies:**
```bash
# Add a new package
cd backend
uv add requests

# This automatically:
# - Updates pyproject.toml
# - Installs the package
# - Updates the lock file
```

**3. Running Commands:**
```bash
# ALWAYS use uv run for Python commands
uv run python manage.py migrate
uv run python manage.py makemigrations
uv run python manage.py createsuperuser
uv run python manage.py shell
uv run pytest
uv run python script.py
```

**4. Docker Development:**
```bash
# Inside Docker container, UV is already installed
docker-compose exec api uv run python manage.py migrate
docker-compose exec api uv run pytest
```

### Critical Rules

**DO:**
- ✅ Use `uv sync` to install dependencies
- ✅ Use `uv add <package>` to add dependencies
- ✅ Use `uv run python <command>` to run Python
- ✅ Use `backend/pyproject.toml` for all backend dependencies
- ✅ Commit `pyproject.toml` to git
- ✅ Use UV in Dockerfiles

**DON'T:**
- ❌ Use `pip install` - Use `uv add` or `uv sync` instead
- ❌ Use `python manage.py` - Use `uv run python manage.py` instead
- ❌ Use direct `python` commands - Use `uv run python` instead
- ❌ Use `requirements.txt` - Use `pyproject.toml` instead
- ❌ Use root-level `pyproject.toml` for new backend code
- ❌ Mix pip and UV

### Video Processing Job

The video processing job uses the SAME `backend/pyproject.toml` file:

```dockerfile
# job/Dockerfile
FROM python:3.12-slim

# Install FFmpeg and system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy backend dependencies
COPY backend/pyproject.toml ./

# Install dependencies using UV
RUN uv pip install --system --no-cache .

# Copy job code
COPY job/src/ ./src/

# Run the job
CMD ["python", "-m", "src.main"]
```

### CI/CD Integration

**GitHub Actions Example:**
```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      
      - name: Install dependencies
        run: |
          cd backend
          uv sync
      
      - name: Run tests
        run: |
          cd backend
          uv run pytest
```

### Migration from pip to UV

If you have existing code using pip:

```bash
# 1. Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create pyproject.toml from requirements.txt (if needed)
cd backend
uv pip compile requirements.txt -o pyproject.toml

# 3. Install dependencies
uv sync

# 4. Test that everything works
uv run python manage.py check

# 5. Update all scripts to use uv run
# Replace: python manage.py migrate
# With: uv run python manage.py migrate
```

### Troubleshooting

**Issue: "uv: command not found"**
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (if needed)
export PATH="$HOME/.cargo/bin:$PATH"
```

**Issue: "Package not found"**
```bash
# Make sure you're in the backend directory
cd backend

# Sync dependencies
uv sync

# If still not working, try reinstalling
rm -rf .venv
uv sync
```

**Issue: "Permission denied"**
```bash
# UV needs write access to create virtual environment
# Make sure you have write permissions in the backend directory
chmod -R u+w backend/
```

---

## Component Design

### 1. React Frontend (JavaScript Only)

**Directory Structure:**
```
frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── Button.jsx
│   │   ├── Input.jsx
│   │   ├── Spinner.jsx
│   │   ├── VideoPlayer.jsx
│   │   └── Toast.jsx
│   ├── pages/
│   │   ├── Home.jsx
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Generate.jsx
│   │   ├── Collections.jsx
│   │   ├── CollectionDetail.jsx
│   │   └── Profile.jsx
│   ├── utils/
│   │   ├── api.js          # Fetch wrapper with JWT
│   │   └── auth.js         # Auth helpers
│   ├── App.jsx             # Router setup
│   └── main.jsx            # Entry point
├── nginx.conf
├── Dockerfile
├── package.json
├── vite.config.js
└── tailwind.config.js
```

**Key Features:**
- React 18.3.1 with JavaScript only (NO TypeScript)
- JWT tokens stored in localStorage
- Automatic token refresh
- Simple fetch() API calls
- No state management libraries (just useState/useEffect)
- Tailwind CSS for styling
- Vite for building

**Authentication Implementation:**
```javascript
// utils/api.js
export async function apiCall(url, options = {}) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
  });
  
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiCall(url, options);
    } else {
      window.location.href = '/login';
      throw new Error('Session expired');
    }
  }
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Request failed');
  }
  
  return response.json();
}

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return false;
  
  try {
    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    });
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access);
      return true;
    }
  } catch (err) {
    console.error('Token refresh failed:', err);
  }
  
  return false;
}
```

**Dockerfile:**
```dockerfile
FROM node:18 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

---

### 2. Django REST API

**Directory Structure:**
```
backend/
├── api/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── authentication/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── choreography/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── jobs.py          # Cloud Run Jobs API
│   │   └── urls.py
│   └── collections/
│       ├── __init__.py
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       └── urls.py
├── core/
│   ├── __init__.py
│   ├── middleware.py
│   └── permissions.py
├── services/
│   ├── __init__.py
│   ├── jobs_service.py      # Cloud Run Jobs client
│   ├── storage_service.py   # GCS client
│   └── elasticsearch_service.py
├── Dockerfile
├── requirements.txt
└── manage.py
```

**Key Components:**

#### JWT Authentication
```python
# settings.py
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

CORS_ALLOWED_ORIGINS = [
    'https://frontend-xxx.run.app',
]
CORS_ALLOW_CREDENTIALS = True
```

#### Cloud Run Jobs Service
```python
# services/jobs_service.py
from google.cloud import run_v2
import os

class CloudRunJobsService:
    def __init__(self):
        self.client = run_v2.JobsClient()
        self.project_id = os.environ['GCP_PROJECT_ID']
        self.region = os.environ['GCP_REGION']
        self.job_name = 'video-processor'
    
    def create_job_execution(self, task_id, user_id, parameters):
        """Create a Cloud Run Job execution"""
        job_path = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"
        
        request = run_v2.RunJobRequest(
            name=job_path,
            overrides={
                "container_overrides": [{
                    "env": [
                        {"name": "TASK_ID", "value": task_id},
                        {"name": "USER_ID", "value": str(user_id)},
                        {"name": "AUDIO_INPUT", "value": parameters['audio_input']},
                        {"name": "DIFFICULTY", "value": parameters['difficulty']},
                        {"name": "ENERGY_LEVEL", "value": parameters.get('energy_level', '')},
                        {"name": "STYLE", "value": parameters.get('style', '')},
                    ]
                }]
            }
        )
        
        # This triggers the job immediately
        operation = self.client.run_job(request=request)
        execution = operation.result()  # Wait for job to start
        
        return execution.name
```

#### Choreography Generation View
```python
# apps/choreography/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ChoreographyTask
from services.jobs_service import CloudRunJobsService
import uuid

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_choreography(request):
    """Start choreography generation (creates Cloud Run Job)"""
    # Validate input
    serializer = ChoreographyGenerationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Create task - MUST use 'started' status to match original app
    task_id = str(uuid.uuid4())
    task = ChoreographyTask.objects.create(
        task_id=task_id,
        user=request.user,
        status='started',  # Match original app's status choices!
        progress=0,
        stage='initializing',
        message='Choreography generation queued'
    )
    
    # Create Cloud Run Job execution
    jobs_service = CloudRunJobsService()
    try:
        execution_name = jobs_service.create_job_execution(
            task_id=task_id,
            user_id=request.user.id,
            parameters=serializer.validated_data
        )
        
        # Store execution name for monitoring (NEW field, safe to add)
        task.job_execution_name = execution_name
        task.save()
        
    except Exception as e:
        task.status = 'failed'
        task.error = str(e)
        task.save()
        return Response(
            {'error': 'Failed to create job execution'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Return task info
    return Response({
        'task_id': task_id,
        'job_execution_name': execution_name,
        'status': 'started',  # Match original app!
        'message': 'Choreography generation started',
        'poll_url': f'/api/choreography/tasks/{task_id}'
    }, status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_status(request, task_id):
    """Get task status (polls database)"""
    try:
        task = ChoreographyTask.objects.get(task_id=task_id, user=request.user)
    except ChoreographyTask.DoesNotExist:
        return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'task_id': task.task_id,
        'status': task.status,
        'progress': task.progress,
        'stage': task.stage,
        'message': task.message,
        'result': task.result,
        'error': task.error,
        'created_at': task.created_at,
        'updated_at': task.updated_at,
    })
```

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 api.wsgi:application
```

---

### 3. Cloud Run Job (Video Processing)

**Directory Structure:**
```
job/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── pipeline.py          # Choreography pipeline
│   └── services/
│       ├── __init__.py
│       ├── video_generator.py
│       ├── music_analyzer.py
│       ├── pose_detector.py
│       ├── elasticsearch_service.py
│       ├── storage_service.py
│       └── database.py      # Direct DB connection
├── Dockerfile
├── requirements.txt
└── README.md
```

**Main Entry Point:**
```python
# src/main.py
import os
import sys
from pipeline import ChoreoGenerationPipeline
from services.database import update_task_status

def main():
    # Get parameters from environment variables
    task_id = os.environ['TASK_ID']
    user_id = int(os.environ['USER_ID'])
    audio_input = os.environ['AUDIO_INPUT']
    difficulty = os.environ['DIFFICULTY']
    energy_level = os.environ.get('ENERGY_LEVEL', '')
    style = os.environ.get('STYLE', '')
    
    print(f"Starting job for task {task_id}")
    
    try:
        # Update status to processing
        update_task_status(task_id, 'processing', 10, 'downloading', 'Downloading audio...')
        
        # Run pipeline
        pipeline = ChoreoGenerationPipeline()
        result = pipeline.generate(
            audio_input=audio_input,
            difficulty=difficulty,
            energy_level=energy_level,
            style=style
        )
        
        if result.success:
            # Update status to completed
            update_task_status(
                task_id, 'completed', 100, 'completed',
                'Choreography generated successfully!',
                result=result.to_dict()
            )
            print(f"Job completed successfully for task {task_id}")
        else:
            # Update status to failed
            update_task_status(
                task_id, 'failed', 0, 'failed',
                'Generation failed',
                error=result.error_message
            )
            print(f"Job failed for task {task_id}: {result.error_message}")
            sys.exit(1)
    
    except Exception as e:
        # Update status to failed
        update_task_status(
            task_id, 'failed', 0, 'failed',
            'Unexpected error',
            error=str(e)
        )
        print(f"Job failed with exception for task {task_id}: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

**Database Service:**
```python
# src/services/database.py
import psycopg2
import os
import json

def get_db_connection():
    """Get database connection to EXISTING Cloud SQL database"""
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        port=os.environ.get('DB_PORT', 5432),
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )

def update_task_status(task_id, status, progress, stage, message, result=None, error=None):
    """
    Update task status in database
    
    CRITICAL: Table name MUST match original app (choreography_tasks)
    Status values MUST match original app ('started', 'running', 'completed', 'failed')
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # MUST use exact table name from original app
            cursor.execute("""
                UPDATE choreography_tasks
                SET status = %s, progress = %s, stage = %s, message = %s,
                    result = %s, error = %s, updated_at = NOW()
                WHERE task_id = %s
            """, (
                status, progress, stage, message,
                json.dumps(result) if result else None,
                error,
                task_id
            ))
            conn.commit()
    finally:
        conn.close()
```

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

# Install FFmpeg and system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Run the job
CMD ["python", "-m", "src.main"]
```

---

## Data Flow

### Choreography Generation Flow

```
1. User clicks "Generate" in React app
   ↓
2. React: POST /api/choreography/generate
   {
     "audio_input": "gs://bucket/songs/song.mp3",
     "difficulty": "intermediate"
   }
   Headers: Authorization: Bearer <jwt_token>
   ↓
3. Django API:
   - Validates JWT token
   - Creates ChoreographyTask (status='pending')
   - Calls Cloud Run Jobs API to create execution
   - Returns 202 Accepted with task_id
   ↓
4. React: Start polling GET /api/choreography/tasks/{task_id}
   (every 2 seconds)
   ↓
5. Cloud Run Job: Starts execution
   - Reads task_id from environment variable
   - Updates task status to 'processing' in database
   - Downloads audio
   - Analyzes music
   - Queries Elasticsearch
   - Generates video with FFmpeg
   - Uploads to Cloud Storage
   - Updates task status to 'completed' in database
   ↓
6. React: Poll detects status='completed'
   - Stop polling
   - Display video player with GCS URL
   - Show "Save to Collection" button
   ↓
7. User clicks "Save"
   ↓
8. React: POST /api/collections
   {
     "title": "My Choreography",
     "video_url": "gs://bucket/output/video.mp4",
     "difficulty": "intermediate",
     "duration": 180.5
   }
   ↓
9. Django API:
   - Create SavedChoreography record
   - Return 201 Created
   ↓
10. React: Navigate to /collections
```

---

## Security Design

### JWT Authentication

**Token Structure:**
```json
{
  "token_type": "access",
  "exp": 1698345600,
  "iat": 1698342000,
  "jti": "abc123",
  "user_id": 42,
  "username": "dancer123"
}
```

**Token Storage:**
- Access token: localStorage (60 min lifetime)
- Refresh token: localStorage (7 days lifetime)
- Automatic refresh 5 minutes before expiration

**API Security:**
- All endpoints require JWT except /auth/login, /auth/register, /auth/refresh
- CORS whitelist: frontend Cloud Run URL
- Rate limiting: 100 requests/minute per user
- SQL injection protection: Django ORM
- XSS protection: React escaping

**Job Security:**
- Service account with minimal permissions
- Cloud SQL connection via Unix socket
- Secrets from Secret Manager
- No external network access (except GCS, Elasticsearch)

---

## Deployment Architecture

### Cloud Run Services

**Frontend (React):**
```yaml
Service: bachata-frontend
Region: us-central1
Memory: 512Mi
CPU: 1
Min Instances: 0
Max Instances: 10
Port: 8080
Environment:
  - VITE_API_URL=https://bachata-api-xxx.run.app
```

**Backend (Django):**
```yaml
Service: bachata-api
Region: us-central1
Memory: 2Gi
CPU: 2
Min Instances: 1
Max Instances: 10
Port: 8080
Environment:
  - DJANGO_SETTINGS_MODULE=api.settings
  - ENVIRONMENT=production
  - GCP_PROJECT_ID=<project-id>
  - GCP_REGION=us-central1
Secrets:
  - DJANGO_SECRET_KEY
  - DB_PASSWORD
  - ELASTICSEARCH_API_KEY
  - GOOGLE_API_KEY
Cloud SQL: bachata-db (Unix socket)
```

**Job (Video Processing):**
```yaml
Job: video-processor
Region: us-central1
Memory: 4Gi
CPU: 4
Max Retries: 3
Task Timeout: 3600s
Parallelism: 5
Environment:
  - ENVIRONMENT=production
Secrets:
  - DB_PASSWORD
  - ELASTICSEARCH_API_KEY
  - GOOGLE_API_KEY
Cloud SQL: bachata-db (Unix socket)
```

---

## Monitoring & Observability

### Metrics to Track

**API Metrics:**
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Active users
- JWT token refresh rate

**Job Metrics:**
- Jobs created/second
- Job execution time
- Success/failure rate
- Queue depth (pending jobs)
- Concurrent executions

**Business Metrics:**
- Choreographies generated/day
- Average generation time
- User registrations
- Collection saves

### Logging Strategy

**Structured Logging:**
```python
logger.info("Job started", extra={
    "task_id": task_id,
    "user_id": user_id,
    "difficulty": difficulty,
    "timestamp": datetime.utcnow().isoformat()
})
```

**Log Levels:**
- DEBUG: Development only
- INFO: Normal operations
- WARNING: Recoverable errors
- ERROR: Failed operations
- CRITICAL: System failures

### Alerting

**Critical Alerts:**
- API error rate >5%
- Job execution time >5 minutes
- Job failure rate >10%
- Database connection failures

**Warning Alerts:**
- API response time >1 second
- Pending jobs >50
- Disk usage >80%

---

## Cost Optimization

### Estimated Monthly Costs

**Cloud Run (Frontend):**
- Min instances: 0 (scale to zero)
- Estimated: $5-10/month

**Cloud Run (API):**
- Min instances: 1 (always warm)
- Estimated: $140/month

**Cloud Run Jobs:**
- 100 jobs/month × 60s each
- Estimated: $0.64/month

**Cloud SQL:**
- db-f1-micro
- Estimated: $15/month

**Elasticsearch Serverless:**
- Search project
- Estimated: $95-200/month

**Cloud Storage:**
- 100GB
- Estimated: $2/month

**Total: $260-370/month**

**Optimization Strategies:**
- Scale frontend to zero when idle
- Use Cloud CDN for static assets
- Compress videos before upload
- Clean up old tasks (>30 days)
- Use Cloud Storage lifecycle policies

---

## Testing Strategy

### Unit Tests
- API endpoints (pytest-django)
- Serializers validation
- Job pipeline logic
- React components (Jest + React Testing Library)

### Integration Tests
- End-to-end API flows
- Job execution
- Database operations
- Authentication flows

### Load Tests
- API: 100 concurrent users
- Jobs: 10 concurrent executions
- Database: 1000 queries/second

### Manual Tests
- User registration and login
- Choreography generation
- Video playback
- Collection management
- Mobile responsiveness

### Data Compatibility Tests
- Backend can read data created by original app
- Original app can read data created by backend
- Both systems can write simultaneously without conflicts
- Elasticsearch queries return same results from both systems
- Video files accessible from both systems

---

## Success Criteria

### Technical Success Criteria
- ✅ All API endpoints functional and documented
- ✅ JWT authentication working
- ✅ Video generation completes in <2 minutes
- ✅ React frontend loads in <2 seconds
- ✅ 99.9% uptime for API
- ✅ All existing features working
- ✅ Mobile responsive
- ✅ Comprehensive test coverage (>80%)

### Data Compatibility Success Criteria
- ✅ **Zero data loss during migration**
- ✅ **Backend can read data created by original app**
- ✅ **Original app can read data created by backend**
- ✅ **Both systems can run simultaneously without conflicts**
- ✅ **Elasticsearch queries return same results from both systems**
- ✅ **Video files accessible from both systems**

### Migration Success Criteria
- ✅ **Clean cut migration** - DNS switched all at once
- ✅ **Original Django app kept as backup** (no traffic, just reference)
- ✅ **Rollback capability available** (can switch DNS back if needed)
- ✅ **No user complaints about missing functionality**
- ✅ **Performance meets or exceeds original app**
- ✅ **1-2 weeks verification period** before deleting original app

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Schema mismatch between apps** | **Critical** | **High** | **Document original schema first, mirror models exactly, verify db_table names, test data compatibility** |
| **Data corruption from concurrent writes** | **Critical** | **Medium** | **Test both systems writing simultaneously, use database transactions, monitor for conflicts** |
| **Breaking original app with backend changes** | **Critical** | **Medium** | **Never change existing fields, only add new nullable fields, test original app after backend deployment** |
| Data migration issues | High | Medium | Thorough testing, rollback plan |
| Job execution failures | Medium | Low | Cloud Run Jobs retry logic, monitoring |
| Performance degradation | Medium | Medium | Load testing, monitoring |
| User disruption | High | Low | Parallel deployment, clean cut with rollback plan |
| Cost increase | Medium | Low | Pay-per-use jobs, budget alerts |

---

## Migration Approach

**⚠️ CRITICAL: Complete system MUST work locally with Docker Compose before ANY cloud deployment.**

### Phase 0: Database & Schema Analysis (Before Starting)
1. **Document existing database schema** from original app
2. **Identify all tables** used by original app
3. **Map models** from original to backend structure
4. **Verify Elasticsearch index** structure and embeddings
5. **Document GCS bucket** structure and file paths
6. **Create MODEL_REUSE_STRATEGY.md** with mapping

### Phase 1: Local Development (Week 1-4)
1. **Set up Docker Compose** with PostgreSQL, Elasticsearch, Django API, React Frontend, Job service
2. **Build Django REST API** with mirrored models
3. **Build React Frontend** with all pages and components
4. **Build Video Processing Job** with FFmpeg and pipeline logic
5. **Test complete system locally**:
   - User registration and login
   - Choreography generation (API → Job → Database → Frontend)
   - Video playback
   - Collection management
6. **Fix all issues locally**
7. **DO NOT PROCEED until everything works locally**

### Phase 2: Cloud Infrastructure Setup (Week 5)
1. Set up Cloud SQL (connect to existing database)
2. Set up Cloud Run services (API and Frontend)
3. Set up Cloud Run Jobs (video processor)
4. Configure secrets and environment variables
5. Test connectivity between services

### Phase 3: Cloud Deployment (Week 5-6)
1. Deploy Django REST API to Cloud Run
2. Deploy React Frontend to Cloud Run
3. Deploy Video Processing Job to Cloud Run Jobs
4. Test complete system in cloud
5. Verify all features work in cloud

### Phase 4: Parallel Operation (Week 6-7)
1. Original app continues on Compute Engine
2. New system running on Cloud Run
3. **Both connect to SAME Cloud SQL database**
4. Both can read/write ChoreographyTask and SavedChoreography
5. Both query same Elasticsearch index
6. Both use same GCS bucket
7. Test data compatibility

### Phase 5: Complete Migration (Clean Cut) (Week 7)
1. **Verify new system** works correctly in production
2. **Test all features** thoroughly
3. **CLEAN CUT**: Update DNS to point to new system (all traffic at once)
4. **Monitor closely** for first 24-48 hours
5. **Keep original app running** on Compute Engine (as reference/backup only, no traffic)
6. Verify all features working correctly
7. Monitor for 1-2 weeks
8. Fix any issues that arise

### Phase 6: Cleanup (Week 8+)
1. **Confirm migration success** - all features working, no critical issues
2. **Archive original app codebase** for reference
3. **Delete original Django app** from Compute Engine
4. Keep database (shared, still in use)
5. Update documentation

---

## Rollback Plan

### Why Keep Original App?

1. **Quick Rollback** - If new system fails, switch DNS back to original app
2. **Zero Data Loss** - Both systems use same database, no data sync needed
3. **Reference** - Can compare behavior if issues arise
4. **Confidence** - Team can migrate knowing rollback is possible

### Rollback Procedure

**If Critical Issues Occur:**

1. **Immediate Action** (< 15 minutes):
   - Update DNS to point back to original app
   - Verify original app is responding correctly
   - Notify team of rollback

2. **Investigation** (1-2 hours):
   - Identify root cause of failure
   - Document issues encountered
   - Assess impact on users and data

3. **Fix** (1-2 weeks):
   - Fix issues in new system
   - Test thoroughly
   - Retry cutover when ready

### When to Delete Original App

**Wait 1-2 weeks after cutover, then:**

- ✅ New system running smoothly
- ✅ All features verified working
- ✅ No critical bugs
- ✅ Team confident in new system

### Cleanup Steps

1. Archive original app codebase
2. Delete Compute Engine instance
3. Update documentation
4. Keep database (still in use by new system)

---

## Local Development Setup

### Docker Compose Configuration

For local development, we'll use Docker Compose to run all services:

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: bachata_buddy
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  # Elasticsearch (for move search)
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
  
  # Django REST API
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
      - ./data:/app/data  # Mount data directory
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/bachata_buddy
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - GCP_PROJECT_ID=local-dev
      - GCP_REGION=us-central1
      - DJANGO_SECRET_KEY=local-dev-secret-key
    depends_on:
      - db
      - elasticsearch
  
  # React Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    command: npm run dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - api
  
  # Video Processing Job (for local testing)
  job:
    build:
      context: ./job
      dockerfile: Dockerfile
    volumes:
      - ./job:/app
      - ./data:/app/data  # Mount data directory
    environment:
      - TASK_ID=${TASK_ID:-test-task-id}
      - USER_ID=${USER_ID:-1}
      - AUDIO_INPUT=${AUDIO_INPUT:-/app/data/songs/test.mp3}
      - DIFFICULTY=${DIFFICULTY:-intermediate}
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=bachata_buddy
      - DB_USER=postgres
      - DB_PASSWORD=postgres
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    depends_on:
      - db
      - elasticsearch
    profiles:
      - job  # Only run when explicitly requested

volumes:
  postgres_data:
  elasticsearch_data:
```

**Backend Dockerfile.dev:**
```dockerfile
FROM python:3.12-slim

# Install FFmpeg for local testing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**Frontend Dockerfile.dev:**
```dockerfile
FROM node:18

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

### Local Development Workflow

**1. Initial Setup:**
```bash
# Clone repository
git clone <repo-url>
cd bachata_buddy

# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create .env file
cat > .env << EOF
GOOGLE_API_KEY=your-api-key-here
EOF

# Start all services
docker-compose up -d

# Run migrations (using UV)
docker-compose exec api uv run python manage.py migrate

# Create superuser (using UV)
docker-compose exec api uv run python manage.py createsuperuser

# Load initial data (optional, using UV)
docker-compose exec api uv run python manage.py loaddata initial_data.json
```

**2. Daily Development:**
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f frontend

# Run tests (using UV)
docker-compose exec api uv run pytest
docker-compose exec frontend npm test

# Stop services
docker-compose down
```

**3. Testing Video Processing Job Locally:**
```bash
# Set environment variables
export TASK_ID=test-task-123
export USER_ID=1
export AUDIO_INPUT=/app/data/songs/test.mp3
export DIFFICULTY=intermediate

# Run job (using UV inside container)
docker-compose run --rm job uv run python -m src.main
```

**4. Alternative: Run Without Docker (Native Development with UV)**

If you prefer to run services natively:

```bash
# Terminal 1: Database
docker-compose up -d db elasticsearch

# Terminal 2: Django API (using UV)
cd backend
uv sync  # Install dependencies
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bachata_buddy
export ELASTICSEARCH_URL=http://localhost:9200
uv run python manage.py runserver

# Terminal 3: React Frontend
cd frontend
npm install
npm run dev

# Terminal 4: Job (for testing, using UV)
cd backend
uv sync  # Job uses same dependencies as backend
export TASK_ID=test-task-123
export USER_ID=1
export AUDIO_INPUT=./data/songs/test.mp3
export DIFFICULTY=intermediate
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=bachata_buddy
export DB_USER=postgres
export DB_PASSWORD=postgres
cd ../job
uv run python -m src.main
```

**Note:** UV automatically manages virtual environments, so you don't need to manually create or activate them.

### Local vs Production Differences

| Aspect | Local Development | Production (Cloud Run) |
|--------|------------------|------------------------|
| Database | PostgreSQL in Docker | Cloud SQL |
| Elasticsearch | Docker container | Elasticsearch Serverless |
| Storage | Local filesystem | Cloud Storage (GCS) |
| Job Execution | Manual `docker-compose run` | Cloud Run Jobs API |
| Authentication | JWT (same) | JWT (same) |
| CORS | localhost:5173 | frontend-xxx.run.app |

### Simulating Cloud Run Jobs Locally

Since Cloud Run Jobs are triggered by Django in production, we need a way to simulate this locally:

**Option 1: Manual Job Execution**
```bash
# Django creates task in database
# Manually run job with task_id
docker-compose run --rm -e TASK_ID=<task-id> job python -m src.main
```

**Option 2: Local Job Queue (Development Only)**

Add a simple job queue for local development:

```python
# backend/apps/choreography/jobs.py (local development)
import subprocess
import os

def create_video_processing_job_local(task_id, user_id, parameters):
    """Local development: Run job in subprocess"""
    env = os.environ.copy()
    env.update({
        'TASK_ID': task_id,
        'USER_ID': str(user_id),
        'AUDIO_INPUT': parameters['audio_input'],
        'DIFFICULTY': parameters['difficulty'],
    })
    
    # Run job in background
    subprocess.Popen(
        ['docker-compose', 'run', '--rm', 'job', 'python', '-m', 'src.main'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
```

**Option 3: Use Celery for Local Development**

If you want a more production-like experience locally, you could use Celery:

```yaml
# Add to docker-compose.yml
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: celery -A api worker -l info
    volumes:
      - ./backend:/app
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
      - db
```

But this adds complexity. For simplicity, **Option 1 (manual execution) is recommended for local development**.

---

## Data Models (Mirroring Original App)

### ChoreographyTask Model

**Original Location:** `choreography/models.py`  
**Backend Location:** `backend/apps/choreography/models.py`  
**Table Name:** `choreography_tasks`

```python
class ChoreographyTask(models.Model):
    """Mirrors original choreography.models.ChoreographyTask"""
    
    STATUS_CHOICES = [
        ('started', 'Started'),      # Match original choices!
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # MUST match original field types exactly
    task_id = models.CharField(max_length=36, primary_key=True)  # CharField, not UUID!
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='choreography_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started', db_index=True)
    progress = models.IntegerField(default=0)
    stage = models.CharField(max_length=50, default='initializing')
    message = models.TextField(default='Starting choreography generation...')
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    job_execution_name = models.CharField(max_length=500, null=True, blank=True)  # NEW for Cloud Run Jobs
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'choreography_tasks'  # MUST match original!
        ordering = ['-created_at']
```

### SavedChoreography Model

**Original Location:** `choreography/models.py`  
**Backend Location:** `backend/apps/collections/models.py`  
**Table Name:** `saved_choreographies`

```python
class SavedChoreography(models.Model):
    """Mirrors original choreography.models.SavedChoreography"""
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    # MUST match original field types exactly
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='choreographies')  # Match original!
    title = models.CharField(max_length=200)
    video_path = models.FileField(upload_to='choreographies/%Y/%m/', max_length=500)  # FileField, not CharField!
    thumbnail_path = models.ImageField(upload_to='thumbnails/%Y/%m/', null=True, blank=True, max_length=500)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, db_index=True)
    duration = models.FloatField(help_text="Duration in seconds")
    music_info = models.JSONField(null=True, blank=True)
    generation_parameters = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'saved_choreographies'  # MUST match original!
        ordering = ['-created_at']
```

### User Model

**Original Location:** Django's built-in User  
**Backend Location:** `backend/apps/authentication/models.py`  
**Table Name:** `auth_user`

```python
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Extends Django's User model"""
    display_name = models.CharField(max_length=200, blank=True)
    is_instructor = models.BooleanField(default=False)
    preferences = models.JSONField(default=dict, blank=True)
    
    # Uses Django's default auth_user table
```

---

## Critical Implementation Rules

### DO
- ✅ Mirror existing models exactly
- ✅ Use same database tables
- ✅ Use same Elasticsearch index
- ✅ Use same GCS bucket
- ✅ Add new nullable fields if needed
- ✅ Test data compatibility thoroughly
- ✅ Use `db_table` to match original table names
- ✅ Use same `related_name` for ForeignKeys
- ✅ Match field types exactly (CharField vs UUID, FileField vs CharField)

### DON'T
- ❌ Change existing field types
- ❌ Rename existing fields
- ❌ Change table names
- ❌ Create new database
- ❌ Regenerate Elasticsearch embeddings
- ❌ Change GCS bucket structure
- ❌ Assume models can be "improved" during migration
- ❌ Use different status choices than original app

---

## Next Steps

1. Review and approve design
2. **Phase 0: Database & Schema Analysis**
   - Document existing database schema
   - Map all models from original to backend
   - Create MODEL_REUSE_STRATEGY.md
3. **Phase 1: Local Development (MUST COMPLETE BEFORE CLOUD)**
   - Set up Docker Compose environment
   - Create project scaffolding (Django, React, Job)
   - Implement Backend API - Mirror models exactly
   - Implement React Frontend
   - Implement Video Processing Job
   - Test complete system locally
   - Verify all features work locally
4. **Phase 2: Cloud Deployment (ONLY AFTER LOCAL WORKS)**
   - Set up GCP infrastructure (Cloud Run, Cloud Run Jobs)
   - Deploy Backend API to Cloud Run
   - Deploy React Frontend to Cloud Run
   - Deploy Video Processing Job to Cloud Run Jobs
   - Test complete system in cloud
5. **Phase 3: Migration**
   - Test data compatibility with original app
   - Parallel operation testing
   - Clean cut migration (all traffic at once)
   - Monitor for 1-2 weeks
   - Delete original app after verification
