"""
Simple Task Status Updater for Local Development

This utility provides a simple interface for updating choreography task status
in the database. It's used by the mock job service and can be used by the real
Cloud Run Job service as well.

Usage:
    from services.task_status_updater import TaskStatusUpdater
    
    updater = TaskStatusUpdater()
    
    # Update task status
    updater.update_status(
        task_id="uuid",
        status="processing",
        progress=50,
        stage="analyzing",
        message="Analyzing music features..."
    )
    
    # Mark task as completed
    updater.mark_completed(
        task_id="uuid",
        result={
            "video_url": "gs://bucket/video.mp4",
            "duration": 180.5
        }
    )
    
    # Mark task as failed
    updater.mark_failed(
        task_id="uuid",
        error="Failed to download audio"
    )
"""
import logging
from typing import Dict, Any, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


class TaskStatusUpdater:
    """
    Simple utility for updating choreography task status in the database.
    
    This class provides a clean interface for updating task status, progress,
    and results. It handles all the database operations and logging.
    """
    
    def __init__(self):
        """Initialize the task status updater"""
        logger.debug("TaskStatusUpdater initialized")
    
    def update_status(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        message: Optional[str] = None
    ) -> bool:
        """
        Update task status fields
        
        Args:
            task_id: UUID of the choreography task
            status: New status ('started', 'running', 'completed', 'failed')
            progress: Progress percentage (0-100)
            stage: Current stage name
            message: User-friendly status message
        
        Returns:
            True if update successful, False otherwise
        """
        from apps.choreography.models import ChoreographyTask
        
        try:
            task = ChoreographyTask.objects.get(task_id=task_id)
            
            # Update fields if provided
            if status is not None:
                task.status = status
            if progress is not None:
                task.progress = max(0, min(100, progress))  # Clamp to 0-100
            if stage is not None:
                task.stage = stage
            if message is not None:
                task.message = message
            
            task.save()
            
            logger.info(
                f"Task status updated: {task_id}",
                extra={
                    'task_id': task_id,
                    'status': task.status,
                    'progress': task.progress,
                    'stage': task.stage
                }
            )
            
            return True
            
        except ChoreographyTask.DoesNotExist:
            logger.error(
                f"Task not found: {task_id}",
                extra={'task_id': task_id}
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to update task status: {e}",
                extra={'task_id': task_id, 'error': str(e)},
                exc_info=True
            )
            return False
    
    def mark_completed(
        self,
        task_id: str,
        result: Dict[str, Any],
        message: str = "Choreography generated successfully!"
    ) -> bool:
        """
        Mark task as completed with result
        
        Args:
            task_id: UUID of the choreography task
            result: Result data (video_url, thumbnail_url, duration, etc.)
            message: Success message
        
        Returns:
            True if update successful, False otherwise
        """
        from apps.choreography.models import ChoreographyTask
        
        try:
            task = ChoreographyTask.objects.get(task_id=task_id)
            
            task.status = 'completed'
            task.progress = 100
            task.stage = 'completed'
            task.message = message
            task.result = result
            task.error = None
            
            task.save()
            
            logger.info(
                f"Task marked as completed: {task_id}",
                extra={
                    'task_id': task_id,
                    'result': result
                }
            )
            
            return True
            
        except ChoreographyTask.DoesNotExist:
            logger.error(
                f"Task not found: {task_id}",
                extra={'task_id': task_id}
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to mark task as completed: {e}",
                extra={'task_id': task_id, 'error': str(e)},
                exc_info=True
            )
            return False
    
    def mark_failed(
        self,
        task_id: str,
        error: str,
        message: str = "Job failed"
    ) -> bool:
        """
        Mark task as failed with error message
        
        Args:
            task_id: UUID of the choreography task
            error: Error message
            message: User-friendly failure message
        
        Returns:
            True if update successful, False otherwise
        """
        from apps.choreography.models import ChoreographyTask
        
        try:
            task = ChoreographyTask.objects.get(task_id=task_id)
            
            task.status = 'failed'
            task.progress = 0
            task.stage = 'failed'
            task.message = message
            task.error = error
            task.result = None
            
            task.save()
            
            logger.info(
                f"Task marked as failed: {task_id}",
                extra={
                    'task_id': task_id,
                    'error': error
                }
            )
            
            return True
            
        except ChoreographyTask.DoesNotExist:
            logger.error(
                f"Task not found: {task_id}",
                extra={'task_id': task_id}
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to mark task as failed: {e}",
                extra={'task_id': task_id, 'error': str(e)},
                exc_info=True
            )
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current task status
        
        Args:
            task_id: UUID of the choreography task
        
        Returns:
            Dict with task status information, or None if not found
        """
        from apps.choreography.models import ChoreographyTask
        
        try:
            task = ChoreographyTask.objects.get(task_id=task_id)
            
            return {
                'task_id': str(task.task_id),
                'status': task.status,
                'progress': task.progress,
                'stage': task.stage,
                'message': task.message,
                'result': task.result,
                'error': task.error,
                'created_at': task.created_at,
                'updated_at': task.updated_at
            }
            
        except ChoreographyTask.DoesNotExist:
            logger.warning(
                f"Task not found: {task_id}",
                extra={'task_id': task_id}
            )
            return None
        except Exception as e:
            logger.error(
                f"Failed to get task status: {e}",
                extra={'task_id': task_id, 'error': str(e)},
                exc_info=True
            )
            return None
