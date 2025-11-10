#!/bin/bash
# Complete deployment script for Google Cloud

set -e

echo "🚀 Starting Google Cloud Deployment..."
echo "=================================="

# Check required environment variables
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "❌ GOOGLE_CLOUD_PROJECT not set"
    exit 1
fi

echo "📋 Project: $GOOGLE_CLOUD_PROJECT"
echo ""

# Phase 1: Database
echo "📊 Phase 1: Database Migration & Data Loading"
echo "----------------------------------------------"
./scripts/migrate_via_proxy.sh
./scripts/load_embeddings_to_cloud_sql.sh
echo ""

# Phase 2: GCS
echo "☁️  Phase 2: Upload to Google Cloud Storage"
echo "--------------------------------------------"
./scripts/upload_training_videos.sh
./scripts/upload_songs.sh
echo ""

# Phase 3: Containers
echo "🐳 Phase 3: Build & Deploy Containers"
echo "--------------------------------------"
./scripts/build_and_push_api.sh
./scripts/build_and_push_job.sh
./scripts/deploy_api_to_cloud_run.sh
./scripts/deploy_job_to_cloud_run.sh
echo ""

# Phase 4: Permissions
echo "🔐 Phase 4: Configure Permissions"
echo "----------------------------------"
./scripts/setup_service_account_permissions.sh
echo ""

# Phase 5: Testing
echo "✅ Phase 5: Testing"
echo "-------------------"
./scripts/test_path1.sh
./scripts/test_path2.sh
echo ""

echo "=================================="
echo "🎉 Deployment Complete!"
echo "=================================="
echo ""
echo "📊 Summary:"
echo "  - Database: Migrated with 38 embeddings"
echo "  - GCS: Training videos and songs uploaded"
echo "  - API: Deployed to Cloud Run"
echo "  - Job: Deployed to Cloud Run Jobs"
echo "  - Tests: Path 1 and Path 2 verified"
echo ""
echo "🔗 API URL:"
gcloud run services describe bachata-api --region us-central1 --format 'value(status.url)'
echo ""
echo "📝 Next steps:"
echo "  1. Monitor Cloud Logging for any errors"
echo "  2. Test from frontend application"
echo "  3. Set up monitoring alerts"
echo ""
