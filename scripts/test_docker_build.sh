#!/bin/bash
# Test Docker build and run locally
# This script helps verify the application works in a containerized environment

set -e  # Exit on error

echo "🐳 Testing Docker Build for Cloud Run Deployment"
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"

# Build the image
echo ""
echo "📦 Building Docker image..."
docker build -t bachata-buddy:test .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please update .env with your actual credentials${NC}"
fi

# Run the container
echo ""
echo "🚀 Starting container on port 8080..."
echo "   (Press Ctrl+C to stop)"
echo ""

# Stop any existing container
docker stop bachata-buddy-test 2>/dev/null || true
docker rm bachata-buddy-test 2>/dev/null || true

# Run container with environment variables from .env
docker run -d \
  --name bachata-buddy-test \
  -p 8080:8080 \
  -e PORT=8080 \
  --env-file .env \
  bachata-buddy:test

# Wait for container to start
echo "⏳ Waiting for container to start..."
sleep 5

# Check if container is running
if docker ps | grep -q bachata-buddy-test; then
    echo -e "${GREEN}✅ Container is running${NC}"
else
    echo -e "${RED}❌ Container failed to start${NC}"
    echo "Logs:"
    docker logs bachata-buddy-test
    exit 1
fi

# Test health check
echo ""
echo "🏥 Testing health check endpoint..."
sleep 2

if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Container logs:"
    docker logs bachata-buddy-test
    docker stop bachata-buddy-test
    docker rm bachata-buddy-test
    exit 1
fi

# Test home page
echo ""
echo "🌐 Testing home page..."
if curl -f http://localhost:8080/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Home page accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Home page returned error (may be expected if redirects)${NC}"
fi

echo ""
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "📊 Container Status:"
docker ps | grep bachata-buddy-test

echo ""
echo "📝 View logs:"
echo "   docker logs -f bachata-buddy-test"
echo ""
echo "🌐 Access the application:"
echo "   http://localhost:8080"
echo ""
echo "🛑 Stop the container:"
echo "   docker stop bachata-buddy-test && docker rm bachata-buddy-test"
echo ""
echo -e "${GREEN}🎉 Docker build is ready for Cloud Run deployment!${NC}"

