#!/bin/bash
# Run Django migrations via Cloud SQL Proxy (local connection to cloud database)

set -e

echo "🔄 Running Django migrations via Cloud SQL Proxy"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Check if cloud-sql-proxy is installed
if ! command -v cloud-sql-proxy &> /dev/null; then
    echo "❌ cloud-sql-proxy not found. Installing..."
    echo ""
    echo "Run one of these commands:"
    echo "  brew install cloud-sql-proxy  # macOS"
    echo "  # OR download from: https://cloud.google.com/sql/docs/postgres/connect-instance-auth-proxy"
    exit 1
fi

# Load .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

export $(cat .env | grep -v '^#' | xargs)

INSTANCE_CONNECTION_NAME="bachata-buddy:us-central1:bachata-db"
PROXY_PORT=5433

echo "📋 Starting Cloud SQL Proxy..."
echo "  Instance: $INSTANCE_CONNECTION_NAME"
echo "  Local port: $PROXY_PORT"
echo ""

# Start proxy in background
cloud-sql-proxy $INSTANCE_CONNECTION_NAME --port=$PROXY_PORT &
PROXY_PID=$!

# Wait for proxy to be ready
echo "⏳ Waiting for proxy to be ready..."
sleep 5

# Trap to ensure proxy is killed on exit
trap "echo '🛑 Stopping proxy...'; kill $PROXY_PID 2>/dev/null || true" EXIT

# Set environment for local connection via proxy
export DB_HOST=127.0.0.1
export DB_PORT=$PROXY_PORT
export ENVIRONMENT=local

echo "✅ Proxy ready!"
echo ""
echo "🔄 Running migrations..."
echo ""

# Run migrations using uv
uv run python manage.py migrate --noinput

echo ""
echo "=" | head -c 80 | tr '\n' '='
echo ""
echo "✅ Migrations completed!"
echo ""
