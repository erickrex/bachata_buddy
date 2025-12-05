# Microservices Migration - Task Breakdown

**Project:** Bachata Buddy - Simplified Serverless Migration  
**Date:** November 2, 2025 (Last Updated)  
**Total Estimated Effort:** 6-8 weeks

**⚠️ CRITICAL REQUIREMENTS:**
1. **LOCAL DEVELOPMENT FIRST** - Complete system MUST work locally before ANY cloud deployment
2. **DATABASE SCHEMA EVOLUTION** - Backend starts with existing schema, can improve with migrations
3. **NO CLOUD DEPLOYMENT** until Phases 0-3 are complete and verified locally
4. **UV PACKAGE MANAGER** - ALL Python operations MUST use UV (NOT pip, NOT direct python commands)
   - Dependencies: `backend/pyproject.toml` (NOT root-level, NOT requirements.txt)
   - Install deps: `cd backend && uv sync`
   - Add deps: `cd backend && uv add <package>`
   - Run Python: `uv run python <script>`
   - Run Django: `uv run python manage.py <command>`
   - Run tests: `uv run pytest`
   - Dockerfiles: MUST include UV installation from `ghcr.io/astral-sh/uv:latest`

---

## Current Status Summary

### Phase 0: Database & Schema Analysis ✅ COMPLETE
- All tasks completed
- Database schema documented
- Model mapping strategy created
- Local development environment set up and tested

### Phase 1: Local Backend API Development 🔄 IN PROGRESS (85% Complete)
- ✅ Project setup complete
- ✅ Models implemented (ChoreographyTask, SavedChoreography, User)
- ✅ JWT authentication complete (register, login, refresh, profile)
- ✅ Choreography Task API complete (generate, get, list, cancel)
- ✅ Collections API complete (CRUD, filtering, search, stats)
- ✅ Cloud Run Jobs Service implemented
- ⏳ OpenAPI documentation - NOT STARTED
- ⏳ Local backend testing - NOT STARTED

### Phase 2: Local Video Processing Job Development ⏳ NOT STARTED
- Basic job structure exists
- Need to implement video processing pipeline
- Need to integrate with database
- Need to extract logic from monolith

### Phase 3: Local React Frontend Development ⏳ NOT STARTED (10% Complete)
- ✅ Basic React app with Vite set up
- ✅ Tailwind CSS configured
- ⏳ Need to implement all pages and components
- ⏳ Need to implement API integration
- ⏳ Need to implement authentication flow

### Phase 4-8: Integration, Cloud Deployment, Migration ⏳ NOT STARTED
- Blocked until Phases 1-3 are complete

---

## Phase 0: Database & Schema Analysis - Week 1 (3-5 days)

### 0.1 Document Existing Database Schema (1 day)

**Tasks:**
- [x] Connect to existing Cloud SQL database (read-only)
- [x] Document all tables used by original app
- [x] Document ChoreographyTask model fields and types
- [x] Document SavedChoreography model fields and types
- [x] Document User model extensions
- [x] Document all ForeignKey relationships and related_names
- [x] Document field choices (status, difficulty, etc.)
- [x] Create schema diagram
- [x] Save documentation to `backend/EXISTING_SCHEMA.md`

**Acceptance Criteria:**
- ✅ All tables documented with exact field types
- ✅ All relationships documented
- ✅ Field choices documented
- ✅ Schema diagram created

_Requirements: Phase 0 from requirements.md, Database & Schema Reuse Strategy from design.md_

---

### 0.2 Create Model Mapping Strategy (4 hours)

**Tasks:**
- [x] Map ChoreographyTask from original to backend location
- [x] Map SavedChoreography from original to backend location
- [x] Identify fields for Phase 1 (initial compatibility)
- [x] Identify potential improvements for Phase 2 (future migrations)
- [x] Document db_table names for each model
- [x] Document related_name for each ForeignKey
- [x] Create `backend/MODEL_REUSE_STRATEGY.md` (if not exists, update if exists)
- [x] Document migration strategy for schema improvements
- [x] Review with team

**Acceptance Criteria:**
- ✅ MODEL_REUSE_STRATEGY.md created/updated
- ✅ All models mapped with Phase 1 compatible field types
- ✅ Phase 2 improvements documented
- ✅ db_table names documented
- ✅ Team reviewed and approved

_Requirements: Database & Schema Strategy from requirements.md and design.md_

---

### 0.3 Set Up Local Development Environment (1 day)

**Tasks:**
- [x] Create docker-compose.yml with PostgreSQL, Elasticsearch, Django API, React Frontend, Job service
- [x] Create Dockerfile.dev for Django API
- [x] Create Dockerfile.dev for React Frontend
- [x] Create Dockerfile for Job service
- [x] Create .env.example file with all required variables
- [x] Set up local PostgreSQL database
- [x] Set up local Elasticsearch container
- [x] Test docker-compose up
- [x] Document local development workflow in `LOCAL_DEVELOPMENT.md`

**Acceptance Criteria:**
- ✅ All services start with docker-compose up
- ✅ Can access Django API at localhost:8000
- ✅ Can access React frontend at localhost:5173
- ✅ PostgreSQL accessible at localhost:5432
- ✅ Elasticsearch accessible at localhost:9200
- ✅ Documentation is clear

_Requirements: Phase 1 from requirements.md, Local Development Setup from design.md_

---

### 0.1 Create Docker Compose Configuration (2 hours)

**Tasks:**
- [x] Create docker-compose.yml with all services
- [x] Create Dockerfile.dev for Django API
- [x] Create Dockerfile.dev for React Frontend
- [x] Create .env.example file
- [x] Test docker-compose up
- [x] Document local development workflow

**Acceptance Criteria:**
- ✅ All services start with docker-compose up
- ✅ Can access Django API at localhost:8000
- ✅ Can access React frontend at localhost:5173
- ✅ Database migrations run successfully
- ✅ Documentation is clear

---

## Phase 1: Local Backend API Development - Week 2-3

**⚠️ CRITICAL: All development in this phase is LOCAL ONLY. No cloud deployment.**

### 1.1 Project Setup (4 hours)

**⚠️ CRITICAL: Use UV for ALL Python dependency management and execution**

**Tasks:**
- [x] Create Django project structure in `backend/` directory
- [x] Create `backend/pyproject.toml` with project dependencies (NOT requirements.txt)
- [x] Install UV package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [x] Install Django REST Framework and dependencies using UV (`cd backend && uv sync`)
- [x] Configure settings for LOCAL development (PostgreSQL in Docker)
- [x] Configure CORS for React frontend (localhost:5173)
- [x] Set up environment variables in `.env.local`
- [x] Create Dockerfile.dev for local API development (MUST include UV installation)
- [x] Test local development environment with docker-compose

**Dependencies Location:** `backend/pyproject.toml` (NOT root-level pyproject.toml)

**Dependencies:**
```toml
[project]
name = "bachata-buddy-api"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = [
    "django>=5.2",
    "djangorestframework>=3.14",
    "djangorestframework-simplejwt>=5.3",
    "drf-spectacular>=0.27",
    "django-cors-headers>=4.3",
    "psycopg2-binary>=2.9",
    "google-cloud-run>=0.10",
    "google-cloud-storage>=2.10",
    "gunicorn>=21.2",
    "python-dotenv>=1.0",
    "elasticsearch>=8.11",
    "google-generativeai>=0.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-django>=4.5.0",
    "pytest-cov>=4.1.0",
]
```

**Dockerfile.dev MUST include UV:**
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

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**UV Commands to Use:**
- Install dependencies: `cd backend && uv sync`
- Add new dependency: `cd backend && uv add <package-name>`
- Run migrations: `uv run python manage.py migrate`
- Run server: `uv run python manage.py runserver`
- Run tests: `uv run pytest`

**Acceptance Criteria:**
- ✅ Django project runs locally with docker-compose
- ✅ UV is installed and working
- ✅ Dependencies managed via `backend/pyproject.toml` (NOT root-level)
- ✅ All Python commands use `uv run python` (NOT direct `python`)
- ✅ Dockerfile.dev includes UV installation
- ✅ Can connect to local PostgreSQL database
- ✅ Environment variables loaded correctly
- ✅ Docker build succeeds
- ✅ No cloud dependencies configured yet

_Requirements: Phase 1 from requirements.md, Dependency Management with UV from design.md_

---

### 1.2 Implement Backend Models - Phase 1 (Initial Compatibility) (6 hours)

**Tasks:**
- [x] Create `backend/apps/choreography/models.py`
- [x] Implement ChoreographyTask model (Phase 1 - Compatible)
  - Use CharField(36) for task_id (start with compatibility)
  - Use status choices: 'started', 'running', 'completed', 'failed'
  - Use related_name='choreography_tasks'
  - Set db_table='choreography_tasks'
  - Add job_execution_name field (nullable, new field)
  - Add TODO comments for Phase 2 improvements (UUIDField migration)
- [x] Create `backend/apps/collections/models.py`
- [x] Implement SavedChoreography model (Phase 1 - Compatible)
  - Use FileField for video_path
  - Use related_name='choreographies'
  - Set db_table='saved_choreographies'
  - Add TODO comments for Phase 2 improvements
- [x] Create `backend/apps/authentication/models.py`
- [x] Extend Django User model if needed
- [x] Run migrations on local database
- [x] Verify table names match original
- [x] Document Phase 2 improvement plan in MODEL_REUSE_STRATEGY.md

**Acceptance Criteria:**
- ✅ ChoreographyTask model compatible with existing data
- ✅ SavedChoreography model compatible with existing data
- ✅ db_table names match original database
- ✅ Field types compatible with existing schema
- ✅ related_name matches original
- ✅ Status choices match original
- ✅ Migrations run successfully on local database
- ✅ Can query existing data structure (if test data available)
- ✅ Phase 2 improvements documented

_Requirements: Database & Schema Strategy from requirements.md and design.md, Data Models section from design.md_

---

### 1.3 JWT Authentication System (6 hours)

**Tasks:**
- [x] Install djangorestframework-simplejwt
- [x] Configure JWT settings (60 min access, 7 days refresh)
- [x] Create User model (extend AbstractUser if needed)
- [x] Create registration endpoint POST /api/auth/register
- [x] Create login endpoint POST /api/auth/login
- [x] Create token refresh endpoint POST /api/auth/refresh
- [x] Create user profile endpoint GET /api/auth/me
- [x] Create update profile endpoint PUT /api/auth/me
- [x] Add password validation
- [x] Write unit tests for auth endpoints

**API Endpoints:**
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
GET  /api/auth/me
PUT  /api/auth/me
```

**Acceptance Criteria:**
- ✅ User can register with email/username/password
- ✅ User can login and receive JWT tokens (access + refresh)
- ✅ Access token expires after 60 minutes
- ✅ Refresh token works for 7 days
- ✅ User can update profile
- ✅ Password validation enforced
- ✅ CORS configured for React frontend (localhost:5173)
- ✅ All tests pass locally

_Requirements: Backend API section from requirements.md_

---

### 1.4 Choreography Task API (5 hours)

**Tasks:**
- [x] Create task serializers (using Phase 1 compatible model)
- [x] Implement POST /api/choreography/generate
  - Create task with status='started' (match original!)
  - Store task in database
  - Return task_id for polling
- [x] Implement GET /api/choreography/tasks/{id}
- [x] Implement GET /api/choreography/tasks (list)
- [x] Implement DELETE /api/choreography/tasks/{id} (cancel)
- [x] Add pagination for task list
- [x] Add filtering by status
- [x] Write unit tests

**Acceptance Criteria:**
- ✅ Can create task with status='started' (matching original)
- ✅ Can query task status
- ✅ Can list user's tasks with pagination
- ✅ Can cancel pending tasks
- ✅ Only user can access their own tasks
- ✅ All tests pass locally

_Requirements: Choreography Generation section from requirements.md_

---

### 1.5 Local Job Simulation (4 hours)

**Tasks:**
- [x] Create mock job execution for local development
- [x] Implement simple task status updater
- [x] Create endpoint to manually trigger "job completion"
- [x] Test task status updates in local database
- [x] Document local job testing workflow

**Acceptance Criteria:**
- ✅ Can simulate job execution locally
- ✅ Task status updates in local database
- ✅ Can test full flow without Cloud Run Jobs
- ✅ Documentation clear for local testing

_Requirements: Local Development section from design.md_

---

### 1.6 Cloud Run Jobs Service (5 hours)

**Tasks:**
- [x] Install google-cloud-run library
- [x] Create CloudRunJobsService class
- [x] Implement create_job_execution() method
- [x] Add error handling and retries
- [x] Configure service account permissions
- [x] Test job creation locally (mock)
- [x] Add logging for job operations
- [x] Write unit tests with mocks

**Service:**
```python
class CloudRunJobsService:
    def create_job_execution(self, task_id, user_id, parameters):
        """Create Cloud Run Job execution"""
        # Returns execution name
        pass
```

**Acceptance Criteria:**
- ✅ Can create job execution via API
- ✅ Job execution name stored in database
- ✅ Error handling for failed job creation
- ✅ Logging for debugging
- ✅ Service account configured with minimal permissions

---

### 1.5 Collections API (5 hours)

**Tasks:**
- [x] Create collection serializers (using Phase 1 compatible model)
- [x] Implement GET /api/collections (list with pagination)
- [x] Implement GET /api/collections/{id}
- [x] Implement POST /api/collections (save)
- [x] Implement PUT /api/collections/{id} (update)
- [x] Implement DELETE /api/collections/{id}
- [x] Implement GET /api/collections/stats
- [x] Add filtering by difficulty
- [x] Add search functionality
- [x] Write unit tests

**Acceptance Criteria:**
- ✅ Can list user's collections with pagination
- ✅ Can save choreography to collection
- ✅ Can update choreography metadata
- ✅ Can delete choreography
- ✅ Can get collection statistics
- ✅ Filtering and search work correctly
- ✅ All tests pass locally

_Requirements: Collections section from requirements.md_

---

### 1.7 OpenAPI Documentation (2 hours)

**Tasks:**
- [x] Install drf-spectacular
- [x] Configure OpenAPI schema generation in settings.py
- [x] Add drf-spectacular URLs to api/urls.py
- [x] Add docstrings to all endpoints with OpenAPI annotations
- [x] Add example requests/responses to serializers
- [x] Test Swagger UI at /api/docs
- [x] Generate OpenAPI spec file

**Acceptance Criteria:**
- ✅ Swagger UI accessible at /api/docs locally
- ✅ All endpoints documented
- ✅ Example requests/responses provided
- ✅ OpenAPI spec file generated

_Requirements: Backend API section from requirements.md_

---

### 1.8 Local Backend Testing (4 hours)

**Tasks:**
- [x] Create comprehensive test script
- [x] Test authentication flow (register, login, refresh, profile)
- [x] Test task creation and status updates
- [x] Test task listing with pagination and filtering
- [x] Test task cancellation
- [x] Test collections CRUD operations
- [x] Test collections filtering and search
- [x] Test error handling (invalid inputs, unauthorized access)
- [x] Test pagination and filtering edge cases
- [x] Fix any issues found
- [x] Document test results

**Acceptance Criteria:**
- ✅ All endpoints work correctly locally
- ✅ Authentication flow works
- ✅ Task management works
- ✅ Collections management works
- ✅ Error handling works
- ✅ No critical bugs
- ✅ Test results documented
- ✅ All 164 tests passing

_Requirements: Phase 1 from requirements.md_

---

## Phase 2: Local Video Processing Job Development - Week 3-4

**⚠️ CRITICAL: All development in this phase is LOCAL ONLY. No cloud deployment.**

### 2.1 Job Project Setup (3 hours)

**⚠️ CRITICAL: Job uses SAME `backend/pyproject.toml` for dependencies, managed with UV**

**Tasks:**
- [x] Create job project structure
- [x] Add video processing dependencies to `backend/pyproject.toml` using UV
  - `cd backend && uv add librosa opencv-python ultralytics`
- [x] Install system dependencies (FFmpeg) in Dockerfile
- [x] Configure environment variables
- [x] Create Dockerfile for job (MUST include UV and use backend/pyproject.toml)
- [ ] Test local development environment with docker-compose
- [x] Set up logging

**Dependencies Location:** `backend/pyproject.toml` (shared with API)

**Additional Dependencies to Add:**
```bash
cd backend
uv add librosa>=0.10.0
uv add opencv-python>=4.8.0
uv add ultralytics>=8.0.0
```

**Job Dockerfile MUST include UV and use backend/pyproject.toml:**
```dockerfile
FROM python:3.12-slim

# Install FFmpeg and system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy backend dependencies (job shares backend/pyproject.toml)
COPY backend/pyproject.toml ./

# Install dependencies using UV
RUN uv pip install --system --no-cache .

# Copy job code
COPY job/src/ ./src/

# Run the job
CMD ["python", "-m", "src.main"]
```

**UV Commands to Use:**
- Add dependencies: `cd backend && uv add <package>`
- Run job locally: `cd backend && uv run python -m job.src.main`
- Test job: `docker-compose run --rm job uv run python -m src.main`

**Acceptance Criteria:**
- ✅ Job project structure created
- ⏳ All dependencies added to `backend/pyproject.toml` using UV
- ⏳ Job Dockerfile includes UV installation
- ⏳ Job uses `backend/pyproject.toml` for dependencies
- ✅ Docker build succeeds
- ⏳ Can run job locally with docker-compose
- ⏳ FFmpeg available in job container

_Requirements: Dependency Management with UV from design.md_

---

### 2.2 Database Integration (3 hours)

**Tasks:**
- [x] Create database connection utility in job/src/services/database.py
- [x] Implement get_db_connection() function
- [x] Implement update_task_status() function
- [x] Use PostgreSQL connection (local) / Cloud SQL Unix socket (production)
- [x] Add connection pooling
- [x] Test database updates from job
- [x] Add error handling and retries

**Acceptance Criteria:**
- ✅ Job can connect to local PostgreSQL database
- ✅ Can update task status using table name 'choreography_tasks'
- ✅ Uses status values matching original ('started', 'running', 'completed', 'failed')
- ✅ Connection pooling works
- ✅ Error handling for DB failures
- ✅ Automatic retry logic implemented with exponential backoff
- ✅ All database operations wrapped with retry decorator

_Requirements: Database & Schema Reuse Strategy from design.md_

---

### 2.3 Extract Video Processing Logic (6 hours)

**Tasks:**
- [x] Create job/src/services/ directory structure
- [x] Extract and adapt video_generator.py from monolith to job/src/services/
- [x] Extract and adapt music_analyzer.py from monolith to job/src/services/
- [x] Extract and adapt pose_detector.py from monolith to job/src/services/
- [x] Create elasticsearch_service.py for job (reuse existing logic)
- [x] Create storage_service.py for GCS operations
- [x] Remove Django dependencies from extracted code
- [x] Update file paths for Cloud Storage
- [x] Update database access (direct SQL instead of Django ORM)
- [x] Test each service independently

**Acceptance Criteria:**
- ✅ All services work without Django
- ✅ Can process videos with FFmpeg
- ✅ Can analyze music with Librosa
- ✅ Can detect poses with YOLOv8
- ✅ Can query Elasticsearch

---

### 2.4 Choreography Pipeline (5 hours)

**Tasks:**
- [ ] Create ChoreoGenerationPipeline class in job/src/pipeline.py
- [x] Implement generate() method with all pipeline steps
- [x] Integrate all services (music, pose, video, elasticsearch, storage)
- [x] Add progress tracking (write to DB after each step)
- [x] Upload results to Cloud Storage
- [x] Update task status in database (completed/failed)
- [x] Add comprehensive error handling for each step
- [x] Test end-to-end pipeline locally

**Pipeline Steps:**
1. Download audio from YouTube or Cloud Storage
2. Analyze music features (tempo, energy, structure)
3. Query Elasticsearch for matching moves
4. Generate choreography sequence
5. Download training videos from GCS
6. Process videos with FFmpeg
7. Upload result to GCS
8. Update task status to completed

**Acceptance Criteria:**
- ✅ Pipeline processes choreography end-to-end
- ✅ Progress updates sent to database after each step
- ✅ Results uploaded to Cloud Storage
- ✅ Task status updated correctly
- ✅ Error handling for all steps

---

### 2.5 Main Entry Point (2 hours)

**Tasks:**
- [x] Create main.py entry point (basic structure exists)
- [x] Update main.py to read all parameters from environment variables
- [x] Call pipeline with parameters
- [x] Handle exceptions and update task status
- [x] Add comprehensive logging
- [x] Test with docker-compose run job

**Acceptance Criteria:**
- ✅ Job reads environment variables (TASK_ID, USER_ID, AUDIO_INPUT, etc.)
- ✅ Job calls pipeline correctly
- ✅ Job updates task status on success/failure with correct status values
- ✅ Job logs all operations with structured logging
- ✅ All exceptions caught and handled gracefully
- ✅ Task status always updated (even on failure)
- ✅ Comprehensive error logging with stack traces
- ✅ Can run job locally with docker-compose run job

_Requirements: Phase 2 from requirements.md_

---

### 2.6 Local Job Testing (3 hours)

**Tasks:**
- [x] Test full flow locally: API creates task → manually run job → job updates database
- [x] Test with different audio inputs
- [x] Test error scenarios
- [x] Test job updates task status correctly
- [x] Monitor performance
- [x] Fix any issues
- [x] Document local testing workflow

**Acceptance Criteria:**
- ✅ Full flow works end-to-end locally
- ✅ Videos generated successfully
- ✅ Task status updates correctly in local database
- ✅ Job uses correct table name and status values
- ✅ Processing completes successfully
- ✅ All issues fixed

_Requirements: Phase 2 from requirements.md_

---

## Phase 3: Local React Frontend Development - Week 4-5

**⚠️ CRITICAL: All development in this phase is LOCAL ONLY. No cloud deployment.**

### 3.1 Project Setup (3 hours)

**Tasks:**
- [x] Create React app with Vite
- [x] Install dependencies (React Router, Tailwind)
- [x] Configure Tailwind CSS
- [ ] Set up project structure (components/, pages/, utils/)
- [x] Create Dockerfile for frontend
- [x] Test local development

**Dependencies:**
```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.20.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "tailwindcss": "^3.3.0",
    "@vitejs/plugin-react": "^4.2.0"
  }
}
```

**Acceptance Criteria:**
- ✅ React app runs locally with docker-compose
- ✅ Tailwind CSS configured
- ✅ Can build for production
- ✅ Docker build succeeds
- ✅ Can access at localhost:5173

_Requirements: Phase 3 from requirements.md_

---

### 3.2 API Utility Functions (4 hours)

**Tasks:**
- [ ] Create src/utils/ directory
- [ ] Create utils/api.js with fetch wrapper
- [ ] Implement JWT token management (localStorage)
- [ ] Implement automatic token refresh on 401
- [ ] Create login() function
- [ ] Create logout() function
- [ ] Create apiCall() function with auth headers
- [ ] Add error handling for network errors and API errors
- [ ] Test API functions with backend

**Acceptance Criteria:**
- ✅ Can make authenticated API calls to localhost:8001
- ✅ JWT tokens stored in localStorage
- ✅ Automatic token refresh works
- ✅ Error handling for 401/403
- ✅ Logout clears tokens

_Requirements: React Frontend section from requirements.md_

---

### 3.3 Authentication UI (5 hours)

**Tasks:**
- [ ] Create src/pages/ directory
- [ ] Create src/components/ directory
- [ ] Create Login.jsx page
- [ ] Create Register.jsx page
- [ ] Create Button.jsx component
- [ ] Create Input.jsx component
- [ ] Implement login flow (call API, store tokens, redirect)
- [ ] Implement registration flow (call API, store tokens, redirect)
- [ ] Add client-side form validation
- [ ] Add error messages display
- [ ] Test authentication flow with backend

**Components:**
- pages/Login.jsx
- pages/Register.jsx
- components/Button.jsx
- components/Input.jsx

**Acceptance Criteria:**
- ✅ User can register locally
- ✅ User can login and receive tokens
- ✅ Tokens stored in localStorage
- ✅ Form validation works
- ✅ Error messages displayed
- ✅ Redirects to /generate after login
- ✅ Works with local API

_Requirements: React Frontend section from requirements.md_

---

### 3.4 Choreography Generation UI (6 hours)

**Tasks:**
- [ ] Create Generate.jsx page
- [ ] Create generation form with inputs (audio_input, difficulty, energy_level, style)
- [ ] Create task status display component
- [ ] Create VideoPlayer.jsx component
- [ ] Create Spinner.jsx component
- [ ] Implement task polling with useEffect (every 2 seconds)
- [ ] Add progress bar showing task progress
- [ ] Add error handling and display
- [ ] Add "Save to Collection" button when complete
- [ ] Test generation flow with backend and mock job

**Components:**
- pages/Generate.jsx
- components/VideoPlayer.jsx
- components/Spinner.jsx

**Acceptance Criteria:**
- ✅ User can submit generation form locally
- ✅ Task status updates in real-time (polling local API)
- ✅ Progress bar shows current stage
- ✅ Video plays when generation completes
- ✅ Error messages displayed clearly
- ✅ Can save to collection
- ✅ Works with local API and job

_Requirements: React Frontend section from requirements.md_

---

### 3.5 Collections UI (5 hours)

**Tasks:**
- [ ] Create Collections.jsx page (list view)
- [ ] Create collection card component for grid display
- [ ] Create CollectionDetail.jsx page (single view)
- [ ] Implement filtering by difficulty dropdown
- [ ] Implement search by title input
- [ ] Implement pagination controls
- [ ] Add delete functionality with confirmation
- [ ] Add edit functionality (update title, etc.)
- [ ] Test collections flow with backend

**Components:**
- pages/Collections.jsx
- pages/CollectionDetail.jsx
- components/CollectionCard.jsx (optional)

**Acceptance Criteria:**
- ✅ User can view collections locally
- ✅ Can filter by difficulty
- ✅ Can search by title
- ✅ Pagination works
- ✅ Can view choreography details
- ✅ Can delete choreography
- ✅ Works with local API

_Requirements: React Frontend section from requirements.md_

---

### 3.6 Common Components (3 hours)

**Tasks:**
- [ ] Create Button.jsx component with variants (primary, secondary, danger)
- [ ] Create Input.jsx component with label and error display
- [ ] Create Spinner.jsx component for loading states
- [ ] Create Toast.jsx notification component (optional)
- [ ] Style all components with Tailwind CSS
- [ ] Make components responsive
- [ ] Add ARIA labels for accessibility
- [ ] Test components in different pages

**Components:**
- components/Button.jsx
- components/Input.jsx
- components/Spinner.jsx
- components/Toast.jsx (optional)

**Acceptance Criteria:**
- ✅ All components styled consistently
- ✅ Components reusable across pages
- ✅ Responsive design
- ✅ Accessible (ARIA labels)

---

### 3.7 Routing & Navigation (2 hours)

**Tasks:**
- [ ] Set up React Router in App.jsx
- [ ] Create all routes with BrowserRouter
- [ ] Create Navigation.jsx component with links
- [ ] Create ProtectedRoute component to check auth
- [ ] Create Home.jsx page (landing page)
- [ ] Create Profile.jsx page
- [ ] Create NotFound.jsx page (404)
- [ ] Add navigation menu with active page highlighting
- [ ] Test navigation and protected routes

**Routes:**
- / - Home
- /login - Login
- /register - Register
- /generate - Generate choreography (protected)
- /collections - Collections (protected)
- /collections/:id - Collection detail (protected)
- /profile - User profile (protected)

**Acceptance Criteria:**
- ✅ All routes work correctly locally
- ✅ Protected routes redirect to login
- ✅ Navigation menu highlights active page
- ✅ 404 page for invalid routes

_Requirements: React Frontend section from requirements.md_

---

### 3.8 Local Frontend Testing (3 hours)

**Tasks:**
- [ ] Test all pages load correctly
- [ ] Test authentication flow (register → login → logout)
- [ ] Test choreography generation flow (form → polling → video display)
- [ ] Test collections management (list → detail → edit → delete)
- [ ] Test mobile responsiveness on different screen sizes
- [ ] Test error handling (network errors, API errors, validation errors)
- [ ] Test navigation and protected routes
- [ ] Fix any issues found
- [ ] Document test results

**Acceptance Criteria:**
- ✅ All pages work correctly locally
- ✅ Authentication flow works
- ✅ Generation flow works
- ✅ Collections management works
- ✅ Mobile responsive
- ✅ Error handling works
- ✅ No critical bugs

_Requirements: Phase 3 from requirements.md_

---

## Phase 4: Local Integration Testing - Week 5-6

**⚠️ CRITICAL: Complete system MUST work locally before proceeding to Phase 5 (Cloud Deployment).**

### 4.1 Complete Local System Testing (1 day)

**Tasks:**
- [ ] Start complete system with docker-compose up
- [ ] Test end-to-end user flow:
  1. User registration
  2. User login
  3. Create choreography task (API)
  4. Manually run job with docker-compose run job
  5. Job updates task status in database
  6. Frontend polls and displays status
  7. Video playback
  8. Save to collection
  9. View collections
- [ ] Test error scenarios
- [ ] Test mobile responsiveness
- [ ] Verify database schema compatible with existing data
- [ ] Fix any issues found
- [ ] Document all test results

**Acceptance Criteria:**
- ✅ Complete end-to-end flow works locally
- ✅ User can register and login
- ✅ Choreography generation works (API → Job → Database → Frontend)
- ✅ Task status updates correctly with correct status values
- ✅ Video playback works
- ✅ Collections management works
- ✅ Error handling works
- ✅ Mobile responsive
- ✅ Database schema matches original
- ✅ NO CRITICAL BUGS

_Requirements: Phase 4 from requirements.md_

---

### 4.2 Local Performance Testing (4 hours)

**Tasks:**
- [ ] Test API performance locally
- [ ] Test job execution time
- [ ] Test database query performance
- [ ] Identify any bottlenecks
- [ ] Optimize if needed
- [ ] Document performance metrics

**Acceptance Criteria:**
- ✅ API response time acceptable
- ✅ Job execution time acceptable
- ✅ Database queries performant
- ✅ No critical bottlenecks
- ✅ Performance metrics documented

---

### 4.3 Local System Documentation (4 hours)

**Tasks:**
- [ ] Document complete local setup process
- [ ] Document testing procedures
- [ ] Document known issues and workarounds
- [ ] Create troubleshooting guide
- [ ] Document database schema mapping
- [ ] Update README with local development instructions

**Acceptance Criteria:**
- ✅ Setup documentation complete
- ✅ Testing procedures documented
- ✅ Known issues documented
- ✅ Troubleshooting guide created
- ✅ Schema mapping documented
- ✅ README updated

---

### 4.4 Go/No-Go Decision for Cloud Deployment (2 hours)

**Tasks:**
- [ ] Review all test results from Phase 4
- [ ] Verify all acceptance criteria met
- [ ] Verify database schema compatible with existing data
- [ ] Verify complete end-to-end flow works locally
- [ ] Team review and sign-off
- [ ] Make GO/NO-GO decision for cloud deployment

**GO Criteria (ALL must be met):**
- ✅ Complete end-to-end flow works locally
- ✅ All acceptance criteria met
- ✅ Database schema compatible with existing data
- ✅ No critical bugs
- ✅ Performance acceptable
- ✅ Team sign-off obtained

**If NO-GO:**
- Fix critical issues
- Re-test
- Repeat Go/No-Go decision

_Requirements: Phase 4 from requirements.md, "DO NOT PROCEED to cloud until everything works locally"_

---

## Phase 5: Cloud Infrastructure Setup - Week 7

**⚠️ ONLY PROCEED IF Phase 4 Go/No-Go decision is GO.**

### 5.1 Cloud SQL Setup (4 hours)

**Tasks:**
- [ ] Verify access to existing Cloud SQL database
- [ ] Configure connection from Cloud Run services
- [ ] Set up Unix socket connection
- [ ] Configure service accounts
- [ ] Test connection from local machine
- [ ] Document connection details

**Acceptance Criteria:**
- ✅ Can connect to existing Cloud SQL database
- ✅ Service accounts configured
- ✅ Connection tested
- ✅ Documentation complete

_Requirements: Phase 2 from requirements.md (Cloud Infrastructure Setup)_

---

### 5.2 Cloud Run Services Setup (4 hours)

**Tasks:**
- [ ] Create Cloud Run service for Django API
- [ ] Create Cloud Run service for React Frontend
- [ ] Configure environment variables
- [ ] Configure secrets in Secret Manager
- [ ] Set up CORS for frontend domain
- [ ] Configure health checks
- [ ] Document service configurations

**Acceptance Criteria:**
- ✅ Cloud Run services created
- ✅ Environment variables configured
- ✅ Secrets configured
- ✅ CORS configured
- ✅ Health checks configured
- ✅ Documentation complete

---

### 5.3 Cloud Run Jobs Setup (4 hours)

**Tasks:**
- [ ] Create Cloud Run Job for video processor
- [ ] Configure environment variables
- [ ] Configure secrets
- [ ] Set up Cloud SQL connection
- [ ] Configure retry policy
- [ ] Test job creation via API
- [ ] Document job configuration

**Acceptance Criteria:**
- ✅ Cloud Run Job created
- ✅ Environment variables configured
- ✅ Secrets configured
- ✅ Cloud SQL connection configured
- ✅ Retry policy configured
- ✅ Documentation complete

---

## Phase 6: Cloud Deployment - Week 7-8

### 6.1 Deploy Backend API to Cloud Run (4 hours)

**Tasks:**
- [ ] Create Dockerfile for production
- [ ] Create cloudbuild.yaml
- [ ] Deploy to Cloud Run
- [ ] Test connection to existing Cloud SQL database
- [ ] Test reading existing data from original app
- [ ] Test API endpoints
- [ ] Monitor logs
- [ ] Fix any issues

**Acceptance Criteria:**
- ✅ API deployed to Cloud Run
- ✅ Can connect to existing Cloud SQL database
- ✅ Can read existing data from original app
- ✅ All endpoints work
- ✅ No critical errors

_Requirements: Phase 3 from requirements.md (Cloud Deployment)_

---

### 6.2 Deploy Video Processing Job to Cloud Run Jobs (4 hours)

**Tasks:**
- [ ] Create Dockerfile for production
- [ ] Create cloudbuild.yaml
- [ ] Deploy to Cloud Run Jobs
- [ ] Test job execution triggered by API
- [ ] Verify job updates database correctly
- [ ] Monitor logs
- [ ] Fix any issues

**Acceptance Criteria:**
- ✅ Job deployed to Cloud Run Jobs
- ✅ API can trigger job executions
- ✅ Job updates database correctly with correct table name and status values
- ✅ Job processes videos successfully
- ✅ No critical errors

---

### 6.3 Deploy React Frontend to Cloud Run (4 hours)

**Tasks:**
- [ ] Create production build
- [ ] Create Dockerfile with nginx
- [ ] Create cloudbuild.yaml
- [ ] Configure environment variables (API URL)
- [ ] Deploy to Cloud Run
- [ ] Test all pages
- [ ] Test authentication flow
- [ ] Fix any issues

**Acceptance Criteria:**
- ✅ Frontend deployed to Cloud Run
- ✅ All pages load correctly
- ✅ Authentication works
- ✅ API calls work
- ✅ No critical errors

---

### 6.4 Cloud Integration Testing (1 day)

**Tasks:**
- [ ] Test complete end-to-end flow in cloud
- [ ] Test user registration and login
- [ ] Test choreography generation (API → Job → Database → Frontend)
- [ ] Test video playback
- [ ] Test collections management
- [ ] Test error handling
- [ ] Monitor performance
- [ ] Fix any issues

**Acceptance Criteria:**
- ✅ Complete end-to-end flow works in cloud
- ✅ All features work correctly
- ✅ Performance acceptable
- ✅ No critical bugs

_Requirements: Phase 3 from requirements.md_

---

## Phase 7: Data Compatibility Testing - Week 8

### 7.1 Test Data Compatibility with Original App (1 day)

**Tasks:**
- [ ] Backend reads data created by original app
- [ ] Original app reads data created by backend
- [ ] Test both systems writing simultaneously
- [ ] Verify no data corruption
- [ ] Verify Elasticsearch queries return same results
- [ ] Verify video files accessible from both systems
- [ ] Document test results

**Acceptance Criteria:**
- ✅ Backend can read original app's data
- ✅ Original app can read backend's data
- ✅ No data corruption from concurrent writes
- ✅ Elasticsearch queries consistent
- ✅ Video files accessible from both
- ✅ Test results documented

_Requirements: Testing Requirements from requirements.md and design.md_

---

### 7.2 Parallel Operation Testing (2 days)

**Tasks:**
- [ ] Run both systems in parallel
- [ ] Route test traffic to new system
- [ ] Monitor both systems
- [ ] Verify data consistency
- [ ] Test rollback procedure
- [ ] Fix any issues
- [ ] Document results

**Acceptance Criteria:**
- ✅ Both systems run in parallel
- ✅ Data consistency maintained
- ✅ Rollback procedure tested
- ✅ No critical issues
- ✅ Results documented

_Requirements: Phase 4 from requirements.md (Parallel Operation)_

---

## Phase 8: Migration Cutover - Week 9

### 8.1 Clean Cut Migration (1 day)

**Tasks:**
- [ ] Final verification of new system
- [ ] Update DNS to point to new system (all traffic at once)
- [ ] Monitor closely for first 24-48 hours
- [ ] Keep original app running (no traffic, backup only)
- [ ] Verify all features working
- [ ] Monitor for issues
- [ ] Fix any critical issues immediately

**Acceptance Criteria:**
- ✅ DNS updated successfully
- ✅ All traffic routed to new system
- ✅ Original app kept as backup
- ✅ All features working
- ✅ No critical issues
- ✅ Monitoring in place

_Requirements: Phase 5 from requirements.md (Complete Migration)_

---

### 8.2 Post-Migration Monitoring (1-2 weeks)

**Tasks:**
- [ ] Monitor system for 1-2 weeks
- [ ] Track performance metrics
- [ ] Track error rates
- [ ] Gather user feedback
- [ ] Fix any issues
- [ ] Document lessons learned

**Acceptance Criteria:**
- ✅ System stable for 1-2 weeks
- ✅ Performance meets SLAs
- ✅ Error rates acceptable
- ✅ No user complaints
- ✅ Issues fixed
- ✅ Lessons learned documented

---

### 8.3 Cleanup (After 1-2 weeks)

**Tasks:**
- [ ] Confirm migration success
- [ ] Archive original app codebase
- [ ] Delete original Django app from Compute Engine
- [ ] Keep database (still in use)
- [ ] Update documentation
- [ ] Celebrate! 🎉

**Acceptance Criteria:**
- ✅ Migration confirmed successful
- ✅ Original app archived
- ✅ Compute Engine instance deleted
- ✅ Database retained
- ✅ Documentation updated

_Requirements: Phase 6 from requirements.md (Cleanup)_

---

## Phase 9: Schema Improvements (OPTIONAL) - After Migration Success

**⚠️ ONLY START AFTER:**
- Migration is successful (1-2 weeks of stable operation)
- Original app is decommissioned
- All users migrated to new system
- No rollback risk

---

### 9.1 Plan Schema Improvements (1 day)

**Tasks:**
- [ ] Review Phase 1 models and identify improvements
- [ ] Prioritize improvements (UUIDField, better field names, constraints)
- [ ] Create migration plan for each improvement
- [ ] Document rollback strategy for each migration
- [ ] Review with team

**Acceptance Criteria:**
- ✅ All improvements documented
- ✅ Migration plan created
- ✅ Rollback strategy documented
- ✅ Team approved

---

### 9.2 Implement Schema Migrations (Variable)

**Example Improvements:**

**Task: Migrate task_id from CharField to UUIDField**
- [ ] Create data migration to convert existing UUIDs
- [ ] Test migration on production data copy
- [ ] Add new uuid_task_id field (nullable)
- [ ] Populate new field with converted values
- [ ] Switch primary key to new field
- [ ] Remove old task_id field
- [ ] Test rollback procedure

**Task: Improve status field choices**
- [ ] Create data migration to update status values
- [ ] Map 'started' → 'pending', 'running' → 'processing'
- [ ] Update model choices
- [ ] Test with existing data

**Task: Add validators and constraints**
- [ ] Add progress validators (0-100)
- [ ] Add NOT NULL constraints where appropriate
- [ ] Add composite indexes for common queries
- [ ] Test performance improvements

**Acceptance Criteria:**
- ✅ Each migration tested on production data copy
- ✅ Rollback tested and verified
- ✅ No data loss
- ✅ Performance maintained or improved
- ✅ All tests passing

_Note: Schema improvements are OPTIONAL and should only be done after migration success_

---

## Summary

**Total Estimated Effort:** 6-8 weeks (+ optional schema improvements)

**Phase 0 (Database & Schema Analysis):** 3-5 days
**Phase 1 (Local Backend API):** 35 hours (~2 weeks)
**Phase 2 (Local Video Processing Job):** 26 hours (~1.5 weeks)
**Phase 3 (Local React Frontend):** 31 hours (~1.5 weeks)
**Phase 4 (Local Integration Testing):** 2-3 days
**Phase 5 (Cloud Infrastructure Setup):** 12 hours (~3 days)
**Phase 6 (Cloud Deployment):** 16 hours (~4 days)
**Phase 7 (Data Compatibility Testing):** 3 days
**Phase 8 (Migration Cutover):** 1-2 weeks
**Phase 9 (Schema Improvements - OPTIONAL):** Variable (after migration success)

**Total:** ~140 hours + monitoring (~6-8 weeks at 20-25 hours/week)
**Optional:** Schema improvements can be done incrementally after successful migration

**Critical Path:**
1. **Phase 0-4 MUST be complete before ANY cloud deployment**
2. Complete system MUST work locally before proceeding to Phase 5
3. Database schema MUST be compatible with existing data
4. Data compatibility MUST be verified before cutover

**Critical Success Factors:**
- ✅ **LOCAL DEVELOPMENT FIRST** - No cloud deployment until local works
- ✅ **DATABASE SCHEMA EVOLUTION** - Start with compatibility, improve with migrations
- ✅ **DATA COMPATIBILITY** - Both systems can read/write same data
- ✅ **CLEAN CUT MIGRATION** - All traffic at once, keep original as backup
- ✅ **ROLLBACK READY** - Can switch DNS back if needed

**Risks:**
- Schema mismatch between apps (CRITICAL)
- Data corruption from concurrent writes (CRITICAL)
- Breaking original app with backend changes (CRITICAL)
- Video processing performance
- User disruption during cutover

**Mitigation:**
- Document original schema first
- Start with compatible models (Phase 1)
- Plan schema improvements for Phase 2
- Test data compatibility thoroughly
- Local development and testing first
- Parallel operation testing
- Rollback plan ready
- Monitoring and alerting in place
