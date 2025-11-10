#!/bin/bash
# =============================================================================
# FAST SONG PIPELINE - Path 1 and Path 2 with 134 BPM Song
# =============================================================================

set -e

API_BASE="http://localhost:8001/api"
OUTPUT_DIR="fast_song_pipeline_$(date +%Y%m%d_%H%M%S)"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

mkdir -p "$OUTPUT_DIR"

echo "==================================================================="
echo "  FAST SONG PIPELINE - 134 BPM"
echo "==================================================================="
echo ""
echo "  Song: Este_secreto by Melvin War (134 BPM)"
echo "  Output: $OUTPUT_DIR"
echo ""

# Authenticate
echo -e "${BLUE}[1/7]${NC} Authenticating..."
AUTH_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"username":"e2etest_weighted","password":"testpass123"}')

TOKEN=$(echo "$AUTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "ERROR: Authentication failed"
    exit 1
fi
echo -e "${GREEN}✓${NC} Authenticated"
echo ""

# Trigger Path 1
echo -e "${BLUE}[2/7]${NC} Triggering Path 1 (Song Template - 134 BPM)"
echo -e "${CYAN}      Song ID: 7 (Este_secreto)${NC}"
echo -e "${CYAN}      Difficulty: advanced${NC}"
echo -e "${CYAN}      Energy: high${NC}"
echo -e "${CYAN}      Style: modern${NC}"

PATH1_RESPONSE=$(curl -s -X POST "$API_BASE/choreography/generate-from-song/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "song_id": 7,
    "difficulty": "advanced",
    "energy_level": "high",
    "style": "modern"
  }')

PATH1_TASK_ID=$(echo "$PATH1_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('task_id', ''))" 2>/dev/null)

if [ -z "$PATH1_TASK_ID" ]; then
    echo "ERROR: Path 1 failed"
    echo "$PATH1_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓${NC} Path 1 triggered: $PATH1_TASK_ID"
echo "$PATH1_RESPONSE" | python3 -m json.tool > "$OUTPUT_DIR/path1_trigger.json" 2>/dev/null
echo ""

# Trigger Path 2
echo -e "${BLUE}[3/7]${NC} Triggering Path 2 (AI Generation - Fast Song)"
echo -e "${CYAN}      Query: 'Create an energetic advanced bachata with fast spins and turns'${NC}"

PATH2_RESPONSE=$(curl -s -X POST "$API_BASE/choreography/generate-with-ai/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "Create an energetic advanced bachata with fast spins and turns"
  }')

PATH2_TASK_ID=$(echo "$PATH2_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('task_id', ''))" 2>/dev/null)

if [ -z "$PATH2_TASK_ID" ]; then
    echo "ERROR: Path 2 failed"
    echo "$PATH2_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓${NC} Path 2 triggered: $PATH2_TASK_ID"
echo "$PATH2_RESPONSE" | python3 -m json.tool > "$OUTPUT_DIR/path2_trigger.json" 2>/dev/null
echo ""

# Wait for blueprints
echo -e "${BLUE}[4/7]${NC} Waiting for blueprints (10 seconds)..."
sleep 10
echo ""

# Verify blueprints
echo -e "${BLUE}[5/7]${NC} Verifying blueprints..."

PATH1_BLUEPRINT=$(docker exec bachata_db psql -U postgres -d bachata_vibes -t -c \
  "SELECT blueprint_json FROM blueprints WHERE task_id = '$PATH1_TASK_ID'" | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

if [ -z "$PATH1_BLUEPRINT" ]; then
    echo "ERROR: Path 1 blueprint not found"
    exit 1
fi

PATH1_MOVES=$(echo "$PATH1_BLUEPRINT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('moves', [])))" 2>/dev/null)
echo -e "${GREEN}✓${NC} Path 1 blueprint: $PATH1_MOVES moves"
echo "$PATH1_BLUEPRINT" | python3 -m json.tool > "$OUTPUT_DIR/path1_blueprint.json" 2>/dev/null

PATH2_BLUEPRINT=$(docker exec bachata_db psql -U postgres -d bachata_vibes -t -c \
  "SELECT blueprint_json FROM blueprints WHERE task_id = '$PATH2_TASK_ID'" | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

if [ -z "$PATH2_BLUEPRINT" ]; then
    echo "ERROR: Path 2 blueprint not found"
    exit 1
fi

PATH2_MOVES=$(echo "$PATH2_BLUEPRINT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('moves', [])))" 2>/dev/null)
echo -e "${GREEN}✓${NC} Path 2 blueprint: $PATH2_MOVES moves"
echo "$PATH2_BLUEPRINT" | python3 -m json.tool > "$OUTPUT_DIR/path2_blueprint.json" 2>/dev/null
echo ""

# Process Path 1 video
echo -e "${BLUE}[6/7]${NC} Processing Path 1 video (134 BPM)..."
export BLUEPRINT_JSON="$PATH1_BLUEPRINT"
export TASK_ID="$PATH1_TASK_ID"
export USER_ID=47

if docker-compose --profile job run --rm job > "$OUTPUT_DIR/path1_job.log" 2>&1; then
    echo -e "${GREEN}✓${NC} Path 1 video generated"
    if [ -f "data/choreographies/choreography_${PATH1_TASK_ID}.mp4" ]; then
        VIDEO_SIZE=$(du -h "data/choreographies/choreography_${PATH1_TASK_ID}.mp4" | cut -f1)
        echo -e "${CYAN}      Size: $VIDEO_SIZE${NC}"
    fi
else
    echo "ERROR: Path 1 video generation failed"
    tail -50 "$OUTPUT_DIR/path1_job.log"
fi
echo ""

# Process Path 2 video
echo -e "${BLUE}[7/7]${NC} Processing Path 2 video (Fast Song)..."
export BLUEPRINT_JSON="$PATH2_BLUEPRINT"
export TASK_ID="$PATH2_TASK_ID"
export USER_ID=47

if docker-compose --profile job run --rm job > "$OUTPUT_DIR/path2_job.log" 2>&1; then
    echo -e "${GREEN}✓${NC} Path 2 video generated"
    if [ -f "data/choreographies/choreography_${PATH2_TASK_ID}.mp4" ]; then
        VIDEO_SIZE=$(du -h "data/choreographies/choreography_${PATH2_TASK_ID}.mp4" | cut -f1)
        echo -e "${CYAN}      Size: $VIDEO_SIZE${NC}"
    fi
else
    echo "ERROR: Path 2 video generation failed"
    tail -50 "$OUTPUT_DIR/path2_job.log"
fi
echo ""

# Summary
echo "==================================================================="
echo "  FAST SONG PIPELINE COMPLETE"
echo "==================================================================="
echo ""
echo "Path 1 (Song Template - 134 BPM):"
echo "  Task ID: $PATH1_TASK_ID"
echo "  Moves: $PATH1_MOVES"
echo "  Video: data/choreographies/choreography_${PATH1_TASK_ID}.mp4"
echo ""
echo "Path 2 (AI Generation - Fast Song):"
echo "  Task ID: $PATH2_TASK_ID"
echo "  Moves: $PATH2_MOVES"
echo "  Video: data/choreographies/choreography_${PATH2_TASK_ID}.mp4"
echo ""
echo "Output: $OUTPUT_DIR"
echo "==================================================================="
