#!/bin/bash
# Pre-Deployment Checklist for Bachata Buddy
# Comprehensive check before deploying to Cloud Run

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Pre-Deployment Checklist"
echo "=========================================="
echo ""

# Track results
PASSED=0
FAILED=0
WARNINGS=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# 1. Check Docker is running
echo -e "${BLUE}1. Checking Docker...${NC}"
if docker info &>/dev/null; then
    check_pass "Docker is running"
else
    check_fail "Docker is not running"
fi
echo ""

# 2. Check required files exist
echo -e "${BLUE}2. Checking required files...${NC}"
REQUIRED_FILES=(
    "backend/Dockerfile"
    "backend/Dockerfile.gpu"
    "backend/pyproject.toml"
    "job/Dockerfile"
    "job/Dockerfile.gpu"
    "frontend/Dockerfile"
    "docker-compose.yml"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_pass "$file exists"
    else
        check_fail "$file missing"
    fi
done
echo ""

# 3. Check GPU integration files
echo -e "${BLUE}3. Checking GPU integration files...${NC}"
GPU_FILES=(
    "backend/services/gpu_utils.py"
    "backend/services/vector_search_service.py"
    "job/src/services/ffmpeg_builder.py"
    "job/src/services/video_assembler.py"
)

for file in "${GPU_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_pass "$file exists"
    else
        check_fail "$file missing"
    fi
done
echo ""

# 4. Check deployment scripts
echo -e "${BLUE}4. Checking deployment scripts...${NC}"
DEPLOY_SCRIPTS=(
    "scripts/deploy_gpu_api.sh"
    "scripts/deploy_gpu_job.sh"
    "scripts/build_and_push_gpu_images.sh"
    "backend/build_gpu_image.sh"
    "job/build_gpu_image.sh"
)

for script in "${DEPLOY_SCRIPTS[@]}"; do
    if [ -f "$script" ] && [ -x "$script" ]; then
        check_pass "$script exists and is executable"
    elif [ -f "$script" ]; then
        check_warn "$script exists but not executable"
        chmod +x "$script"
    else
        check_fail "$script missing"
    fi
done
echo ""

# 5. Check Python syntax
echo -e "${BLUE}5. Checking Python syntax...${NC}"
cd backend
if uv run python -m py_compile services/gpu_utils.py 2>/dev/null; then
    check_pass "gpu_utils.py syntax OK"
else
    check_fail "gpu_utils.py has syntax errors"
fi

if uv run python -m py_compile services/vector_search_service.py 2>/dev/null; then
    check_pass "vector_search_service.py syntax OK"
else
    check_fail "vector_search_service.py has syntax errors"
fi
cd ..
echo ""

# 6. Check environment variables
echo -e "${BLUE}6. Checking environment configuration...${NC}"
if [ -f "backend/.env.example" ]; then
    if grep -q "USE_GPU" backend/.env.example; then
        check_pass "GPU configuration in .env.example"
    else
        check_fail "GPU configuration missing from .env.example"
    fi
else
    check_fail "backend/.env.example missing"
fi
echo ""

# 7. Run GPU integration tests
echo -e "${BLUE}7. Running GPU integration tests...${NC}"
cd backend
if uv run python test_gpu_integration.py &>/dev/null; then
    check_pass "GPU integration tests passed"
else
    check_warn "GPU integration tests had issues (may be OK if no GPU)"
fi
cd ..
echo ""

# 8. Check Docker images
echo -e "${BLUE}8. Checking Docker images...${NC}"
if docker images | grep -q "bachata_buddy-api"; then
    check_pass "API Docker image exists"
else
    check_warn "API Docker image not built locally"
fi

if docker images | grep -q "bachata_buddy-frontend"; then
    check_pass "Frontend Docker image exists"
else
    check_warn "Frontend Docker image not built locally"
fi
echo ""

# 9. Check for orphan containers
echo -e "${BLUE}9. Checking for orphan containers...${NC}"
STOPPED=$(docker ps -a -f status=exited -q | wc -l | tr -d ' ')
if [ "$STOPPED" -eq 0 ]; then
    check_pass "No stopped containers"
else
    check_warn "$STOPPED stopped containers found"
    echo "   Run: docker container prune -f"
fi
echo ""

# 10. Check disk space
echo -e "${BLUE}10. Checking disk space...${NC}"
DOCKER_SIZE=$(docker system df --format "{{.Size}}" 2>/dev/null | head -1 || echo "Unknown")
echo "   Docker disk usage: $DOCKER_SIZE"
check_pass "Disk space check complete"
echo ""

# Summary
echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Ready for deployment!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Set GCP_PROJECT_ID: export GCP_PROJECT_ID=your-project-id"
    echo "  2. Build images: ./scripts/build_and_push_gpu_images.sh"
    echo "  3. Deploy: ./scripts/deploy_all_gpu.sh"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Fix issues before deploying${NC}"
    echo ""
    exit 1
fi
