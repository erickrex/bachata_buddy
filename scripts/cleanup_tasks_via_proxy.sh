#!/bin/bash
# Clean up stuck tasks via Cloud SQL Proxy

set -e

echo "🧹 Cleaning up stuck choreography tasks"
echo "=" | head -c 80 | tr '\n' '='
echo ""

# Check if cloud-sql-proxy is installed
if ! command -v cloud-sql-proxy &> /dev/null; then
    echo "❌ cloud-sql-proxy not found"
    exit 1
fi

INSTANCE_CONNECTION_NAME="bachata-buddy:us-central1:bachata-db"
PROXY_PORT=5433

echo "📋 Starting Cloud SQL Proxy..."
cloud-sql-proxy $INSTANCE_CONNECTION_NAME --port=$PROXY_PORT &
PROXY_PID=$!

# Wait for proxy
sleep 5

# Trap to ensure proxy is killed
trap "echo '🛑 Stopping proxy...'; kill $PROXY_PID 2>/dev/null || true" EXIT

# Set environment
export DB_HOST=127.0.0.1
export DB_PORT=$PROXY_PORT

echo "🧹 Running cleanup script..."
uv run python scripts/cleanup_stuck_tasks.py

echo ""
echo "✅ Cleanup completed!"
