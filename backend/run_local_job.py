#!/usr/bin/env python
"""
Local Job Runner - Manually execute video assembly jobs in development

Usage:
    uv run python run_local_job.py <task_id>
    
Example:
    uv run python run_local_job.py 5e0ebecf-71b9-4eb8-aedf-619658c2084d
"""

import os
import sys
import django
import json
import subprocess

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from apps.choreography.models import ChoreographyTask


def run_job(task_id: str):
    """Run the video assembly job for a specific task"""
    
    print(f"🎬 Running job for task: {task_id}")
    print("=" * 60)
    
    # Get task from database
    try:
        task = ChoreographyTask.objects.get(task_id=task_id)
    except ChoreographyTask.DoesNotExist:
        print(f"❌ Error: Task {task_id} not found in database")
        return 1
    
    print(f"✓ Task found: {task.status}")
    print(f"✓ User ID: {task.user_id}")
    print(f"✓ Blueprint exists: {bool(task.blueprint)}")
    
    if not task.blueprint:
        print("❌ Error: Task has no blueprint")
        return 1
    
    # Convert blueprint to JSON string
    # task.blueprint is already a dict (JSONField)
    if isinstance(task.blueprint, dict):
        blueprint_json = json.dumps(task.blueprint, separators=(',', ':'))
    else:
        # If it's a model instance, get its dict representation
        blueprint_json = json.dumps(task.blueprint.__dict__, separators=(',', ':'), default=str)
    
    print(f"✓ Blueprint size: {len(blueprint_json)} bytes")
    print()
    print("🚀 Starting Docker job container...")
    print("=" * 60)
    
    # Run the job container
    cmd = [
        'docker-compose',
        'run',
        '--rm',
        '-e', f'TASK_ID={task_id}',
        '-e', f'USER_ID={task.user_id}',
        '-e', f'BLUEPRINT_JSON={blueprint_json}',
        'job'
    ]
    
    try:
        result = subprocess.run(cmd, cwd='/app')
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Job interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Error running job: {e}")
        return 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: uv run python run_local_job.py <task_id>")
        print()
        print("Example:")
        print("  uv run python run_local_job.py 5e0ebecf-71b9-4eb8-aedf-619658c2084d")
        sys.exit(1)
    
    task_id = sys.argv[1]
    sys.exit(run_job(task_id))
