#!/bin/bash
# Fix Cloud Run database connection to use Unix socket

set -e

echo "🔧 Fixing Cloud Run database connection"
echo "========================================"
echo ""

PROJECT_ID="bachata-buddy"
SERVICE_NAME="bachata-buddy"
REGION="us-central1"
INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:bachata-db"

echo "📋 Configuration:"
echo "  Service: $SERVICE_NAME"
echo "  Region: $REGION"
echo "  Cloud SQL: $INSTANCE_CONNECTION_NAME"
echo ""

echo "🔄 Updating Cloud Run service to use Unix socket..."
echo ""

gcloud run services update $SERVICE_NAME \
    --region=$REGION \
    --update-env-vars="DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME" \
    --quiet

echo ""
echo "========================================"
echo "✅ Cloud Run service updated!"
echo ""
echo "Changes made:"
echo "  ❌ OLD: DB_HOST=35.188.209.4"
echo "  ✅ NEW: DB_HOST=/cloudsql/$INSTANCE_CONNECTION_NAME"
echo ""
echo "🔍 Verifying connection..."
echo ""

# Wait a moment for the service to update
sleep 5

# Check the logs
echo "📊 Recent logs (checking for database connection):"
gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=10

echo ""
echo "✅ Done! Try your app now:"
echo "   https://$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)' | sed 's|https://||')/auth/register/"
