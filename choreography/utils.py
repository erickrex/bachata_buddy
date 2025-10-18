"""
Task management utilities for background choreography generation.

This module provides thread-safe task storage and management for tracking
the progress of background choreography generation tasks.
"""

import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


# In-memory task storage with thread-safe access
_active_tasks: Dict[str, Dict[str, Any]] = {}
_task_lock = threading.Lock()


def create_task(task_id: str, user_id: int, **kwargs) -> Dict[str, Any]:
    """
    Create a new task in storage.
    
    Args:
        task_id: Unique identifier for the task
        user_id: ID of the user who owns this task
        **kwargs: Additional task data
        
    Returns:
        The created task data dictionary
    """
    with _task_lock:
        task_data = {
            'task_id': task_id,
            'status': 'started',
            'progress': 0,
            'stage': 'initializing',
            'message': 'Starting choreography generation...',
            'result': None,
            'error': None,
            'user_id': user_id,
            'created_at': time.time(),
            **kwargs
        }
        _active_tasks[task_id] = task_data
        return task_data.copy()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a task from storage.
    
    Args:
        task_id: Unique identifier for the task
        
    Returns:
        Task data dictionary if found, None otherwise
    """
    with _task_lock:
        task_data = _active_tasks.get(task_id)
        return task_data.copy() if task_data else None


def update_task(task_id: str, **updates) -> bool:
    """
    Update an existing task with new data.
    
    Args:
        task_id: Unique identifier for the task
        **updates: Fields to update in the task
        
    Returns:
        True if task was updated, False if task not found
    """
    with _task_lock:
        if task_id in _active_tasks:
            _active_tasks[task_id].update(updates)
            return True
        return False


def cleanup_old_tasks(max_age_hours: int = 1) -> int:
    """
    Remove tasks older than the specified age.
    
    This function should be called periodically to prevent memory buildup
    from completed or failed tasks.
    
    Args:
        max_age_hours: Maximum age of tasks to keep (default: 1 hour)
        
    Returns:
        Number of tasks removed
    """
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    removed_count = 0
    
    with _task_lock:
        # Find tasks to remove
        tasks_to_remove = [
            task_id
            for task_id, task_data in _active_tasks.items()
            if current_time - task_data.get('created_at', 0) > max_age_seconds
        ]
        
        # Remove old tasks
        for task_id in tasks_to_remove:
            del _active_tasks[task_id]
            removed_count += 1
    
    return removed_count


def get_all_tasks() -> Dict[str, Dict[str, Any]]:
    """
    Get all active tasks (for debugging/monitoring).
    
    Returns:
        Dictionary of all active tasks
    """
    with _task_lock:
        return {task_id: task_data.copy() for task_id, task_data in _active_tasks.items()}


def delete_task(task_id: str) -> bool:
    """
    Delete a specific task from storage.
    
    Args:
        task_id: Unique identifier for the task
        
    Returns:
        True if task was deleted, False if task not found
    """
    with _task_lock:
        if task_id in _active_tasks:
            del _active_tasks[task_id]
            return True
        return False


def list_all_tasks() -> dict:
    """
    List all active tasks with summary statistics.
    
    Returns:
        Dictionary with task summary and all task data
    """
    with _task_lock:
        tasks_copy = {task_id: task_data.copy() for task_id, task_data in _active_tasks.items()}
        
        return {
            'total_tasks': len(tasks_copy),
            'running_tasks': len([t for t in tasks_copy.values() if t['status'] == 'running']),
            'completed_tasks': len([t for t in tasks_copy.values() if t['status'] == 'completed']),
            'failed_tasks': len([t for t in tasks_copy.values() if t['status'] == 'failed']),
            'tasks': tasks_copy
        }
