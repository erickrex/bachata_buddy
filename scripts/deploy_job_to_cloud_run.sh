#!/bin/bash
# Deploy Video Processing Job to Cloud Run Jobs
# This script deploys the blueprint-based video processor as a Cloud Run Job

set -e

echo "🚀 Deploying Video Processing Job to Cloud Run Jobs"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No GCP project configured"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# Configuration
REGION=${REGION:-us-central1}
JOB_NAME=${JOB_NAME:-video-processor}
MEMORY=${MEMORY:-512Mi}
CPU=${CPU:-1}
TIMEOUT=${TIMEOUT:-300}
MAX_RETRIES=${MAX_RETRIES:-3}
SERVICE_ACCOUNT=${SERVICE_ACCOUNT:-bachata-job-sa@${PROJECT_ID}.iam.gserviceaccount.com}

echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Job Name: $JOB_NAME"
echo "  Memory: $MEMORY"
echo "  CPU: $CPU"
echo "  Timeout: ${TIMEOUT}s"
echo "  Max Retries: $MAX_RETRIES"
echo "  Service Account: $SERVICE_ACCOUNT"
echo ""

# Ask for confirmation
echo "⚠️  This will deploy the video processing job to Cloud Run Jobs in project: $PROJECT_ID"
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

# Build and push Docker image
echo ""
echo "🐳 Building Docker image..."
cd job
IMAGE_NAME="gcr.io/${PROJECT_ID}/${JOB_NAME}:latest"
docker build -t $IMAGE_NAME -f Dockerfile .

echo ""
echo "📤 Pushing image to Container Registry..."
docker push $IMAGE_NAME

# Deploy Cloud Run Job
echo ""
echo "🚀 Deploying Cloud Run Job..."
gcloud run jobs deploy $JOB_NAME \
    --image $IMAGE_NAME \
    --region $REGION \
    --memory $MEMORY \
    --cpu $CPU \
    --task-timeout ${TIMEOUT}s \
    --max-retries $MAX_RETRIES \
    --service-account $SERVICE_ACCOUNT \
    --set-env-vars="ENVIRONMENT=cloud,GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION}" \
    --set-secrets="DB_PASSWORD=db-password:latest" \
    --set-cloudsql-instances="${PROJECT_ID}:${REGION}:bachata-db"

echo ""
echo "=" | head -c 80 | tr '\n' '='
echo ""
echo "✅ Deployment successful!"
echo ""
echo "📊 View job details:"
echo "  gcloud run jobs describe $JOB_NAME --region $REGION"
echo ""
echo "🔍 View job executions:"
echo "  gcloud run jobs executions list --job $JOB_NAME --region $REGION"
echo ""
echo "📝 Test job execution (manual):"
echo "  gcloud run jobs execute $JOB_NAME --region $REGION"
echo ""
echo "⚠️  IMPORTANT:"
echo "  - Job executions are triggered by the API, not manually"
echo "  - Each execution receives BLUEPRINT_JSON via environment variable"
echo "  - Resource limits: ${MEMORY} memory, ${CPU} CPU, ${TIMEOUT}s timeout"
echo "  - Elasticsearch has been removed from the job container"
echo ""
