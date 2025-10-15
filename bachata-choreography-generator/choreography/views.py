from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, FileResponse, Http404
from django.conf import settings
from pathlib import Path
import uuid
import threading
import logging
import asyncio
import os
import json

from .forms import ChoreographyGenerationForm
from .utils import create_task, get_task, update_task, cleanup_old_tasks, list_all_tasks, delete_task
from app.services.choreography_pipeline import ChoreoGenerationPipeline, PipelineConfig

logger = logging.getLogger(__name__)


def index(request):
    """Main choreography generation page"""
    form = ChoreographyGenerationForm()
    return render(request, 'choreography/index.html', {
        'form': form
    })


@login_required
@require_http_methods(["POST"])
def create_choreography(request):
    """Start choreography generation task"""
    try:
        form = ChoreographyGenerationForm(request.POST)
        
        if not form.is_valid():
            logger.warning(f"Invalid form submission from user {request.user.id}: {form.errors}")
            return JsonResponse({
                'error': 'Invalid form data',
                'errors': form.errors
            }, status=400)
        
        # Check concurrency limit (max 3 concurrent generations)
        from .utils import list_all_tasks
        task_summary = list_all_tasks()
        active_count = task_summary['running_tasks']
        
        if active_count >= 3:
            logger.warning(f"Concurrency limit reached: {active_count} active tasks")
            return JsonResponse({
                'error': 'Too many concurrent generations. Please try again in a few minutes.',
                'active_tasks': active_count,
                'limit': 3
            }, status=429)
        
        # Create unique task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task status
        create_task(task_id, request.user.id)
        
        # Get form data
        cleaned_data = form.cleaned_data
        song_selection = cleaned_data.get('song_selection')
        youtube_url = cleaned_data.get('youtube_url')
        difficulty = cleaned_data.get('difficulty')
        
        # Get auto_save preference (default True)
        auto_save = request.POST.get('auto_save', 'true').lower() in ('true', '1', 'yes', 'on')
        
        # Determine audio input
        audio_input = youtube_url if song_selection == 'new_song' else song_selection
        
        # Start background thread with auto_save parameter
        thread = threading.Thread(
            target=generate_choreography_background,
            args=(task_id, request.user.id, audio_input, difficulty, auto_save),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Started choreography generation task {task_id} for user {request.user.id}")
        
        return JsonResponse({
            'task_id': task_id,
            'status': 'started'
        })
        
    except Exception as e:
        logger.error(f"Error creating choreography task for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An unexpected error occurred while starting generation',
            'details': str(e)
        }, status=500)


def generate_choreography_background(task_id: str, user_id: int, audio_input: str, difficulty: str, auto_save: bool = True):
    """
    Background function to generate choreography.
    Updates task progress at various stages.
    Supports auto-save functionality based on user preferences.
    Handles specific exceptions: YouTubeDownloadError, MusicAnalysisError, VideoGenerationError.
    """
    try:
        # Import custom exceptions
        from app.exceptions import (
            YouTubeDownloadError,
            MusicAnalysisError,
            VideoGenerationError,
            MoveAnalysisError,
            ResourceError,
            ServiceUnavailableError
        )
        
        # Create user-specific output directory
        user_output_dir = Path(settings.MEDIA_ROOT) / 'output' / f'user_{user_id}'
        user_temp_dir = Path(settings.MEDIA_ROOT) / 'temp' / f'user_{user_id}'
        user_output_dir.mkdir(parents=True, exist_ok=True)
        user_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Stage 1: Downloading (10%)
        update_task(
            task_id,
            status='running',
            progress=10,
            stage='downloading',
            message='Downloading audio...'
        )
        
        # Stage 2: Analyzing (25%)
        update_task(
            task_id,
            progress=25,
            stage='analyzing',
            message='Analyzing music features...'
        )
        
        # Initialize pipeline with user-specific directories
        config = PipelineConfig(
            output_directory=str(user_output_dir),
            temp_directory=str(user_temp_dir),
            quality_mode='balanced'
        )
        pipeline = ChoreoGenerationPipeline(config)
        
        # Stage 3: Selecting (40%)
        update_task(
            task_id,
            progress=40,
            stage='selecting',
            message='Selecting dance moves...'
        )
        
        # Stage 4: Generating (70%)
        update_task(
            task_id,
            progress=70,
            stage='generating',
            message='Generating choreography video...'
        )
        
        # Run the pipeline (async function, need to run in event loop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                pipeline.generate_choreography(
                    audio_input=audio_input,
                    difficulty=difficulty
                )
            )
        finally:
            loop.close()
        
        # Stage 5: Finalizing (90%)
        update_task(
            task_id,
            progress=90,
            stage='finalizing',
            message='Finalizing video...'
        )
        
        # Check if generation was successful
        if result.success and result.output_path:
            # Extract filename from path
            video_filename = Path(result.output_path).name
            
            # Auto-save functionality
            saved_choreography_id = None
            auto_saved = False
            
            # Check if auto-save is enabled and user preferences allow it
            if auto_save:
                try:
                    from django.contrib.auth import get_user_model
                    from choreography.models import SavedChoreography
                    
                    User = get_user_model()
                    user = User.objects.get(id=user_id)
                    
                    # Check user preferences (default to True)
                    user_preferences = user.preferences or {}
                    should_auto_save = user_preferences.get('auto_save_choreographies', True)
                    
                    if should_auto_save:
                        # Auto-save the choreography
                        choreography = SavedChoreography.objects.create(
                            user=user,
                            title=f'Auto-saved Choreography',
                            video_path=result.output_path,
                            difficulty=difficulty,
                            duration=result.sequence_duration or 0,
                            music_info={
                                'source': audio_input,
                                'difficulty': difficulty
                            },
                            generation_parameters={
                                'difficulty': difficulty,
                                'audio_input': audio_input,
                                'task_id': task_id
                            }
                        )
                        saved_choreography_id = str(choreography.id)
                        auto_saved = True
                        logger.info(f"Auto-saved choreography {saved_choreography_id} for user {user_id}")
                except Exception as save_error:
                    logger.warning(f"Auto-save failed for task {task_id}: {save_error}", exc_info=True)
                    # Don't fail the entire task if auto-save fails
            
            # Update task with completed status
            update_task(
                task_id,
                status='completed',
                progress=100,
                stage='completed',
                message='Choreography generated successfully!' + (' (Auto-saved to collection)' if auto_saved else ''),
                result={
                    'video_path': result.output_path,
                    'video_filename': video_filename,
                    'processing_time': result.processing_time,
                    'sequence_duration': result.sequence_duration,
                    'moves_analyzed': result.moves_analyzed,
                    'metadata_path': result.metadata_path,
                    'saved_choreography_id': saved_choreography_id,
                    'auto_saved': auto_saved
                }
            )
            logger.info(f"Task {task_id} completed successfully")
        else:
            # Generation failed
            error_msg = result.error_message or 'Unknown error during generation'
            update_task(
                task_id,
                status='failed',
                progress=0,
                stage='failed',
                message='Generation failed',
                error=error_msg
            )
            logger.error(f"Task {task_id} failed: {error_msg}")
    
    except YouTubeDownloadError as e:
        # Handle YouTube download errors
        error_msg = f"YouTube download failed: {e.message}"
        logger.error(f"Task {task_id} - YouTubeDownloadError: {error_msg}", exc_info=True)
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='Failed to download from YouTube',
            error=error_msg
        )
    
    except MusicAnalysisError as e:
        # Handle music analysis errors
        error_msg = f"Music analysis failed: {e.message}"
        logger.error(f"Task {task_id} - MusicAnalysisError: {error_msg}", exc_info=True)
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='Failed to analyze music',
            error=error_msg
        )
    
    except VideoGenerationError as e:
        # Handle video generation errors
        error_msg = f"Video generation failed: {e.message}"
        logger.error(f"Task {task_id} - VideoGenerationError: {error_msg}", exc_info=True)
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='Failed to generate video',
            error=error_msg
        )
    
    except MoveAnalysisError as e:
        # Handle move analysis errors
        error_msg = f"Move analysis failed: {e.message}"
        logger.error(f"Task {task_id} - MoveAnalysisError: {error_msg}", exc_info=True)
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='Failed to analyze dance moves',
            error=error_msg
        )
    
    except ResourceError as e:
        # Handle resource errors (memory, disk space, etc.)
        error_msg = f"Resource error: {e.message}"
        logger.error(f"Task {task_id} - ResourceError: {error_msg}", exc_info=True)
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='Insufficient system resources',
            error=error_msg
        )
    
    except ServiceUnavailableError as e:
        # Handle service unavailable errors
        error_msg = f"Service unavailable: {e.message}"
        logger.error(f"Task {task_id} - ServiceUnavailableError: {error_msg}", exc_info=True)
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='Required service is unavailable',
            error=error_msg
        )
    
    except OSError as e:
        # Handle file system errors
        error_msg = f"File system error: {str(e)}"
        logger.error(f"Task {task_id} - OSError: {error_msg}", exc_info=True)
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='File system error occurred',
            error=error_msg
        )
    
    except MemoryError as e:
        # Handle memory errors
        error_msg = "Insufficient memory to complete generation"
        logger.error(f"Task {task_id} - MemoryError: {error_msg}", exc_info=True)
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='Insufficient memory',
            error=error_msg
        )
            
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Task {task_id} failed with unexpected exception: {error_msg}", exc_info=True)
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='An unexpected error occurred',
            error=error_msg
        )


@login_required
def task_status(request, task_id):
    """Get task status for polling"""
    try:
        # Validate task_id format
        try:
            uuid.UUID(task_id)
        except ValueError:
            logger.warning(f"Invalid task_id format: {task_id}")
            return JsonResponse({
                'error': 'Invalid task ID format'
            }, status=400)
        
        task_data = get_task(task_id)
        
        if not task_data:
            logger.debug(f"Task not found: {task_id}")
            return JsonResponse({
                'error': 'Task not found'
            }, status=404)
        
        # Verify user owns this task
        if task_data.get('user_id') != request.user.id:
            logger.warning(f"Unauthorized access attempt to task {task_id} by user {request.user.id}")
            return JsonResponse({
                'error': 'Unauthorized'
            }, status=403)
        
        return JsonResponse(task_data)
        
    except Exception as e:
        logger.error(f"Error retrieving task status for {task_id}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An unexpected error occurred while retrieving task status'
        }, status=500)


@login_required
def serve_video(request, filename):
    """
    Serve generated video with authentication check and fallback logic.
    
    FastAPI parity: Searches user directory first, then falls back to searching
    all user directories to handle HTML video element requests without auth headers.
    """
    try:
        # Sanitize filename to prevent directory traversal
        filename = os.path.basename(filename)
        
        # Additional security check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.warning(f"Path traversal attempt detected: {filename}")
            return JsonResponse({'error': 'Invalid filename'}, status=400)
        
        # Verify it's a video file
        if not filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            logger.warning(f"Invalid file type requested: {filename}")
            return JsonResponse({'error': 'Invalid file type'}, status=400)
        
        video_path = None
        
        # Check user-specific directory first
        user_video_path = Path(settings.MEDIA_ROOT) / 'output' / f'user_{request.user.id}' / filename
        if user_video_path.exists() and user_video_path.is_file():
            video_path = user_video_path
        
        # Fallback: search all user directories (for HTML video element compatibility)
        if not video_path:
            output_dir = Path(settings.MEDIA_ROOT) / 'output'
            logger.debug(f"Searching for {filename} in user directories under {output_dir}")
            
            if output_dir.exists():
                for user_dir in output_dir.glob("user_*"):
                    if user_dir.is_dir():
                        potential_path = user_dir / filename
                        logger.debug(f"Checking: {potential_path}")
                        if potential_path.exists() and potential_path.is_file():
                            video_path = potential_path
                            logger.debug(f"Found video at: {video_path}")
                            break
        
        # Final fallback: general output directory (backward compatibility)
        if not video_path:
            general_video_path = Path(settings.MEDIA_ROOT) / 'output' / filename
            if general_video_path.exists() and general_video_path.is_file():
                video_path = general_video_path
        
        if not video_path:
            logger.warning(f"Video not found: {filename} for user {request.user.id}")
            raise Http404('Video not found')
        
        # Return video file
        return FileResponse(
            open(video_path, 'rb'),
            content_type='video/mp4',
            filename=filename
        )
        
    except Http404:
        raise
    except Exception as e:
        logger.error(f"Error serving video {filename}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An unexpected error occurred while serving video'
        }, status=500)



@login_required
def list_tasks(request):
    """
    List all active tasks with summary statistics.
    
    FastAPI parity: GET /api/tasks
    Auto-cleans old completed/failed tasks (>1 hour).
    """
    try:
        # Clean up old tasks
        cleanup_old_tasks(max_age_hours=1)
        
        # Get task summary
        task_summary = list_all_tasks()
        
        return JsonResponse(task_summary)
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Error retrieving tasks'
        }, status=500)


@login_required
@require_http_methods(["DELETE", "POST"])
def cancel_task(request, task_id):
    """
    Cancel/delete a task from tracking.
    
    FastAPI parity: DELETE /api/task/{task_id}
    Note: Cannot stop running generation, only removes from tracking.
    """
    try:
        task_data = get_task(task_id)
        
        if not task_data:
            return JsonResponse({
                'error': 'Task not found'
            }, status=404)
        
        # Verify user owns this task
        if task_data.get('user_id') != request.user.id:
            return JsonResponse({
                'error': 'Unauthorized'
            }, status=403)
        
        previous_status = task_data['status']
        
        # Delete the task
        delete_task(task_id)
        
        logger.info(f"Task {task_id} removed from tracking (was {previous_status})")
        
        return JsonResponse({
            'message': 'Task removed from tracking',
            'task_id': task_id,
            'previous_status': previous_status
        })
        
    except Exception as e:
        logger.error(f"Error canceling task: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Error cancelling task'
        }, status=500)



@login_required
@require_http_methods(["POST"])
def validate_youtube_url(request):
    """
    Validate a YouTube URL without starting generation.
    
    FastAPI parity: POST /api/validate/youtube
    Returns video info, duration, availability status.
    """
    try:
        data = json.loads(request.body)
        url = data.get('url', '').strip()
        
        if not url:
            return JsonResponse({
                'valid': False,
                'message': 'URL is required',
                'error_type': 'missing_url'
            }, status=400)
        
        # Basic YouTube URL validation
        import re
        youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        if not re.match(youtube_regex, url):
            return JsonResponse({
                'valid': False,
                'message': 'Invalid YouTube URL format',
                'error_type': 'invalid_format',
                'details': {}
            })
        
        # Try to extract video ID
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        if not video_id_match:
            return JsonResponse({
                'valid': False,
                'message': 'Could not extract video ID from URL',
                'error_type': 'invalid_video_id',
                'details': {}
            })
        
        video_id = video_id_match.group(1)
        
        # Try to get video info using yt-dlp
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return JsonResponse({
                    'valid': True,
                    'message': 'Valid YouTube URL',
                    'details': {
                        'video_id': video_id,
                        'title': info.get('title', 'Unknown'),
                        'duration': info.get('duration', 0),
                        'uploader': info.get('uploader', 'Unknown'),
                        'view_count': info.get('view_count', 0)
                    }
                })
                
        except Exception as yt_error:
            return JsonResponse({
                'valid': False,
                'message': f'Could not access video: {str(yt_error)}',
                'error_type': 'access_error',
                'details': {
                    'video_id': video_id
                }
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'valid': False,
            'message': 'Invalid JSON',
            'error_type': 'invalid_json'
        }, status=400)
    except Exception as e:
        logger.error(f"YouTube validation error: {e}", exc_info=True)
        return JsonResponse({
            'valid': False,
            'message': 'Error validating YouTube URL',
            'error_type': 'server_error'
        }, status=500)


def task_progress(request):
    """
    Get progress for the most recent active task (for HTMX polling).
    
    FastAPI parity: GET /task/progress
    Returns HTML/JavaScript for Alpine.js integration.
    """
    from django.http import HttpResponse
    
    try:
        # Find the most recent active task for the current user
        all_tasks = list_all_tasks()
        
        # Filter for current user's active tasks if authenticated
        if request.user.is_authenticated:
            from .utils import get_all_tasks
            user_tasks = [
                (task_id, task_data) for task_id, task_data in get_all_tasks().items()
                if task_data.get('user_id') == request.user.id and task_data['status'] in ['started', 'running']
            ]
        else:
            user_tasks = []
        
        if not user_tasks:
            # No active tasks - stop polling
            return HttpResponse("""
            <script>
                const container = document.querySelector('[x-data*="choreographyGenerator"]');
                if (container && container._x_dataStack) {
                    const data = container._x_dataStack[0];
                    data.isGenerating = false;
                }
            </script>
            """)
        
        # Get the most recent task
        task_id, task_data = max(user_tasks, key=lambda x: x[1].get('created_at', 0))
        
        # Escape quotes in messages
        message = task_data['message'].replace("'", "\\'").replace('"', '\\"')
        
        # Update progress in the parent component
        progress_script = f"""
        <script>
            const container = document.querySelector('[x-data*="choreographyGenerator"]');
            if (container && container._x_dataStack) {{
                const data = container._x_dataStack[0];
                data.progress = {task_data['progress']};
                data.progressMessage = '{message}';
                data.currentTaskId = '{task_id}';
                
                // Check if completed
                if ('{task_data['status']}' === 'completed') {{
                    data.showResult({json.dumps(task_data.get('result', {}))});
                }} else if ('{task_data['status']}' === 'failed') {{
                    const errorMsg = '{task_data.get('error', 'Generation failed').replace("'", "\\'")}';
                    data.showError(errorMsg);
                }}
            }}
        </script>
        """
        
        return HttpResponse(progress_script)
        
    except Exception as e:
        logger.error(f"Error getting task progress: {e}", exc_info=True)
        return HttpResponse("""
        <script>
            const container = document.querySelector('[x-data*="choreographyGenerator"]');
            if (container && container._x_dataStack) {
                const data = container._x_dataStack[0];
                data.showError('Error checking progress');
            }
        </script>
        """)
