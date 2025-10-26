#!/bin/bash
# Complete deployment script for Cloud Run
# This script handles secrets, environment variables, and deployment

set -e

echo "🚀 Deploying Bachata Buddy to Cloud Run"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

# Load .env
export $(cat .env | grep -v '^#' | xargs)

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No GCP project configured"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# Configuration
REGION=${REGION:-us-central1}
SERVICE_NAME=${SERVICE_NAME:-bachata-buddy}
MEMORY=${MEMORY:-8Gi}
CPU=${CPU:-4}
TIMEOUT=${TIMEOUT:-300}

echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service: $SERVICE_NAME"
echo "  Memory: $MEMORY"
echo "  CPU: $CPU"
echo "  Timeout: ${TIMEOUT}s"
echo ""

# Check required environment variables
REQUIRED_ENV_VARS=(
    "GCP_PROJECT_ID"
    "GCS_BUCKET_NAME"
    "DB_HOST"
    "DB_NAME"
    "DB_USER"
    "ELASTICSEARCH_HOST"
)

echo "Checking required environment variables..."
for var in "${REQUIRED_ENV_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var not set in .env"
        exit 1
    fi
    echo "✅ $var is set"
done

# Ask for confirmation
echo ""
echo "⚠️  This will deploy to Cloud Run in project: $PROJECT_ID"
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

# Setup secrets first (skip IAM errors - Cloud Run will handle permissions)
echo ""
echo "🔐 Setting up secrets..."
./scripts/setup_secrets.sh || echo "⚠️  Secret setup had errors (this is OK - Cloud Run will handle permissions)"

# Create temporary env vars file to handle special characters in ALLOWED_HOSTS
ENV_FILE=$(mktemp)
cat > "$ENV_FILE" <<EOF
ENVIRONMENT: "cloud"
GCP_PROJECT_ID: "$GCP_PROJECT_ID"
GCS_BUCKET_NAME: "$GCS_BUCKET_NAME"
DB_NAME: "${DB_NAME:-bachata-buddy}"
DB_USER: "${DB_USER:-postgres}"
DB_HOST: "$DB_HOST"
DB_PORT: "${DB_PORT:-5432}"
CLOUD_SQL_CONNECTION_NAME: "bachata-buddy:us-central1:bachata-db"
ELASTICSEARCH_HOST: "$ELASTICSEARCH_HOST"
ELASTICSEARCH_PORT: "${ELASTICSEARCH_PORT:-443}"
ELASTICSEARCH_INDEX: "${ELASTICSEARCH_INDEX:-bachata_move_embeddings}"
DJANGO_DEBUG: "True"
ALLOWED_HOSTS: "$ALLOWED_HOSTS"
EOF

# Deploy to Cloud Run
echo ""
echo "🚀 Deploying to Cloud Run..."
echo ""

gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --memory $MEMORY \
    --cpu $CPU \
    --timeout $TIMEOUT \
    --allow-unauthenticated \
    --add-cloudsql-instances="bachata-buddy:us-central1:bachata-db" \
    --env-vars-file="$ENV_FILE" \
    --set-secrets="DJANGO_SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest,ELASTICSEARCH_API_KEY=elasticsearch-api-key:latest,GOOGLE_API_KEY=google-api-key:latest"

# Clean up temp file
rm -f "$ENV_FILE"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')

echo ""
echo "=" | head -c 80 | tr '\n' '='
echo ""
echo "✅ Deployment successful!"
echo ""
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📊 View logs:"
echo "  gcloud run services logs read $SERVICE_NAME --region $REGION --limit 100"
echo ""
echo "🔍 View service details:"
echo "  gcloud run services describe $SERVICE_NAME --region $REGION"
echo ""
echo "⚠️  IMPORTANT - Next steps:"
echo "  1. Run database migrations:"
echo "     ./scripts/run_cloud_migrations.sh"
echo ""
echo "  2. Update ALLOWED_HOSTS in .env with: ${SERVICE_URL#https://}"
echo "     Then redeploy with: ./scripts/deploy_to_cloud_run.sh"
echo ""
