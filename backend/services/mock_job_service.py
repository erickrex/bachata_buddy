"""
Mock Job Service for Local Development

Simulates Cloud Run Job execution for local testing without requiring
actual Cloud Run infrastructure. Uses blueprint-based architecture.

Usage:
    # In local development, use this instead of CloudRunJobsService
    import json
    from services.mock_job_service import MockJobService
    
    service = MockJobService()
    
    # Create blueprint
    blueprint = {
        "task_id": "uuid",
        "audio_path": "gs://bucket/song.mp3",
        "moves": [...],
        "output_config": {...}
    }
    
    # Submit job with blueprint
    execution_name = service.create_job_execution(
        task_id="uuid",
        user_id=123,
        parameters={"blueprint_json": json.dumps(blueprint)}
    )
    
    # Manually trigger job completion
    service.complete_job(task_id, success=True, result={...})
"""
import logging
import time
import threading
from typing import Dict, Any, Optional
from django.utils import timezone
from services.task_status_updater import TaskStatusUpdater

logger = logging.getLogger(__name__)


class MockJobService:
    """
    Mock service for simulating Cloud Run Job executions locally.
    
    This service allows testing the full choreography generation flow
    without requiring Cloud Run infrastructure. It provides methods to:
    - Create mock job executions
    - Manually trigger job completion
    - Simulate job progress updates
    """
    
    def __init__(self):
        self.project_id = 'local-dev'
        self.region = 'local'
        self.job_name = 'video-processor-mock'
        self._active_jobs = {}  # Track active mock jobs
        self.status_updater = TaskStatusUpdater()  # Use the simple status updater
        logger.info("MockJobService initialized for local development")
    
    def create_job_execution(self, task_id: str, user_id: int, parameters: Dict[str, Any]) -> str:
        """
        Create a mock job execution
        
        Args:
            task_id: UUID of the choreography task
            user_id: ID of the user
            parameters: Dict with blueprint_json (required)
        
        Returns:
            Mock execution name string
        """
        execution_name = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}/executions/mock-{task_id}"
        
        # Store job info for later reference
        self._active_jobs[task_id] = {
            'execution_name': execution_name,
            'user_id': user_id,
            'parameters': parameters,
            'status': 'pending',
            'created_at': timezone.now()
        }
        
        logger.info(
            f"Mock job execution created: {execution_name}",
            extra={
                'task_id': task_id,
                'user_id': user_id,
                'execution_name': execution_name,
                'parameters': parameters,
                'mode': 'mock'
            }
        )
        
        return execution_name
    
    def complete_job(self, task_id: str, success: bool = True, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """
        Manually complete a mock job execution
        
        This method updates the task status in the database to simulate
        job completion. Use this in local development to test the full flow.
        
        Args:
            task_id: UUID of the choreography task
            success: Whether the job completed successfully
            result: Result data (for successful jobs)
            error: Error message (for failed jobs)
        """
        try:
            if success:
                # Use status updater to mark as completed
                default_result = {
                    'video_url': f'gs://mock-bucket/choreographies/mock-{task_id}.mp4',
                    'thumbnail_url': f'gs://mock-bucket/thumbnails/mock-{task_id}.jpg',
                    'duration': 180.5,
                    'moves_count': 12
                }
                updated = self.status_updater.mark_completed(
                    task_id=task_id,
                    result=result or default_result
                )
            else:
                # Use status updater to mark as failed
                updated = self.status_updater.mark_failed(
                    task_id=task_id,
                    error=error or 'Mock job failure'
                )
            
            if not updated:
                raise ValueError(f"Task {task_id} not found")
            
            # Update active jobs tracking
            if task_id in self._active_jobs:
                self._active_jobs[task_id]['status'] = 'completed' if success else 'failed'
            
            logger.info(
                f"Mock job completed for task {task_id}",
                extra={
                    'task_id': task_id,
                    'success': success,
                    'mode': 'mock'
                }
            )
            
        except ValueError:
            logger.error(
                f"Task {task_id} not found when completing mock job",
                extra={'task_id': task_id, 'mode': 'mock'}
            )
            raise
    
    def simulate_job_progress(self, task_id: str, duration_seconds: int = 10):
        """
        Simulate job progress over time (runs in background thread)
        
        This method simulates a realistic job execution by updating
        the task progress incrementally over the specified duration.
        
        Args:
            task_id: UUID of the choreography task
            duration_seconds: How long the simulation should take
        """
        def _progress_updater():
            stages = [
                (10, 'downloading', 'Downloading audio...'),
                (30, 'analyzing', 'Analyzing music features...'),
                (50, 'querying', 'Finding matching moves...'),
                (70, 'generating', 'Generating choreography sequence...'),
                (90, 'processing', 'Processing video...'),
                (100, 'uploading', 'Uploading result...'),
            ]
            
            try:
                # Update status to processing
                self.status_updater.update_status(
                    task_id=task_id,
                    status='running'
                )
                
                step_duration = duration_seconds / len(stages)
                
                for progress, stage, message in stages:
                    time.sleep(step_duration)
                    
                    # Use status updater for each progress update
                    self.status_updater.update_status(
                        task_id=task_id,
                        progress=progress,
                        stage=stage,
                        message=message
                    )
                    
                    logger.debug(
                        f"Mock job progress update: {progress}%",
                        extra={
                            'task_id': task_id,
                            'progress': progress,
                            'stage': stage,
                            'mode': 'mock'
                        }
                    )
                
                # Complete the job
                self.complete_job(task_id, success=True)
                
            except Exception as e:
                logger.error(
                    f"Error during progress simulation: {e}",
                    extra={'task_id': task_id, 'error': str(e), 'mode': 'mock'},
                    exc_info=True
                )
                self.complete_job(task_id, success=False, error=str(e))
        
        # Start progress simulation in background thread
        thread = threading.Thread(target=_progress_updater, daemon=True)
        thread.start()
        
        logger.info(
            f"Started mock job progress simulation for task {task_id}",
            extra={
                'task_id': task_id,
                'duration_seconds': duration_seconds,
                'mode': 'mock'
            }
        )
    
    def cancel_job_execution(self, execution_name: str) -> bool:
        """
        Cancel a mock job execution
        
        Args:
            execution_name: Mock execution name
        
        Returns:
            True if cancelled successfully
        """
        # Extract task_id from execution name
        task_id = execution_name.split('mock-')[-1] if 'mock-' in execution_name else None
        
        if task_id and task_id in self._active_jobs:
            self._active_jobs[task_id]['status'] = 'cancelled'
            
            logger.info(
                f"Mock job execution cancelled: {execution_name}",
                extra={
                    'execution_name': execution_name,
                    'task_id': task_id,
                    'mode': 'mock'
                }
            )
            return True
        
        logger.warning(
            f"Mock job execution not found for cancellation: {execution_name}",
            extra={'execution_name': execution_name, 'mode': 'mock'}
        )
        return False
    
    def get_job_execution_status(self, execution_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a mock job execution
        
        Args:
            execution_name: Mock execution name
        
        Returns:
            Dict with execution status information
        """
        # Extract task_id from execution name
        task_id = execution_name.split('mock-')[-1] if 'mock-' in execution_name else None
        
        if task_id and task_id in self._active_jobs:
            job_info = self._active_jobs[task_id]
            return {
                'name': execution_name,
                'status': job_info['status'],
                'start_time': job_info['created_at'],
                'completion_time': None,
            }
        
        return {
            'name': execution_name,
            'status': 'unknown',
            'start_time': None,
            'completion_time': None,
        }
    
    def get_active_jobs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active mock jobs
        
        Returns:
            Dict mapping task_id to job info
        """
        return self._active_jobs.copy()
