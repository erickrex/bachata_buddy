#!/bin/bash
# Load embeddings to Cloud SQL database

set -e

echo "📊 Loading embeddings to Cloud SQL..."

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
INSTANCE_NAME=${CLOUD_SQL_INSTANCE:-"bachata-db"}
REGION=${CLOUD_SQL_REGION:-"us-central1"}
DB_USER=${DB_USER:-"postgres"}
DB_NAME=${DB_NAME:-"bachata_buddy"}

# Start Cloud SQL Proxy
echo "🔌 Starting Cloud SQL Proxy..."
cloud_sql_proxy -instances=${PROJECT_ID}:${REGION}:${INSTANCE_NAME}=tcp:5433 &
PROXY_PID=$!

# Wait for proxy to be ready
sleep 5

# Set database URL
export DATABASE_URL="postgresql://${DB_USER}@localhost:5433/${DB_NAME}"

# Run embedding loader
echo "📥 Loading embeddings..."
cd backend
uv run python scripts/load_embeddings_to_db.py

# Verify
echo "✅ Verifying embeddings..."
uv run python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()
from apps.choreography.models import MoveEmbedding

count = MoveEmbedding.objects.count()
print(f'Total embeddings: {count}')

if count == 38:
    print('✅ All 38 embeddings loaded successfully!')
else:
    print(f'⚠️  Expected 38 embeddings, found {count}')
    exit(1)
"

# Stop proxy
kill $PROXY_PID

echo "✅ Embeddings loaded to Cloud SQL!"
