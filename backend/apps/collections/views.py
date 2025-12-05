from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import SavedChoreography
from .serializers import (
    SavedChoreographySerializer,
    CollectionStatsSerializer,
    SaveChoreographySerializer,
    BulkDeleteSerializer
)
from apps.choreography.models import ChoreographyTask
from services.storage_service import StorageService
import logging

logger = logging.getLogger(__name__)


@extend_schema(
    summary="List saved choreographies",
    description="""
    Retrieve a paginated list of the authenticated user's saved choreographies.
    
    Supports filtering by difficulty level and searching by title. Results are paginated
    with customizable page size.
    """,
    parameters=[
        OpenApiParameter(
            name='difficulty',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by difficulty level',
            enum=['beginner', 'intermediate', 'advanced'],
            required=False
        ),
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search by title (case-insensitive partial match)',
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
            description='Number of items per page',
            required=False
        )
    ],
    responses={
        200: OpenApiResponse(
            response=SavedChoreographySerializer,
            description="Paginated list of saved choreographies",
            examples=[
                OpenApiExample(
                    'Collection List',
                    value={
                        'count': 15,
                        'next': 'http://localhost:8000/api/collections?page=2',
                        'previous': None,
                        'results': [
                            {
                                'id': 1,
                                'title': 'Romantic Bachata',
                                'video_path': 'https://storage.googleapis.com/bucket/video1.mp4',
                                'difficulty': 'intermediate',
                                'duration': 180,
                                'music_info': {'song': 'Obsesión', 'artist': 'Aventura'},
                                'generation_parameters': {'energy_level': 'medium', 'style': 'romantic'},
                                'created_at': '2025-11-02T10:35:00Z'
                            }
                        ]
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Collections'],
    methods=['GET']
)
@extend_schema(
    summary="Save choreography",
    description="""
    Save a generated choreography to the user's collection.
    
    After a choreography generation task completes, use this endpoint to save it
    to your collection with metadata like title, difficulty, and music information.
    """,
    request=SavedChoreographySerializer,
    responses={
        201: OpenApiResponse(
            response=SavedChoreographySerializer,
            description="Choreography saved successfully",
            examples=[
                OpenApiExample(
                    'Saved Choreography',
                    value={
                        'id': 1,
                        'title': 'Romantic Bachata',
                        'video_path': 'https://storage.googleapis.com/bucket/video1.mp4',
                        'difficulty': 'intermediate',
                        'duration': 180,
                        'music_info': {'song': 'Obsesión', 'artist': 'Aventura'},
                        'generation_parameters': {'energy_level': 'medium', 'style': 'romantic'},
                        'created_at': '2025-11-02T10:35:00Z'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Validation error",
            examples=[
                OpenApiExample(
                    'Missing Required Field',
                    value={'video_path': ['This field is required.']}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Collections'],
    methods=['POST']
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def collection_list(request):
    """
    List or create saved choreographies.
    
    GET: Retrieve paginated list with optional filtering and search.
    POST: Save a new choreography to the collection.
    """
    if request.method == 'GET':
        queryset = SavedChoreography.objects.filter(user=request.user)
        
        # Filter by difficulty if provided
        difficulty = request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # Search by title if provided
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)
        
        # Paginate
        from core.pagination import PageNumberPagination as CustomPagination
        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        serializer = SavedChoreographySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    elif request.method == 'POST':
        serializer = SavedChoreographySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get choreography details",
    description="Retrieve detailed information about a specific saved choreography.",
    responses={
        200: OpenApiResponse(
            response=SavedChoreographySerializer,
            description="Choreography details",
            examples=[
                OpenApiExample(
                    'Choreography Detail',
                    value={
                        'id': 1,
                        'title': 'Romantic Bachata',
                        'video_path': 'https://storage.googleapis.com/bucket/video1.mp4',
                        'difficulty': 'intermediate',
                        'duration': 180,
                        'music_info': {'song': 'Obsesión', 'artist': 'Aventura', 'tempo': 120},
                        'generation_parameters': {'energy_level': 'medium', 'style': 'romantic'},
                        'created_at': '2025-11-02T10:35:00Z'
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required"),
        404: OpenApiResponse(
            description="Choreography not found or does not belong to user",
            examples=[
                OpenApiExample(
                    'Not Found',
                    value={'detail': 'Not found.'}
                )
            ]
        )
    },
    tags=['Collections'],
    methods=['GET']
)
@extend_schema(
    summary="Update choreography",
    description="""
    Update metadata for a saved choreography.
    
    Supports partial updates - only include fields you want to change.
    Common use cases: updating title, changing difficulty rating, or adding notes.
    """,
    request=SavedChoreographySerializer,
    responses={
        200: OpenApiResponse(
            response=SavedChoreographySerializer,
            description="Choreography updated successfully",
            examples=[
                OpenApiExample(
                    'Updated Choreography',
                    value={
                        'id': 1,
                        'title': 'Updated Title',
                        'video_path': 'https://storage.googleapis.com/bucket/video1.mp4',
                        'difficulty': 'advanced',
                        'duration': 180,
                        'music_info': {'song': 'Obsesión', 'artist': 'Aventura'},
                        'generation_parameters': {'energy_level': 'medium', 'style': 'romantic'},
                        'created_at': '2025-11-02T10:35:00Z'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Validation error",
            examples=[
                OpenApiExample(
                    'Invalid Difficulty',
                    value={'difficulty': ['"expert" is not a valid choice.']}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required"),
        404: OpenApiResponse(description="Choreography not found or does not belong to user")
    },
    tags=['Collections'],
    methods=['PUT']
)
@extend_schema(
    summary="Delete choreography",
    description="""
    Permanently delete a saved choreography from the collection.
    
    **Warning:** This action cannot be undone. The video file will remain in storage
    but will no longer be accessible through the API.
    """,
    responses={
        204: OpenApiResponse(description="Choreography deleted successfully"),
        401: OpenApiResponse(description="Authentication required"),
        404: OpenApiResponse(description="Choreography not found or does not belong to user")
    },
    tags=['Collections'],
    methods=['DELETE']
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def collection_detail(request, pk):
    """
    Get, update, or delete a saved choreography.
    
    GET: Retrieve choreography details.
    PUT: Update choreography metadata (partial updates supported).
    DELETE: Permanently delete choreography from collection.
    """
    choreography = get_object_or_404(SavedChoreography, id=pk, user=request.user)
    
    if request.method == 'GET':
        serializer = SavedChoreographySerializer(choreography)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = SavedChoreographySerializer(choreography, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        choreography.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="Get collection statistics",
    description="""
    Retrieve statistics about the user's choreography collection.
    
    Returns:
    - Total number of saved choreographies
    - Count by difficulty level (beginner, intermediate, advanced)
    - Total duration of all choreographies in seconds
    
    Useful for dashboard displays and collection overview.
    """,
    responses={
        200: OpenApiResponse(
            response=CollectionStatsSerializer,
            description="Collection statistics",
            examples=[
                OpenApiExample(
                    'Stats',
                    value={
                        'total_count': 25,
                        'by_difficulty': {
                            'beginner': 8,
                            'intermediate': 12,
                            'advanced': 5
                        },
                        'total_duration': 4500
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Collections']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def collection_stats(request):
    """
    Get collection statistics.
    
    Returns aggregate statistics about the user's saved choreographies.
    """
    queryset = SavedChoreography.objects.filter(user=request.user)
    
    stats = {
        'total_count': queryset.count(),
        'by_difficulty': dict(
            queryset.values('difficulty').annotate(count=Count('id')).values_list('difficulty', 'count')
        ),
        'total_duration': queryset.aggregate(total=Sum('duration'))['total'] or 0,
    }
    
    serializer = CollectionStatsSerializer(stats)
    return Response(serializer.data)



@extend_schema(
    summary="Save choreography from task",
    description="""
    Save a completed choreography generation task to the user's collection.
    
    After a choreography generation task completes successfully, use this endpoint
    to save it to your collection with optional custom title and difficulty.
    
    **Workflow:**
    1. Generate choreography via POST /api/choreography/generate
    2. Poll task status via GET /api/choreography/tasks/{task_id}
    3. When status is 'completed', save via POST /api/collections/save
    
    **Title Generation:**
    - If no title provided, generates: "Choreography YYYY-MM-DD HH:MM"
    
    **Difficulty:**
    - If not provided, uses difficulty from task generation parameters
    - If task has no difficulty, defaults to 'intermediate'
    """,
    request=SaveChoreographySerializer,
    responses={
        201: OpenApiResponse(
            response=SavedChoreographySerializer,
            description="Choreography saved successfully",
            examples=[
                OpenApiExample(
                    'Saved Choreography',
                    value={
                        'id': '550e8400-e29b-41d4-a716-446655440000',
                        'title': 'My Romantic Bachata',
                        'video_path': 'choreographies/2025/11/video.mp4',
                        'difficulty': 'intermediate',
                        'duration': 180.5,
                        'music_info': {'song': 'Obsesión', 'artist': 'Aventura'},
                        'generation_parameters': {'task_id': '...', 'energy_level': 'medium'},
                        'created_at': '2025-11-03T10:30:00Z'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Task not completed or validation error",
            examples=[
                OpenApiExample(
                    'Task Not Completed',
                    value={'error': 'Cannot save incomplete choreography'}
                ),
                OpenApiExample(
                    'Invalid Task ID',
                    value={'task_id': ['Invalid UUID format']}
                )
            ]
        ),
        404: OpenApiResponse(
            description="Task not found or does not belong to user",
            examples=[
                OpenApiExample(
                    'Not Found',
                    value={'detail': 'Not found.'}
                )
            ]
        ),
        409: OpenApiResponse(
            description="Choreography already saved",
            examples=[
                OpenApiExample(
                    'Already Saved',
                    value={'error': 'Choreography already saved'}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Collections']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_choreography(request):
    """
    Save a completed choreography task to user's collection.
    
    Validates the task is completed and not already saved, then creates
    a SavedChoreography record with data from the task result.
    """
    serializer = SaveChoreographySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    task_id = serializer.validated_data['task_id']
    
    # Get task and validate it belongs to user
    task = get_object_or_404(ChoreographyTask, task_id=str(task_id), user=request.user)
    
    # Check if task is completed
    if task.status != 'completed':
        return Response(
            {'error': 'Cannot save incomplete choreography'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already saved (look for task_id in generation_parameters)
    existing = SavedChoreography.objects.filter(
        user=request.user,
        generation_parameters__task_id=str(task_id)
    ).first()
    
    if existing:
        return Response(
            {'error': 'Choreography already saved'},
            status=status.HTTP_409_CONFLICT
        )
    
    # Extract data from task result
    result = task.result or {}
    
    # Generate title if not provided
    title = serializer.validated_data.get('title')
    if not title:
        title = f"Choreography {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    
    # Get difficulty (priority: request > result > default)
    difficulty = serializer.validated_data.get('difficulty')
    if not difficulty:
        difficulty = result.get('difficulty') or result.get('generation_parameters', {}).get('difficulty', 'intermediate')
    
    # Get video path from result (check both video_path and video_url)
    video_path = result.get('video_path') or result.get('video_url', '')
    # Clean up the path - remove /media/ prefix if present
    if video_path.startswith('/media/'):
        video_path = video_path[7:]
    
    # Create SavedChoreography
    choreography = SavedChoreography.objects.create(
        user=request.user,
        title=title,
        video_path=video_path,
        difficulty=difficulty,
        duration=result.get('sequence_duration') or result.get('total_duration', 0),
        music_info=result.get('music_info', {}),
        generation_parameters={
            'task_id': str(task_id),
            **result.get('generation_parameters', {})
        }
    )
    
    logger.info(f"User {request.user.id} saved choreography from task {task_id}")
    
    return Response(
        SavedChoreographySerializer(choreography).data,
        status=status.HTTP_201_CREATED
    )



@extend_schema(
    summary="Delete all choreographies",
    description="""
    Bulk delete all choreographies in the user's collection.
    
    **⚠️ WARNING:** This action is irreversible and will permanently delete
    all saved choreographies for the authenticated user.
    
    **Safety Mechanism:**
    - Requires explicit confirmation parameter set to `true`
    - Uses database transaction for atomicity
    - Logs deletion for audit trail
    
    **Use Cases:**
    - User wants to clear their entire collection
    - User wants to start fresh
    - Testing/development cleanup
    
    **Note:** This only deletes the database records. Video files in GCS
    are not automatically deleted and may need separate cleanup.
    """,
    request=BulkDeleteSerializer,
    responses={
        200: OpenApiResponse(
            description="All choreographies deleted successfully",
            examples=[
                OpenApiExample(
                    'Deletion Success',
                    value={
                        'deleted_count': 15,
                        'message': 'Successfully deleted 15 choreographies'
                    }
                ),
                OpenApiExample(
                    'Empty Collection',
                    value={
                        'deleted_count': 0,
                        'message': 'Successfully deleted 0 choreographies'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Confirmation not provided",
            examples=[
                OpenApiExample(
                    'Missing Confirmation',
                    value={'error': 'Confirmation required'}
                ),
                OpenApiExample(
                    'Invalid Confirmation',
                    value={'confirmation': ['Confirmation required to delete all choreographies']}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Collections']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def delete_all_choreographies(request):
    """
    Bulk delete all user's choreographies.
    
    Requires explicit confirmation and uses transaction for safety.
    """
    serializer = BulkDeleteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Confirmation validated by serializer, proceed with deletion
    deleted_count, _ = SavedChoreography.objects.filter(
        user=request.user
    ).delete()
    
    logger.info(f"User {request.user.id} deleted {deleted_count} choreographies via bulk delete")
    
    return Response({
        'deleted_count': deleted_count,
        'message': f'Successfully deleted {deleted_count} choreographies'
    }, status=status.HTTP_200_OK)



@extend_schema(
    summary="Clean up orphaned choreographies",
    description="""
    Clean up choreography records that reference non-existent video files in GCS.
    
    This endpoint identifies and removes "orphaned" choreography records where
    the associated video file no longer exists in Google Cloud Storage.
    
    **Use Cases:**
    - Free up database space by removing invalid records
    - Clean up after manual GCS file deletions
    - Maintain data integrity between database and storage
    
    **Process:**
    1. Iterates through user's choreographies
    2. Checks if each video file exists in GCS
    3. Collects IDs of choreographies with missing files
    4. Deletes orphaned records in a transaction
    5. Returns count of cleaned records
    
    **Performance:**
    - Completes in <30 seconds for typical collections
    - Uses batch operations for efficiency
    - Transaction-safe (all or nothing)
    
    **Note:** This only removes database records. It does not delete
    any files from GCS.
    """,
    responses={
        200: OpenApiResponse(
            description="Cleanup completed successfully",
            examples=[
                OpenApiExample(
                    'Cleanup Success',
                    value={
                        'cleaned_count': 3,
                        'message': 'Cleaned up 3 orphaned choreographies'
                    }
                ),
                OpenApiExample(
                    'No Orphans Found',
                    value={
                        'cleaned_count': 0,
                        'message': 'Cleaned up 0 orphaned choreographies'
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Collections']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cleanup_collection(request):
    """
    Clean up orphaned choreography records.
    
    Identifies and removes choreographies where video files no longer exist in GCS.
    """
    storage = StorageService()
    choreographies = SavedChoreography.objects.filter(user=request.user)
    
    orphaned_ids = []
    
    # Check each choreography's video file
    for choreo in choreographies:
        video_path = str(choreo.video_path)
        
        # Skip empty paths
        if not video_path or video_path == '':
            orphaned_ids.append(choreo.id)
            continue
        
        # Check if file exists in GCS
        if not storage.file_exists(video_path):
            orphaned_ids.append(choreo.id)
            logger.debug(f"Found orphaned choreography {choreo.id}: video file {video_path} does not exist")
    
    # Delete orphaned records
    cleaned_count = 0
    if orphaned_ids:
        cleaned_count = SavedChoreography.objects.filter(
            id__in=orphaned_ids
        ).delete()[0]
    
    logger.info(f"User {request.user.id} cleaned up {cleaned_count} orphaned choreographies")
    
    return Response({
        'cleaned_count': cleaned_count,
        'message': f'Cleaned up {cleaned_count} orphaned choreographies'
    }, status=status.HTTP_200_OK)
