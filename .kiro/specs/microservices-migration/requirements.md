# Microservices Migration Requirements

**Project:** Bachata Buddy - Microservices Architecture Migration  
**Date:** October 26, 2025  
**Status:** Planning Phase

---

## Executive Summary

Migrate Bachata Buddy from a monolithic Django application to a simplified serverless architecture with:
- **Backend:** Django REST Framework API (Cloud Run)
- **Frontend:** React 18.3.1 SPA (Cloud Run) - **JavaScript ONLY, NO TypeScript**
- **Video Processing:** Cloud Run Jobs (triggered directly by API)
- **Deployment:** Fully serverless on Google Cloud Platform

**Key Simplifications:**
1. **No Pub/Sub** - Django directly creates Cloud Run Jobs via API
2. **No Worker Service** - Cloud Run Jobs are standalone, triggered on-demand
3. **Dumb Frontend** - React only handles UI, Django handles ALL business logic
4. **Direct Database** - Jobs write status directly to Cloud SQL, no message passing
5. **JavaScript Only** - React 18.3.1 with JavaScript, NO TypeScript
6. **No HTMX/Alpine.js** - Complete migration to React
7. **Separate Deployments** - Frontend and backend deploy independently on Cloud Run
8. **⚠️ SHARED DATABASE WITH SCHEMA EVOLUTION** - Backend API uses same Cloud SQL database, starts with existing schema, improves with migrations
9. **⚠️ CLEAN CUT MIGRATION** - Deploy new system, switch DNS all at once, keep original app as reference only (not used for traffic)
10. **⚠️ LOCAL DEVELOPMENT FIRST** - Complete system (Django REST API + React Frontend + Job processing) MUST work locally with Docker Compose before ANY Google Cloud deployment

**Frontend Decision: React 18.3.1 (JavaScript Only)**

This spec uses **React 18.3.1 with JavaScript ONLY (NO TypeScript)** for the frontend, deployed separately from the Django backend on Cloud Run.

**Why React:**
- ✅ Modern, component-based architecture
- ✅ Easier to add mobile apps later (React Native)
- ✅ Large ecosystem and community
- ✅ Component reusability
- ✅ Separate deployment from Django API
- ✅ Better for complex client-side interactions

**Why JavaScript (NOT TypeScript):**
- ✅ Simpler for team to maintain
- ✅ No type compilation step
- ✅ Faster development
- ✅ Less tooling complexity
- ✅ Easier onboarding for new developers

**Architecture:**
```
┌──────────────────────────────────────────────────────────────┐
│  React Frontend (Cloud Run)                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  nginx serving built React app:                        │  │
│  │  • React 18.3.1 (JavaScript only)                      │  │
│  │  • React Router for routing                            │  │
│  │  • Fetch API for HTTP calls                            │  │
│  │  • Tailwind CSS for styling                            │  │
│  │  • Vite for building                                   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           │
                           │ fetch() API calls
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Django REST API (Cloud Run)                                  │
│  • Returns JSON                                               │
│  • Creates Cloud Run Jobs                                     │
│  • Manages authentication (httpOnly cookies)                  │
│  • Handles ALL business logic                                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Current Architecture (Monolithic)

```
┌─────────────────────────────────────────┐
│   Django Monolith (Compute Engine)      │
│  ┌───────────────────────────────────┐  │
│  │ • Django Templates (HTMX/Alpine)  │  │
│  │ • Django Views (Business Logic)   │  │
│  │ • Background Threads (Video Gen)  │  │
│  │ • Static Files (WhiteNoise)       │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Problems:**
- ❌ Tight coupling between frontend and backend
- ❌ Background threads unreliable in Cloud Run
- ❌ Can't scale frontend and backend independently
- ❌ Video processing blocks web requests
- ❌ Difficult to add mobile apps or external integrations
- ❌ Complex deployment with multiple services

---

## Target Architecture (Simplified Serverless)

```
┌──────────────────┐     ┌──────────────────┐
│  React Frontend  │────▶│  Django REST API │
│  (Cloud Run)     │     │  (Cloud Run)     │
│  • SPA           │     │  • JWT Auth      │
│  • React Router  │     │  • CRUD APIs     │
│  • Axios         │     │  • Jobs API      │◀─┐
└──────────────────┘     └────────┬─────────┘  │
                                  │             │
                                  │ Creates     │ Updates
                                  │             │
                                  ▼             │
                         ┌────────────────────┐ │
                         │  Cloud Run Job     │ │
                         │  (Video Processing)│─┘
                         │  • FFmpeg          │
                         │  • Video Gen       │
                         │  • Direct DB Write │
                         └────────┬───────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │   Shared Services         │
                    │  • Cloud SQL              │
                    │  • Elasticsearch          │
                    │  • Cloud Storage          │
                    │  • Secret Manager         │
                    └───────────────────────────┘
```

**Benefits:**
- ✅ **Simpler architecture** - No Pub/Sub, no separate worker service, no message queues
- ✅ **Dumb frontend** - React only handles UI, Django handles ALL logic
- ✅ **Independent scaling** - Frontend and backend scale separately
- ✅ **Reliable async processing** - Cloud Run Jobs with automatic retries
- ✅ **Modern SPA experience** - Fast, responsive UI
- ✅ **Easy to extend** - Add mobile apps, just call Django API
- ✅ **Lower operational complexity** - Fewer moving parts, easier to debug
- ✅ **Reduced cost** - No Pub/Sub fees, no always-running worker, pay-per-job execution
- ✅ **Direct database writes** - Jobs update status directly, no message passing
- ✅ **JavaScript only** - No TypeScript complexity, easier for team to maintain

---

## ⚠️ CRITICAL: Database & Schema Strategy

### Shared Database Requirement

**THE BACKEND API WILL USE THE SAME CLOUD SQL DATABASE AS THE ORIGINAL MONOLITHIC APP.**

This is a **migration**, not a greenfield project. The existing schema serves as our starting point, but we can improve it with migrations.

### Why Shared Database?

1. **Zero Downtime Migration** - Both systems operate simultaneously during cutover
2. **Data Consistency** - No need to sync data between databases
3. **Gradual Migration** - Can migrate features incrementally
4. **Rollback Safety** - Easy to rollback to monolithic app if issues arise
5. **Working System** - Original Django app is working correctly, don't break it
6. **Schema Evolution** - Can improve schema with migrations after initial compatibility

### Schema Strategy (Two-Phase Approach)

**PHASE 1: Initial Compatibility (Start with existing schema)**
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

**Migration Philosophy:**
- Start with compatibility, improve incrementally
- Use Django migrations to transform data safely
- Document all schema changes
- Test migrations on production data copies
- Maintain rollback capability

**Models to Mirror:**

| Original Model | Original Location | Backend Location | Table Name |
|----------------|-------------------|------------------|------------|
| ChoreographyTask | `choreography/models.py` | `backend/apps/choreography/models.py` | `choreography_tasks` |
| SavedChoreography | `choreography/models.py` | `backend/apps/collections/models.py` | `saved_choreographies` |
| User | Django's built-in | `backend/apps/authentication/models.py` | `auth_user` |

**Example - ChoreographyTask (Phase 1: Initial Compatibility):**
```python
# Original: choreography/models.py
class ChoreographyTask(models.Model):
    task_id = models.CharField(max_length=36, primary_key=True)  # CharField storing UUID strings
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='choreography_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    # ... other fields
    
    class Meta:
        db_table = 'choreography_tasks'

# Backend Phase 1: backend/apps/choreography/models.py (Initial - Compatible)
class ChoreographyTask(models.Model):
    """Start with compatibility, improve later with migrations"""
    task_id = models.CharField(max_length=36, primary_key=True)  # Start with same type
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='choreography_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    job_execution_name = models.CharField(max_length=500, null=True)  # NEW field (safe to add)
    # ... other fields match
    
    class Meta:
        db_table = 'choreography_tasks'  # Match original

# Backend Phase 2: After migration (Improved - with data migration)
class ChoreographyTask(models.Model):
    """Improved version after data migration"""
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4)  # Improved to proper UUID
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='choreography_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')  # Better naming
    job_execution_name = models.CharField(max_length=500, null=True)
    # ... other fields
    
    class Meta:
        db_table = 'choreography_tasks'  # MUST match original!
```

**Schema Changes:**

*Phase 1 (Initial Compatibility):*
- ✅ Can add new fields to backend models (e.g., `job_execution_name`)
- ✅ New fields must be nullable or have defaults
- ✅ Original app will ignore new fields (no migration needed there)
- ✅ Can add new indexes and constraints

*Phase 2 (After Migration):*
- ✅ Can change field types with data migrations (e.g., CharField → UUIDField)
- ✅ Can rename fields with migrations
- ✅ Can normalize schema structure
- ✅ Can add NOT NULL constraints after data cleanup
- ✅ Can improve choice values with data migrations

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

### Migration Approach

**Phase 1: Parallel Operation (Week 4-5)**
1. Original app continues on Compute Engine
2. Backend API deployed to Cloud Run
3. **Both connect to SAME Cloud SQL database**
4. Both can read/write ChoreographyTask and SavedChoreography
5. Both query same Elasticsearch index
6. Both use same GCS bucket

**Phase 2: Gradual Cutover**
1. Route new users to React frontend + Backend API
2. Existing users continue with original app
3. Monitor both systems
4. Verify data consistency

**Phase 3: Complete Migration**
1. All traffic routed to new system
2. Original app decommissioned
3. Backend API becomes primary system

### Testing Requirements

**MUST TEST:**
- ✅ Backend can read data created by original app
- ✅ Original app can read data created by backend
- ✅ No data corruption or conflicts
- ✅ Both systems can run simultaneously
- ✅ Elasticsearch queries return same results
- ✅ Video files accessible from both systems

### Documentation

See `backend/MODEL_REUSE_STRATEGY.md` for detailed implementation guide.

---

## Core Requirements

### 1. Dependency Management (UV and pyproject.toml)

**User Story:** As a developer, I want to use UV for all Python dependency management and execution with separate pyproject.toml files for each service, so that each microservice can be independently managed and deployed with consistent tooling.

#### Acceptance Criteria

1. WHERE THE Backend_API service is deployed, THE System SHALL use a pyproject.toml file located at `backend/pyproject.toml` for dependency management
2. THE Backend_API pyproject.toml SHALL include only dependencies required for the REST API service
3. THE System SHALL use UV as the ONLY package manager for all Python operations including installing dependencies, running Python scripts, and managing virtual environments
4. THE Backend_Dockerfile SHALL install dependencies using UV with the command `uv pip install --system --no-cache .`
5. WHEN developers add new dependencies, THE System SHALL use the command `uv add <package-name>` to update backend/pyproject.toml
6. WHEN developers install dependencies locally, THE System SHALL use the command `uv sync` to install all dependencies from backend/pyproject.toml
7. WHEN developers run Python scripts or Django commands, THE System SHALL use UV to execute them (e.g., `uv run python manage.py migrate`)
8. WHERE THE Video_Processing_Job is deployed, THE System SHALL use the same backend/pyproject.toml file for shared dependencies
9. THE Root_Level pyproject.toml SHALL remain for the legacy monolithic application during migration as reference only
10. WHEN THE migration is complete, THE System SHALL allow removal of the root-level pyproject.toml without affecting the backend service
11. THE Backend pyproject.toml SHALL NOT depend on or reference the root-level pyproject.toml
12. THE Backend service SHALL be independently deployable using only its own pyproject.toml file
13. THE Development documentation SHALL specify UV commands for all Python operations (no pip, no python directly)

**Glossary:**
- **Backend_API**: The Django REST Framework service running on Cloud Run
- **Video_Processing_Job**: The Cloud Run Job that processes videos
- **Backend_Dockerfile**: The Dockerfile used to build the backend API container
- **Root_Level**: The top-level directory of the repository (bachata_buddy/)
- **System**: The complete Bachata Buddy microservices architecture
- **UV**: A fast Python package installer and resolver that replaces pip and manages Python environments
- **uv sync**: UV command to install all dependencies from pyproject.toml (replaces `pip install -r requirements.txt`)
- **uv add**: UV command to add a new dependency to pyproject.toml (replaces `pip install <package>`)
- **uv run**: UV command to run Python scripts with the correct environment (replaces direct `python` command)

---

### 2. Backend API (Django REST Framework)

**Technology Stack:**
- Django 5.2+
- Django REST Framework 3.14+
- djangorestframework-simplejwt for JWT authentication (httpOnly cookies)
- drf-spectacular for OpenAPI documentation
- google-cloud-run (Cloud Run Jobs API client)
- Cloud Run deployment

**Cloud Run Jobs Integration:**

**YES, Cloud Run Jobs are PERFECT for FFmpeg!** Here's why:

1. **Heavy Dependencies Supported** - Cloud Run Jobs run Docker containers, so you can install FFmpeg, C libraries, Python packages, anything you need
2. **Long-Running Tasks** - Jobs can run up to 24 hours (vs 60 min for Cloud Run services)
3. **High Memory/CPU** - Jobs support up to 32GB RAM and 8 CPUs
4. **Triggered On-Demand** - Django creates job executions via API, no always-running worker
5. **Automatic Retries** - Built-in retry logic if job fails
6. **Parallel Execution** - Multiple jobs can run concurrently

**How Django Triggers Cloud Run Jobs:**

```python
from google.cloud import run_v2

# Create job execution
def create_video_processing_job(task_id, user_id, parameters):
    client = run_v2.JobsClient()
    
    # Create job execution with environment variables
    request = run_v2.RunJobRequest(
        name=f"projects/{PROJECT_ID}/locations/{REGION}/jobs/video-processor",
        overrides={
            "container_overrides": [{
                "env": [
                    {"name": "TASK_ID", "value": task_id},
                    {"name": "USER_ID", "value": str(user_id)},
                    {"name": "AUDIO_INPUT", "value": parameters['audio_input']},
                    {"name": "DIFFICULTY", "value": parameters['difficulty']},
                ]
            }]
        }
    )
    
    # This triggers the job immediately
    execution = client.run_job(request=request)
    return execution.name  # Store in database for monitoring
```

**Cloud Run Job Dockerfile (with FFmpeg):**

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
COPY . .

# Run the job
CMD ["python", "main.py"]
```

**Job Monitoring:**

Django doesn't need to actively monitor jobs. The Cloud Run Job writes progress directly to the database:

1. Django creates job execution, stores task_id in database with status='pending'
2. Cloud Run Job starts, reads task_id from environment variable
3. Job updates database directly: `UPDATE tasks SET status='processing', progress=50 WHERE task_id=?`
4. React polls Django: `GET /api/tasks/{task_id}`
5. Django queries database, returns current status
6. When job completes, it updates: `UPDATE tasks SET status='completed', result=? WHERE task_id=?`

**Why This Works Better Than Pub/Sub + Worker:**

| Aspect | Cloud Run Jobs (This Spec) | Pub/Sub + Worker (Old Spec) |
|--------|---------------------------|------------------------------|
| Complexity | ✅ Simple - Django triggers job directly | ❌ Complex - Message queue + subscriber |
| Cost | ✅ Pay per job execution | ❌ Pay for Pub/Sub + always-running worker |
| Scaling | ✅ Automatic - GCP manages | ❌ Manual - Configure worker instances |
| Retries | ✅ Built-in retry logic | ❌ Manual retry implementation |
| Monitoring | ✅ Job writes to DB directly | ❌ Worker polls Pub/Sub, writes to DB |
| FFmpeg Support | ✅ Full Docker container | ✅ Full Docker container |
| Long-Running | ✅ Up to 24 hours | ✅ Up to 24 hours |
| Deployment | ✅ Single job definition | ❌ Separate worker service |

**API Endpoints Required:**


#### Authentication & Users
- `POST /api/auth/register` - User registration (returns JWT tokens)
- `POST /api/auth/login` - Login (returns JWT access + refresh tokens)
- `POST /api/auth/refresh` - Refresh access token using refresh token
- `POST /api/auth/logout` - Logout (client discards tokens)
- `GET /api/auth/me` - Get current user profile (requires JWT in Authorization header)
- `PUT /api/auth/me` - Update user profile (requires JWT in Authorization header)

#### Choreography Generation
- `POST /api/choreography/generate` - Start choreography generation (creates Cloud Run Job, returns task_id)
- `GET /api/choreography/tasks/{task_id}` - Get task status (polls database, returns user-friendly status)
- `GET /api/choreography/tasks` - List user's tasks (paginated, filtered by status)
- `DELETE /api/choreography/tasks/{task_id}` - Cancel task (cancels Cloud Run Job execution, updates DB)
- `POST /api/choreography/parse-query` - Parse natural language query (Gemini AI, returns parameters)

#### Collections
- `GET /api/collections` - List user's saved choreographies
- `GET /api/collections/{id}` - Get choreography details
- `POST /api/collections` - Save choreography
- `PUT /api/collections/{id}` - Update choreography metadata
- `DELETE /api/collections/{id}` - Delete choreography
- `GET /api/collections/stats` - Get collection statistics

#### Search & Discovery
- `GET /api/moves/search` - Search moves (Elasticsearch)
- `POST /api/moves/parse-query` - Parse natural language query (Gemini)

#### Health & Monitoring
- `GET /api/health` - Health check endpoint
- `GET /api/metrics` - API metrics (optional)

**Non-Functional Requirements:**
- JWT authentication via Authorization header: `Bearer <token>`
- Access token lifetime: 60 minutes
- Refresh token lifetime: 7 days
- Tokens stored in React state/localStorage (client-side)
- CORS configuration for React frontend (specific domain)
- Rate limiting (100 requests/minute per user)
- Request/response logging
- OpenAPI documentation at `/api/docs`
- Response time <200ms for CRUD operations
- Response time <500ms for job creation
- Pagination for list endpoints (20 items per page)
- All business logic in Django (React is "dumb")
- Comprehensive error messages for frontend display
- Task status includes user-friendly messages

---

### 2. Video Processing Job (Cloud Run Jobs)

**Technology Stack:**
- Python 3.12+
- FFmpeg for video processing
- Librosa for audio analysis
- YOLOv8 for pose detection
- Google Cloud Run Jobs API client
- Direct Cloud SQL connection

**Job Responsibilities:**
- Receive task parameters via environment variables
- Download audio from YouTube or Cloud Storage
- Analyze music features (tempo, energy, structure)
- Query Elasticsearch for matching moves
- Generate choreography sequence
- Process videos with FFmpeg
- Upload result to Cloud Storage
- Update task status directly in Cloud SQL

**Job Input (Environment Variables):**
```bash
TASK_ID=uuid
USER_ID=123
AUDIO_INPUT=gs://bucket/songs/song.mp3
DIFFICULTY=intermediate
ENERGY_LEVEL=high
STYLE=romantic
```

**Job Output (Database Update):**
- Updates ChoreographyTask record with status, progress, result, or error
- Stores video URL in Cloud Storage path

**Non-Functional Requirements:**
- Process videos in <2 minutes
- Handle 5+ concurrent job executions
- Automatic retry on failure (max 3 attempts via Cloud Run Jobs)
- Graceful error handling
- Progress updates every 10 seconds (written to database)
- Memory limit: 4GB
- CPU: 4 cores
- Timeout: 1 hour

---

### 3. React Frontend (JavaScript Only - "Dumb" SPA)

**Technology Stack:**
- React 18.3.1 (**JavaScript ONLY, NO TypeScript**)
- React Router 6+ for client-side routing
- Native Fetch API (no Axios or other HTTP libraries)
- Tailwind CSS for styling
- Vite for build tooling
- nginx for serving built files
- Cloud Run deployment

**Architecture Philosophy: "Dumb Frontend with Interactivity"**

The React frontend is as simple as possible. Django REST API handles ALL business logic, data processing, and state management. React is ONLY responsible for:
1. Rendering UI components
2. Handling user interactions (clicks, form inputs)
3. Making API calls to Django via fetch()
4. Displaying data received from Django
5. Basic client-side routing

**What Django Handles (NOT React):**
- Authentication logic and session management
- Form validation (server-side)
- Business rules
- Data transformations
- Task status polling coordination
- Error handling and retry logic
- State persistence
- Complex calculations
- All data processing

**What React Handles (Minimal):**
- UI rendering
- Form input capture
- Button clicks
- API calls (fetch)
- Display loading spinners
- Show/hide UI elements
- Client-side routing
- Display data from Django

**Pages Required:**
- `/` - Home page (landing, links to generate)
- `/login` - Login form (POST to Django, redirect on success)
- `/register` - Registration form (POST to Django, redirect on success)
- `/generate` - Choreography generation form (minimal, just inputs)
- `/collections` - List of saved choreographies (fetch from Django, display)
- `/collections/:id` - Single choreography view (fetch from Django, video player)
- `/profile` - User profile form (fetch from Django, POST updates)

**File Structure:**
```
frontend/
├── public/
│   └── index.html           # Single HTML file
├── src/
│   ├── components/
│   │   ├── Button.jsx       # Reusable button
│   │   ├── Input.jsx        # Reusable input
│   │   ├── Spinner.jsx      # Loading spinner
│   │   ├── VideoPlayer.jsx  # HTML5 video wrapper
│   │   └── Toast.jsx        # Simple notification
│   ├── pages/
│   │   ├── Home.jsx         # Landing page
│   │   ├── Login.jsx        # Login form
│   │   ├── Register.jsx     # Registration form
│   │   ├── Generate.jsx     # Generation form
│   │   ├── Collections.jsx  # List view
│   │   ├── CollectionDetail.jsx # Single view
│   │   └── Profile.jsx      # Profile form
│   ├── utils/
│   │   ├── api.js           # Fetch wrapper functions
│   │   └── auth.js          # Check if logged in (read cookie)
│   ├── App.jsx              # Router setup
│   └── main.jsx             # Entry point
├── nginx.conf               # nginx configuration
├── Dockerfile               # Container for Cloud Run
├── package.json             # Dependencies
├── vite.config.js           # Vite configuration
└── tailwind.config.js       # Tailwind configuration
```

**API Integration Pattern (JavaScript with JWT):**
```javascript
// utils/api.js - Simple fetch wrapper with JWT
export async function apiCall(url, options = {}) {
  // Get JWT token from localStorage
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
  });
  
  // Handle 401 Unauthorized (token expired)
  if (response.status === 401) {
    // Try to refresh token
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry original request with new token
      return apiCall(url, options);
    } else {
      // Redirect to login
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

// Refresh access token
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

// Login function
export async function login(username, password) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Login failed');
  }
  
  const data = await response.json();
  
  // Store tokens in localStorage
  localStorage.setItem('access_token', data.access);
  localStorage.setItem('refresh_token', data.refresh);
  localStorage.setItem('user', JSON.stringify(data.user));
  
  return data;
}

// Logout function
export function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  window.location.href = '/login';
}

// Example: Generate choreography
export async function generateChoreography(formData) {
  return apiCall('/api/choreography/generate', {
    method: 'POST',
    body: JSON.stringify(formData),
  });
}

// Example: Poll task status
export async function getTaskStatus(taskId) {
  return apiCall(`/api/tasks/${taskId}`);
}
```

**React Component Example (JavaScript):**
```javascript
// pages/Generate.jsx
import { useState, useEffect } from 'react';
import { generateChoreography, getTaskStatus } from '../utils/api';
import Button from '../components/Button';
import Spinner from '../components/Spinner';
import VideoPlayer from '../components/VideoPlayer';

export default function Generate() {
  const [formData, setFormData] = useState({ song: '', difficulty: 'intermediate' });
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Handle form submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const result = await generateChoreography(formData);
      setTaskId(result.task_id);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };
  
  // Poll task status
  useEffect(() => {
    if (!taskId) return;
    
    const interval = setInterval(async () => {
      try {
        const result = await getTaskStatus(taskId);
        setStatus(result);
        
        if (result.status === 'completed' || result.status === 'failed') {
          clearInterval(interval);
          setLoading(false);
        }
      } catch (err) {
        setError(err.message);
        clearInterval(interval);
        setLoading(false);
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [taskId]);
  
  return (
    <div>
      <h1>Generate Choreography</h1>
      
      {!taskId && (
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={formData.song}
            onChange={(e) => setFormData({ ...formData, song: e.target.value })}
            placeholder="Song name"
          />
          <select
            value={formData.difficulty}
            onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
          <Button type="submit" disabled={loading}>
            {loading ? 'Generating...' : 'Generate'}
          </Button>
        </form>
      )}
      
      {loading && <Spinner />}
      {error && <div className="error">{error}</div>}
      
      {status && (
        <div>
          <div className="progress-bar">
            <div style={{ width: `${status.progress}%` }} />
          </div>
          <p>{status.message}</p>
          
          {status.status === 'completed' && (
            <VideoPlayer src={status.result.video_url} />
          )}
        </div>
      )}
    </div>
  );
}
```

**No State Management Libraries:**
- No Redux, Zustand, or Context API for global state
- Each page fetches its own data from Django
- Use React's built-in `useState` and `useEffect` only
- Django is the source of truth for ALL state

**No Complex Data Fetching:**
- No TanStack Query, SWR, or Apollo
- Simple `fetch()` calls in `useEffect`
- Django handles caching, pagination, filtering

**Authentication Flow:**
```
1. User submits login form
2. React POSTs to /api/auth/login with { username, password }
3. Django validates, returns { access_token, refresh_token, user }
4. React stores tokens in localStorage
5. React redirects to /generate
6. All subsequent requests include: Authorization: Bearer <access_token>
7. Django validates JWT on each request
8. If token expired, React calls /api/auth/refresh with refresh_token
9. If refresh fails, React redirects to /login
```

**Task Polling Flow:**
```
1. User submits generation form
2. React POSTs to /api/choreography/generate
3. Django creates Cloud Run Job, returns { task_id }
4. React starts interval: fetch(`/api/tasks/${task_id}`) every 2s
5. Django queries database, returns { status, progress, message }
6. React updates UI with progress bar
7. When status='completed', React displays video
8. React clears interval
```

**Deployment:**
```dockerfile
# Dockerfile
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

**nginx Configuration:**
```nginx
server {
    listen 8080;
    root /usr/share/nginx/html;
    index index.html;
    
    # Serve React app
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Proxy API calls to Django backend
    location /api/ {
        proxy_pass https://django-api-xxx.run.app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Non-Functional Requirements:**
- Initial load time <2 seconds
- Bundle size <200KB (gzipped)
- Mobile responsive (Tailwind breakpoints)
- Accessibility: semantic HTML, ARIA labels
- SEO: Consider server-side rendering for landing pages (optional)
- No PWA features (keep it simple)
- JavaScript only (NO TypeScript)

---

## Data Models

**⚠️ IMPORTANT: These models MUST mirror the original app's models exactly to work with the same database.**

See original models in:
- `choreography/models.py::ChoreographyTask`
- `choreography/models.py::SavedChoreography`

### ChoreographyTask (Backend Model - Mirrors Original)
```python
# Location: backend/apps/choreography/models.py
# Original: choreography/models.py
class ChoreographyTask(models.Model):
    """Mirrors original choreography.models.ChoreographyTask"""
    
    STATUS_CHOICES = [
        ('started', 'Started'),      # Match original choices!
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
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

### SavedChoreography (Backend Model - Mirrors Original)
```python
# Location: backend/apps/collections/models.py
# Original: choreography/models.py
class SavedChoreography(models.Model):
    """Mirrors original choreography.models.SavedChoreography"""
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
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

### User (Backend Model)
```python
# Location: backend/apps/authentication/models.py
# Note: May need to extend Django's User or create custom model
class User(AbstractUser):
    # Add any custom fields needed
    display_name = models.CharField(max_length=200, blank=True)
    is_instructor = models.BooleanField(default=False)
    preferences = models.JSONField(default=dict, blank=True)
```

---

## API Contracts

### POST /api/choreography/generate

**Request:**
```json
{
  "audio_input": "https://youtube.com/watch?v=xxx",
  "difficulty": "intermediate",
  "energy_level": "high",
  "style": "romantic"
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_execution_name": "projects/PROJECT/locations/REGION/jobs/video-processor/executions/xxx",
  "status": "pending",
  "message": "Choreography generation started",
  "poll_url": "/api/choreography/tasks/550e8400-e29b-41d4-a716-446655440000"
}
```

### GET /api/choreography/tasks/{task_id}

**Response (200 OK):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 65,
  "stage": "generating",
  "message": "Generating choreography video...",
  "result": null,
  "error": null,
  "created_at": "2025-10-26T12:00:00Z",
  "updated_at": "2025-10-26T12:00:45Z"
}
```

**Response (200 OK - Completed):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "stage": "completed",
  "message": "Choreography generated successfully!",
  "result": {
    "video_url": "https://storage.googleapis.com/bucket/output/video.mp4",
    "duration": 180.5,
    "processing_time": 45.2,
    "moves_count": 12
  },
  "error": null,
  "created_at": "2025-10-26T12:00:00Z",
  "updated_at": "2025-10-26T12:01:00Z"
}
```

---

## Migration Strategy

**⚠️ CRITICAL: This is a migration, not a greenfield project. Backend MUST use existing database and schema.**

**⚠️ LOCAL DEVELOPMENT FIRST: Complete system MUST work locally before ANY cloud deployment.**

### Phase 0: Database & Schema Analysis (Before Starting)
1. **Document existing database schema** from original app
2. **Identify all tables** used by original app
3. **Map models** from original to backend structure
4. **Verify Elasticsearch index** structure and embeddings
5. **Document GCS bucket** structure and file paths
6. **Create MODEL_REUSE_STRATEGY.md** with mapping

### Phase 1: Local Development - Backend API (Week 1-2)
1. Create new Django REST Framework project
2. **Mirror existing models** from original app (CRITICAL!)
3. **Verify db_table names** match original
4. Set up Docker Compose with PostgreSQL
5. Implement JWT authentication
6. Create API endpoints for all CRUD operations
7. **Test with local database** (PostgreSQL in Docker)
8. Test with Postman/curl locally
9. **MUST WORK LOCALLY before proceeding**

### Phase 2: Local Development - Video Processing Job (Week 2-3)
1. Extract video processing logic to standalone Python script
2. Implement job entry point (reads from environment variables)
3. Add progress tracking (direct database writes)
4. Add to Docker Compose as separate service
5. Test job execution locally with `docker-compose run job`
6. Test end-to-end: API creates task → manually run job → job updates DB
7. **MUST WORK LOCALLY before proceeding**

### Phase 3: Local Development - React Frontend (Week 3-4)
1. Create React app with Vite
2. Implement authentication flow
3. Build all pages and components
4. Integrate with local API (http://localhost:8000)
5. Add to Docker Compose
6. Test all user flows locally
7. **MUST WORK LOCALLY before proceeding**

### Phase 4: Local Integration Testing (Week 4)
1. **Run complete system locally with Docker Compose**
2. Test end-to-end user flows:
   - User registration and login
   - Choreography generation (API → Job → Database → Frontend)
   - Video playback
   - Collection management
3. **Verify all features work locally**
4. Fix any issues
5. **DO NOT PROCEED TO CLOUD until everything works locally**

### Phase 5: Cloud Deployment - Infrastructure Setup (Week 5)
1. Set up Cloud SQL (connect to existing database)
2. Set up Cloud Run services (API and Frontend)
3. Set up Cloud Run Jobs (video processor)
4. Configure secrets and environment variables
5. Test connectivity between services

### Phase 6: Cloud Deployment - Backend API (Week 5)
1. Deploy Django REST API to Cloud Run
2. **Test database connection** to existing Cloud SQL
3. **Test reading existing data** from original app
4. Test API endpoints in cloud
5. Verify JWT authentication works

### Phase 7: Cloud Deployment - Video Processing Job (Week 5-6)
1. Deploy job to Cloud Run Jobs
2. Test job execution triggered by API
3. Verify job can write to Cloud SQL
4. Test end-to-end flow in cloud

### Phase 8: Cloud Deployment - React Frontend (Week 6)
1. Deploy React app to Cloud Run
2. Configure CORS and API URL
3. Test all user flows in cloud
4. Verify authentication works

### Phase 9: Cutover & Verification (Week 6-7)
1. **Verify new system** works correctly in production
2. **Test all features** thoroughly
3. **CLEAN CUT**: Update DNS to point to new system (all traffic at once)
4. **Monitor closely** for first 24-48 hours
5. **Keep original app running** on Compute Engine (as reference/backup only, no traffic)
6. Verify all features working correctly
7. Monitor for 1-2 weeks
8. Fix any issues that arise

### Phase 10: Cleanup (Week 8+)
1. **Confirm migration success** - all features working, no critical issues
2. **Archive original app codebase** for reference
3. **Delete original Django app** from Compute Engine
4. Keep database (shared, still in use)
5. Update documentation
6. Celebrate! 🎉

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
| Data migration issues | High | Medium | Thorough testing, rollback plan |
| Job execution failures | Medium | Low | Cloud Run Jobs retry logic, monitoring |
| Performance degradation | Medium | Medium | Load testing, monitoring |
| User disruption | High | Low | Parallel deployment, gradual cutover |
| Cost increase | Medium | Low | Pay-per-use jobs, budget alerts |
| **Breaking original app with backend changes** | **Critical** | **Medium** | **Never change existing fields, only add new nullable fields, test original app after backend deployment** |

---

## Rollback Strategy

**Original Django app kept running as backup (no traffic) for quick rollback if needed.**

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

## Next Steps

1. Review and approve requirements
2. Create detailed design document
3. Break down into tasks
4. Estimate effort and timeline
5. Begin Phase 1 implementation
