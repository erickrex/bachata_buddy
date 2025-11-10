#!/bin/bash

# Service Account Permissions Setup for Cloud Run Jobs
# This script configures minimal IAM permissions for the microservices architecture
#
# Architecture:
# - Django REST API (Cloud Run) - Creates and manages Cloud Run Jobs
# - Cloud Run Job (video-processor) - Processes videos, writes to Cloud SQL
# - Both services need specific permissions to access shared resources
#
# Usage:
#   ./setup_service_account_permissions.sh <project-id> [region]
#
# Example:
#   ./setup_service_account_permissions.sh my-project-id us-central1

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if project ID is provided
if [ -z "$1" ]; then
    print_error "Usage: $0 <project-id> [region]"
    print_error "Example: $0 my-project-id us-central1"
    exit 1
fi

PROJECT_ID="$1"
REGION="${2:-us-central1}"

print_info "Setting up service account permissions for project: $PROJECT_ID"
print_info "Region: $REGION"

# Set the project
gcloud config set project "$PROJECT_ID"

# Service account names
API_SERVICE_ACCOUNT="bachata-api-sa"
JOB_SERVICE_ACCOUNT="bachata-job-sa"
CLOUDBUILD_SERVICE_ACCOUNT="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

# Cloud SQL instance
CLOUD_SQL_INSTANCE="bachata-db"

print_info "=== Step 1: Create Service Accounts ==="

# Create API service account
if gcloud iam service-accounts describe "${API_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" &>/dev/null; then
    print_warning "API service account already exists: ${API_SERVICE_ACCOUNT}"
else
    print_info "Creating API service account: ${API_SERVICE_ACCOUNT}"
    gcloud iam service-accounts create "$API_SERVICE_ACCOUNT" \
        --display-name="Bachata Buddy API Service Account" \
        --description="Service account for Django REST API on Cloud Run"
fi

# Create Job service account
if gcloud iam service-accounts describe "${JOB_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" &>/dev/null; then
    print_warning "Job service account already exists: ${JOB_SERVICE_ACCOUNT}"
else
    print_info "Creating Job service account: ${JOB_SERVICE_ACCOUNT}"
    gcloud iam service-accounts create "$JOB_SERVICE_ACCOUNT" \
        --display-name="Bachata Buddy Job Service Account" \
        --description="Service account for video processing Cloud Run Jobs"
fi

print_info "=== Step 2: Configure API Service Account Permissions ==="

# API needs to:
# 1. Create and manage Cloud Run Jobs
# 2. Access Cloud SQL
# 3. Read/write Cloud Storage
# 4. Access Secret Manager
# 5. Access Elasticsearch (via API key, no IAM needed)

print_info "Granting Cloud Run Jobs permissions to API service account..."

# Cloud Run Jobs - Create and manage job executions
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${API_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.developer" \
    --condition=None

print_info "Granting Cloud SQL permissions to API service account..."

# Cloud SQL - Connect via Unix socket
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${API_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client" \
    --condition=None

print_info "Granting Cloud Storage permissions to API service account..."

# Cloud Storage - Read/write for videos and audio files
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${API_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin" \
    --condition=None

print_info "Granting Secret Manager permissions to API service account..."

# Secret Manager - Read secrets (DB password, API keys)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${API_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None

print_info "=== Step 3: Configure Job Service Account Permissions ==="

# Job needs to:
# 1. Access Cloud SQL (write task status)
# 2. Read/write Cloud Storage (download audio, upload videos)
# 3. Access Secret Manager (DB password, API keys)
# 4. Access Elasticsearch (via API key, no IAM needed)

print_info "Granting Cloud SQL permissions to Job service account..."

# Cloud SQL - Connect via Unix socket
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${JOB_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client" \
    --condition=None

print_info "Granting Cloud Storage permissions to Job service account..."

# Cloud Storage - Read/write for videos and audio files
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${JOB_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin" \
    --condition=None

print_info "Granting Secret Manager permissions to Job service account..."

# Secret Manager - Read secrets (DB password, API keys)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${JOB_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None

print_info "=== Step 4: Configure Cloud Build Service Account Permissions ==="

# Cloud Build needs to:
# 1. Deploy to Cloud Run
# 2. Push images to Container Registry
# 3. Access Secret Manager (for migrations)
# 4. Connect to Cloud SQL (for migrations)

print_info "Granting Cloud Run deployment permissions to Cloud Build..."

# Cloud Run - Deploy services
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CLOUDBUILD_SERVICE_ACCOUNT}" \
    --role="roles/run.admin" \
    --condition=None

print_info "Granting IAM permissions to Cloud Build (for service account assignment)..."

# IAM - Assign service accounts to Cloud Run services
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CLOUDBUILD_SERVICE_ACCOUNT}" \
    --role="roles/iam.serviceAccountUser" \
    --condition=None

print_info "Granting Cloud SQL permissions to Cloud Build (for migrations)..."

# Cloud SQL - Connect for migrations
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CLOUDBUILD_SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.client" \
    --condition=None

print_info "Granting Secret Manager permissions to Cloud Build..."

# Secret Manager - Read secrets for migrations
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CLOUDBUILD_SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None

print_info "=== Step 5: Verify Service Accounts ==="

print_info "API Service Account: ${API_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud iam service-accounts describe "${API_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" --format="value(email)"

print_info "Job Service Account: ${JOB_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud iam service-accounts describe "${JOB_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" --format="value(email)"

print_info "=== Step 6: Summary of Permissions ==="

cat << EOF

${GREEN}Service Account Permissions Configured Successfully!${NC}

API Service Account (${API_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com):
  ✓ roles/run.developer          - Create and manage Cloud Run Jobs
  ✓ roles/cloudsql.client         - Connect to Cloud SQL
  ✓ roles/storage.objectAdmin     - Read/write Cloud Storage
  ✓ roles/secretmanager.secretAccessor - Read secrets

Job Service Account (${JOB_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com):
  ✓ roles/cloudsql.client         - Connect to Cloud SQL
  ✓ roles/storage.objectAdmin     - Read/write Cloud Storage
  ✓ roles/secretmanager.secretAccessor - Read secrets

Cloud Build Service Account (${CLOUDBUILD_SERVICE_ACCOUNT}):
  ✓ roles/run.admin               - Deploy Cloud Run services
  ✓ roles/iam.serviceAccountUser  - Assign service accounts
  ✓ roles/cloudsql.client         - Connect to Cloud SQL for migrations
  ✓ roles/secretmanager.secretAccessor - Read secrets for migrations

${YELLOW}Next Steps:${NC}

1. Deploy API to Cloud Run with service account:
   ${GREEN}gcloud run deploy bachata-api \\
     --service-account=${API_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com \\
     --region=${REGION}${NC}

2. Create Cloud Run Job with service account:
   ${GREEN}gcloud run jobs create video-processor \\
     --image=gcr.io/${PROJECT_ID}/video-processor:latest \\
     --service-account=${JOB_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com \\
     --region=${REGION} \\
     --memory=4Gi \\
     --cpu=4 \\
     --max-retries=3 \\
     --task-timeout=3600s${NC}

3. Update cloudbuild.yaml to use service accounts (see documentation)

4. Test the setup:
   ${GREEN}./test_service_account_permissions.sh ${PROJECT_ID}${NC}

EOF

print_info "Setup complete!"
