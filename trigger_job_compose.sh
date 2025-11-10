#!/bin/bash
#
# Trigger Job Using Docker Compose
#
# This script retrieves a blueprint from the database and runs
# the job container using docker-compose.
#
# Usage: ./trigger_job_compose.sh <task_id>
#

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <task_id>"
    echo ""
    echo "Example:"
    echo "  $0 bc201153-f8ca-4b2c-9fa6-a2276bbaf28f"
    exit 1
fi

TASK_ID="$1"

echo "================================================================================"
echo "Triggering Job for Task: $TASK_ID"
echo "================================================================================"
echo ""

# Step 1: Retrieve blueprint from database
echo "[1/2] Retrieving blueprint from database..."
BLUEPRINT_JSON=$(docker exec bachata_db psql -U postgres -d bachata_vibes -t -c "SELECT blueprint_json FROM blueprints WHERE task_id = '$TASK_ID'" | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

if [ -z "$BLUEPRINT_JSON" ] || [ "$BLUEPRINT_JSON" = "" ]; then
    echo "✗ No blueprint found for task $TASK_ID"
    exit 1
fi

echo "✓ Blueprint retrieved"
MOVES_COUNT=$(echo "$BLUEPRINT_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('moves', [])))")
echo "  Size: $(echo "$BLUEPRINT_JSON" | wc -c) bytes"
echo "  Moves: $MOVES_COUNT"
echo ""

# Step 2: Run job using docker-compose
echo "[2/2] Running job container..."
echo ""

# Export environment variables for docker-compose
export BLUEPRINT_JSON
export TASK_ID
export USER_ID=1

# Change to the directory containing docker-compose.yml
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Run the job container
docker-compose --profile job run --rm job

EXIT_CODE=$?

echo ""
echo "================================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS - Video generated!"
    echo ""
    echo "Check the video at: data/choreographies/choreography_${TASK_ID}.mp4"
else
    echo "FAILED - Exit code: $EXIT_CODE"
fi
echo "================================================================================"

exit $EXIT_CODE
