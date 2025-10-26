#!/usr/bin/env python
"""
Clean up stuck choreography tasks from the database.
This script deletes tasks that are stuck in 'running' or 'started' state.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bachata_buddy.settings')
django.setup()

from choreography.models import ChoreographyTask
from django.utils import timezone
from datetime import timedelta

def cleanup_stuck_tasks():
    """Delete tasks stuck in running/started state for more than 10 minutes."""
    
    # Find tasks stuck in running/started state
    cutoff_time = timezone.now() - timedelta(minutes=10)
    
    stuck_tasks = ChoreographyTask.objects.filter(
        status__in=['running', 'started'],
        created_at__lt=cutoff_time
    )
    
    count = stuck_tasks.count()
    
    if count == 0:
        print("✅ No stuck tasks found")
        return
    
    print(f"🧹 Found {count} stuck tasks:")
    for task in stuck_tasks:
        age_minutes = (timezone.now() - task.created_at).total_seconds() / 60
        print(f"  - Task {task.task_id}: {task.status}, age: {age_minutes:.1f} minutes")
    
    # Delete them
    stuck_tasks.delete()
    print(f"✅ Deleted {count} stuck tasks")

if __name__ == '__main__':
    cleanup_stuck_tasks()
