#!/usr/bin/env python
"""
Local Job Runner - Manually execute video assembly jobs in development

This script fetches the blueprint from the database and runs the job container
with Docker Compose to generate the actual video.

Usage (from backend directory):
    cd backend
    uv run python run_local_job.py <task_id>
    
Example:
    cd backend
    uv run python run_local_job.py c0f4d712-3895-440a-988d-5ad7999d39f6
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Check if we're in the right directory
if not os.path.exists('manage.py'):
    print("❌ Error: This script must be run from the backend directory")
    print()
    print("Please run:")
    print("  cd backend")
    print(f"  uv run python run_local_job.py {sys.argv[1] if len(sys.argv) > 1 else '<task_id>'}")
    sys.exit(1)

# Load .env file manually before Django setup
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

import django

# Setup Django with database connection
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

# Database connection: Check if we should use Docker or native PostgreSQL
# By default, use 'db' hostname (Docker) - override with DB_HOST=localhost for native
db_host = os.environ.get('DB_HOST', 'db')

# If using Docker's 'db' hostname, we need to check if we're running inside or outside Docker
# Outside Docker: use 'host.docker.internal' or the Docker network IP
# For simplicity, we'll use localhost and assume Docker's db is mapped to port 5432
if db_host == 'db':
    # Running outside Docker, connect via localhost (Docker maps 5432:5432)
    # NOTE: If you have native PostgreSQL also on 5432, stop it or use a different port
    os.environ['DB_HOST'] = 'localhost'
else:
    os.environ['DB_HOST'] = db_host

django.setup()

from django.db import connection
from apps.choreography.models import ChoreographyTask


def run_job(task_id: str):
    """Run the video assembly job for a specific task"""
    
    print(f"🎬 Running job for task: {task_id}")
    print("=" * 60)
    
    # Debug: Print database connection info
    db_settings = connection.settings_dict
    print(f"📊 Database: {db_settings['NAME']} @ {db_settings['HOST']}:{db_settings['PORT']}")
    print("=" * 60)
    
    # Get task from database
    try:
        task = ChoreographyTask.objects.get(task_id=task_id)
    except ChoreographyTask.DoesNotExist:
        print(f"❌ Error: Task {task_id} not found in database")
        return 1
    
    print(f"✓ Task found: {task.status}")
    print(f"✓ User ID: {task.user_id}")
    
    # Get blueprint from related Blueprint model
    try:
        blueprint = task.blueprint  # OneToOne relation
        blueprint_dict = blueprint.blueprint_json
        print(f"✓ Blueprint exists: True")
        print(f"✓ Moves count: {len(blueprint_dict.get('moves', []))}")
    except Exception as e:
        print(f"❌ Error: Task has no blueprint - {e}")
        return 1
    
    # Convert blueprint to JSON string
    if isinstance(blueprint_dict, dict):
        blueprint_json = json.dumps(blueprint_dict, separators=(',', ':'))
    else:
        blueprint_json = json.dumps(blueprint_dict, separators=(',', ':'), default=str)
    
    print(f"✓ Blueprint size: {len(blueprint_json)} bytes")
    print()
    print("🚀 Starting Docker job container...")
    print("=" * 60)
    
    # Get the parent directory (bachata_buddy)
    parent_dir = os.path.dirname(os.getcwd())
    
    # Run the job container from the parent directory
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
        result = subprocess.run(cmd, cwd=parent_dir)
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
        print("  cd backend")
        print("  uv run python run_local_job.py c0f4d712-3895-440a-988d-5ad7999d39f6")
        sys.exit(1)
    
    task_id = sys.argv[1]
    sys.exit(run_job(task_id))
