#!/bin/bash
# Run Django migrations using the already-deployed Cloud Run image

set -e

echo "🔄 Running Django migrations on Cloud SQL (using deployed image)"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Load .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

export $(cat .env | grep -v '^#' | xargs)

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION=${REGION:-us-central1}
JOB_NAME="bachata-buddy-migrate"
SERVICE_NAME="bachata-buddy"

echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Job: $JOB_NAME"
echo ""

# Get the image from the deployed service
echo "🔍 Getting image from deployed service..."
IMAGE=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(spec.template.spec.containers[0].image)')

if [ -z "$IMAGE" ]; then
    echo "❌ Error: Could not get image from service $SERVICE_NAME"
    echo "Make sure the service is deployed first"
    exit 1
fi

echo "✅ Using image: $IMAGE"
echo ""

echo "🚀 Creating/updating Cloud Run Job for migrations..."
gcloud run jobs deploy $JOB_NAME \
    --image $IMAGE \
    --region $REGION \
    --memory 2Gi \
    --cpu 2 \
    --task-timeout 600 \
    --max-retries 0 \
    --set-cloudsql-instances="bachata-buddy:us-central1:bachata-db" \
    --set-env-vars="ENVIRONMENT=cloud,GCP_PROJECT_ID=$GCP_PROJECT_ID,GCS_BUCKET_NAME=$GCS_BUCKET_NAME,DB_NAME=${DB_NAME:-bachata-buddy},DB_USER=${DB_USER:-postgres},DB_HOST=$DB_HOST,DB_PORT=${DB_PORT:-5432},CLOUD_SQL_CONNECTION_NAME=bachata-buddy:us-central1:bachata-db,ELASTICSEARCH_HOST=$ELASTICSEARCH_HOST,ELASTICSEARCH_PORT=${ELASTICSEARCH_PORT:-443},ELASTICSEARCH_INDEX=${ELASTICSEARCH_INDEX:-bachata_move_embeddings},DJANGO_DEBUG=False" \
    --set-secrets="DJANGO_SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest,ELASTICSEARCH_API_KEY=elasticsearch-api-key:latest,GOOGLE_API_KEY=google-api-key:latest" \
    --command="python" \
    --args="manage.py,migrate,--noinput"

echo ""
echo "✅ Job created/updated. Now executing..."
echo ""

# Execute the job
gcloud run jobs execute $JOB_NAME --region $REGION --wait

echo ""
echo "=" | head -c 80 | tr '\n' '='
echo ""
echo "✅ Migrations completed!"
echo ""
echo "📊 View job logs:"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=$JOB_NAME\" --limit 50 --format json"
echo ""
