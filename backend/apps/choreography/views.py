from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import ChoreographyTask, Song
from .serializers import (
    ChoreographyTaskSerializer,
    ChoreographyTaskListSerializer,
    QueryParseSerializer,
    AIGenerationSerializer,
    SongSerializer,
    SongDetailSerializer,
    SongGenerationSerializer
)
from services.jobs_service import CloudRunJobsService
from services.gemini_service import GeminiService
import logging

logger = logging.getLogger(__name__)


@extend_schema(
    summary="List available songs",
    description="""
    Retrieve a paginated list of available songs for choreography generation.
    
    This endpoint returns all songs stored in the system with their metadata.
    Songs can be filtered by genre, BPM range, and searched by title or artist.
    
    **Query Parameters:**
    - `genre`: Filter by genre (e.g., "bachata", "salsa")
    - `bpm_min`: Minimum BPM (beats per minute)
    - `bpm_max`: Maximum BPM (beats per minute)
    - `search`: Search in title or artist (case-insensitive)
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 20, max: 100)
    
    **Ordering:**
    - Songs are ordered by title (ascending) by default
    
    **Example Queries:**
    - `/api/choreography/songs/` - List all songs
    - `/api/choreography/songs/?genre=bachata` - Filter by genre
    - `/api/choreography/songs/?bpm_min=120&bpm_max=130` - Filter by BPM range
    - `/api/choreography/songs/?search=rosa` - Search for "rosa" in title or artist
    - `/api/choreography/songs/?page_size=50` - Get 50 songs per page
    """,
    parameters=[
        OpenApiParameter(
            name='genre',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by genre',
            required=False
        ),
        OpenApiParameter(
            name='bpm_min',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Minimum BPM (beats per minute)',
            required=False
        ),
        OpenApiParameter(
            name='bpm_max',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Maximum BPM (beats per minute)',
            required=False
        ),
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search in title or artist (case-insensitive)',
            required=False
        ),
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Page number',
            required=False
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Number of items per page (max: 100)',
            required=False
        )
    ],
    responses={
        200: OpenApiResponse(
            response=SongSerializer,
            description="Paginated list of songs",
            examples=[
                OpenApiExample(
                    'Song List',
                    value={
                        'count': 25,
                        'next': 'http://localhost:8001/api/choreography/songs/?page=2',
                        'previous': None,
                        'results': [
                            {
                                'id': 1,
                                'title': 'Bachata Rosa',
                                'artist': 'Juan Luis Guerra',
                                'duration': 245.5,
                                'bpm': 120,
                                'genre': 'bachata',
                                'created_at': '2025-11-08T10:00:00Z'
                            },
                            {
                                'id': 2,
                                'title': 'Obsesión',
                                'artist': 'Aventura',
                                'duration': 268.0,
                                'bpm': 125,
                                'genre': 'bachata',
                                'created_at': '2025-11-08T10:05:00Z'
                            }
                        ]
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid query parameters",
            examples=[
                OpenApiExample(
                    'Invalid BPM',
                    value={'error': 'bpm_min and bpm_max must be positive integers'}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Choreography']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_songs(request):
    """
    List available songs with filtering and pagination.
    
    Returns a paginated list of songs from the database.
    Supports filtering by genre, BPM range, and searching by title or artist.
    """
    queryset = Song.objects.all()
    
    # Filter by genre if provided
    genre = request.query_params.get('genre')
    if genre:
        queryset = queryset.filter(genre__iexact=genre)
    
    # Filter by BPM range if provided
    bpm_min = request.query_params.get('bpm_min')
    bpm_max = request.query_params.get('bpm_max')
    
    if bpm_min:
        try:
            bpm_min = int(bpm_min)
            if bpm_min < 0:
                return Response(
                    {'error': 'bpm_min must be a positive integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            queryset = queryset.filter(bpm__gte=bpm_min)
        except ValueError:
            return Response(
                {'error': 'bpm_min must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    if bpm_max:
        try:
            bpm_max = int(bpm_max)
            if bpm_max < 0:
                return Response(
                    {'error': 'bpm_max must be a positive integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            queryset = queryset.filter(bpm__lte=bpm_max)
        except ValueError:
            return Response(
                {'error': 'bpm_max must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Search by title or artist if provided
    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(artist__icontains=search)
        )
    
    # Order by title (default ordering from model)
    queryset = queryset.order_by('title')
    
    # Paginate
    paginator = PageNumberPagination()
    paginator.page_size = 20  # Default page size
    
    # Allow custom page size via query param (max 100)
    page_size = request.query_params.get('page_size')
    if page_size:
        try:
            page_size = int(page_size)
            if 1 <= page_size <= 100:
                paginator.page_size = page_size
            elif page_size > 100:
                return Response(
                    {'error': 'page_size cannot exceed 100'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'page_size must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    page = paginator.paginate_queryset(queryset, request)
    
    # Serialize and return
    serializer = SongSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    summary="Get song details",
    description="""
    Retrieve detailed information about a specific song.
    
    This endpoint returns complete song metadata including the audio file path.
    The audio_path can be either a local file path (development) or a GCS path (production).
    
    **Audio Path Formats:**
    - Local: `songs/bachata-rosa.mp3`
    - GCS: `gs://bachata-buddy-bucket/songs/bachata-rosa.mp3`
    
    **Use Case:**
    Use this endpoint to get full song details before generating choreography.
    The returned audio_path is used internally by the generation process.
    """,
    responses={
        200: OpenApiResponse(
            response=SongDetailSerializer,
            description="Song details retrieved successfully",
            examples=[
                OpenApiExample(
                    'Song Detail',
                    value={
                        'id': 1,
                        'title': 'Bachata Rosa',
                        'artist': 'Juan Luis Guerra',
                        'duration': 245.5,
                        'bpm': 120,
                        'genre': 'bachata',
                        'audio_path': 'songs/bachata-rosa.mp3',
                        'created_at': '2025-11-08T10:00:00Z',
                        'updated_at': '2025-11-08T10:00:00Z'
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required"),
        404: OpenApiResponse(
            description="Song not found",
            examples=[
                OpenApiExample(
                    'Not Found',
                    value={'detail': 'Not found.'}
                )
            ]
        )
    },
    tags=['Choreography']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def song_detail(request, song_id):
    """
    Get detailed information about a specific song.
    
    Returns complete song metadata including audio_path for choreography generation.
    """
    song = get_object_or_404(Song, id=song_id)
    serializer = SongDetailSerializer(song)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Generate choreography from song template",
    description="""
    Generate choreography from a pre-existing song template.
    
    This endpoint creates a choreography generation task using a song from the system's
    song library. The song's audio file is automatically retrieved and passed to the
    Cloud Run Job for processing.
    
    **Workflow:**
    1. Validate that the song_id exists
    2. Create ChoreographyTask with song reference
    3. Retrieve song's audio_path (local or GCS)
    4. Trigger Cloud Run Job with audio_path and parameters
    5. Return task_id for status polling
    
    **Parameters:**
    - song_id: ID of the song from the song library (required)
    - difficulty: beginner, intermediate, or advanced (default: intermediate)
    - energy_level: low, medium, or high (optional)
    - style: traditional, modern, romantic, or sensual (optional)
    
    **Response:**
    - Returns immediately with task_id (202 Accepted)
    - Poll /api/choreography/tasks/{task_id} for status
    - When complete, result includes video URL
    
    **Example:**
    ```json
    {
        "song_id": 1,
        "difficulty": "intermediate",
        "energy_level": "medium",
        "style": "romantic"
    }
    ```
    """,
    request=SongGenerationSerializer,
    responses={
        202: OpenApiResponse(
            description="Task created successfully",
            examples=[
                OpenApiExample(
                    'Task Created',
                    value={
                        'task_id': '550e8400-e29b-41d4-a716-446655440000',
                        'song': {
                            'id': 1,
                            'title': 'Bachata Rosa',
                            'artist': 'Juan Luis Guerra'
                        },
                        'status': 'pending',
                        'message': 'Choreography generation started',
                        'poll_url': '/api/choreography/tasks/550e8400-e29b-41d4-a716-446655440000'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid input parameters",
            examples=[
                OpenApiExample(
                    'Invalid Song ID',
                    value={'song_id': ['Song with ID 999 does not exist']}
                ),
                OpenApiExample(
                    'Invalid Difficulty',
                    value={'difficulty': ['"expert" is not a valid choice.']}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required"),
        500: OpenApiResponse(
            description="Failed to create job execution",
            examples=[
                OpenApiExample(
                    'Job Creation Failed',
                    value={'error': 'Failed to create job execution'}
                )
            ]
        )
    },
    tags=['Choreography']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_from_song(request):
    """
    Generate choreography from a song template.
    
    Creates a new task and triggers asynchronous video processing using a pre-existing song.
    Uses blueprint-based architecture: generates complete blueprint in API, passes to job container.
    """
    # Import services at the top to avoid variable shadowing issues
    from services.blueprint_generator import BlueprintGenerator
    from services.vector_search_service import VectorSearchService
    
    serializer = SongGenerationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Get the song (validation already confirmed it exists)
    song_id = serializer.validated_data['song_id']
    song = Song.objects.get(id=song_id)
    
    # Create task with song reference
    import uuid
    task_id = str(uuid.uuid4())
    task = ChoreographyTask.objects.create(
        task_id=task_id,
        user=request.user,
        status='pending',
        progress=0,
        stage='generating_blueprint',
        message='Generating choreography blueprint...',
        song=song
    )
    
    # Extract parameters
    difficulty = serializer.validated_data['difficulty']
    energy_level = serializer.validated_data.get('energy_level', 'medium')
    style = serializer.validated_data.get('style', 'modern')
    
    try:
        # Generate blueprint using BlueprintGenerator
        # Initialize services
        from services.vector_search_service import get_vector_search_service
        vector_search = get_vector_search_service()
        gemini_service = GeminiService()
        
        # Import MusicAnalyzer from job container (temporary until we move it to backend)
        import sys
        import os
        job_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', '..', 'job', 'src', 'services')
        if job_path not in sys.path:
            sys.path.insert(0, job_path)
        from music_analyzer import MusicAnalyzer
        
        music_analyzer = MusicAnalyzer()
        
        # Create blueprint generator
        blueprint_gen = BlueprintGenerator(
            vector_search_service=vector_search,
            music_analyzer=music_analyzer,
            gemini_service=gemini_service
        )
        
        # Generate blueprint
        logger.info(f"Generating blueprint for task {task_id} with song {song_id}")
        blueprint = blueprint_gen.generate_blueprint(
            task_id=task_id,
            song_path=song.audio_path,
            difficulty=difficulty,
            energy_level=energy_level,
            style=style,
            user_id=request.user.id
        )
        
        # Store blueprint in database
        from .models import Blueprint
        Blueprint.objects.create(
            task=task,
            blueprint_json=blueprint
        )
        
        logger.info(f"Blueprint generated and stored for task {task_id}")
        
        # Update task status
        task.stage = 'submitting_job'
        task.message = 'Blueprint generated, submitting job...'
        task.save()
        
    except Exception as e:
        logger.error(
            f"Failed to generate blueprint for task {task_id}: {e}",
            extra={
                'task_id': task_id,
                'song_id': song_id,
                'user_id': request.user.id,
                'error': str(e)
            },
            exc_info=True
        )
        task.status = 'failed'
        task.error = f'Blueprint generation failed: {str(e)}'
        task.save()
        return Response(
            {'error': 'Failed to generate blueprint'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Create Cloud Run Job execution with blueprint
    jobs_service = CloudRunJobsService()
    try:
        import json
        execution_name = jobs_service.create_job_execution(
            task_id=task_id,
            user_id=request.user.id,
            parameters={'blueprint_json': json.dumps(blueprint)}
        )
        
        # Store execution name for monitoring
        task.job_execution_name = execution_name
        task.status = 'started'
        task.stage = 'video_assembly'
        task.message = 'Job submitted, assembling video...'
        task.save()
        
        logger.info(
            f"Created job execution for task {task_id} with song {song_id}: {execution_name}",
            extra={
                'task_id': task_id,
                'song_id': song_id,
                'song_title': song.title,
                'user_id': request.user.id,
                'execution_name': execution_name
            }
        )
        
    except Exception as e:
        logger.error(
            f"Failed to create job execution for task {task_id} with song {song_id}: {e}",
            extra={
                'task_id': task_id,
                'song_id': song_id,
                'user_id': request.user.id,
                'error': str(e)
            }
        )
        task.status = 'failed'
        task.error = f'Job submission failed: {str(e)}'
        task.save()
        return Response(
            {'error': 'Failed to create job execution'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Return task info with song details
    return Response({
        'task_id': task_id,
        'song': {
            'id': song.id,
            'title': song.title,
            'artist': song.artist
        },
        'status': 'started',
        'message': 'Choreography generation started',
        'poll_url': f'/api/choreography/tasks/{task_id}'
    }, status=status.HTTP_202_ACCEPTED)


@extend_schema(
    summary="Get task status",
    description="""
    Retrieve the current status and progress of a choreography generation task.
    
    Use this endpoint to poll for task updates. The task progresses through several stages:
    - **pending**: Task queued, waiting to start
    - **started**: Job execution created
    - **running**: Processing in progress (check progress field for percentage)
    - **completed**: Video generation finished (result contains video URL)
    - **failed**: Error occurred (error field contains details)
    
    Poll this endpoint every 2-5 seconds while status is 'pending', 'started', or 'running'.
    """,
    responses={
        200: OpenApiResponse(
            response=ChoreographyTaskSerializer,
            description="Task status retrieved",
            examples=[
                OpenApiExample(
                    'Task Running',
                    value={
                        'task_id': '550e8400-e29b-41d4-a716-446655440000',
                        'status': 'running',
                        'progress': 45,
                        'stage': 'video_processing',
                        'message': 'Processing video frames',
                        'result': None,
                        'error': None,
                        'created_at': '2025-11-02T10:30:00Z',
                        'updated_at': '2025-11-02T10:32:15Z'
                    }
                ),
                OpenApiExample(
                    'Task Completed',
                    value={
                        'task_id': '550e8400-e29b-41d4-a716-446655440000',
                        'status': 'completed',
                        'progress': 100,
                        'stage': 'completed',
                        'message': 'Choreography generated successfully',
                        'result': {
                            'video_url': 'https://storage.googleapis.com/bucket/video.mp4',
                            'duration': 180,
                            'move_count': 12
                        },
                        'error': None,
                        'created_at': '2025-11-02T10:30:00Z',
                        'updated_at': '2025-11-02T10:35:00Z'
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required"),
        404: OpenApiResponse(
            description="Task not found or does not belong to user",
            examples=[
                OpenApiExample(
                    'Not Found',
                    value={'detail': 'Not found.'}
                )
            ]
        )
    },
    tags=['Choreography'],
    methods=['GET']
)
@extend_schema(
    summary="Cancel task",
    description="""
    Cancel a pending or running choreography generation task.
    
    This endpoint attempts to cancel the Cloud Run Job execution and marks the task as failed.
    Only tasks with status 'started' or 'running' can be cancelled.
    
    **Note:** If the job has already completed processing, cancellation may not be possible.
    """,
    responses={
        200: OpenApiResponse(
            description="Task cancelled successfully",
            examples=[
                OpenApiExample(
                    'Cancelled',
                    value={
                        'message': 'Task cancelled successfully',
                        'task_id': '550e8400-e29b-41d4-a716-446655440000',
                        'status': 'failed'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Task cannot be cancelled",
            examples=[
                OpenApiExample(
                    'Already Completed',
                    value={'error': 'Cannot cancel task with status "completed". Only started or running tasks can be cancelled.'}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required"),
        404: OpenApiResponse(description="Task not found or does not belong to user")
    },
    tags=['Choreography'],
    methods=['DELETE']
)
@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def task_detail(request, task_id):
    """
    Get task status or cancel task.
    
    GET: Retrieve current task status and progress.
    DELETE: Cancel a pending or running task.
    """
    task = get_object_or_404(ChoreographyTask, task_id=task_id, user=request.user)
    
    if request.method == 'GET':
        # Get task status (polls database)
        serializer = ChoreographyTaskSerializer(task, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'DELETE':
        # Cancel a pending or processing task
        # Check if task can be cancelled
        if task.status not in ['started', 'running']:
            return Response(
                {'error': f'Cannot cancel task with status "{task.status}". Only started or running tasks can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Attempt to cancel Cloud Run Job execution if it exists
        if task.job_execution_name:
            jobs_service = CloudRunJobsService()
            try:
                cancelled = jobs_service.cancel_job_execution(task.job_execution_name)
                if cancelled:
                    logger.info(f"Successfully cancelled job execution for task {task_id}")
                else:
                    logger.warning(f"Could not cancel job execution for task {task_id} - may have already completed")
            except Exception as e:
                logger.error(f"Error cancelling job execution for task {task_id}: {e}")
                # Continue with task cancellation even if job cancellation fails
        
        # Update task status to cancelled
        task.status = 'failed'
        task.error = 'Cancelled by user'
        task.message = 'Task cancelled by user'
        task.save()
        
        logger.info(f"Task {task_id} cancelled by user {request.user.id}")
        
        return Response({
            'message': 'Task cancelled successfully',
            'task_id': str(task.task_id),
            'status': 'failed'
        }, status=status.HTTP_200_OK)


@extend_schema(
    summary="List user tasks",
    description="""
    Retrieve a paginated list of the authenticated user's choreography generation tasks.
    
    Tasks are ordered by creation date (most recent first). Use query parameters to filter
    by status and control pagination.
    
    **Status Values:**
    - `pending`: Task queued, waiting to start
    - `started`: Job execution created
    - `running`: Processing in progress
    - `completed`: Video generation finished
    - `failed`: Error occurred or cancelled by user
    """,
    parameters=[
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by task status',
            enum=['pending', 'started', 'running', 'completed', 'failed'],
            required=False
        ),
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Page number',
            required=False
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Number of items per page (max: 100)',
            required=False
        )
    ],
    responses={
        200: OpenApiResponse(
            response=ChoreographyTaskListSerializer,
            description="Paginated list of tasks",
            examples=[
                OpenApiExample(
                    'Task List',
                    value={
                        'count': 25,
                        'next': 'http://localhost:8000/api/choreography/tasks?page=2',
                        'previous': None,
                        'results': [
                            {
                                'task_id': '550e8400-e29b-41d4-a716-446655440000',
                                'status': 'completed',
                                'progress': 100,
                                'stage': 'completed',
                                'message': 'Choreography generated successfully',
                                'created_at': '2025-11-02T10:30:00Z',
                                'updated_at': '2025-11-02T10:35:00Z'
                            },
                            {
                                'task_id': '660e8400-e29b-41d4-a716-446655440001',
                                'status': 'running',
                                'progress': 60,
                                'stage': 'video_processing',
                                'message': 'Processing video frames',
                                'created_at': '2025-11-02T09:15:00Z',
                                'updated_at': '2025-11-02T09:20:00Z'
                            }
                        ]
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid query parameters",
            examples=[
                OpenApiExample(
                    'Invalid Status',
                    value={'error': 'Invalid status. Must be one of: pending, started, running, completed, failed'}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Choreography']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_tasks(request):
    """
    List user's tasks with pagination and filtering.
    
    Returns a paginated list of choreography generation tasks for the authenticated user.
    Supports filtering by status and custom page sizes.
    """
    queryset = ChoreographyTask.objects.filter(user=request.user)
    
    # Filter by status if provided
    status_filter = request.query_params.get('status')
    if status_filter:
        # Validate status is a valid choice
        valid_statuses = [choice[0] for choice in ChoreographyTask.STATUS_CHOICES]
        if status_filter not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        queryset = queryset.filter(status=status_filter)
    
    # Order by created_at descending (most recent first)
    queryset = queryset.order_by('-created_at')
    
    # Paginate
    paginator = PageNumberPagination()
    # Allow custom page size via query param (max 100)
    page_size = request.query_params.get('page_size')
    if page_size:
        try:
            page_size = int(page_size)
            if 1 <= page_size <= 100:
                paginator.page_size = page_size
        except (ValueError, TypeError):
            pass  # Use default page size
    
    page = paginator.paginate_queryset(queryset, request)
    
    # Use lightweight serializer for list view
    serializer = ChoreographyTaskListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)



@extend_schema(
    summary="Parse natural language query",
    description="""
    Parse a natural language description into structured choreography parameters using AI.
    
    This endpoint uses Google's Gemini AI to understand user intent and extract
    choreography parameters from natural language descriptions.
    
    **Examples:**
    - "Create a romantic beginner choreography with slow tempo"
    - "I want an energetic intermediate routine for a party"
    - "Make me a sensual advanced bachata with body rolls"
    
    **Extracted Parameters:**
    - difficulty: beginner, intermediate, or advanced
    - style: romantic, energetic, sensual, or playful
    - energy_level: low, medium, or high
    - tempo: slow, medium, or fast
    
    **Confidence Score:**
    - 0.9: High confidence (AI parsing successful)
    - 0.6: Medium confidence (fallback keyword matching)
    
    **Performance:**
    - Typical response time: 1-3 seconds
    - Rate limited to 60 requests/minute
    
    **Fallback Behavior:**
    - If AI service unavailable, uses keyword matching
    - Always returns valid parameters (never fails)
    """,
    request=QueryParseSerializer,
    responses={
        200: OpenApiResponse(
            description="Query parsed successfully",
            examples=[
                OpenApiExample(
                    'Successful Parse',
                    value={
                        'parameters': {
                            'difficulty': 'beginner',
                            'style': 'romantic',
                            'energy_level': 'low',
                            'tempo': 'slow'
                        },
                        'confidence': 0.9,
                        'query': 'Create a romantic beginner choreography with slow tempo'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid query",
            examples=[
                OpenApiExample(
                    'Empty Query',
                    value={'query': ['Query cannot be empty']}
                ),
                OpenApiExample(
                    'Ambiguous Query',
                    value={
                        'error': 'Could not understand your query. Please try rephrasing.',
                        'suggestions': [
                            'Try specifying a difficulty level (beginner, intermediate, or advanced)',
                            'Try describing the style (romantic, energetic, sensual, or playful)'
                        ]
                    }
                )
            ]
        ),
        503: OpenApiResponse(
            description="AI service temporarily unavailable",
            examples=[
                OpenApiExample(
                    'Service Unavailable',
                    value={'error': 'AI service temporarily unavailable'}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Choreography']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def parse_natural_language_query(request):
    """
    Parse natural language query using Gemini AI.
    
    Extracts structured choreography parameters from user's natural language description.
    """
    serializer = QueryParseSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    query = serializer.validated_data['query']
    
    try:
        # Initialize Gemini service
        gemini_service = GeminiService()
        
        # Parse query
        parameters = gemini_service.parse_choreography_request(query)
        
        logger.info(f"User {request.user.id} parsed query: '{query[:50]}...' -> {parameters.difficulty}/{parameters.style}")
        
        return Response({
            'parameters': parameters.to_dict(),
            'confidence': parameters.confidence,
            'query': query
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        # Gemini service not configured (missing API key)
        logger.error(f"Gemini service error: {e}")
        return Response(
            {'error': 'AI service temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
        
    except Exception as e:
        # Query parsing failed
        logger.warning(f"Failed to parse query '{query[:50]}...': {e}")
        
        # Try to generate suggestions
        try:
            gemini_service = GeminiService()
            suggestions = gemini_service.suggest_alternatives(query, {
                'difficulties': ['beginner', 'intermediate', 'advanced'],
                'styles': ['romantic', 'energetic', 'sensual', 'playful']
            })
        except:
            suggestions = [
                'Try specifying a difficulty level (beginner, intermediate, or advanced)',
                'Try describing the style (romantic, energetic, sensual, or playful)',
                'Include tempo preference (slow, medium, or fast)'
            ]
        
        return Response({
            'error': 'Could not understand your query. Please try rephrasing.',
            'suggestions': suggestions
        }, status=status.HTTP_400_BAD_REQUEST)



@extend_schema(
    summary="Generate choreography with AI",
    description="""
    Generate a choreography using natural language description with AI-enhanced explanations.
    
    This endpoint combines AI query parsing with choreography generation, allowing users
    to describe what they want in natural language instead of specifying technical parameters.
    
    **Workflow:**
    1. Parse natural language query using Gemini AI (if parameters not provided)
    2. Create choreography generation task
    3. Trigger Cloud Run Job with AI mode enabled
    4. Job generates choreography with AI explanations for each move
    5. Return task ID for status polling
    
    **Examples:**
    - "Create a romantic beginner choreography for a slow song"
    - "I want an energetic intermediate routine for a party"
    - "Make me a sensual advanced bachata"
    
    **AI Enhancements:**
    - Natural language understanding
    - AI-generated explanations for move selections
    - Context-aware choreography generation
    
    **Response:**
    - Returns immediately with task_id (202 Accepted)
    - Poll /api/choreography/tasks/{task_id} for status
    - When complete, result includes AI explanations
    
    **Performance:**
    - Query parsing: 1-3 seconds
    - Total generation: 2-5 minutes (depending on audio length)
    """,
    request=AIGenerationSerializer,
    responses={
        202: OpenApiResponse(
            description="AI generation task created successfully",
            examples=[
                OpenApiExample(
                    'Task Created',
                    value={
                        'task_id': '550e8400-e29b-41d4-a716-446655440000',
                        'status': 'started',
                        'message': 'AI choreography generation started',
                        'poll_url': '/api/choreography/tasks/550e8400-e29b-41d4-a716-446655440000'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid query or parameters",
            examples=[
                OpenApiExample(
                    'Empty Query',
                    value={'query': ['Query cannot be empty']}
                ),
                OpenApiExample(
                    'Parse Error',
                    value={'error': 'Could not parse query'}
                )
            ]
        ),
        500: OpenApiResponse(
            description="Failed to create job execution",
            examples=[
                OpenApiExample(
                    'Job Creation Failed',
                    value={'error': 'Failed to create job execution'}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Choreography']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_with_ai(request):
    """
    Generate choreography with AI explanations.
    
    Parses natural language query and creates choreography generation task with AI mode.
    Uses blueprint-based architecture: generates complete blueprint in API, passes to job container.
    """
    # Import services at the top to avoid variable shadowing issues
    from services.blueprint_generator import BlueprintGenerator
    from services.vector_search_service import VectorSearchService
    from services.gemini_service import GeminiService
    
    serializer = AIGenerationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    query = serializer.validated_data['query']
    parameters = serializer.validated_data.get('parameters')
    
    # Parse query if parameters not provided
    if not parameters:
        try:
            gemini_svc = GeminiService()
            parsed = gemini_svc.parse_choreography_request(query)
            parameters = parsed.to_dict()
            logger.info(f"User {request.user.id} AI generation - parsed query: {parameters}")
        except Exception as e:
            logger.error(f"Failed to parse query for AI generation: {e}")
            return Response(
                {'error': 'Could not parse query'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Create task
    import uuid
    task_id = str(uuid.uuid4())
    task = ChoreographyTask.objects.create(
        task_id=task_id,
        user=request.user,
        status='pending',
        progress=0,
        stage='generating_blueprint',
        message='Generating AI choreography blueprint...'
    )
    
    # Extract parameters with defaults
    difficulty = parameters.get('difficulty', 'intermediate')
    energy_level = parameters.get('energy_level', 'medium')
    style = parameters.get('style', 'modern')
    
    # Select appropriate song using intelligent song selector
    try:
        from services.song_selector import SongSelector
        
        song_selector = SongSelector()
        song = song_selector.select_song_for_choreography(
            query=query,
            difficulty=difficulty,
            energy_level=energy_level,
            style=style
        )
        
        # Link song to task
        task.song = song
        task.save()
        
        logger.info(
            f"Selected song {song.id} ({song.title} by {song.artist}) for AI generation task {task_id}",
            extra={
                'song_id': song.id,
                'song_title': song.title,
                'song_bpm': song.bpm,
                'song_genre': song.genre,
                'query': query[:50],
                'difficulty': difficulty,
                'energy_level': energy_level,
                'style': style
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to select song for AI generation: {e}")
        task.status = 'failed'
        task.error = f'Song selection failed: {str(e)}'
        task.save()
        return Response(
            {'error': 'Failed to select song'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    try:
        # Generate blueprint using BlueprintGenerator
        from services.blueprint_generator import BlueprintGenerator
        from services.vector_search_service import get_vector_search_service
        
        # Initialize services
        vector_search = get_vector_search_service()
        gemini_svc = GeminiService()
        
        # Import MusicAnalyzer from job container (temporary until we move it to backend)
        import sys
        import os
        job_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', '..', 'job', 'src', 'services')
        if job_path not in sys.path:
            sys.path.insert(0, job_path)
        from music_analyzer import MusicAnalyzer
        
        music_analyzer = MusicAnalyzer()
        
        # Create blueprint generator
        blueprint_gen = BlueprintGenerator(
            vector_search_service=vector_search,
            music_analyzer=music_analyzer,
            gemini_service=gemini_svc
        )
        
        # Generate blueprint
        logger.info(f"Generating AI blueprint for task {task_id} with query: {query[:50]}...")
        blueprint = blueprint_gen.generate_blueprint(
            task_id=task_id,
            song_path=song.audio_path,
            difficulty=difficulty,
            energy_level=energy_level,
            style=style,
            user_id=request.user.id
        )
        
        # Add AI-specific metadata to blueprint
        blueprint['generation_parameters']['ai_mode'] = True
        blueprint['generation_parameters']['original_query'] = query
        
        # Store blueprint in database
        from .models import Blueprint
        Blueprint.objects.create(
            task=task,
            blueprint_json=blueprint
        )
        
        logger.info(f"AI blueprint generated and stored for task {task_id}")
        
        # Update task status
        task.stage = 'submitting_job'
        task.message = 'Blueprint generated, submitting job...'
        task.save()
        
    except Exception as e:
        logger.error(
            f"Failed to generate AI blueprint for task {task_id}: {e}",
            extra={
                'task_id': task_id,
                'user_id': request.user.id,
                'query': query[:100],
                'error': str(e)
            },
            exc_info=True
        )
        task.status = 'failed'
        task.error = f'Blueprint generation failed: {str(e)}'
        task.save()
        return Response(
            {'error': 'Failed to generate blueprint'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Trigger Cloud Run Job with blueprint
    jobs_service = CloudRunJobsService()
    try:
        import json
        execution_name = jobs_service.create_job_execution(
            task_id=task_id,
            user_id=request.user.id,
            parameters={'blueprint_json': json.dumps(blueprint)}
        )
        
        task.job_execution_name = execution_name
        task.status = 'started'
        task.stage = 'video_assembly'
        task.message = 'Job submitted, assembling video...'
        task.save()
        
        logger.info(f"Created AI generation job for task {task_id}: {execution_name}")
        
    except Exception as e:
        logger.error(f"Failed to create AI generation job for task {task_id}: {e}")
        task.status = 'failed'
        task.error = f'Job submission failed: {str(e)}'
        task.save()
        return Response(
            {'error': 'Failed to create job execution'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response({
        'task_id': task_id,
        'status': 'started',
        'message': 'AI choreography generation started',
        'poll_url': f'/api/choreography/tasks/{task_id}'
    }, status=status.HTTP_202_ACCEPTED)


@extend_schema(
    summary="Serve choreography video",
    description="""
    Serve the generated choreography video file.
    
    This endpoint streams the video file for a completed choreography task.
    The video is served with proper content-type headers for browser playback.
    
    **Access Control:**
    - Requires authentication
    - Users can only access their own videos
    
    **Response:**
    - Content-Type: video/mp4
    - Supports range requests for seeking
    """,
    responses={
        200: OpenApiResponse(description="Video file stream"),
        404: OpenApiResponse(description="Video not found or task not completed"),
        403: OpenApiResponse(description="Not authorized to access this video"),
    },
    tags=['Choreography']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def serve_video(request, task_id):
    """
    Serve the generated choreography video file.
    
    Streams the video file for browser playback with proper headers.
    """
    from django.http import FileResponse, Http404
    import os
    from django.conf import settings
    
    # Get the task and verify ownership
    task = get_object_or_404(ChoreographyTask, task_id=task_id)
    
    # Check if user owns this task
    if task.user_id != request.user.id:
        return Response(
            {'error': 'You do not have permission to access this video'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if task is completed
    if task.status != 'completed':
        return Response(
            {'error': 'Video is not ready yet. Task status: ' + task.status},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get video path from task result
    if not task.result or 'output_path' not in task.result:
        logger.error(f'No output_path in task result for task {task_id}')
        return Response(
            {'error': 'Video path not found in task result'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Construct full path - result contains relative path like "output/user_123/video.mp4"
    output_path = task.result.get('output_path', '')
    local_path = os.path.join('/app/data', output_path)
    
    # Verify file exists
    if not os.path.exists(local_path):
        logger.error(f'Video file not found: {local_path}')
        return Response(
            {'error': 'Video file not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Open and serve the file
    try:
        video_file = open(local_path, 'rb')
        video_filename = os.path.basename(local_path)
        response = FileResponse(video_file, content_type='video/mp4')
        response['Content-Disposition'] = f'inline; filename="{video_filename}"'
        response['Accept-Ranges'] = 'bytes'
        return response
    except Exception as e:
        logger.error(f'Error serving video: {str(e)}')
        return Response(
            {'error': 'Error serving video file'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
