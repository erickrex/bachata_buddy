#!/bin/bash
# Setup secrets for Cloud Run deployment
# This script reads from .env and creates secrets in Google Secret Manager

set -e

echo "🔐 Setting up secrets for Cloud Run deployment"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env file with your secrets first"
    exit 1
fi

# Load .env
export $(cat .env | grep -v '^#' | xargs)

# Check required variables
REQUIRED_VARS=(
    "DJANGO_SECRET_KEY"
    "DB_PASSWORD"
    "ELASTICSEARCH_API_KEY"
    "GOOGLE_API_KEY"
)

echo "Checking required environment variables..."
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var not set in .env"
        exit 1
    fi
    echo "✅ $var is set"
done

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No GCP project configured"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo ""
echo "📋 Project: $PROJECT_ID"
echo ""

# Enable Secret Manager API
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --quiet

# Create secrets
echo ""
echo "Creating secrets..."

create_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if gcloud secrets describe $secret_name &>/dev/null; then
        echo "⏭️  Secret $secret_name already exists, adding new version..."
        echo -n "$secret_value" | gcloud secrets versions add $secret_name --data-file=-
    else
        echo "➕ Creating secret $secret_name..."
        echo -n "$secret_value" | gcloud secrets create $secret_name --data-file=-
    fi
}

create_secret "django-secret-key" "$DJANGO_SECRET_KEY"
create_secret "db-password" "$DB_PASSWORD"
create_secret "elasticsearch-api-key" "$ELASTICSEARCH_API_KEY"
create_secret "google-api-key" "$GOOGLE_API_KEY"

# Grant access to Cloud Run service account
echo ""
echo "Granting access to Cloud Run service account..."

SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"
echo "Service account: $SERVICE_ACCOUNT"

for secret in django-secret-key db-password elasticsearch-api-key google-api-key; do
    echo "  Granting access to $secret..."
    gcloud secrets add-iam-policy-binding $secret \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet
done

# Summary
echo ""
echo "=" | head -c 80 | tr '\n' '='
echo ""
echo "✅ Secrets configured successfully!"
echo ""
echo "📋 Created secrets:"
gcloud secrets list --filter="name:django-secret-key OR name:db-password OR name:elasticsearch-api-key OR name:google-api-key"
echo ""
echo "🚀 Next steps:"
echo "1. Deploy to Cloud Run with:"
echo "   gcloud run deploy bachata-buddy --source . --region us-central1 \\"
echo "     --set-secrets='DJANGO_SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest,ELASTICSEARCH_API_KEY=elasticsearch-api-key:latest,GOOGLE_API_KEY=google-api-key:latest'"
echo ""
echo "2. Or use the full deployment command from SECRETS_MANAGEMENT_GUIDE.md"
echo ""
