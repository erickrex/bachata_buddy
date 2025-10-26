#!/bin/bash
# Test if Cloud Run can connect to the database

set -e

echo "🧪 Testing Cloud Run database connection"
echo "========================================="
echo ""

SERVICE_URL="https://bachata-buddy-302645054067.us-central1.run.app"

echo "📋 Testing endpoints:"
echo "  Service: $SERVICE_URL"
echo ""

echo "1️⃣ Testing health endpoint..."
curl -s "$SERVICE_URL/health" | head -5 || echo "  ⚠️  No health endpoint"
echo ""

echo "2️⃣ Testing registration page (should load without DB errors)..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/auth/register/")
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Registration page loads (HTTP $HTTP_CODE)"
else
    echo "  ❌ Registration page failed (HTTP $HTTP_CODE)"
fi
echo ""

echo "3️⃣ Checking recent logs for database errors..."
ERRORS=$(gcloud run services logs read bachata-buddy --region=us-central1 --limit=50 2>/dev/null | grep -i "relation.*does not exist\|connection refused" | wc -l | tr -d ' ')

if [ "$ERRORS" = "0" ]; then
    echo "  ✅ No database errors in recent logs"
else
    echo "  ⚠️  Found $ERRORS database errors in recent logs"
    echo ""
    echo "Recent errors:"
    gcloud run services logs read bachata-buddy --region=us-central1 --limit=50 2>/dev/null | grep -i "relation.*does not exist\|connection refused" | tail -3
fi

echo ""
echo "========================================="
echo "✅ Test complete!"
echo ""
echo "Try it yourself:"
echo "  $SERVICE_URL/auth/register/"
