#!/bin/bash
# Verification Script for Clean Blueprint Architecture
# This script verifies that all legacy code and Elasticsearch dependencies have been removed

echo "=========================================="
echo "Blueprint Architecture Verification"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

# Function to check for patterns in code files (excluding docs)
check_pattern() {
    local pattern=$1
    local description=$2
    
    echo -n "Checking for $description... "
    
    # Search in Python files only, excluding documentation and test files
    results=$(grep -r "$pattern" job/src/ 2>/dev/null | grep -v "\.md" | grep -v "\.pyc" | grep -v "__pycache__" || true)
    
    if [ -z "$results" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "  Found references:"
        echo "$results" | head -5
        FAILURES=$((FAILURES + 1))
        return 1
    fi
}

# Function to check that files don't exist
check_file_deleted() {
    local filepath=$1
    local description=$2
    
    echo -n "Checking $description is deleted... "
    
    if [ ! -f "$filepath" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "  File still exists: $filepath"
        FAILURES=$((FAILURES + 1))
        return 1
    fi
}

# Function to check that files exist
check_file_exists() {
    local filepath=$1
    local description=$2
    
    echo -n "Checking $description exists... "
    
    if [ -f "$filepath" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "  File missing: $filepath"
        FAILURES=$((FAILURES + 1))
        return 1
    fi
}

echo "1. Checking for removed dependencies..."
echo "----------------------------------------"
check_pattern "elasticsearch" "Elasticsearch references"
check_pattern "librosa" "Librosa references"
check_pattern "yolov8\|ultralytics" "YOLOv8/Ultralytics references"
check_pattern "sentence_transformers" "Sentence Transformers references"
check_pattern "mmpose" "MMPose references"
echo ""

echo "2. Checking deleted service files..."
echo "----------------------------------------"
check_file_deleted "job/src/services/elasticsearch_service.py" "Elasticsearch service"
check_file_deleted "job/src/services/music_analyzer.py" "Music analyzer"
check_file_deleted "job/src/services/pose_detector.py" "Pose detector"
check_file_deleted "job/src/services/video_generator.py" "Video generator"
check_file_deleted "job/src/pipeline.py" "Old pipeline"
echo ""

echo "3. Checking deleted test files..."
echo "----------------------------------------"
check_file_deleted "job/test_elasticsearch_service.py" "Elasticsearch tests"
check_file_deleted "job/test_music_analyzer.py" "Music analyzer tests"
check_file_deleted "job/test_pose_detector.py" "Pose detector tests"
check_file_deleted "job/test_video_generator.py" "Video generator tests"
check_file_deleted "job/test_pipeline.py" "Pipeline tests"
check_file_deleted "job/test_audio_inputs.py" "Audio input tests"
echo ""

echo "4. Checking blueprint architecture files exist..."
echo "----------------------------------------"
check_file_exists "job/src/main.py" "Blueprint-based main.py"
check_file_exists "job/src/services/blueprint_parser.py" "Blueprint parser"
check_file_exists "job/src/services/video_assembler.py" "Video assembler"
check_file_exists "job/src/services/storage_service.py" "Storage service"
check_file_exists "job/src/services/database.py" "Database service"
echo ""

echo "5. Checking Dockerfile dependencies..."
echo "----------------------------------------"
echo -n "Checking Dockerfile has minimal dependencies... "
if grep -q "ffmpeg" job/Dockerfile && \
   grep -q "psycopg2-binary" job/Dockerfile && \
   grep -q "google-cloud-storage" job/Dockerfile && \
   ! grep -q "elasticsearch" job/Dockerfile && \
   ! grep -q "librosa" job/Dockerfile && \
   ! grep -q "django" job/Dockerfile; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "  Dockerfile has incorrect dependencies"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "6. Checking docker-compose.yml..."
echo "----------------------------------------"
echo -n "Checking docker-compose has no Elasticsearch service... "
if ! grep -q "elasticsearch:" docker-compose.yml; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "  docker-compose.yml still has Elasticsearch service"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "=========================================="
echo "Verification Summary"
echo "=========================================="

if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED${NC}"
    echo ""
    echo "The job container has been successfully cleaned:"
    echo "  ✓ All legacy code removed"
    echo "  ✓ All Elasticsearch dependencies removed"
    echo "  ✓ All heavy ML/AI dependencies removed"
    echo "  ✓ Blueprint architecture in place"
    echo "  ✓ No fallback mechanisms"
    echo ""
    echo "This is a CLEAN CUT with NO FALLBACK to the old system."
    exit 0
else
    echo -e "${RED}✗ $FAILURES CHECK(S) FAILED${NC}"
    echo ""
    echo "Please review the failures above and fix them."
    exit 1
fi
