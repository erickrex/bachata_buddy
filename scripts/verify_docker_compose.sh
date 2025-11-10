#!/bin/bash
# Verification script for docker-compose setup
# This script checks that all services are properly configured

set -e

echo "🔍 Verifying Docker Compose Configuration..."
echo ""

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found!"
    exit 1
fi
echo "✅ docker-compose.yml exists"

# Validate docker-compose configuration
echo ""
echo "🔍 Validating docker-compose configuration..."
if docker-compose config --quiet; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors"
    exit 1
fi

# Check if required Dockerfiles exist
echo ""
echo "🔍 Checking Dockerfiles..."
if [ -f "backend/Dockerfile.dev" ]; then
    echo "✅ backend/Dockerfile.dev exists"
else
    echo "❌ backend/Dockerfile.dev not found"
    exit 1
fi

if [ -f "frontend/Dockerfile.dev" ]; then
    echo "✅ frontend/Dockerfile.dev exists"
else
    echo "❌ frontend/Dockerfile.dev not found"
    exit 1
fi

if [ -f "job/Dockerfile" ]; then
    echo "✅ job/Dockerfile exists"
else
    echo "❌ job/Dockerfile not found"
    exit 1
fi

# Check if .env.example exists
echo ""
echo "🔍 Checking environment files..."
if [ -f ".env.example" ]; then
    echo "✅ .env.example exists"
else
    echo "❌ .env.example not found"
    exit 1
fi

# List all services
echo ""
echo "📋 Available services:"
docker-compose config --services | while read service; do
    echo "  - $service"
done

# List services with profiles
echo ""
echo "📋 Services with profiles:"
echo "  Profile 'microservices':"
echo "    - api (Django REST API)"
echo "    - frontend (React Frontend)"
echo "  Profile 'job':"
echo "    - job (Video Processing Job)"

echo ""
echo "✅ All checks passed!"
echo ""
echo "📚 Next steps:"
echo "  1. Copy .env.example to .env and configure your API keys"
echo "  2. Start services: docker-compose up -d"
echo "  3. Run migrations: docker-compose exec web python manage.py migrate"
echo "  4. Create superuser: docker-compose exec web python manage.py createsuperuser"
echo ""
echo "🚀 To start microservices:"
echo "  docker-compose --profile microservices up -d"
echo ""
echo "🎬 To run the job:"
echo "  docker-compose --profile job run --rm job"
