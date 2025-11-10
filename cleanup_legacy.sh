#!/bin/bash
# =============================================================================
# BACHATA BUDDY - LEGACY APP CLEANUP SCRIPT
# =============================================================================
# This script removes the legacy monolithic Django app and preserves the
# new microservices architecture (backend/, frontend/, job/)
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "==================================================================="
echo "  BACHATA BUDDY - LEGACY APP CLEANUP"
echo "==================================================================="
echo ""
echo "This script will delete the legacy monolithic Django app."
echo ""
echo -e "${GREEN}PRESERVED:${NC}"
echo "  ✅ backend/     - Django REST API microservice"
echo "  ✅ frontend/    - React frontend"
echo "  ✅ job/         - Video processing container"
echo "  ✅ data/        - Shared data directory"
echo "  ✅ scripts/     - Deployment scripts"
echo "  ✅ .git/        - Git repository"
echo ""
echo -e "${RED}TO BE DELETED:${NC}"
echo "  ❌ bachata_buddy/        - Legacy Django project"
echo "  ❌ ai_services/          - Legacy app"
echo "  ❌ choreography/         - Legacy app"
echo "  ❌ common/               - Legacy app"
echo "  ❌ core/                 - Legacy app"
echo "  ❌ instructors/          - Legacy app"
echo "  ❌ user_collections/     - Legacy app"
echo "  ❌ users/                - Legacy app"
echo "  ❌ video_processing/     - Legacy app"
echo "  ❌ templates/            - Legacy templates"
echo "  ❌ static/               - Legacy static files"
echo "  ❌ staticfiles/          - Legacy collected static"
echo "  ❌ tests/                - Legacy tests"
echo "  ❌ output/               - Legacy output"
echo "  ❌ temp/                 - Legacy temp"
echo "  ❌ test_output/          - Legacy test output"
echo "  ❌ docs/                 - Empty folder"
echo "  ❌ manage.py             - Legacy manage script"
echo "  ❌ Dockerfile            - Legacy Dockerfile"
echo "  ❌ Dockerfile.dev        - Legacy dev Dockerfile"
echo "  ❌ pyproject.toml        - Legacy dependencies"
echo "  ❌ uv.lock               - Legacy lock file"
echo "  ❌ pytest.ini            - Legacy pytest config"
echo "  ❌ health_check.py       - Legacy health check"
echo "  ❌ yolov8n-pose.pt       - Duplicate model file"
echo ""
echo "==================================================================="
echo ""
read -p "Are you sure you want to continue? Type 'yes' to proceed: " confirm

if [ "$confirm" != "yes" ]; then
    echo ""
    echo -e "${YELLOW}Cleanup cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Starting cleanup...${NC}"
echo ""

# Function to safely delete with confirmation
safe_delete() {
    local path=$1
    local type=$2
    
    if [ -e "$path" ]; then
        echo -e "${YELLOW}Deleting $type:${NC} $path"
        rm -rf "$path"
        echo -e "${GREEN}✓${NC} Deleted"
    else
        echo -e "${BLUE}ℹ${NC} Not found (already deleted): $path"
    fi
}

# Delete legacy Django project
echo ""
echo "==================================================================="
echo "1. Deleting Legacy Django Project"
echo "==================================================================="
safe_delete "bachata_buddy" "folder"

# Delete legacy apps
echo ""
echo "==================================================================="
echo "2. Deleting Legacy Django Apps"
echo "==================================================================="
safe_delete "ai_services" "folder"
safe_delete "choreography" "folder"
safe_delete "common" "folder"
safe_delete "core" "folder"
safe_delete "instructors" "folder"
safe_delete "user_collections" "folder"
safe_delete "users" "folder"
safe_delete "video_processing" "folder"

# Delete legacy templates/static
echo ""
echo "==================================================================="
echo "3. Deleting Legacy Templates and Static Files"
echo "==================================================================="
safe_delete "templates" "folder"
safe_delete "static" "folder"
safe_delete "staticfiles" "folder"

# Delete legacy tests
echo ""
echo "==================================================================="
echo "4. Deleting Legacy Tests"
echo "==================================================================="
safe_delete "tests" "folder"

# Delete legacy output directories
echo ""
echo "==================================================================="
echo "5. Deleting Legacy Output Directories"
echo "==================================================================="
safe_delete "output" "folder"
safe_delete "temp" "folder"
safe_delete "test_output" "folder"

# Delete empty docs
echo ""
echo "==================================================================="
echo "6. Deleting Empty Docs Folder"
echo "==================================================================="
safe_delete "docs" "folder"

# Delete legacy root files
echo ""
echo "==================================================================="
echo "7. Deleting Legacy Root Files"
echo "==================================================================="
safe_delete "manage.py" "file"
safe_delete "Dockerfile" "file"
safe_delete "Dockerfile.dev" "file"
safe_delete "pyproject.toml" "file"
safe_delete "uv.lock" "file"
safe_delete "pytest.ini" "file"
safe_delete "health_check.py" "file"
safe_delete "yolov8n-pose.pt" "file"

# Summary
echo ""
echo "==================================================================="
echo "  CLEANUP COMPLETE"
echo "==================================================================="
echo ""
echo -e "${GREEN}Successfully deleted:${NC}"
echo "  ✓ Legacy Django project (bachata_buddy/)"
echo "  ✓ Legacy Django apps (8 folders)"
echo "  ✓ Legacy templates and static files"
echo "  ✓ Legacy tests"
echo "  ✓ Legacy output directories"
echo "  ✓ Legacy root files"
echo ""
echo -e "${GREEN}Preserved:${NC}"
echo "  ✅ backend/     - Django REST API microservice"
echo "  ✅ frontend/    - React frontend"
echo "  ✅ job/         - Video processing container"
echo "  ✅ data/        - Shared data directory"
echo "  ✅ scripts/     - Deployment scripts"
echo "  ✅ .git/        - Git repository"
echo ""
echo "==================================================================="
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Verify remaining structure:"
echo "   ls -la"
echo ""
echo "2. Update docker-compose.yml to remove 'web' service"
echo ""
echo "3. Test the new architecture:"
echo "   docker-compose up -d db api"
echo "   ./run_complete_pipeline.sh"
echo ""
echo "4. Commit changes:"
echo "   git add -A"
echo "   git commit -m 'Remove legacy monolithic Django app'"
echo ""
echo "==================================================================="
echo ""
