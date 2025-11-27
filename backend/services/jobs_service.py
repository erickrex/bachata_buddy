"""
Job Service for Video Processing

Handles creation and management of video processing jobs.
Supports both local development (mock mode) and AWS deployment.

For AWS deployment, this can be extended to use:
- AWS ECS Tasks
- AWS Lambda
- AWS App Runner Jobs
- Or a job queue system like Celery/RQ

Usage:
    import json
    from services.jobs_service_new import JobsService
    
    # Generate blueprint (done by BlueprintGenerator)
    blueprint = {
        "task_id": "uuid",
        "audio_path": "path/to/song.mp3",
        "moves": [...],
        "output_config": {...}
    }
    
    # Submit job with blueprint
    service = JobsService()
    execution_name = service.create_job_execution(
        task_id="uuid",
        user_id=123,
        parameters={"blueprint_json": json.dumps(blueprint)}
    )
"""
import os
import logging
import time
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class JobExecutionError(Exception):
    """Raised when job execution fails"""
    pass


class JobCancellationError(Exception):
    """Raised when job cancellation fails"""
    pass


class JobsService:
    """Service for managing video processing jobs"""
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    RETRY_BACKOFF = 2  # exponential backoff multiplier
    
    def __init__(self):
        self.environment = os.environ.get('ENVIRONMENT', 'local')
        self.job_mode = os.environ.get('JOB_MODE', 'mock')  # 'mock', 'aws', or 'celery'
        
        logger.info(f"JobsService initialized in {self.job_mode} mode (environment: {self.environment})")
        
        # Initialize AWS client if in AWS mode
        if self.job_mode == 'aws':
            try:
                import boto3
                self.ecs_client = boto3.client('ecs')
                logger.info("AWS ECS client initialized")
            except ImportError:
                logger.warning("boto3 not installed, falling back to mock mode")
                self.job_mode = 'mock'
            except Exception as e:
                logger.warning(f"Failed to initialize AWS client: {e}, falling back to mock mode")
                self.job_mode = 'mock'
    
    def create_job_execution(
        self,
        task_id: str,
        user_id: int,
        parameters: Dict[str, Any]
    ) -> str:
        """
        Create a job execution for video processing.
        
        Args:
            task_id: UUID of the choreography task
            user_id: ID of the user
            parameters: Dict with blueprint_json (required)
        
        Returns:
            Execution name/ID string
            
        Raises:
            JobExecutionError: If job creation fails
        """
        logger.info(
            f"Job creation requested for task {task_id}",
            extra={
                'task_id': task_id,
                'user_id': user_id,
                'job_mode': self.job_mode
            }
        )
        
        if self.job_mode == 'mock':
            return self._create_mock_job(task_id, user_id, parameters)
        elif self.job_mode == 'aws':
            return self._create_aws_job(task_id, user_id, parameters)
        elif self.job_mode == 'celery':
            return self._create_celery_job(task_id, user_id, parameters)
        else:
            raise JobExecutionError(f"Unknown job mode: {self.job_mode}")
    
    def _create_mock_job(
        self,
        task_id: str,
        user_id: int,
        parameters: Dict[str, Any]
    ) -> str:
        """
        Create a mock job execution for local development.
        
        In mock mode, we just log the job creation and return a fake execution ID.
        The actual video processing would need to be triggered manually or through
        a separate local job runner.
        """
        execution_id = f"mock-execution-{uuid.uuid4().hex[:8]}"
        
        logger.info(
            f"Mock job created: {execution_id}",
            extra={
                'task_id': task_id,
                'user_id': user_id,
                'execution_id': execution_id,
                'blueprint_size': len(parameters.get('blueprint_json', ''))
            }
        )
        
        # In a real implementation, you might:
        # 1. Write the blueprint to a file
        # 2. Trigger a local job runner
        # 3. Use a job queue like RQ or Celery
        
        return execution_id
    
    def _create_aws_job(
        self,
        task_id: str,
        user_id: int,
        parameters: Dict[str, Any]
    ) -> str:
        """
        Create an AWS ECS task for video processing.
        
        This is a placeholder for AWS implementation. You would need to:
        1. Define an ECS task definition for the job container
        2. Run the task with the blueprint as environment variable or S3 file
        3. Return the task ARN as the execution ID
        """
        try:
            # Example ECS task run (needs to be configured)
            cluster = os.environ.get('AWS_ECS_CLUSTER', 'bachata-buddy-cluster')
            task_definition = os.environ.get('AWS_ECS_TASK_DEFINITION', 'video-processor')
            
            # You would pass the blueprint via environment variable or S3
            response = self.ecs_client.run_task(
                cluster=cluster,
                taskDefinition=task_definition,
                launchType='FARGATE',  # or 'EC2'
                overrides={
                    'containerOverrides': [
                        {
                            'name': 'video-processor',
                            'environment': [
                                {'name': 'TASK_ID', 'value': task_id},
                                {'name': 'USER_ID', 'value': str(user_id)},
                                # Blueprint would typically be stored in S3 and referenced here
                            ]
                        }
                    ]
                }
            )
            
            task_arn = response['tasks'][0]['taskArn']
            logger.info(f"AWS ECS task created: {task_arn}")
            return task_arn
            
        except Exception as e:
            logger.error(f"Failed to create AWS job: {e}")
            raise JobExecutionError(f"Failed to create AWS job: {e}")
    
    def _create_celery_job(
        self,
        task_id: str,
        user_id: int,
        parameters: Dict[str, Any]
    ) -> str:
        """
        Create a Celery task for video processing.
        
        This is a placeholder for Celery implementation.
        """
        try:
            # Import Celery task
            from tasks import process_video_task
            
            # Submit task to Celery
            result = process_video_task.delay(
                task_id=task_id,
                user_id=user_id,
                blueprint_json=parameters.get('blueprint_json')
            )
            
            logger.info(f"Celery task created: {result.id}")
            return result.id
            
        except ImportError:
            logger.error("Celery not configured")
            raise JobExecutionError("Celery not configured")
        except Exception as e:
            logger.error(f"Failed to create Celery job: {e}")
            raise JobExecutionError(f"Failed to create Celery job: {e}")
    
    def get_job_status(self, execution_name: str) -> Dict[str, Any]:
        """
        Get the status of a job execution.
        
        Args:
            execution_name: Execution name/ID returned by create_job_execution
        
        Returns:
            Dict with status information
        """
        if self.job_mode == 'mock':
            return {
                'execution_name': execution_name,
                'status': 'RUNNING',
                'message': 'Mock job status'
            }
        elif self.job_mode == 'aws':
            # Query ECS task status
            try:
                response = self.ecs_client.describe_tasks(
                    cluster=os.environ.get('AWS_ECS_CLUSTER', 'bachata-buddy-cluster'),
                    tasks=[execution_name]
                )
                task = response['tasks'][0]
                return {
                    'execution_name': execution_name,
                    'status': task['lastStatus'],
                    'message': task.get('stoppedReason', '')
                }
            except Exception as e:
                logger.error(f"Failed to get AWS job status: {e}")
                return {
                    'execution_name': execution_name,
                    'status': 'UNKNOWN',
                    'message': str(e)
                }
        else:
            return {
                'execution_name': execution_name,
                'status': 'UNKNOWN',
                'message': f'Status check not implemented for {self.job_mode} mode'
            }
    
    def cancel_job(self, execution_name: str) -> bool:
        """
        Cancel a running job execution.
        
        Args:
            execution_name: Execution name/ID to cancel
        
        Returns:
            True if cancelled successfully
            
        Raises:
            JobCancellationError: If cancellation fails
        """
        logger.info(f"Job cancellation requested: {execution_name}")
        
        if self.job_mode == 'mock':
            logger.info(f"Mock job cancelled: {execution_name}")
            return True
        elif self.job_mode == 'aws':
            try:
                self.ecs_client.stop_task(
                    cluster=os.environ.get('AWS_ECS_CLUSTER', 'bachata-buddy-cluster'),
                    task=execution_name,
                    reason='User requested cancellation'
                )
                logger.info(f"AWS task cancelled: {execution_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to cancel AWS job: {e}")
                raise JobCancellationError(f"Failed to cancel job: {e}")
        else:
            raise JobCancellationError(f"Cancellation not implemented for {self.job_mode} mode")


# Alias for backward compatibility
CloudRunJobsService = JobsService
