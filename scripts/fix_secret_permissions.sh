#!/bin/bash
# Grant Secret Manager permissions to Cloud Run service account

set -e

echo "🔐 Fixing Secret Manager Permissions"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No GCP project configured"
    exit 1
fi

# Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

echo "📋 Project: $PROJECT_ID"
echo "📋 Project Number: $PROJECT_NUMBER"
echo ""

# The compute service account that Cloud Run uses
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "🔐 Granting Secret Manager access to: $COMPUTE_SA"
echo ""

# List of secrets
SECRETS=(
    "django-secret-key"
    "db-password"
    "elasticsearch-api-key"
    "google-api-key"
)

# Grant Secret Accessor role for each secret
for SECRET in "${SECRETS[@]}"; do
    echo "Granting access to secret: $SECRET"
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID
done

echo ""
echo "✅ Secret permissions granted successfully!"
echo ""
echo "🚀 Now retry deployment:"
echo "   ./scripts/deploy_to_cloud_run.sh"
echo ""
