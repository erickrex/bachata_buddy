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
    SongGenerationSerializer,
    DescribeChoreographySerializer,
    GenerateChoreographySerializer
)
from django.conf import settings
import logging
import uuid
import time

logger = logging.getLogger(__name__)


# Video generation timeout in seconds (10 minutes)
VIDEO_GENERATION_TIMEOUT = 600


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
    summary="Generate choreography video synchronously",
    description="""
    Generate choreography video synchronously from a song.
    
    This endpoint generates a choreography video immediately within the HTTP request.
    The video is assembled using FFmpeg directly in the backend, eliminating the need
    for a separate job container.
    
    **Workflow:**
    1. Validate song_id and parameters
    2. Generate blueprint using BlueprintGenerator
    3. Assemble video using VideoAssemblyService (FFmpeg)
    4. Return video_url directly in response
    
    **Parameters:**
    - song_id: ID of the song from the song library (required)
    - difficulty: beginner, intermediate, or advanced (default: intermediate)
    - energy_level: low, medium, or high (default: medium)
    - style: traditional, modern, romantic, or sensual (default: modern)
    
    **Response:**
    - Returns video_url directly when complete (200 OK)
    - Task record is updated with progress during generation
    
    **Timeout:**
    - Request will timeout after 10 minutes if video assembly takes too long
    
    **Example Request:**
    ```json
    {
        "song_id": 1,
        "difficulty": "intermediate",
        "energy_level": "medium",
        "style": "modern"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "completed",
        "video_url": "https://storage.example.com/output/video.mp4",
        "duration_seconds": 45.2
    }
    ```
    """,
    request=GenerateChoreographySerializer,
    responses={
        200: OpenApiResponse(
            description="Video generated successfully",
            examples=[
                OpenApiExample(
                    'Success',
                    value={
                        'task_id': '550e8400-e29b-41d4-a716-446655440000',
                        'status': 'completed',
                        'video_url': 'https://storage.example.com/output/video.mp4',
                        'duration_seconds': 45.2
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
        404: OpenApiResponse(
            description="Resource not found",
            examples=[
                OpenApiExample(
                    'Song Not Found',
                    value={'error': 'Song not found', 'details': 'Song with ID 999 does not exist'}
                )
            ]
        ),
        500: OpenApiResponse(
            description="Video assembly failed",
            examples=[
                OpenApiExample(
                    'Assembly Failed',
                    value={
                        'error': 'Video assembly failed',
                        'details': 'FFmpeg error: ...',
                        'stage': 'concatenating'
                    }
                )
            ]
        ),
        504: OpenApiResponse(
            description="Request timeout",
            examples=[
                OpenApiExample(
                    'Timeout',
                    value={
                        'error': 'Video generation timed out',
                        'details': 'Video assembly exceeded 10 minute limit'
                    }
                )
            ]
        )
    },
    tags=['Choreography']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_choreography(request):
    """
    Generate choreography video synchronously.
    
    Creates a choreography video immediately within the HTTP request using
    VideoAssemblyService for FFmpeg-based video assembly.
    
    **Feature: job-integration**
    **Validates: Requirements 1.1, 7.1, 7.2**
    """
    from services.blueprint_generator import BlueprintGenerator
    from services.video_assembly_service import VideoAssemblyService, VideoAssemblyError
    from services.storage.factory import get_storage_backend
    from services.vector_search_service import get_vector_search_service
    from music_analyzer import MusicAnalyzer
    
    # Validate request
    serializer = GenerateChoreographySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Get the song
    song_id = serializer.validated_data['song_id']
    try:
        song = Song.objects.get(id=song_id)
    except Song.DoesNotExist:
        return Response(
            {'error': 'Song not found', 'details': f'Song with ID {song_id} does not exist'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Extract parameters
    difficulty = serializer.validated_data['difficulty']
    energy_level = serializer.validated_data.get('energy_level') or 'medium'
    style = serializer.validated_data.get('style') or 'modern'
    
    # Create task record
    task_id = str(uuid.uuid4())
    task = ChoreographyTask.objects.create(
        task_id=task_id,
        user=request.user,
        status='started',
        progress=0,
        stage='generating_blueprint',
        message='Generating choreography blueprint...',
        song=song
    )
    
    logger.info(
        f"Starting synchronous video generation for task {task_id}",
        extra={
            'task_id': task_id,
            'song_id': song_id,
            'user_id': request.user.id,
            'difficulty': difficulty,
            'energy_level': energy_level,
            'style': style
        }
    )
    
    start_time = time.time()
    
    # Progress callback to update task record
    def progress_callback(stage: str, progress: int, message: str):
        """Update task record with progress."""
        task.stage = stage
        task.progress = progress
        task.message = message
        task.save()
        logger.debug(f"Task {task_id} progress: {stage} ({progress}%) - {message}")
    
    try:
        # Step 1: Generate blueprint (10% progress)
        progress_callback('generating_blueprint', 10, 'Analyzing music and generating blueprint...')
        
        # Initialize services
        vector_search = get_vector_search_service()
        music_analyzer = MusicAnalyzer()
        
        blueprint_gen = BlueprintGenerator(
            vector_search_service=vector_search,
            music_analyzer=music_analyzer
        )
        
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
        
        logger.info(f"Blueprint generated for task {task_id}: {len(blueprint.get('moves', []))} moves")
        
        # Step 2: Assemble video using VideoAssemblyService
        progress_callback('video_assembly', 15, 'Starting video assembly...')
        
        storage_backend = get_storage_backend()
        video_assembly = VideoAssemblyService(storage_service=storage_backend)
        
        # Check FFmpeg availability
        if not video_assembly.check_ffmpeg_available():
            raise VideoAssemblyError("FFmpeg is not available in the system PATH")
        
        # Assemble video with progress updates
        video_url = video_assembly.assemble_video(
            blueprint=blueprint,
            progress_callback=progress_callback
        )
        
        # Calculate duration
        elapsed_time = time.time() - start_time
        
        # Update task as completed
        task.status = 'completed'
        task.progress = 100
        task.stage = 'completed'
        task.message = 'Choreography video generated successfully'
        task.result = {
            'video_url': video_url,
            'output_path': blueprint.get('output_config', {}).get('output_path'),
            'duration_seconds': elapsed_time,
            'move_count': len(blueprint.get('moves', []))
        }
        task.save()
        
        logger.info(
            f"Video generation completed for task {task_id} in {elapsed_time:.1f}s",
            extra={
                'task_id': task_id,
                'video_url': video_url,
                'duration_seconds': elapsed_time
            }
        )
        
        return Response({
            'task_id': task_id,
            'status': 'completed',
            'video_url': video_url,
            'duration_seconds': round(elapsed_time, 2)
        }, status=status.HTTP_200_OK)
        
    except VideoAssemblyError as e:
        elapsed_time = time.time() - start_time
        error_msg = str(e)
        current_stage = task.stage
        
        # Update task with error
        task.status = 'failed'
        task.message = 'Video assembly failed'
        task.error = error_msg
        task.save()
        
        logger.error(
            f"Video assembly failed for task {task_id}: {error_msg}",
            extra={
                'task_id': task_id,
                'error': error_msg,
                'elapsed_time': elapsed_time,
                'stage': current_stage
            }
        )
        
        # Check if it was a timeout (Requirements 1.4, 6.4)
        if elapsed_time >= VIDEO_GENERATION_TIMEOUT:
            return Response({
                'error': 'Video generation timed out',
                'details': f'Video assembly exceeded {VIDEO_GENERATION_TIMEOUT // 60} minute limit',
                'task_id': task_id,
                'stage': current_stage
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
        
        # Check for specific error types (Requirements 6.1, 6.2, 6.3)
        if 'FFmpeg is not available' in error_msg:
            return Response({
                'error': 'FFmpeg not available',
                'details': error_msg,
                'task_id': task_id,
                'stage': current_stage
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if 'Failed to fetch' in error_msg or 'not found after download' in error_msg:
            return Response({
                'error': 'Resource not found',
                'details': error_msg,
                'task_id': task_id,
                'stage': current_stage
            }, status=status.HTTP_404_NOT_FOUND)
        
        # General processing error (Requirements 1.3, 6.3)
        return Response({
            'error': 'Video assembly failed',
            'details': error_msg,
            'stage': current_stage,
            'task_id': task_id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except FileNotFoundError as e:
        # Handle missing files (Requirements 6.2)
        elapsed_time = time.time() - start_time
        error_msg = str(e)
        current_stage = task.stage
        
        task.status = 'failed'
        task.message = 'Required file not found'
        task.error = error_msg
        task.save()
        
        logger.error(
            f"File not found for task {task_id}: {error_msg}",
            extra={
                'task_id': task_id,
                'error': error_msg,
                'stage': current_stage
            }
        )
        
        return Response({
            'error': 'Resource not found',
            'details': error_msg,
            'task_id': task_id,
            'stage': current_stage
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = str(e)
        current_stage = task.stage
        
        # Update task with error
        task.status = 'failed'
        task.message = 'Video generation failed'
        task.error = error_msg
        task.save()
        
        logger.error(
            f"Video generation failed for task {task_id}: {error_msg}",
            extra={
                'task_id': task_id,
                'error': error_msg,
                'elapsed_time': elapsed_time
            },
            exc_info=True
        )
        
        return Response({
            'error': 'Video generation failed',
            'details': error_msg,
            'task_id': task_id,
            'stage': current_stage
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




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
        # Use ParameterExtractor instead of GeminiService
        from services.parameter_extractor import ParameterExtractor
        
        extractor = ParameterExtractor()
        parameters = extractor.extract(query)
        
        logger.info(f"User {request.user.id} parsed query: '{query[:50]}...' -> {parameters.get('difficulty')}/{parameters.get('style')}")
        
        return Response({
            'parameters': parameters,
            'confidence': 0.8,  # Default confidence since ParameterExtractor doesn't provide this
            'query': query
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        # Parameter extraction failed
        logger.error(f"Parameter extraction error: {e}")
        return Response(
            {'error': 'AI service temporarily unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
        
    except Exception as e:
        # Query parsing failed
        logger.warning(f"Failed to parse query '{query[:50]}...': {e}")
        
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
    from services.parameter_extractor import ParameterExtractor
    
    serializer = AIGenerationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    query = serializer.validated_data['query']
    parameters = serializer.validated_data.get('parameters')
    
    # Parse query if parameters not provided
    if not parameters:
        try:
            extractor = ParameterExtractor()
            parameters = extractor.extract(query)
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
        
        # Import MusicAnalyzer from backend
        from music_analyzer import MusicAnalyzer
        
        music_analyzer = MusicAnalyzer()
        
        # Create blueprint generator
        blueprint_gen = BlueprintGenerator(
            vector_search_service=vector_search,
            music_analyzer=music_analyzer
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
    
    # Assemble video using VideoAssemblyService (synchronous)
    from services.video_assembly_service import VideoAssemblyService, VideoAssemblyError
    from services.storage_service import get_storage_service
    
    # Progress callback to update task record
    def progress_callback(stage: str, progress: int, message: str):
        """Update task record with progress."""
        task.stage = stage
        task.progress = progress
        task.message = message
        task.save()
        logger.debug(f"Task {task_id} progress: {stage} ({progress}%) - {message}")
    
    try:
        storage_service = get_storage_service()
        video_assembly = VideoAssemblyService(storage_service=storage_service)
        
        # Check FFmpeg availability
        if not video_assembly.check_ffmpeg_available():
            raise VideoAssemblyError("FFmpeg is not available in the system PATH")
        
        task.status = 'started'
        task.stage = 'video_assembly'
        task.message = 'Assembling video...'
        task.save()
        
        # Assemble video with progress updates
        video_url = video_assembly.assemble_video(
            blueprint=blueprint,
            progress_callback=progress_callback
        )
        
        # Update task as completed
        task.status = 'completed'
        task.progress = 100
        task.stage = 'completed'
        task.message = 'AI choreography video generated successfully'
        task.result = {
            'video_url': video_url,
            'output_path': blueprint.get('output_config', {}).get('output_path'),
            'move_count': len(blueprint.get('moves', []))
        }
        task.save()
        
        logger.info(f"AI video generation completed for task {task_id}")
        
    except VideoAssemblyError as e:
        logger.error(f"Video assembly failed for AI task {task_id}: {e}")
        task.status = 'failed'
        task.error = f'Video assembly failed: {str(e)}'
        task.save()
        return Response(
            {'error': 'Video assembly failed', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        logger.error(f"Failed to assemble AI video for task {task_id}: {e}")
        task.status = 'failed'
        task.error = f'Video assembly failed: {str(e)}'
        task.save()
        return Response(
            {'error': 'Failed to assemble video'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response({
        'task_id': task_id,
        'status': 'completed',
        'video_url': video_url,
        'message': 'AI choreography generation completed'
    }, status=status.HTTP_200_OK)


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



@extend_schema(
    summary="Generate choreography from natural language description (Path 2)",
    description="""
    Generate choreography using natural language description with agent orchestration.
    
    This is the Path 2 endpoint that uses OpenAI function calling for intelligent
    workflow orchestration. The agent autonomously decides which services to call
    and in what order based on the user's natural language request.
    
    **Agent Workflow:**
    1. Extract parameters from natural language using OpenAI
    2. Analyze music features
    3. Search for matching dance moves
    4. Generate choreography blueprint
    5. Trigger video assembly job
    
    **Examples:**
    - "Create a romantic beginner choreography"
    - "I want an energetic intermediate routine"
    - "Make me a sensual advanced bachata"
    
    **Agent Features:**
    - Natural language understanding
    - Intelligent function calling orchestration
    - Real-time reasoning updates
    - Adaptive workflow based on request
    
    **Response:**
    - Returns immediately with task_id (202 Accepted)
    - Poll /api/choreography/tasks/{task_id} for status
    - Task message field contains agent reasoning steps
    - When complete, result includes video URL
    
    **Performance:**
    - Parameter extraction: 1-3 seconds
    - Total generation: 2-5 minutes (depending on audio length)
    """,
    request=DescribeChoreographySerializer,
    responses={
        202: OpenApiResponse(
            description="Agent workflow started successfully",
            examples=[
                OpenApiExample(
                    'Task Created',
                    value={
                        'task_id': '550e8400-e29b-41d4-a716-446655440000',
                        'status': 'started',
                        'message': 'Analyzing your request...',
                        'poll_url': '/api/choreography/tasks/550e8400-e29b-41d4-a716-446655440000'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid request",
            examples=[
                OpenApiExample(
                    'Empty Request',
                    value={'user_request': ['Request cannot be empty']}
                ),
                OpenApiExample(
                    'Too Short',
                    value={'user_request': ['Request must be at least 10 characters long']}
                )
            ]
        ),
        500: OpenApiResponse(
            description="Failed to start agent workflow",
            examples=[
                OpenApiExample(
                    'Workflow Failed',
                    value={'error': 'Failed to start agent workflow'}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Choreography']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def describe_choreography(request):
    """
    Generate choreography from natural language description using agent orchestration.
    
    This is the Path 2 endpoint that uses OpenAI function calling to orchestrate
    the choreography generation workflow. The agent autonomously decides which
    services to call based on the user's natural language request.
    """
    # Validate request
    serializer = DescribeChoreographySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user_request = serializer.validated_data['user_request']
    
    # Create task
    import uuid
    task_id = str(uuid.uuid4())
    task = ChoreographyTask.objects.create(
        task_id=task_id,
        user=request.user,
        status='pending',
        progress=0,
        stage='parsing_request',
        message='Analyzing your request...'
    )
    
    logger.info(
        f"Created Path 2 agent task {task_id}",
        extra={
            'task_id': task_id,
            'user_id': request.user.id,
            'user_request': user_request[:100]
        }
    )
    
    # Select a song from the database based on the user request
    # This ensures the agent has a valid song path to work with
    try:
        from services.song_selector import SongSelector
        from services.parameter_extractor import ParameterExtractor
        import os
        
        # Extract parameters from user request to help with song selection
        openai_api_key = os.getenv('OPENAI_API_KEY')
        param_extractor = ParameterExtractor(openai_api_key=openai_api_key)
        params = param_extractor.extract_parameters(user_request)
        
        difficulty = params.get('difficulty', 'intermediate')
        energy_level = params.get('energy_level', 'medium')
        style = params.get('style', 'modern')
        
        song_selector = SongSelector()
        song = song_selector.select_song_for_choreography(
            query=user_request,
            difficulty=difficulty,
            energy_level=energy_level,
            style=style
        )
        
        # Link song to task
        task.song = song
        task.save()
        
        logger.info(
            f"Selected song {song.id} ({song.title} by {song.artist}) for Path 2 task {task_id}",
            extra={
                'song_id': song.id,
                'song_title': song.title,
                'song_path': song.audio_path,
                'task_id': task_id
            }
        )
        
    except Exception as e:
        logger.error(
            f"Failed to select song for Path 2 task {task_id}: {e}",
            exc_info=True
        )
        task.status = 'failed'
        task.error = f'Song selection failed: {str(e)}'
        task.save()
        return Response(
            {'error': 'Failed to select song for choreography'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Initialize agent service using factory function
    try:
        from services import get_agent_service
        
        agent_service = get_agent_service()
        
        logger.info(f"Initialized agent service for task {task_id}")
        
    except Exception as e:
        logger.error(
            f"Failed to initialize agent service for task {task_id}: {e}",
            exc_info=True
        )
        task.status = 'failed'
        task.error = f'Agent initialization failed: {str(e)}'
        task.save()
        return Response(
            {'error': 'Failed to initialize agent service'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Execute workflow asynchronously
    # Note: In production, this should be executed in a background task/thread
    # For now, we'll execute synchronously but return immediately
    try:
        # Start workflow in background (simplified for now)
        import threading
        
        # Capture song_path for the thread
        song_path = song.audio_path
        
        def run_workflow():
            try:
                agent_service.create_workflow(
                    task_id=task_id,
                    user_request=user_request,
                    user_id=request.user.id,
                    song_path=song_path  # Pass the selected song path
                )
            except Exception as e:
                logger.error(
                    f"Agent workflow failed for task {task_id}: {e}",
                    exc_info=True
                )
                # Update task with error
                from apps.choreography.models import ChoreographyTask
                task = ChoreographyTask.objects.get(task_id=task_id)
                task.status = 'failed'
                task.error = f'Workflow execution failed: {str(e)}'
                task.save()
        
        # Start workflow thread
        workflow_thread = threading.Thread(target=run_workflow, daemon=True)
        workflow_thread.start()
        
        logger.info(f"Started agent workflow thread for task {task_id}")
        
    except Exception as e:
        logger.error(
            f"Failed to start agent workflow for task {task_id}: {e}",
            exc_info=True
        )
        task.status = 'failed'
        task.error = f'Failed to start workflow: {str(e)}'
        task.save()
        return Response(
            {'error': 'Failed to start agent workflow'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Return task info immediately
    return Response({
        'task_id': task_id,
        'status': 'started',
        'message': task.message,
        'poll_url': f'/api/choreography/tasks/{task_id}'
    }, status=status.HTTP_202_ACCEPTED)
