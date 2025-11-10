"""
Cloud Run Jobs Service

Handles creation and management of Cloud Run Job executions for video processing.
Uses blueprint-based architecture where the API generates complete video assembly
instructions and the job container simply executes them.

Service Account Requirements:
    The Cloud Run service using this class must have the following IAM roles:
    - roles/run.developer: Create and manage Cloud Run Job executions
    - roles/cloudsql.client: Connect to Cloud SQL (for task status updates)
    - roles/storage.objectAdmin: Read/write Cloud Storage (for videos/audio)
    - roles/secretmanager.secretAccessor: Read secrets (DB password, API keys)

    Setup:
        Run scripts/setup_service_account_permissions.sh to configure permissions.
        See backend/SERVICE_ACCOUNT_SETUP.md for detailed documentation.

Usage:
    import json
    from services.jobs_service import CloudRunJobsService
    
    # Generate blueprint (done by BlueprintGenerator)
    blueprint = {
        "task_id": "uuid",
        "audio_path": "gs://bucket/song.mp3",
        "moves": [...],
        "output_config": {...}
    }
    
    # Submit job with blueprint
    service = CloudRunJobsService()
    execution_name = service.create_job_execution(
        task_id="uuid",
        user_id=123,
        parameters={"blueprint_json": json.dumps(blueprint)}
    )
"""
import os
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class JobExecutionError(Exception):
    """Raised when job execution fails"""
    pass


class JobCancellationError(Exception):
    """Raised when job cancellation fails"""
    pass


class CloudRunJobsService:
    """Service for managing Cloud Run Jobs"""
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    RETRY_BACKOFF = 2  # exponential backoff multiplier
    
    def __init__(self):
        self.project_id = os.environ.get('GCP_PROJECT_ID', 'local-dev')
        self.region = os.environ.get('GCP_REGION', 'us-central1')
        self.job_name = 'video-processor'
        
        # Only import google-cloud-run in production
        if self.project_id != 'local-dev':
            try:
                from google.cloud import run_v2
                self.client = run_v2.JobsClient()
            except ImportError:
                logger.warning("google-cloud-run not installed, using mock mode")
                self.client = None
        else:
            self.client = None
            logger.info("Running in local-dev mode, Cloud Run Jobs disabled")
    
    def create_job_execution(self, task_id: str, user_id: int, parameters: Dict[str, Any]) -> str:
        """
        Create a Cloud Run Job execution with retry logic
        
        Args:
            task_id: UUID of the choreography task
            user_id: ID of the user
            parameters: Dict with blueprint_json (required)
        
        Returns:
            Execution name string
            
        Raises:
            JobExecutionError: If job creation fails after all retries
        """
        logger.info(
            f"Job creation requested for task {task_id}",
            extra={
                'task_id': task_id,
                'user_id': user_id,
                'has_blueprint': bool(parameters.get('blueprint_json')),
                'project_id': self.project_id,
                'region': self.region,
                'job_name': self.job_name
            }
        )
        
        if self.client is None:
            # Local development mode - return mock execution name
            execution_name = f"local-dev-execution-{task_id}"
            logger.info(
                f"Mock job execution created: {execution_name}",
                extra={'task_id': task_id, 'execution_name': execution_name, 'mode': 'local-dev'}
            )
            return execution_name
        
        # Validate required parameters (blueprint_json is required)
        if not parameters.get('blueprint_json'):
            logger.error(
                f"Job creation failed: missing blueprint_json parameter",
                extra={'task_id': task_id, 'user_id': user_id, 'parameters': parameters}
            )
            raise JobExecutionError("Missing required parameter: blueprint_json")
        
        logger.debug(
            f"Parameters validated successfully for task {task_id}",
            extra={'task_id': task_id, 'blueprint_size': len(parameters['blueprint_json'])}
        )
        
        # Retry logic
        last_exception = None
        delay = self.RETRY_DELAY
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(
                    f"Creating Cloud Run Job execution for task {task_id} (attempt {attempt}/{self.MAX_RETRIES})",
                    extra={
                        'task_id': task_id,
                        'user_id': user_id,
                        'attempt': attempt,
                        'max_retries': self.MAX_RETRIES,
                        'retry_delay': delay
                    }
                )
                
                execution_name = self._create_job_execution_internal(task_id, user_id, parameters)
                
                logger.info(
                    f"Job execution created successfully: {execution_name}",
                    extra={
                        'task_id': task_id,
                        'user_id': user_id,
                        'execution_name': execution_name,
                        'attempt': attempt,
                        'success': True
                    }
                )
                return execution_name
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Job creation attempt {attempt}/{self.MAX_RETRIES} failed for task {task_id}: {e}",
                    extra={
                        'task_id': task_id,
                        'user_id': user_id,
                        'attempt': attempt,
                        'max_retries': self.MAX_RETRIES,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    },
                    exc_info=True
                )
                
                # Don't retry on validation errors
                if self._is_non_retryable_error(e):
                    logger.error(
                        f"Non-retryable error encountered: {e}",
                        extra={
                            'task_id': task_id,
                            'user_id': user_id,
                            'error_type': type(e).__name__,
                            'error_message': str(e),
                            'retryable': False
                        }
                    )
                    raise JobExecutionError(f"Job creation failed: {e}") from e
                
                # If not the last attempt, wait before retrying
                if attempt < self.MAX_RETRIES:
                    logger.info(
                        f"Retrying in {delay} seconds...",
                        extra={
                            'task_id': task_id,
                            'attempt': attempt,
                            'next_attempt': attempt + 1,
                            'delay_seconds': delay
                        }
                    )
                    time.sleep(delay)
                    delay *= self.RETRY_BACKOFF  # Exponential backoff
        
        # All retries exhausted
        error_msg = f"Failed to create job execution after {self.MAX_RETRIES} attempts: {last_exception}"
        logger.error(
            error_msg,
            extra={
                'task_id': task_id,
                'user_id': user_id,
                'total_attempts': self.MAX_RETRIES,
                'final_error_type': type(last_exception).__name__,
                'final_error_message': str(last_exception)
            }
        )
        raise JobExecutionError(error_msg) from last_exception
    
    def _create_job_execution_internal(self, task_id: str, user_id: int, parameters: Dict[str, Any]) -> str:
        """
        Internal method to create job execution (without retry logic)
        
        Args:
            task_id: UUID of the choreography task
            user_id: ID of the user
            parameters: Dict with blueprint_json (required)
        
        Returns:
            Execution name string
        """
        from google.cloud import run_v2
        
        job_path = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"
        
        logger.debug(
            f"Preparing job execution request for task {task_id}",
            extra={
                'task_id': task_id,
                'user_id': user_id,
                'job_path': job_path,
                'blueprint_size': len(parameters['blueprint_json'])
            }
        )
        
        # Build environment variables for the job
        env_vars = [
            {"name": "TASK_ID", "value": str(task_id)},
            {"name": "USER_ID", "value": str(user_id)},
            {"name": "BLUEPRINT_JSON", "value": parameters['blueprint_json']},
        ]
        
        logger.info(
            f"Using blueprint-based architecture for task {task_id}",
            extra={
                'task_id': task_id,
                'blueprint_size': len(parameters['blueprint_json'])
            }
        )
        
        # Create job execution request
        request = run_v2.RunJobRequest(
            name=job_path,
            overrides={
                "container_overrides": [{
                    "env": env_vars
                }]
            }
        )
        
        # Trigger the job
        logger.debug(
            f"Sending job execution request to Cloud Run Jobs API",
            extra={'task_id': task_id, 'job_path': job_path}
        )
        operation = self.client.run_job(request=request)
        
        # Wait for job to start with timeout
        try:
            logger.debug(
                f"Waiting for job execution to start (timeout: 30s)",
                extra={'task_id': task_id, 'operation_name': operation.operation.name}
            )
            execution = operation.result(timeout=30)  # 30 second timeout
            logger.info(
                f"Job execution started successfully",
                extra={
                    'task_id': task_id,
                    'execution_name': execution.name,
                    'operation_name': operation.operation.name
                }
            )
        except Exception as e:
            logger.error(
                f"Timeout or error waiting for job to start: {e}",
                extra={
                    'task_id': task_id,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'timeout_seconds': 30
                },
                exc_info=True
            )
            raise
        
        return execution.name
    
    def _is_non_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error should not be retried
        
        Args:
            error: The exception that occurred
        
        Returns:
            True if error should not be retried, False otherwise
        """
        error_str = str(error).lower()
        
        # Don't retry on validation errors
        non_retryable_patterns = [
            'invalid',
            'not found',
            'permission denied',
            'unauthorized',
            'forbidden',
            'bad request',
            'missing required',
        ]
        
        return any(pattern in error_str for pattern in non_retryable_patterns)
    
    def cancel_job_execution(self, execution_name: str) -> bool:
        """
        Cancel a Cloud Run Job execution with retry logic
        
        Args:
            execution_name: Full execution name (e.g., projects/.../executions/xxx)
        
        Returns:
            True if cancellation was successful, False if job already completed
            
        Raises:
            JobCancellationError: If cancellation fails after all retries
        """
        logger.info(
            f"Job cancellation requested",
            extra={'execution_name': execution_name}
        )
        
        if self.client is None:
            # Local development mode - mock cancellation
            logger.info(
                f"Mock job execution cancelled: {execution_name}",
                extra={'execution_name': execution_name, 'mode': 'local-dev'}
            )
            return True
        
        if not execution_name:
            logger.error("Job cancellation failed: execution name is required")
            raise JobCancellationError("Execution name is required")
        
        # Retry logic for cancellation
        last_exception = None
        delay = self.RETRY_DELAY
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(
                    f"Cancelling job execution {execution_name} (attempt {attempt}/{self.MAX_RETRIES})",
                    extra={
                        'execution_name': execution_name,
                        'attempt': attempt,
                        'max_retries': self.MAX_RETRIES
                    }
                )
                
                result = self._cancel_job_execution_internal(execution_name)
                
                if result:
                    logger.info(
                        f"Job execution cancelled successfully: {execution_name}",
                        extra={'execution_name': execution_name, 'cancelled': True}
                    )
                else:
                    logger.info(
                        f"Job execution already completed: {execution_name}",
                        extra={'execution_name': execution_name, 'already_completed': True}
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Cancellation attempt {attempt}/{self.MAX_RETRIES} failed for {execution_name}: {e}",
                    extra={
                        'execution_name': execution_name,
                        'attempt': attempt,
                        'max_retries': self.MAX_RETRIES,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    },
                    exc_info=True
                )
                
                # Don't retry if job is already completed or not found
                if self._is_cancellation_non_retryable_error(e):
                    logger.info(
                        f"Non-retryable cancellation error: {e}",
                        extra={
                            'execution_name': execution_name,
                            'error_type': type(e).__name__,
                            'retryable': False
                        }
                    )
                    return False
                
                # If not the last attempt, wait before retrying
                if attempt < self.MAX_RETRIES:
                    logger.info(
                        f"Retrying cancellation in {delay} seconds...",
                        extra={
                            'execution_name': execution_name,
                            'attempt': attempt,
                            'next_attempt': attempt + 1,
                            'delay_seconds': delay
                        }
                    )
                    time.sleep(delay)
                    delay *= self.RETRY_BACKOFF
        
        # All retries exhausted - log but don't raise (cancellation is best-effort)
        logger.error(
            f"Failed to cancel job execution after {self.MAX_RETRIES} attempts: {last_exception}",
            extra={
                'execution_name': execution_name,
                'total_attempts': self.MAX_RETRIES,
                'final_error_type': type(last_exception).__name__,
                'final_error_message': str(last_exception)
            }
        )
        return False
    
    def _cancel_job_execution_internal(self, execution_name: str) -> bool:
        """
        Internal method to cancel job execution (without retry logic)
        
        Args:
            execution_name: Full execution name
        
        Returns:
            True if cancelled, False if already completed
        """
        from google.cloud import run_v2
        
        # Get execution status first
        try:
            logger.debug(
                f"Checking execution status before cancellation",
                extra={'execution_name': execution_name}
            )
            execution = self.client.get_execution(name=execution_name)
            
            # Check if execution is already in a terminal state
            if execution.completion_time:
                logger.info(
                    f"Job execution {execution_name} already completed at {execution.completion_time}",
                    extra={
                        'execution_name': execution_name,
                        'completion_time': str(execution.completion_time),
                        'already_completed': True
                    }
                )
                return False
            
        except Exception as e:
            # If we can't get status, try to cancel anyway
            logger.warning(
                f"Could not get execution status, attempting cancellation anyway: {e}",
                extra={
                    'execution_name': execution_name,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
        
        # Cancel the execution
        logger.debug(
            f"Sending cancellation request to Cloud Run Jobs API",
            extra={'execution_name': execution_name}
        )
        request = run_v2.DeleteExecutionRequest(name=execution_name)
        operation = self.client.delete_execution(request=request)
        
        # Wait for cancellation to complete with timeout
        try:
            logger.debug(
                f"Waiting for cancellation to complete (timeout: 30s)",
                extra={'execution_name': execution_name, 'operation_name': operation.operation.name}
            )
            operation.result(timeout=30)  # 30 second timeout
            logger.info(
                f"Cancellation completed successfully",
                extra={'execution_name': execution_name}
            )
        except Exception as e:
            logger.error(
                f"Timeout or error waiting for cancellation: {e}",
                extra={
                    'execution_name': execution_name,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'timeout_seconds': 30
                },
                exc_info=True
            )
            raise
        
        return True
    
    def _is_cancellation_non_retryable_error(self, error: Exception) -> bool:
        """
        Determine if a cancellation error should not be retried
        
        Args:
            error: The exception that occurred
        
        Returns:
            True if error should not be retried, False otherwise
        """
        error_str = str(error).lower()
        
        # Don't retry if job is already done or doesn't exist
        non_retryable_patterns = [
            'not found',
            'already completed',
            'already finished',
            'already terminated',
            'does not exist',
        ]
        
        return any(pattern in error_str for pattern in non_retryable_patterns)
    
    def get_job_execution_status(self, execution_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a Cloud Run Job execution
        
        Args:
            execution_name: Full execution name
        
        Returns:
            Dict with execution status information, or None if not found
        """
        logger.debug(
            f"Job execution status requested",
            extra={'execution_name': execution_name}
        )
        
        if self.client is None:
            # Local development mode - return mock status
            logger.info(
                f"Mock job execution status requested: {execution_name}",
                extra={'execution_name': execution_name, 'mode': 'local-dev'}
            )
            return {
                'name': execution_name,
                'status': 'running',
                'start_time': None,
                'completion_time': None,
            }
        
        try:
            from google.cloud import run_v2
            
            execution = self.client.get_execution(name=execution_name)
            status_string = self._get_execution_status_string(execution)
            
            status_info = {
                'name': execution.name,
                'status': status_string,
                'start_time': execution.start_time,
                'completion_time': execution.completion_time,
                'succeeded_count': execution.succeeded_count,
                'failed_count': execution.failed_count,
                'running_count': execution.running_count,
            }
            
            logger.info(
                f"Job execution status retrieved successfully",
                extra={
                    'execution_name': execution_name,
                    'status': status_string,
                    'succeeded_count': execution.succeeded_count,
                    'failed_count': execution.failed_count,
                    'running_count': execution.running_count
                }
            )
            
            return status_info
            
        except Exception as e:
            logger.error(
                f"Failed to get job execution status: {e}",
                extra={
                    'execution_name': execution_name,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            return None
    
    def _get_execution_status_string(self, execution) -> str:
        """
        Convert execution object to status string
        
        Args:
            execution: Cloud Run execution object
        
        Returns:
            Status string (pending, running, succeeded, failed, cancelled)
        """
        if execution.completion_time:
            if execution.succeeded_count > 0:
                return 'succeeded'
            elif execution.failed_count > 0:
                return 'failed'
            else:
                return 'cancelled'
        elif execution.start_time:
            return 'running'
        else:
            return 'pending'
