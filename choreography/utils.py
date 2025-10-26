"""
Task management utilities for background choreography generation.

This module provides database-backed task storage and management for tracking
the progress of background choreography generation tasks.

Uses Django ORM for persistent storage across container restarts in Cloud Run.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


def create_task(task_id: str, user_id: int, **kwargs) -> Dict[str, Any]:
    """
    Create a new task in database storage.
    
    Args:
        task_id: Unique identifier for the task
        user_id: ID of the user who owns this task
        **kwargs: Additional task data
        
    Returns:
        The created task data dictionary
    """
    from .models import ChoreographyTask
    
    try:
        user = User.objects.get(id=user_id)
        task = ChoreographyTask.objects.create(
            task_id=task_id,
            user=user,
            status=kwargs.get('status', 'started'),
            progress=kwargs.get('progress', 0),
            stage=kwargs.get('stage', 'initializing'),
            message=kwargs.get('message', 'Starting choreography generation...'),
            result=kwargs.get('result'),
            error=kwargs.get('error'),
        )
        logger.info(f"Created task {task_id} for user {user_id}")
        return task.to_dict()
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found when creating task {task_id}")
        raise
    except Exception as e:
        logger.error(f"Error creating task {task_id}: {e}", exc_info=True)
        raise


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a task from database storage.
    
    Args:
        task_id: Unique identifier for the task
        
    Returns:
        Task data dictionary if found, None otherwise
    """
    from .models import ChoreographyTask
    
    try:
        task = ChoreographyTask.objects.get(task_id=task_id)
        return task.to_dict()
    except ChoreographyTask.DoesNotExist:
        logger.debug(f"Task {task_id} not found in database")
        return None
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {e}", exc_info=True)
        return None


def update_task(task_id: str, **updates) -> bool:
    """
    Update an existing task with new data.
    
    Args:
        task_id: Unique identifier for the task
        **updates: Fields to update in the task
        
    Returns:
        True if task was updated, False if task not found
    """
    from .models import ChoreographyTask
    
    try:
        task = ChoreographyTask.objects.get(task_id=task_id)
        
        # Update allowed fields
        for field in ['status', 'progress', 'stage', 'message', 'result', 'error']:
            if field in updates:
                setattr(task, field, updates[field])
        
        task.save()
        logger.debug(f"Updated task {task_id}: {updates}")
        return True
    except ChoreographyTask.DoesNotExist:
        logger.warning(f"Cannot update task {task_id}: not found")
        return False
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}", exc_info=True)
        return False


def cleanup_old_tasks(max_age_hours: int = 24) -> int:
    """
    Remove tasks older than the specified age.
    
    This function should be called periodically to prevent database buildup
    from completed or failed tasks.
    
    Args:
        max_age_hours: Maximum age of tasks to keep (default: 24 hours)
        
    Returns:
        Number of tasks removed
    """
    from .models import ChoreographyTask
    
    try:
        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)
        deleted_count, _ = ChoreographyTask.objects.filter(
            created_at__lt=cutoff_time
        ).delete()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old tasks")
        
        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {e}", exc_info=True)
        return 0


def get_all_tasks() -> Dict[str, Dict[str, Any]]:
    """
    Get all active tasks (for debugging/monitoring).
    
    Returns:
        Dictionary of all active tasks
    """
    from .models import ChoreographyTask
    
    try:
        tasks = ChoreographyTask.objects.all()
        return {task.task_id: task.to_dict() for task in tasks}
    except Exception as e:
        logger.error(f"Error getting all tasks: {e}", exc_info=True)
        return {}


def delete_task(task_id: str) -> bool:
    """
    Delete a specific task from storage.
    
    Args:
        task_id: Unique identifier for the task
        
    Returns:
        True if task was deleted, False if task not found
    """
    from .models import ChoreographyTask
    
    try:
        task = ChoreographyTask.objects.get(task_id=task_id)
        task.delete()
        logger.info(f"Deleted task {task_id}")
        return True
    except ChoreographyTask.DoesNotExist:
        logger.warning(f"Cannot delete task {task_id}: not found")
        return False
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}", exc_info=True)
        return False


def list_all_tasks() -> dict:
    """
    List all active tasks with summary statistics.
    
    Returns:
        Dictionary with task summary and all task data
    """
    from .models import ChoreographyTask
    
    try:
        tasks = ChoreographyTask.objects.all()
        tasks_dict = {task.task_id: task.to_dict() for task in tasks}
        
        return {
            'total_tasks': len(tasks_dict),
            'running_tasks': len([t for t in tasks_dict.values() if t['status'] == 'running']),
            'completed_tasks': len([t for t in tasks_dict.values() if t['status'] == 'completed']),
            'failed_tasks': len([t for t in tasks_dict.values() if t['status'] == 'failed']),
            'tasks': tasks_dict
        }
    except Exception as e:
        logger.error(f"Error listing all tasks: {e}", exc_info=True)
        return {
            'total_tasks': 0,
            'running_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'tasks': {}
        }


def cleanup_stuck_tasks(max_age_minutes: int = 10) -> int:
    """
    CRITICAL: Clean up tasks stuck in running/started state.
    
    This prevents the concurrency limit from being reached by zombie tasks
    that never completed due to container restarts or crashes.
    
    Args:
        max_age_minutes: Maximum age of tasks to keep (default: 10 minutes)
        
    Returns:
        Number of tasks cleaned up
    """
    from .models import ChoreographyTask
    
    try:
        cutoff_time = timezone.now() - timedelta(minutes=max_age_minutes)
        
        # Find tasks stuck in running/started state
        stuck_tasks = ChoreographyTask.objects.filter(
            status__in=['running', 'started'],
            created_at__lt=cutoff_time
        )
        
        count = stuck_tasks.count()
        
        if count > 0:
            logger.warning(f"Cleaning up {count} stuck tasks older than {max_age_minutes} minutes")
            # Mark them as failed instead of deleting (for debugging)
            stuck_tasks.update(
                status='failed',
                error=f'Task stuck for more than {max_age_minutes} minutes - likely container restart',
                progress=0
            )
        
        return count
    except Exception as e:
        logger.error(f"Error cleaning up stuck tasks: {e}", exc_info=True)
        return 0
