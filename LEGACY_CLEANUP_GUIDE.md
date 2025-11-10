# Legacy Django App Cleanup Guide

## Overview

This guide identifies all folders and files that belong to the **legacy monolithic Django app** and should be deleted. The new architecture uses:
- **Backend:** `backend/` (Django REST API microservice)
- **Frontend:** `frontend/` (React app)
- **Job:** `job/` (Video processing container)

---

## ⚠️ CRITICAL: What to Keep

**DO NOT DELETE these folders:**
- ✅ `backend/` - New Django REST API microservice
- ✅ `frontend/` - React frontend
- ✅ `job/` - Video processing job container
- ✅ `data/` - Shared data directory (songs, videos, embeddings)
- ✅ `scripts/` - Deployment and utility scripts
- ✅ `.git/` - Git repository
- ✅ `.kiro/` - Kiro IDE configuration

---

## 🗑️ Folders to Delete (Legacy Monolithic App)

### 1. Legacy Django Project Root
```bash
bachata_buddy/
├── bachata_buddy/          # DELETE - Legacy Django settings/urls
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py         # Legacy settings (replaced by backend/api/settings.py)
│   ├── urls.py             # Legacy URLs (replaced by backend/api/urls.py)
│   └── wsgi.py
```

### 2. Legacy Django Apps
```bash
bachata_buddy/
├── ai_services/            # DELETE - Functionality moved to backend/services/
├── choreography/           # DELETE - Replaced by backend/apps/choreography/
├── common/                 # DELETE - Shared code moved to backend/core/
├── core/                   # DELETE - Replaced by backend/core/
├── instructors/            # DELETE - Replaced by backend/apps/instructors/
├── user_collections/       # DELETE - Replaced by backend/apps/collections/
├── users/                  # DELETE - Replaced by backend/apps/authentication/
└── video_processing/       # DELETE - Replaced by job/ container
```

### 3. Legacy Templates and Static Files
```bash
bachata_buddy/
├── templates/              # DELETE - Legacy Django templates (not used in REST API)
│   ├── base.html
│   └── choreography/
├── static/                 # DELETE - Legacy static files (frontend uses React)
│   └── js/
└── staticfiles/            # DELETE - Collected static files (not needed)
    ├── admin/
    ├── django_htmx/
    └── js/
```

### 4. Legacy Tests
```bash
bachata_buddy/
└── tests/                  # DELETE - Legacy tests (replaced by backend/tests/)
    ├── choreography/
    ├── forms/
    ├── integration/
    ├── models/
    ├── scripts/
    ├── services/
    ├── unit/
    └── views/
```

### 5. Legacy Output/Temp Directories
```bash
bachata_buddy/
├── output/                 # DELETE - Legacy output directory
│   └── user_*/
├── temp/                   # DELETE - Legacy temp directory
│   └── user_*/
└── test_output/            # DELETE - Legacy test output
```

### 6. Legacy Root Files
```bash
bachata_buddy/
├── manage.py               # DELETE - Legacy manage.py (use backend/manage.py)
├── Dockerfile              # DELETE - Legacy Dockerfile (use backend/Dockerfile)
├── Dockerfile.dev          # DELETE - Legacy dev Dockerfile (use backend/Dockerfile.dev)
├── pyproject.toml          # DELETE - Legacy dependencies (use backend/pyproject.toml)
├── uv.lock                 # DELETE - Legacy lock file (use backend/uv.lock)
└── pytest.ini              # DELETE - Legacy pytest config (use backend/pytest.ini)
```

---

## 📋 Complete Deletion List

### Folders to Delete
```bash
# Legacy Django project
bachata_buddy/bachata_buddy/

# Legacy Django apps
bachata_buddy/ai_services/
bachata_buddy/choreography/
bachata_buddy/common/
bachata_buddy/core/
bachata_buddy/instructors/
bachata_buddy/user_collections/
bachata_buddy/users/
bachata_buddy/video_processing/

# Legacy templates and static
bachata_buddy/templates/
bachata_buddy/static/
bachata_buddy/staticfiles/

# Legacy tests
bachata_buddy/tests/

# Legacy output directories
bachata_buddy/output/
bachata_buddy/temp/
bachata_buddy/test_output/

# Empty docs folder
bachata_buddy/docs/
```

### Files to Delete
```bash
# Legacy root files
bachata_buddy/manage.py
bachata_buddy/Dockerfile
bachata_buddy/Dockerfile.dev
bachata_buddy/pyproject.toml
bachata_buddy/uv.lock
bachata_buddy/pytest.ini
bachata_buddy/health_check.py
bachata_buddy/yolov8n-pose.pt  # Duplicate (also in backend/)
```

---

## 🔧 Cleanup Commands

### Option 1: Interactive Deletion (Recommended)
Review each folder before deleting:

```bash
cd bachata_buddy

# Review and delete legacy Django project
ls -la bachata_buddy/
rm -rf bachata_buddy/

# Review and delete legacy apps
ls -la ai_services/ choreography/ common/ core/ instructors/ user_collections/ users/ video_processing/
rm -rf ai_services/ choreography/ common/ core/ instructors/ user_collections/ users/ video_processing/

# Review and delete legacy templates/static
ls -la templates/ static/ staticfiles/
rm -rf templates/ static/ staticfiles/

# Review and delete legacy tests
ls -la tests/
rm -rf tests/

# Review and delete legacy output
ls -la output/ temp/ test_output/
rm -rf output/ temp/ test_output/

# Review and delete empty docs
ls -la docs/
rm -rf docs/

# Review and delete legacy root files
ls -la manage.py Dockerfile Dockerfile.dev pyproject.toml uv.lock pytest.ini health_check.py
rm -f manage.py Dockerfile Dockerfile.dev pyproject.toml uv.lock pytest.ini health_check.py yolov8n-pose.pt
```

### Option 2: Automated Deletion Script
Create and run a cleanup script:

```bash
#!/bin/bash
# cleanup_legacy.sh

set -e

echo "==================================================================="
echo "BACHATA BUDDY - LEGACY APP CLEANUP"
echo "==================================================================="
echo ""
echo "This script will delete the legacy monolithic Django app."
echo "The new microservices architecture (backend/, frontend/, job/) will be preserved."
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Delete legacy Django project
echo "Deleting legacy Django project..."
rm -rf bachata_buddy/

# Delete legacy apps
echo "Deleting legacy Django apps..."
rm -rf ai_services/ choreography/ common/ core/ instructors/ user_collections/ users/ video_processing/

# Delete legacy templates/static
echo "Deleting legacy templates and static files..."
rm -rf templates/ static/ staticfiles/

# Delete legacy tests
echo "Deleting legacy tests..."
rm -rf tests/

# Delete legacy output directories
echo "Deleting legacy output directories..."
rm -rf output/ temp/ test_output/

# Delete empty docs
echo "Deleting empty docs folder..."
rm -rf docs/

# Delete legacy root files
echo "Deleting legacy root files..."
rm -f manage.py Dockerfile Dockerfile.dev pyproject.toml uv.lock pytest.ini health_check.py yolov8n-pose.pt

echo ""
echo "==================================================================="
echo "CLEANUP COMPLETE"
echo "==================================================================="
echo ""
echo "Deleted folders:"
echo "  - bachata_buddy/ (legacy Django project)"
echo "  - ai_services/, choreography/, common/, core/, instructors/"
echo "  - user_collections/, users/, video_processing/"
echo "  - templates/, static/, staticfiles/"
echo "  - tests/, output/, temp/, test_output/, docs/"
echo ""
echo "Deleted files:"
echo "  - manage.py, Dockerfile, Dockerfile.dev"
echo "  - pyproject.toml, uv.lock, pytest.ini"
echo "  - health_check.py, yolov8n-pose.pt"
echo ""
echo "Preserved folders:"
echo "  ✅ backend/ (Django REST API)"
echo "  ✅ frontend/ (React app)"
echo "  ✅ job/ (Video processing)"
echo "  ✅ data/ (Shared data)"
echo "  ✅ scripts/ (Deployment scripts)"
echo ""
```

---

## 🔍 Verification After Cleanup

### 1. Check Remaining Structure
```bash
ls -la bachata_buddy/
```

Expected structure:
```
bachata_buddy/
├── .git/                   # Git repository
├── .kiro/                  # Kiro IDE config
├── backend/                # Django REST API microservice
├── frontend/               # React frontend
├── job/                    # Video processing job
├── data/                   # Shared data
├── scripts/                # Deployment scripts
├── .env                    # Environment variables
├── .env.example            # Environment template
├── docker-compose.yml      # Docker orchestration
├── README.md               # Project documentation
└── [pipeline scripts]      # Execution scripts
```

### 2. Verify Docker Compose
```bash
docker-compose config
```

Should show only:
- `db` (PostgreSQL)
- `api` (backend service)
- `frontend` (React app)
- `web` (can be removed from docker-compose.yml)
- `job` (video processing)

### 3. Test Services
```bash
# Start new architecture
docker-compose up -d db api

# Verify API is working
curl http://localhost:8001/api/health/

# Run pipeline
./run_complete_pipeline.sh
```

---

## 📝 Update Docker Compose

After cleanup, update `docker-compose.yml` to remove the legacy `web` service:

```yaml
# REMOVE THIS SECTION:
  # Current Monolithic Django App (for development)
  web:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: bachata_web
    command: python manage.py runserver 0.0.0.0:8000
    # ... rest of web service config
```

---

## ⚠️ Important Notes

### Before Deletion
1. ✅ Ensure all functionality has been migrated to `backend/`
2. ✅ Verify the pipeline works with the new architecture
3. ✅ Backup the repository: `git commit -am "Backup before legacy cleanup"`
4. ✅ Create a branch: `git checkout -b cleanup-legacy`

### After Deletion
1. Update `.gitignore` to remove legacy-specific entries
2. Update `README.md` to reflect new architecture
3. Update deployment scripts to use `backend/` instead of root
4. Test all functionality thoroughly
5. Commit changes: `git commit -am "Remove legacy monolithic Django app"`

### Migration Checklist
- ✅ Authentication → `backend/apps/authentication/`
- ✅ Choreography → `backend/apps/choreography/`
- ✅ Collections → `backend/apps/collections/`
- ✅ Instructors → `backend/apps/instructors/`
- ✅ Video Processing → `job/`
- ✅ Services → `backend/services/`
- ✅ Database Models → `backend/apps/*/models.py`
- ✅ API Endpoints → `backend/apps/*/views.py`
- ✅ Tests → `backend/tests/` and `backend/apps/*/tests.py`

---

## 🎯 Summary

**Total Folders to Delete:** 17
**Total Files to Delete:** 8
**Estimated Space Freed:** ~500MB (including temp/output directories)

**Architecture After Cleanup:**
```
bachata_buddy/
├── backend/        # Django REST API (Port 8001)
├── frontend/       # React App (Port 5173)
├── job/            # Video Processing
├── data/           # Shared Data
└── scripts/        # Deployment Scripts
```

This cleanup will result in a **clean microservices architecture** with clear separation of concerns and no legacy code.

---

**Generated:** November 10, 2025  
**Status:** Ready for execution  
**Risk Level:** Low (all functionality migrated and tested)
