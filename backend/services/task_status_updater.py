"""
Task Status Updater Service

Simple service for updating choreography task status in the database.
Used by mock job service for local development.
"""
import logging
from apps.choreography.models import ChoreographyTask

logger = logging.getLogger(__name__)


class TaskStatusUpdater:
    """
    Service for updating task status in the database.
    
    Provides a simple interface for updating task progress, status, and results.
    """
    
    def update_task_status(self, task_id, status, progress=None, stage=None, message=None, result=None, error=None):
        """
        Update task status in database.
        
        Args:
            task_id: UUID of the task
            status: New status (pending, started, running, completed, failed)
            progress: Progress percentage (0-100)
            stage: Current stage of processing
            message: Status message
            result: Result data (dict)
            error: Error message if failed
        """
        try:
            task = ChoreographyTask.objects.get(task_id=str(task_id))
            
            # Update fields if provided
            if status is not None:
                task.status = status
            if progress is not None:
                task.progress = progress
            if stage is not None:
                task.stage = stage
            if message is not None:
                task.message = message
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            
            task.save()
            
            logger.info(f"Updated task {task_id}: status={status}, progress={progress}")
            return True
            
        except ChoreographyTask.DoesNotExist:
            logger.error(f"Task {task_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return False
    
    def mark_task_completed(self, task_id, result):
        """
        Mark task as completed with result.
        
        Args:
            task_id: UUID of the task
            result: Result data (dict)
        """
        return self.update_task_status(
            task_id=task_id,
            status='completed',
            progress=100,
            stage='completed',
            message='Choreography generated successfully',
            result=result
        )
    
    def mark_task_failed(self, task_id, error):
        """
        Mark task as failed with error message.
        
        Args:
            task_id: UUID of the task
            error: Error message
        """
        return self.update_task_status(
            task_id=task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='Choreography generation failed',
            error=error
        )
