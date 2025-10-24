#!/bin/bash
# Fix Cloud Build permissions for Cloud Run deployment

set -e

echo "🔧 Fixing Cloud Build Permissions"
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

# The compute service account that Cloud Build uses
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "🔐 Granting permissions to: $COMPUTE_SA"
echo ""

# Grant Storage Object Viewer role (needed to read source during build)
echo "Granting Storage Object Viewer role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/storage.objectViewer" \
    --condition=None

# Grant Cloud Build Service Account role
echo "Granting Cloud Build Service Account role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/cloudbuild.builds.builder" \
    --condition=None

# Grant Artifact Registry Writer role (needed to push built images)
echo "Granting Artifact Registry Writer role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/artifactregistry.writer" \
    --condition=None

echo ""
echo "✅ Permissions granted successfully!"
echo ""
echo "⏳ Wait 1-2 minutes for permissions to propagate, then retry deployment:"
echo "   ./scripts/deploy_to_cloud_run.sh"
echo ""
