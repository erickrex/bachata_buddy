#!/bin/bash
# Verify deployment configuration for blueprint-based architecture
# This script checks that all deployment configurations are correct

set -e

echo "🔍 Verifying Deployment Configuration"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    fail "No GCP project configured"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi
pass "GCP project configured: $PROJECT_ID"

REGION=${REGION:-us-central1}
JOB_NAME=${JOB_NAME:-video-processor}

echo ""
echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Job Name: $JOB_NAME"
echo ""

# Check 1: Cloud Run Job exists
echo "1. Checking Cloud Run Job..."
if gcloud run jobs describe $JOB_NAME --region $REGION &>/dev/null; then
    pass "Cloud Run Job exists: $JOB_NAME"
else
    fail "Cloud Run Job not found: $JOB_NAME"
    echo "   Deploy with: ./scripts/deploy_job_to_cloud_run.sh"
fi

# Check 2: Resource limits
echo ""
echo "2. Checking resource limits..."
MEMORY=$(gcloud run jobs describe $JOB_NAME --region $REGION --format="value(template.template.containers[0].resources.limits.memory)" 2>/dev/null || echo "")
CPU=$(gcloud run jobs describe $JOB_NAME --region $REGION --format="value(template.template.containers[0].resources.limits.cpu)" 2>/dev/null || echo "")
TIMEOUT=$(gcloud run jobs describe $JOB_NAME --region $REGION --format="value(template.template.taskCount.timeout)" 2>/dev/null || echo "")

if [ "$MEMORY" = "512Mi" ] || [ "$MEMORY" = "536870912" ]; then
    pass "Memory limit correct: 512Mi"
elif [ -n "$MEMORY" ]; then
    warn "Memory limit is $MEMORY (expected 512Mi)"
    echo "   Update with: gcloud run jobs update $JOB_NAME --region $REGION --memory 512Mi"
else
    fail "Could not determine memory limit"
fi

if [ "$CPU" = "1" ] || [ "$CPU" = "1000m" ]; then
    pass "CPU limit correct: 1"
elif [ -n "$CPU" ]; then
    warn "CPU limit is $CPU (expected 1)"
    echo "   Update with: gcloud run jobs update $JOB_NAME --region $REGION --cpu 1"
else
    fail "Could not determine CPU limit"
fi

if [ "$TIMEOUT" = "300s" ]; then
    pass "Timeout correct: 300s (5 minutes)"
elif [ -n "$TIMEOUT" ]; then
    warn "Timeout is $TIMEOUT (expected 300s)"
    echo "   Update with: gcloud run jobs update $JOB_NAME --region $REGION --task-timeout 300s"
else
    fail "Could not determine timeout"
fi

# Check 3: Environment variables
echo ""
echo "3. Checking environment variables..."
ENV_VARS=$(gcloud run jobs describe $JOB_NAME --region $REGION --format="value(template.template.containers[0].env)" 2>/dev/null || echo "")

# Check for removed Elasticsearch variables
if echo "$ENV_VARS" | grep -q "ELASTICSEARCH"; then
    fail "Elasticsearch variables still present (should be removed)"
    echo "   Remove with: gcloud run jobs update $JOB_NAME --region $REGION --clear-env-vars ELASTICSEARCH_HOST,ELASTICSEARCH_PORT,ELASTICSEARCH_API_KEY,ELASTICSEARCH_INDEX"
else
    pass "Elasticsearch variables removed"
fi

# Check for required variables
if echo "$ENV_VARS" | grep -q "ENVIRONMENT"; then
    pass "ENVIRONMENT variable present"
else
    warn "ENVIRONMENT variable not set"
fi

if echo "$ENV_VARS" | grep -q "GCP_PROJECT_ID"; then
    pass "GCP_PROJECT_ID variable present"
else
    warn "GCP_PROJECT_ID variable not set"
fi

# Check 4: Service account
echo ""
echo "4. Checking service account..."
SERVICE_ACCOUNT=$(gcloud run jobs describe $JOB_NAME --region $REGION --format="value(template.template.serviceAccount)" 2>/dev/null || echo "")

if [ -n "$SERVICE_ACCOUNT" ]; then
    pass "Service account configured: $SERVICE_ACCOUNT"
    
    # Check service account permissions
    echo "   Checking permissions..."
    
    # Cloud SQL Client
    if gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:$SERVICE_ACCOUNT AND bindings.role:roles/cloudsql.client" --format="value(bindings.role)" | grep -q "cloudsql.client"; then
        pass "   - Cloud SQL Client role granted"
    else
        warn "   - Cloud SQL Client role missing"
    fi
    
    # Storage Object Viewer
    if gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:$SERVICE_ACCOUNT AND bindings.role:roles/storage.objectViewer" --format="value(bindings.role)" | grep -q "storage.objectViewer"; then
        pass "   - Storage Object Viewer role granted"
    else
        warn "   - Storage Object Viewer role missing"
    fi
    
    # Storage Object Creator
    if gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:$SERVICE_ACCOUNT AND bindings.role:roles/storage.objectCreator" --format="value(bindings.role)" | grep -q "storage.objectCreator"; then
        pass "   - Storage Object Creator role granted"
    else
        warn "   - Storage Object Creator role missing"
    fi
else
    fail "Service account not configured"
fi

# Check 5: Cloud SQL connection
echo ""
echo "5. Checking Cloud SQL connection..."
SQL_INSTANCES=$(gcloud run jobs describe $JOB_NAME --region $REGION --format="value(template.template.volumes[0].cloudSqlInstance.instances)" 2>/dev/null || echo "")

if [ -n "$SQL_INSTANCES" ]; then
    pass "Cloud SQL instance connected: $SQL_INSTANCES"
else
    warn "Cloud SQL instance not connected"
fi

# Check 6: Secrets
echo ""
echo "6. Checking secrets..."
SECRETS=$(gcloud run jobs describe $JOB_NAME --region $REGION --format="value(template.template.containers[0].env)" 2>/dev/null || echo "")

if echo "$SECRETS" | grep -q "DB_PASSWORD"; then
    pass "DB_PASSWORD secret configured"
else
    warn "DB_PASSWORD secret not configured"
fi

# Check for removed Elasticsearch secret
if echo "$SECRETS" | grep -q "ELASTICSEARCH_API_KEY"; then
    fail "ELASTICSEARCH_API_KEY secret still present (should be removed)"
else
    pass "ELASTICSEARCH_API_KEY secret removed"
fi

# Check 7: Container image
echo ""
echo "7. Checking container image..."
IMAGE=$(gcloud run jobs describe $JOB_NAME --region $REGION --format="value(template.template.containers[0].image)" 2>/dev/null || echo "")

if [ -n "$IMAGE" ]; then
    pass "Container image: $IMAGE"
    
    # Check if image exists
    if gcloud container images describe $IMAGE &>/dev/null; then
        pass "   Image exists in Container Registry"
        
        # Get image size
        SIZE=$(gcloud container images describe $IMAGE --format="value(image_summary.fully_qualified_digest)" 2>/dev/null || echo "")
        if [ -n "$SIZE" ]; then
            pass "   Image is accessible"
        fi
    else
        warn "   Image not found in Container Registry"
    fi
else
    fail "Container image not configured"
fi

# Check 8: Backend API configuration
echo ""
echo "8. Checking backend API configuration..."
if gcloud run services describe bachata-buddy --region $REGION &>/dev/null; then
    pass "Backend API service exists"
    
    # Check if API has vector search environment variables
    API_ENV=$(gcloud run services describe bachata-buddy --region $REGION --format="value(spec.template.spec.containers[0].env)" 2>/dev/null || echo "")
    
    if echo "$API_ENV" | grep -q "MOVE_EMBEDDINGS_CACHE_TTL"; then
        pass "   Vector search cache TTL configured"
    else
        warn "   MOVE_EMBEDDINGS_CACHE_TTL not set (optional)"
    fi
    
    if echo "$API_ENV" | grep -q "VECTOR_SEARCH_TOP_K"; then
        pass "   Vector search top K configured"
    else
        warn "   VECTOR_SEARCH_TOP_K not set (optional)"
    fi
else
    warn "Backend API service not found (may not be deployed yet)"
fi

# Summary
echo ""
echo "=" | head -c 80 | tr '\n' '='
echo ""
echo "📊 Summary:"
echo "  Passed: $PASSED"
echo "  Failed: $FAILED"
echo "  Warnings: $WARNINGS"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠ Some optional configurations are missing (see warnings above)${NC}"
    fi
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the errors above.${NC}"
    exit 1
fi
