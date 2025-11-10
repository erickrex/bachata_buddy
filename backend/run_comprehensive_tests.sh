#!/bin/bash
# Quick script to run comprehensive API tests
# This script checks if the backend is running and provides helpful instructions

set -e

echo "============================================================"
echo "Bachata Buddy - Comprehensive API Test Runner"
echo "============================================================"
echo ""

# Check if backend is running
echo "Checking if backend API is running..."
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Backend API is running"
    echo ""
    
    # Run the comprehensive test script
    echo "Running comprehensive API tests..."
    echo ""
    python test_api_comprehensive.py --base-url http://localhost:8000
    
else
    echo "❌ Backend API is not running at http://localhost:8000"
    echo ""
    echo "To start the backend API, run:"
    echo ""
    echo "  cd backend"
    echo "  uv run python manage.py runserver"
    echo ""
    echo "Or use docker-compose:"
    echo ""
    echo "  docker-compose up backend"
    echo ""
    echo "Then run this script again."
    exit 1
fi
