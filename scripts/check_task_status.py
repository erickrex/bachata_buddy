#!/usr/bin/env python
"""Check the status of a specific task in the database."""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bachata_buddy.settings')
django.setup()

from choreography.models import ChoreographyTask

def check_task(task_id):
    """Check task status."""
    try:
        task = ChoreographyTask.objects.get(task_id=task_id)
        print(f"Task ID: {task.task_id}")
        print(f"Status: {task.status}")
        print(f"Progress: {task.progress}%")
        print(f"Stage: {task.stage}")
        print(f"Message: {task.message}")
        print(f"Error: {task.error}")
        print(f"Created: {task.created_at}")
        print(f"Updated: {task.updated_at}")
    except ChoreographyTask.DoesNotExist:
        print(f"Task {task_id} not found")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_task_status.py <task_id>")
        sys.exit(1)
    
    check_task(sys.argv[1])
