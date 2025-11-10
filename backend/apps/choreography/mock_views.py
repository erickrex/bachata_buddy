"""
Mock Job Control Views for Local Development

These endpoints allow manual control of mock job executions for testing
the choreography generation flow locally without Cloud Run infrastructure.

⚠️ DEVELOPMENT ONLY - These endpoints should NOT be exposed in production!

Usage:
    # Complete a job manually
    POST /api/choreography/mock/complete/{task_id}
    {
        "success": true,
        "result": {
            "video_url": "gs://bucket/video.mp4",
            "duration": 180.5
        }
    }
    
    # Simulate job progress automatically
    POST /api/choreography/mock/simulate/{task_id}
    {
        "duration_seconds": 10
    }
    
    # Get active mock jobs
    GET /api/choreography/mock/jobs
"""
import os
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.choreography.models import ChoreographyTask
from services.mock_job_service import MockJobService
import logging

logger = logging.getLogger(__name__)

# Only allow mock endpoints in local development
ALLOW_MOCK_ENDPOINTS = os.environ.get('ENVIRONMENT', 'development') == 'development'


def check_mock_enabled():
    """Check if mock endpoints are enabled"""
    if not ALLOW_MOCK_ENDPOINTS:
        return Response(
            {'error': 'Mock endpoints are disabled in production'},
            status=status.HTTP_403_FORBIDDEN
        )
    return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_mock_job(request, task_id):
    """
    Manually complete a mock job execution
    
    POST /api/choreography/mock/complete/{task_id}
    
    Body:
    {
        "success": true,  // Whether job succeeded
        "result": {       // Optional: result data for successful jobs
            "video_url": "gs://bucket/video.mp4",
            "thumbnail_url": "gs://bucket/thumb.jpg",
            "duration": 180.5,
            "moves_count": 12
        },
        "error": "Error message"  // Optional: error for failed jobs
    }
    
    Returns:
        200 OK with updated task status
    """
    # Check if mock endpoints are enabled
    error_response = check_mock_enabled()
    if error_response:
        return error_response
    
    # Verify task exists and belongs to user
    task = get_object_or_404(ChoreographyTask, task_id=task_id, user=request.user)
    
    # Get parameters from request
    success = request.data.get('success', True)
    result = request.data.get('result')
    error = request.data.get('error')
    
    # Complete the mock job
    mock_service = MockJobService()
    try:
        mock_service.complete_job(
            task_id=str(task_id),
            success=success,
            result=result,
            error=error
        )
        
        # Refresh task from database
        task.refresh_from_db()
        
        logger.info(
            f"Mock job manually completed for task {task_id}",
            extra={
                'task_id': str(task_id),
                'user_id': request.user.id,
                'success': success,
                'status': task.status
            }
        )
        
        return Response({
            'message': 'Mock job completed successfully',
            'task_id': str(task.task_id),
            'status': task.status,
            'progress': task.progress,
            'stage': task.stage,
            'message_text': task.message,
            'result': task.result,
            'error': task.error
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(
            f"Failed to complete mock job: {e}",
            extra={'task_id': str(task_id), 'error': str(e)}
        )
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(
            f"Unexpected error completing mock job: {e}",
            extra={'task_id': str(task_id), 'error': str(e)},
            exc_info=True
        )
        return Response(
            {'error': 'Failed to complete mock job'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def simulate_mock_job(request, task_id):
    """
    Simulate job progress automatically over time
    
    POST /api/choreography/mock/simulate/{task_id}
    
    Body:
    {
        "duration_seconds": 10  // Optional: how long simulation should take (default: 10)
    }
    
    Returns:
        202 Accepted - simulation started in background
    """
    # Check if mock endpoints are enabled
    error_response = check_mock_enabled()
    if error_response:
        return error_response
    
    # Verify task exists and belongs to user
    task = get_object_or_404(ChoreographyTask, task_id=task_id, user=request.user)
    
    # Check task is in a state that can be simulated
    if task.status not in ['pending', 'processing']:
        return Response(
            {'error': f'Cannot simulate job for task with status "{task.status}". Task must be pending or processing.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get duration from request
    duration_seconds = request.data.get('duration_seconds', 10)
    
    # Validate duration
    if not isinstance(duration_seconds, (int, float)) or duration_seconds < 1 or duration_seconds > 300:
        return Response(
            {'error': 'duration_seconds must be between 1 and 300'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Start simulation
    mock_service = MockJobService()
    try:
        mock_service.simulate_job_progress(
            task_id=str(task_id),
            duration_seconds=int(duration_seconds)
        )
        
        logger.info(
            f"Mock job simulation started for task {task_id}",
            extra={
                'task_id': str(task_id),
                'user_id': request.user.id,
                'duration_seconds': duration_seconds
            }
        )
        
        return Response({
            'message': 'Mock job simulation started',
            'task_id': str(task.task_id),
            'duration_seconds': duration_seconds,
            'poll_url': f'/api/choreography/tasks/{task_id}'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(
            f"Failed to start mock job simulation: {e}",
            extra={'task_id': str(task_id), 'error': str(e)},
            exc_info=True
        )
        return Response(
            {'error': 'Failed to start simulation'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_mock_jobs(request):
    """
    List all active mock jobs
    
    GET /api/choreography/mock/jobs
    
    Returns:
        List of active mock jobs with their status
    """
    # Check if mock endpoints are enabled
    error_response = check_mock_enabled()
    if error_response:
        return error_response
    
    mock_service = MockJobService()
    active_jobs = mock_service.get_active_jobs()
    
    # Filter to only show current user's jobs
    user_jobs = {
        task_id: job_info
        for task_id, job_info in active_jobs.items()
        if job_info['user_id'] == request.user.id
    }
    
    logger.info(
        f"Mock jobs list requested by user {request.user.id}",
        extra={
            'user_id': request.user.id,
            'total_jobs': len(user_jobs)
        }
    )
    
    return Response({
        'count': len(user_jobs),
        'jobs': user_jobs
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_mock_job_progress(request, task_id):
    """
    Manually update mock job progress
    
    POST /api/choreography/mock/progress/{task_id}
    
    Body:
    {
        "progress": 50,
        "stage": "processing",
        "message": "Processing video..."
    }
    
    Returns:
        200 OK with updated task status
    """
    # Check if mock endpoints are enabled
    error_response = check_mock_enabled()
    if error_response:
        return error_response
    
    # Verify task exists and belongs to user
    task = get_object_or_404(ChoreographyTask, task_id=task_id, user=request.user)
    
    # Get parameters from request
    progress = request.data.get('progress')
    stage = request.data.get('stage')
    message = request.data.get('message')
    
    # Validate progress
    if progress is not None:
        if not isinstance(progress, (int, float)) or progress < 0 or progress > 100:
            return Response(
                {'error': 'progress must be between 0 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
        task.progress = int(progress)
    
    # Update fields
    if stage:
        task.stage = stage
    if message:
        task.message = message
    
    # Update status based on progress
    if task.progress > 0 and task.status == 'pending':
        task.status = 'processing'
    
    task.save()
    
    logger.info(
        f"Mock job progress manually updated for task {task_id}",
        extra={
            'task_id': str(task_id),
            'user_id': request.user.id,
            'progress': task.progress,
            'stage': task.stage
        }
    )
    
    return Response({
        'message': 'Progress updated successfully',
        'task_id': str(task.task_id),
        'status': task.status,
        'progress': task.progress,
        'stage': task.stage,
        'message_text': task.message
    }, status=status.HTTP_200_OK)
