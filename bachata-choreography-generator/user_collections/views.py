from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse
from choreography.models import SavedChoreography
from choreography.forms import SaveChoreographyForm


@login_required
def collection_list(request):
    """
    Display user's choreography collection with filtering, search, and pagination.
    
    GET parameters:
    - difficulty: Filter by difficulty level
    - search: Search in title and music_info
    - sort: Sort field (default: '-created_at')
    - page: Page number for pagination
    """
    try:
        # Start with user's choreographies
        choreographies = SavedChoreography.objects.filter(user=request.user)
        
        # Apply difficulty filter
        difficulty = request.GET.get('difficulty')
        if difficulty and difficulty in ['beginner', 'intermediate', 'advanced']:
            choreographies = choreographies.filter(difficulty=difficulty)
        
        # Apply search filter
        search = request.GET.get('search', '').strip()
        if search:
            choreographies = choreographies.filter(
                Q(title__icontains=search) |
                Q(music_info__icontains=search)
            )
        
        # Apply sorting (support both 'sort' and 'sort_by' parameters for compatibility)
        sort = request.GET.get('sort') or request.GET.get('sort_by', '-created_at')
        allowed_sorts = ['created_at', '-created_at', 'title', '-title', 'difficulty', '-difficulty', 'duration', '-duration']
        if sort in allowed_sorts:
            choreographies = choreographies.order_by(sort)
        else:
            choreographies = choreographies.order_by('-created_at')
        
        # Pagination (20 items per page)
        paginator = Paginator(choreographies, 20)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context = {
            'choreographies': page_obj,
            'page_obj': page_obj,
            'difficulty': difficulty,
            'search': search,
            'sort': sort,
        }
        
        return render(request, 'collections/list.html', context)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading collection list for user {request.user.id}: {e}", exc_info=True)
        from django.contrib import messages
        messages.error(request, 'An error occurred while loading your collection.')
        return render(request, 'collections/list.html', {
            'choreographies': [],
            'page_obj': None,
            'difficulty': None,
            'search': '',
            'sort': '-created_at',
        })



@login_required
def choreography_detail(request, pk):
    """
    Display detailed view of a specific choreography.
    Only accessible by the owner.
    """
    choreography = get_object_or_404(SavedChoreography, pk=pk, user=request.user)
    
    context = {
        'choreography': choreography,
    }
    
    return render(request, 'collections/detail.html', context)



@login_required
def choreography_edit(request, pk):
    """
    Edit a choreography's title and difficulty.
    Only accessible by the owner.
    """
    choreography = get_object_or_404(SavedChoreography, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = SaveChoreographyForm(request.POST, instance=choreography)
        if form.is_valid():
            form.save()
            return redirect('collections:detail', pk=choreography.pk)
    else:
        form = SaveChoreographyForm(instance=choreography)
    
    context = {
        'form': form,
        'choreography': choreography,
    }
    
    return render(request, 'collections/edit.html', context)



@login_required
@require_http_methods(["POST", "DELETE"])
def choreography_delete(request, pk):
    """
    Delete a choreography.
    Only accessible by the owner.
    Returns JSON for HTMX requests, redirects otherwise.
    """
    choreography = get_object_or_404(SavedChoreography, pk=pk, user=request.user)
    choreography.delete()
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        return JsonResponse({
            'success': True,
            'message': 'Choreography deleted successfully'
        })
    else:
        return redirect('collections:list')



@login_required
@require_http_methods(["POST"])
def save_choreography(request):
    """
    Save a generated choreography to user's collection.
    Expects POST data with title, difficulty, video_path, duration, music_info, generation_parameters.
    Returns JSON with success status and choreography_id.
    """
    try:
        form = SaveChoreographyForm(request.POST)
        
        if form.is_valid():
            choreography = form.save(commit=False)
            choreography.user = request.user
            
            # Get additional fields from POST data
            choreography.video_path = request.POST.get('video_path', '')
            
            # Validate and parse duration
            try:
                choreography.duration = float(request.POST.get('duration', 0))
            except (ValueError, TypeError):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Invalid duration value: {request.POST.get('duration')}")
                choreography.duration = 0
            
            # Handle JSON fields
            import json
            music_info = request.POST.get('music_info')
            if music_info:
                try:
                    choreography.music_info = json.loads(music_info) if isinstance(music_info, str) else music_info
                except json.JSONDecodeError as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Invalid music_info JSON: {e}")
                    choreography.music_info = {}
            
            generation_parameters = request.POST.get('generation_parameters')
            if generation_parameters:
                try:
                    choreography.generation_parameters = json.loads(generation_parameters) if isinstance(generation_parameters, str) else generation_parameters
                except json.JSONDecodeError as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Invalid generation_parameters JSON: {e}")
                    choreography.generation_parameters = {}
            
            choreography.save()
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Choreography {choreography.id} saved by user {request.user.id}")
            
            return JsonResponse({
                'success': True,
                'choreography_id': str(choreography.id),
                'message': 'Choreography saved successfully'
            })
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid save choreography form: {form.errors}")
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error saving choreography for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while saving choreography'
        }, status=500)



@login_required
def collection_stats(request):
    """
    Get statistics about user's choreography collection.
    Returns JSON with total count, duration stats, and counts by difficulty.
    """
    try:
        choreographies = SavedChoreography.objects.filter(user=request.user)
        
        # Calculate aggregated statistics
        stats = choreographies.aggregate(
            total_count=Count('id'),
            total_duration=Sum('duration'),
            avg_duration=Avg('duration'),
            beginner_count=Count('id', filter=Q(difficulty='beginner')),
            intermediate_count=Count('id', filter=Q(difficulty='intermediate')),
            advanced_count=Count('id', filter=Q(difficulty='advanced')),
        )
        
        # Convert None values to 0 and return flat structure for compatibility
        result = {
            'total_count': stats['total_count'] or 0,
            'total_duration': round(stats['total_duration'] or 0, 2),
            'avg_duration': round(stats['avg_duration'] or 0, 2),
            'beginner_count': stats['beginner_count'] or 0,
            'intermediate_count': stats['intermediate_count'] or 0,
            'advanced_count': stats['advanced_count'] or 0,
        }
        
        return JsonResponse(result)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error calculating collection stats for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An unexpected error occurred while calculating statistics'
        }, status=500)



@login_required
@require_http_methods(["PUT", "PATCH"])
def choreography_update(request, pk):
    """
    Update choreography metadata via API.
    
    FastAPI parity: PUT /collection/{id}
    Allows updating title and difficulty programmatically.
    """
    try:
        choreography = get_object_or_404(SavedChoreography, pk=pk, user=request.user)
        
        # Parse JSON body
        import json
        data = json.loads(request.body)
        
        # Update fields if provided
        if 'title' in data:
            choreography.title = data['title']
        
        if 'difficulty' in data:
            if data['difficulty'] in ['beginner', 'intermediate', 'advanced']:
                choreography.difficulty = data['difficulty']
            else:
                return JsonResponse({
                    'error': 'Invalid difficulty level'
                }, status=400)
        
        choreography.save()
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Choreography {choreography.id} updated by user {request.user.id}")
        
        return JsonResponse({
            'success': True,
            'choreography_id': str(choreography.id),
            'title': choreography.title,
            'difficulty': choreography.difficulty
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating choreography {pk}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to update choreography'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def collection_cleanup(request):
    """
    Clean up orphaned files in user's storage directory.
    
    FastAPI parity: POST /collection/cleanup
    Removes files that are no longer associated with any choreography
    in the user's collection. This helps free up storage space.
    """
    try:
        from pathlib import Path
        from django.conf import settings
        import os
        
        # Get user's choreographies
        choreographies = SavedChoreography.objects.filter(user=request.user)
        
        # Get all video paths from database
        db_video_paths = set()
        for choreo in choreographies:
            if choreo.video_path:
                # Extract just the filename
                video_filename = os.path.basename(choreo.video_path)
                db_video_paths.add(video_filename)
        
        # Get user's output directory
        user_output_dir = Path(settings.MEDIA_ROOT) / 'output' / f'user_{request.user.id}'
        
        orphaned_files = []
        files_removed = 0
        space_freed = 0
        
        if user_output_dir.exists():
            # Check all video files in user's directory
            for video_file in user_output_dir.glob('*.mp4'):
                if video_file.name not in db_video_paths:
                    # This file is orphaned
                    file_size = video_file.stat().st_size
                    orphaned_files.append({
                        'filename': video_file.name,
                        'size': file_size
                    })
                    
                    # Remove the file
                    try:
                        video_file.unlink()
                        files_removed += 1
                        space_freed += file_size
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Could not remove orphaned file {video_file}: {e}")
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Cleanup for user {request.user.id}: removed {files_removed} files, freed {space_freed} bytes")
        
        return JsonResponse({
            'success': True,
            'orphaned_files_found': len(orphaned_files),
            'files_removed': files_removed,
            'space_freed_bytes': space_freed,
            'space_freed_mb': round(space_freed / (1024 * 1024), 2)
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error during cleanup for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to cleanup orphaned files'
        }, status=500)
