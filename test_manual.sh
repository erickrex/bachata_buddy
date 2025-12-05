#!/bin/bash

# =============================================================================
# Bachata Buddy - Manual Testing Script
# =============================================================================
# This script helps you test both Path 1 (traditional) and Path 2 (AI agent)
# workflows manually.
# =============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:8001"
FRONTEND_URL="http://localhost:5173"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Bachata Buddy - Manual Testing Guide                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check services
echo -e "${YELLOW}Step 1: Checking Services...${NC}"
echo ""

if curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend API is running at $API_URL${NC}"
else
    echo -e "${RED}✗ Backend API is not responding${NC}"
    echo "  Run: docker-compose --profile microservices up -d"
    exit 1
fi

if curl -s "$FRONTEND_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is running at $FRONTEND_URL${NC}"
else
    echo -e "${RED}✗ Frontend is not responding${NC}"
    echo "  Run: docker-compose --profile microservices up -d"
    exit 1
fi

echo ""

# Step 2: Get authentication token
echo -e "${YELLOW}Step 2: Getting Authentication Token...${NC}"
echo ""

AUTH_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}')

TOKEN=$(echo $AUTH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access'])" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Failed to get authentication token${NC}"
    echo "  Make sure you created a test user:"
    echo "  docker-compose exec api uv run python manage.py shell -c \\"
    echo "    \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')\""
    exit 1
fi

echo -e "${GREEN}✓ Authentication successful${NC}"
echo "  Token: ${TOKEN:0:50}..."
echo ""

# Step 3: Check OpenAI configuration
echo -e "${YELLOW}Step 3: Checking OpenAI Configuration...${NC}"
echo ""

OPENAI_KEY=$(docker-compose exec -T api env | grep OPENAI_API_KEY | cut -d= -f2 | tr -d '\r')

if [[ "$OPENAI_KEY" == "your-openai-api-key-here" ]] || [ -z "$OPENAI_KEY" ]; then
    echo -e "${RED}✗ OpenAI API key is not configured${NC}"
    echo "  Path 2 (conversational AI) will not work"
    echo ""
    echo "  To configure:"
    echo "  1. Get API key from: https://platform.openai.com/api-keys"
    echo "  2. Edit: bachata_buddy/backend/.env"
    echo "  3. Set: OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE"
    echo "  4. Restart: docker-compose restart api"
    echo ""
    PATH2_ENABLED=false
else
    echo -e "${GREEN}✓ OpenAI API key is configured${NC}"
    echo "  Key: ${OPENAI_KEY:0:20}..."
    PATH2_ENABLED=true
fi

echo ""

# Step 4: Test API endpoints
echo -e "${YELLOW}Step 4: Testing API Endpoints...${NC}"
echo ""

# Test songs endpoint
SONGS_RESPONSE=$(curl -s -X GET "$API_URL/api/songs/" \
  -H "Authorization: Bearer $TOKEN")

SONG_COUNT=$(echo $SONGS_RESPONSE | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

if [ "$SONG_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Songs API working ($SONG_COUNT songs available)${NC}"
else
    echo -e "${YELLOW}⚠ No songs found in database${NC}"
    echo "  You may need to load song data"
fi

echo ""

# Summary
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Testing Instructions                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}Frontend URL:${NC} $FRONTEND_URL"
echo -e "${GREEN}Backend API:${NC} $API_URL"
echo -e "${GREEN}API Docs:${NC} $API_URL/api/docs/"
echo ""

echo -e "${YELLOW}Test Credentials:${NC}"
echo "  Username: testuser"
echo "  Password: testpass123"
echo ""

echo -e "${YELLOW}Path 1 (Traditional Workflow):${NC}"
echo "  1. Open: $FRONTEND_URL"
echo "  2. Login with test credentials"
echo "  3. Click 'Select Song' in navigation"
echo "  4. Choose a song from dropdown"
echo "  5. Select difficulty, style, energy level"
echo "  6. Click 'Generate Choreography'"
echo "  7. Watch the progress page"
echo "  8. View the generated video"
echo ""

if [ "$PATH2_ENABLED" = true ]; then
    echo -e "${YELLOW}Path 2 (Conversational AI):${NC}"
    echo "  1. Open: $FRONTEND_URL"
    echo "  2. Login with test credentials"
    echo "  3. Click 'Describe Choreography' in navigation"
    echo "  4. Try example prompts or type your own:"
    echo "     - 'Create a romantic beginner choreography'"
    echo "     - 'Generate an energetic advanced dance'"
    echo "     - 'Make a sensual intermediate routine'"
    echo "  5. Watch the reasoning panel show agent steps"
    echo "  6. View the generated video"
    echo "  7. Video auto-saves to your collections"
else
    echo -e "${RED}Path 2 (Conversational AI): NOT AVAILABLE${NC}"
    echo "  Configure OpenAI API key to enable Path 2"
fi

echo ""

echo -e "${YELLOW}API Testing (cURL):${NC}"
echo ""
echo "# Test Path 1 (Traditional):"
echo "curl -X POST $API_URL/api/choreography/generate-from-song/ \\"
echo "  -H 'Authorization: Bearer $TOKEN' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"song_id\": 1, \"difficulty\": \"beginner\", \"style\": \"romantic\", \"energy_level\": \"low\"}'"
echo ""

if [ "$PATH2_ENABLED" = true ]; then
    echo "# Test Path 2 (Conversational):"
    echo "curl -X POST $API_URL/api/choreography/describe/ \\"
    echo "  -H 'Authorization: Bearer $TOKEN' \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"user_request\": \"Create a romantic beginner choreography\"}'"
    echo ""
fi

echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View API logs:      docker-compose logs -f api"
echo "  View frontend logs: docker-compose logs -f frontend"
echo "  Restart services:   docker-compose restart"
echo "  Stop services:      docker-compose --profile microservices down"
echo ""

echo -e "${GREEN}✓ Setup complete! Ready for manual testing.${NC}"
echo ""
