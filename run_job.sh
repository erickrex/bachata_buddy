#!/bin/bash
# Run a video assembly job locally
#
# Usage: ./run_job.sh <task_id>
# Example: ./run_job.sh 5e0ebecf-71b9-4eb8-aedf-619658c2084d

set -e

if [ -z "$1" ]; then
    echo "Usage: ./run_job.sh <task_id>"
    echo "Example: ./run_job.sh 5e0ebecf-71b9-4eb8-aedf-619658c2084d"
    exit 1
fi

TASK_ID=$1

echo "🎬 Running job for task: $TASK_ID"
echo "=========================================="

# Get blueprint from database
echo "📋 Fetching blueprint from database..."
BLUEPRINT_JSON=$(docker exec bachata_api uv run python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from apps.choreography.models import ChoreographyTask
import json
task = ChoreographyTask.objects.get(task_id='$TASK_ID')
print(json.dumps(task.blueprint.blueprint_json, separators=(',', ':')))
" 2>/dev/null)

if [ -z "$BLUEPRINT_JSON" ]; then
    echo "❌ Error: Could not fetch blueprint for task $TASK_ID"
    exit 1
fi

# Get user ID
USER_ID=$(docker exec bachata_api uv run python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from apps.choreography.models import ChoreographyTask
task = ChoreographyTask.objects.get(task_id='$TASK_ID')
print(task.user_id)
" 2>/dev/null)

echo "✓ Blueprint fetched (${#BLUEPRINT_JSON} bytes)"
echo "✓ User ID: $USER_ID"
echo ""
echo "🚀 Starting job container..."
echo "=========================================="

# Run the job
docker-compose run --rm \
    -e TASK_ID="$TASK_ID" \
    -e USER_ID="$USER_ID" \
    -e BLUEPRINT_JSON="$BLUEPRINT_JSON" \
    job

echo ""
echo "✅ Job completed!"
