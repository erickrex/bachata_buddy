#!/bin/bash

# Test Service Account Permissions
# This script verifies that service accounts have the correct permissions
#
# Usage:
#   ./test_service_account_permissions.sh <project-id> [region]
#
# Example:
#   ./test_service_account_permissions.sh my-project-id us-central1

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

if [ -z "$1" ]; then
    print_error "Usage: $0 <project-id> [region]"
    exit 1
fi

PROJECT_ID="$1"
REGION="${2:-us-central1}"

API_SERVICE_ACCOUNT="bachata-api-sa@${PROJECT_ID}.iam.gserviceaccount.com"
JOB_SERVICE_ACCOUNT="bachata-job-sa@${PROJECT_ID}.iam.gserviceaccount.com"

print_info "Testing service account permissions for project: $PROJECT_ID"
echo ""

# Function to check if a role is assigned
check_role() {
    local service_account=$1
    local role=$2
    local description=$3
    
    if gcloud projects get-iam-policy "$PROJECT_ID" \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:${service_account} AND bindings.role:${role}" \
        --format="value(bindings.role)" | grep -q "$role"; then
        print_success "$description"
        return 0
    else
        print_error "$description"
        return 1
    fi
}

# Test API Service Account
print_info "=== Testing API Service Account (${API_SERVICE_ACCOUNT}) ==="
echo ""

api_errors=0

check_role "$API_SERVICE_ACCOUNT" "roles/run.developer" "Cloud Run Jobs - Create and manage executions" || ((api_errors++))
check_role "$API_SERVICE_ACCOUNT" "roles/cloudsql.client" "Cloud SQL - Connect via Unix socket" || ((api_errors++))
check_role "$API_SERVICE_ACCOUNT" "roles/storage.objectAdmin" "Cloud Storage - Read/write objects" || ((api_errors++))
check_role "$API_SERVICE_ACCOUNT" "roles/secretmanager.secretAccessor" "Secret Manager - Read secrets" || ((api_errors++))

echo ""

# Test Job Service Account
print_info "=== Testing Job Service Account (${JOB_SERVICE_ACCOUNT}) ==="
echo ""

job_errors=0

check_role "$JOB_SERVICE_ACCOUNT" "roles/cloudsql.client" "Cloud SQL - Connect via Unix socket" || ((job_errors++))
check_role "$JOB_SERVICE_ACCOUNT" "roles/storage.objectAdmin" "Cloud Storage - Read/write objects" || ((job_errors++))
check_role "$JOB_SERVICE_ACCOUNT" "roles/secretmanager.secretAccessor" "Secret Manager - Read secrets" || ((job_errors++))

echo ""

# Test Cloud Build Service Account
CLOUDBUILD_SERVICE_ACCOUNT="${PROJECT_ID}@cloudbuild.gserviceaccount.com"
print_info "=== Testing Cloud Build Service Account (${CLOUDBUILD_SERVICE_ACCOUNT}) ==="
echo ""

build_errors=0

check_role "$CLOUDBUILD_SERVICE_ACCOUNT" "roles/run.admin" "Cloud Run - Deploy services" || ((build_errors++))
check_role "$CLOUDBUILD_SERVICE_ACCOUNT" "roles/iam.serviceAccountUser" "IAM - Assign service accounts" || ((build_errors++))
check_role "$CLOUDBUILD_SERVICE_ACCOUNT" "roles/cloudsql.client" "Cloud SQL - Connect for migrations" || ((build_errors++))
check_role "$CLOUDBUILD_SERVICE_ACCOUNT" "roles/secretmanager.secretAccessor" "Secret Manager - Read secrets" || ((build_errors++))

echo ""

# Summary
print_info "=== Test Summary ==="
echo ""

total_errors=$((api_errors + job_errors + build_errors))

if [ $api_errors -eq 0 ]; then
    print_success "API Service Account: All permissions configured correctly"
else
    print_error "API Service Account: $api_errors permission(s) missing"
fi

if [ $job_errors -eq 0 ]; then
    print_success "Job Service Account: All permissions configured correctly"
else
    print_error "Job Service Account: $job_errors permission(s) missing"
fi

if [ $build_errors -eq 0 ]; then
    print_success "Cloud Build Service Account: All permissions configured correctly"
else
    print_error "Cloud Build Service Account: $build_errors permission(s) missing"
fi

echo ""

if [ $total_errors -eq 0 ]; then
    print_success "All service account permissions are configured correctly!"
    echo ""
    print_info "You can now proceed with deployment:"
    echo "  1. Deploy API: gcloud run deploy bachata-api --service-account=${API_SERVICE_ACCOUNT}"
    echo "  2. Create Job: gcloud run jobs create video-processor --service-account=${JOB_SERVICE_ACCOUNT}"
    exit 0
else
    print_error "Found $total_errors permission issue(s). Please run setup_service_account_permissions.sh"
    exit 1
fi
