#!/bin/bash
# Run Django migrations on Cloud SQL database
# This script connects to your Cloud SQL instance and runs migrations

set -e

echo "🔄 Running Django migrations on Cloud SQL"
echo "=========================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Configuration
PROJECT_ID="bachata-buddy"
INSTANCE_NAME="bachata-db"
REGION="us-central1"
INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:$INSTANCE_NAME"

echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Instance: $INSTANCE_NAME"
echo "  Region: $REGION"
echo ""

# Check if cloud-sql-proxy is installed
if ! command -v cloud-sql-proxy &> /dev/null; then
    echo "❌ cloud-sql-proxy not found. Installing..."
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Installing via Homebrew..."
        brew install cloud-sql-proxy
    else
        echo "Please install cloud-sql-proxy manually:"
        echo "  https://cloud.google.com/sql/docs/postgres/connect-instance-auth-proxy"
        exit 1
    fi
fi

# Start Cloud SQL Proxy
echo "🚀 Starting Cloud SQL Proxy..."
cloud-sql-proxy $INSTANCE_CONNECTION_NAME --port=5433 &
PROXY_PID=$!

# Trap to ensure proxy is killed on exit
trap "echo '🛑 Stopping proxy...'; kill $PROXY_PID 2>/dev/null || true; wait $PROXY_PID 2>/dev/null || true" EXIT INT TERM

# Wait for proxy to be ready
echo "⏳ Waiting for proxy to connect..."
sleep 5

# Check if proxy is running
if ! kill -0 $PROXY_PID 2>/dev/null; then
    echo "❌ Cloud SQL Proxy failed to start"
    echo ""
    echo "Please ensure:"
    echo "  1. You're authenticated: gcloud auth application-default login"
    echo "  2. You have Cloud SQL Client role"
    echo "  3. The instance exists and is running"
    exit 1
fi

echo "✅ Proxy connected!"
echo ""

# Set environment variables for local connection via proxy
export DB_HOST=127.0.0.1
export DB_PORT=5433
export DB_NAME=bachata-buddy
export DB_USER=postgres
export DB_PASSWORD=donerick123
export ENVIRONMENT=local
export DJANGO_SECRET_KEY=donerick123

echo "🔄 Running Django migrations..."
echo ""

# Change to project directory
cd "$(dirname "$0")/.."

# Run migrations using UV
uv run python manage.py migrate --noinput

echo ""
echo "=========================================="
echo "✅ Migrations completed successfully!"
echo ""
echo "📊 Database status:"
uv run python manage.py showmigrations

echo ""
echo "✅ Done!"
