#!/bin/bash
# Check what tables exist in the Cloud SQL database

set -e

echo "🔍 Checking Cloud SQL database tables"
echo "======================================"
echo ""

INSTANCE_CONNECTION_NAME="bachata-buddy:us-central1:bachata-db"

echo "🚀 Starting Cloud SQL Proxy..."
cloud-sql-proxy $INSTANCE_CONNECTION_NAME --port=5433 &
PROXY_PID=$!

trap "echo '🛑 Stopping proxy...'; kill $PROXY_PID 2>/dev/null || true; wait $PROXY_PID 2>/dev/null || true" EXIT INT TERM

echo "⏳ Waiting for proxy..."
sleep 5

echo "✅ Proxy connected!"
echo ""

echo "📊 Listing all tables in database:"
echo ""

PGPASSWORD=donerick123 psql -h 127.0.0.1 -p 5433 -U postgres -d bachata-buddy -c "\dt"

echo ""
echo "📊 Checking for 'users' table specifically:"
echo ""

PGPASSWORD=donerick123 psql -h 127.0.0.1 -p 5433 -U postgres -d bachata-buddy -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE '%user%';"

echo ""
echo "✅ Done!"
