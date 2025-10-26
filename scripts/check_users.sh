#!/bin/bash
# Check if users exist in the database

set -e

echo "👥 Checking users in Cloud SQL database"
echo "========================================"
echo ""

INSTANCE_CONNECTION_NAME="bachata-buddy:us-central1:bachata-db"

echo "🚀 Starting Cloud SQL Proxy..."
cloud-sql-proxy $INSTANCE_CONNECTION_NAME --port=5433 &
PROXY_PID=$!

trap "kill $PROXY_PID 2>/dev/null || true; wait $PROXY_PID 2>/dev/null || true" EXIT INT TERM

sleep 5

echo "✅ Proxy connected!"
echo ""

echo "📊 Users in database:"
echo ""

PGPASSWORD=donerick123 psql -h 127.0.0.1 -p 5433 -U postgres -d bachata-buddy -c "SELECT id, username, email, date_joined FROM users ORDER BY date_joined DESC LIMIT 10;"

echo ""
echo "📊 Total user count:"
PGPASSWORD=donerick123 psql -h 127.0.0.1 -p 5433 -U postgres -d bachata-buddy -t -c "SELECT COUNT(*) FROM users;"

echo ""
echo "✅ Done!"
