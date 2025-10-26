#!/bin/bash
# Setup database credentials in Google Secret Manager

set -e

echo "🔐 Setting up database secrets in Secret Manager"
echo "================================================"
echo ""

PROJECT_ID="bachata-buddy"
REGION="us-central1"

# Database credentials
DB_NAME="bachata-buddy"
DB_USER="postgres"
DB_PASSWORD="donerick123"

echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# Function to create or update secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    echo "🔑 Processing secret: $secret_name"
    
    # Check if secret exists
    if gcloud secrets describe $secret_name --project=$PROJECT_ID &>/dev/null; then
        echo "  ↻ Secret exists, adding new version..."
        echo -n "$secret_value" | gcloud secrets versions add $secret_name \
            --project=$PROJECT_ID \
            --data-file=-
    else
        echo "  ✨ Creating new secret..."
        echo -n "$secret_value" | gcloud secrets create $secret_name \
            --project=$PROJECT_ID \
            --replication-policy="automatic" \
            --data-file=-
    fi
    
    echo "  ✅ Done"
    echo ""
}

# Create/update secrets
create_or_update_secret "db-name" "$DB_NAME"
create_or_update_secret "db-user" "$DB_USER"
create_or_update_secret "db-password" "$DB_PASSWORD"

echo "🔐 Granting access to Cloud Build service account..."
echo ""

# Get Cloud Build service account
BUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

# Grant access to secrets
for secret in db-name db-user db-password; do
    echo "  Granting access to: $secret"
    gcloud secrets add-iam-policy-binding $secret \
        --project=$PROJECT_ID \
        --member="serviceAccount:$BUILD_SA" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet
done

echo ""
echo "================================================"
echo "✅ Database secrets configured successfully!"
echo ""
echo "Secrets created:"
echo "  • db-name"
echo "  • db-user"
echo "  • db-password"
echo ""
echo "Next steps:"
echo "  1. Run migrations: ./scripts/run_cloud_migrations.sh"
echo "  2. Redeploy your app: gcloud builds submit"
