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
from core.services.choreography_pipeline import ChoreoGenerationPipeline, PipelineConfig

logger = logging.getLogger(__name__)


def index(request):
    """Main choreography generation page - redirects to legacy template"""
    # Redirect to legacy template for backward compatibility
    from django.shortcuts import redirect
    return redirect('choreography:select-song')


def select_song(request):
    """
    Legacy template - Traditional song selection with dropdowns.
    UNCHANGED except Elasticsearch connection (uses serverless cloud).
    """
    form = ChoreographyGenerationForm()
    return render(request, 'choreography/index.html', {
        'form': form
    })


def describe_choreo(request):
    """
    NEW AI template - Natural language choreography creation with Gemini.
    
    Handles:
    - Natural language query input
    - Gemini API parsing
    - Parameter confirmation
    - AI-generated explanations
    """
    from core.services.gemini_service import GeminiService, ChoreographyParameters
    
    context = {}
    
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        confirmed = request.POST.get('confirmed', 'false') == 'true'
        parameters_json = request.POST.get('parameters', None)
        
        logger.info(f"[AI Template] User {request.user.id} submitted query: '{query[:100]}...' (confirmed={confirmed})")
        
        if not query:
            logger.warning(f"[AI Template] Empty query from user {request.user.id}")
            return JsonResponse({
                'error': 'Please describe your choreography'
            }, status=400)
        
        try:
            # Initialize Gemini service
            logger.info(f"[AI Template] Initializing Gemini service for user {request.user.id}")
            gemini_service = GeminiService()
            
            if not confirmed:
                # Step 1: Parse query and return parameters for confirmation
                logger.info(f"[AI Template] Parsing query for user {request.user.id}: '{query[:50]}...'")
                try:
                    parameters = gemini_service.parse_choreography_request(query)
                    logger.info(f"[AI Template] Successfully parsed query for user {request.user.id}: difficulty={parameters.difficulty}, style={parameters.style}")
                    
                    return JsonResponse({
                        'parameters': parameters.to_dict(),
                        'query': query
                    })
                    
                except Exception as parse_error:
                    logger.error(f"[AI Template] Failed to parse query for user {request.user.id}: {parse_error}", exc_info=True)
                    
                    # Try to get suggestions
                    try:
                        logger.info(f"[AI Template] Generating suggestions for user {request.user.id}")
                        available_metadata = {
                            'difficulties': ['beginner', 'intermediate', 'advanced'],
                            'styles': ['romantic', 'energetic', 'sensual', 'playful']
                        }
                        suggestions = gemini_service.suggest_alternatives(query, available_metadata)
                        logger.info(f"[AI Template] Generated {len(suggestions)} suggestions for user {request.user.id}")
                    except Exception as sugg_error:
                        logger.error(f"[AI Template] Failed to generate suggestions for user {request.user.id}: {sugg_error}")
                        suggestions = []
                    
                    return JsonResponse({
                        'error': f'Could not understand your query. Please try rephrasing.',
                        'suggestions': suggestions
                    }, status=400)
            
            else:
                # Step 2: Generate choreography with confirmed parameters
                logger.info(f"[AI Template] User {request.user.id} confirmed parameters, starting generation")
                if parameters_json:
                    try:
                        params_dict = json.loads(parameters_json)
                        parameters = ChoreographyParameters.from_dict(params_dict)
                        logger.info(f"[AI Template] Loaded parameters from JSON for user {request.user.id}")
                    except Exception as param_error:
                        logger.error(f"[AI Template] Invalid parameters JSON for user {request.user.id}: {param_error}")
                        return JsonResponse({
                            'error': 'Invalid parameters'
                        }, status=400)
                else:
                    # Re-parse if parameters not provided
                    logger.info(f"[AI Template] Re-parsing query for user {request.user.id}")
                    parameters = gemini_service.parse_choreography_request(query)
                
                # Integrate with choreography generation pipeline
                try:
                    # CRITICAL: Clean up stuck tasks before creating new one
                    from .utils import cleanup_stuck_tasks
                    cleanup_count = cleanup_stuck_tasks(max_age_minutes=5)
                    if cleanup_count > 0:
                        logger.info(f"[AI Template] Cleaned up {cleanup_count} stuck tasks for user {request.user.id}")
                    
                    # Create task for choreography generation
                    task_id = str(uuid.uuid4())
                    logger.info(f"[AI Template] Creating task {task_id} for user {request.user.id}")
                    create_task(task_id, request.user.id)
                    
                    # Start background generation with AI explanations
                    logger.info(f"[AI Template] Starting background thread for task {task_id}")
                    thread = threading.Thread(
                        target=generate_choreography_with_ai_explanations,
                        args=(task_id, request.user.id, parameters, query, gemini_service),
                        daemon=True
                    )
                    thread.start()
                    
                    logger.info(f"[AI Template] Task {task_id} started successfully for user {request.user.id}")
                    
                    # Return task ID for polling
                    return JsonResponse({
                        'task_id': task_id,
                        'status': 'started',
                        'parameters': parameters.to_dict()
                    })
                    
                except Exception as gen_error:
                    logger.error(f"[AI Template] Failed to start choreography generation for user {request.user.id}: {gen_error}", exc_info=True)
                    return JsonResponse({
                        'error': 'Failed to start choreography generation',
                        'details': str(gen_error)
                    }, status=500)
        
        except ValueError as e:
            # Handle missing API key or configuration errors
            logger.error(f"[AI Template] Gemini service configuration error for user {request.user.id}: {e}")
            return JsonResponse({
                'error': 'AI service is not configured. Please contact administrator.',
                'details': str(e)
            }, status=500)
        
        except Exception as e:
            logger.error(f"[AI Template] Unexpected error for user {request.user.id}: {e}", exc_info=True)
            return JsonResponse({
                'error': 'An unexpected error occurred. Please try again.',
                'details': str(e)
            }, status=500)
    
    # GET request - render template
    logger.info(f"[AI Template] Rendering describe_choreo page for user {request.user.id}")
    return render(request, 'choreography/describe_choreo.html', context)


@require_http_methods(["POST"])
def api_parse_query(request):
    """
    AJAX endpoint for parsing natural language queries.
    
    Allows real-time parameter preview before submission.
    """
    from core.services.gemini_service import GeminiService
    
    try:
        # Get query from request body
        data = json.loads(request.body) if request.body else {}
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({
                'error': 'Query is required'
            }, status=400)
        
        # Initialize Gemini service
        gemini_service = GeminiService()
        
        # Parse query
        parameters = gemini_service.parse_choreography_request(query)
        
        return JsonResponse({
            'success': True,
            'parameters': parameters.to_dict()
        })
        
    except ValueError as e:
        logger.error(f"Gemini service error: {e}")
        return JsonResponse({
            'error': 'AI service is not configured',
            'details': str(e)
        }, status=500)
        
    except Exception as e:
        logger.error(f"Failed to parse query: {e}")
        
        # Try to provide suggestions
        try:
            gemini_service = GeminiService()
            available_metadata = {
                'difficulties': ['beginner', 'intermediate', 'advanced'],
                'styles': ['romantic', 'energetic', 'sensual', 'playful']
            }
            suggestions = gemini_service.suggest_alternatives(query, available_metadata)
        except:
            suggestions = []
        
        return JsonResponse({
            'error': 'Could not parse query',
            'suggestions': suggestions
        }, status=400)


@require_http_methods(["POST"])
def create_choreography(request):
    """Start choreography generation task"""
    # Check authentication for AJAX requests
    if not request.user.is_authenticated:
        logger.warning("[Legacy Template] Unauthenticated request to create_choreography")
        return JsonResponse({
            'error': 'Please log in first',
            'message': 'Please log in first'
        }, status=401)
    
    logger.info(f"[Legacy Template] User {request.user.id} initiated choreography generation")
    
    try:
        form = ChoreographyGenerationForm(request.POST)
        
        if not form.is_valid():
            logger.warning(f"[Legacy Template] Invalid form submission from user {request.user.id}: {form.errors}")
            return JsonResponse({
                'error': 'Invalid form data',
                'errors': form.errors
            }, status=400)
        
        # CRITICAL: Clean up stuck tasks before checking concurrency
        from .utils import list_all_tasks, cleanup_stuck_tasks
        from datetime import timedelta
        
        # Clean up tasks stuck for more than 5 minutes
        cleanup_count = cleanup_stuck_tasks(max_age_minutes=5)
        if cleanup_count > 0:
            logger.info(f"[Legacy Template] Cleaned up {cleanup_count} stuck tasks for user {request.user.id}")
        
        # Check concurrency limit (max 3 concurrent generations)
        task_summary = list_all_tasks()
        active_count = task_summary['running_tasks']
        
        logger.info(f"[Legacy Template] Current active tasks: {active_count}/3")
        
        if active_count >= 3:
            logger.warning(f"[Legacy Template] Concurrency limit reached for user {request.user.id}: {active_count} active tasks")
            return JsonResponse({
                'error': 'Too many concurrent generations. Please try again in a few minutes.',
                'active_tasks': active_count,
                'limit': 3
            }, status=429)
        
        # Create unique task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task status
        logger.info(f"[Legacy Template] Creating task {task_id} for user {request.user.id}")
        create_task(task_id, request.user.id)
        
        # Get form data
        cleaned_data = form.cleaned_data
        song_selection = cleaned_data.get('song_selection')
        difficulty = cleaned_data.get('difficulty')
        
        logger.info(f"[Legacy Template] Task {task_id} parameters: song={song_selection}, difficulty={difficulty}")
        
        # Get auto_save preference (default True)
        auto_save = request.POST.get('auto_save', 'true').lower() in ('true', '1', 'yes', 'on')
        logger.info(f"[Legacy Template] Task {task_id} auto_save={auto_save}")
        
        # Convert song filename to local path using audio storage service
        from core.services.audio_storage_service import AudioStorageService
        try:
            logger.info(f"[Legacy Template] Task {task_id} loading song from storage: {song_selection}")
            audio_storage = AudioStorageService()
            audio_input = audio_storage.get_local_path(song_selection)
            logger.info(f"[Legacy Template] Task {task_id} resolved audio path: {audio_input}")
        except FileNotFoundError as e:
            logger.error(f"[Legacy Template] Song not found for task {task_id}: {song_selection} - {e}")
            return JsonResponse({
                'error': f'Song not found: {song_selection}. Please upload songs to cloud storage.',
                'details': str(e)
            }, status=404)
        
        # TEMPORARY FIX: Process synchronously instead of background thread
        # Background threads don't work reliably in Cloud Run's stateless environment
        logger.info(f"[Legacy Template] Starting SYNCHRONOUS choreography generation for task {task_id}")
        
        # Process immediately (this will block the request for 30-60 seconds)
        generate_choreography_background(task_id, request.user.id, audio_input, difficulty, auto_save)
        
        # Get the final task status
        final_task = get_task(task_id)
        
        if final_task and final_task.get('status') == 'completed':
            logger.info(f"[Legacy Template] Task {task_id} completed successfully")
            return JsonResponse({
                'task_id': task_id,
                'status': 'completed',
                'result': final_task.get('result')
            })
        else:
            logger.error(f"[Legacy Template] Task {task_id} failed: {final_task.get('error') if final_task else 'Task not found'}")
            return JsonResponse({
                'task_id': task_id,
                'status': final_task.get('status', 'failed') if final_task else 'failed',
                'error': final_task.get('error', 'Unknown error') if final_task else 'Task not found'
            }, status=500)
        
    except Exception as e:
        logger.error(f"[Legacy Template] Error creating choreography task for user {request.user.id}: {e}", exc_info=True)
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
    logger.info(f"🎬 Background thread started for task {task_id}, user {user_id}, audio: {audio_input}")
    
    # Wrap everything in try-except to catch ANY error
    try:
        # Import custom exceptions
        try:
            from core.exceptions import (
                YouTubeDownloadError,
                MusicAnalysisError,
                VideoGenerationError,
                MoveAnalysisError,
                ResourceError,
                ServiceUnavailableError
            )
        except ImportError as e:
            logger.error(f"Failed to import exceptions: {e}")
            # Define fallback exceptions
            class YouTubeDownloadError(Exception):
                def __init__(self, message): self.message = message
            class MusicAnalysisError(Exception):
                def __init__(self, message): self.message = message
            class VideoGenerationError(Exception):
                def __init__(self, message): self.message = message
            class MoveAnalysisError(Exception):
                def __init__(self, message): self.message = message
            class ResourceError(Exception):
                def __init__(self, message): self.message = message
            class ServiceUnavailableError(Exception):
                def __init__(self, message): self.message = message
        
        # Create user-specific output directory
        user_output_dir = Path(settings.MEDIA_ROOT) / 'output' / f'user_{user_id}'
        user_temp_dir = Path(settings.MEDIA_ROOT) / 'temp' / f'user_{user_id}'
        user_output_dir.mkdir(parents=True, exist_ok=True)
        user_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Stage 1: Downloading (10%)
        logger.info(f"[Generation] Task {task_id} - Stage 1: Downloading audio")
        update_task(
            task_id,
            status='running',
            progress=10,
            stage='downloading',
            message='Downloading audio...'
        )
        
        # Stage 2: Analyzing (25%)
        logger.info(f"[Generation] Task {task_id} - Stage 2: Analyzing music features")
        update_task(
            task_id,
            progress=25,
            stage='analyzing',
            message='Analyzing music features...'
        )
        
        # Initialize pipeline with user-specific directories
        logger.info(f"[Generation] Task {task_id} - Initializing pipeline (output: {user_output_dir})")
        config = PipelineConfig(
            output_directory=str(user_output_dir),
            temp_directory=str(user_temp_dir),
            quality_mode='balanced'
        )
        pipeline = ChoreoGenerationPipeline(config)
        
        # Stage 3: Selecting (40%)
        logger.info(f"[Generation] Task {task_id} - Stage 3: Selecting dance moves")
        update_task(
            task_id,
            progress=40,
            stage='selecting',
            message='Selecting dance moves...'
        )
        
        # Stage 4: Generating (70%)
        logger.info(f"[Generation] Task {task_id} - Stage 4: Generating choreography video")
        update_task(
            task_id,
            progress=70,
            stage='generating',
            message='Generating choreography video...'
        )
        
        # Run the pipeline (async function, need to run in event loop)
        logger.info(f"[Generation] Task {task_id} - Running pipeline with audio: {audio_input}, difficulty: {difficulty}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                pipeline.generate_choreography(
                    audio_input=audio_input,
                    difficulty=difficulty
                )
            )
            logger.info(f"[Generation] Task {task_id} - Pipeline completed: success={result.success}")
        finally:
            loop.close()
        
        # Stage 5: Finalizing (90%)
        logger.info(f"[Generation] Task {task_id} - Stage 5: Finalizing video")
        update_task(
            task_id,
            progress=90,
            stage='finalizing',
            message='Finalizing video...'
        )
        
        # Check if generation was successful
        if result.success and result.output_path:
            logger.info(f"[Generation] Task {task_id} - Video generated successfully: {result.output_path}")
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
    
    except BaseException as e:
        # Catch EVERYTHING including SystemExit, KeyboardInterrupt, etc.
        error_msg = f"Critical error in background thread: {str(e)}"
        logger.critical(f"Task {task_id} - CRITICAL ERROR: {error_msg}", exc_info=True)
        try:
            update_task(
                task_id,
                status='failed',
                progress=0,
                stage='failed',
                message='Critical system error',
                error=error_msg
            )
        except:
            pass  # If we can't even update the task, just log it
        raise  # Re-raise to see it in logs


def generate_choreography_with_ai_explanations(
    task_id: str,
    user_id: int,
    parameters,  # ChoreographyParameters from Gemini
    original_query: str,
    gemini_service
):
    """
    Background function to generate choreography with AI explanations.
    
    This function:
    1. Converts AI-parsed parameters to pipeline format
    2. Generates choreography using the pipeline
    3. Generates AI explanations for each selected move
    4. Returns results with explanations
    """
    logger.info(f"[AI Generation] Task {task_id} - Starting AI choreography generation for user {user_id}")
    logger.info(f"[AI Generation] Task {task_id} - Original query: '{original_query[:100]}...'")
    
    try:
        from core.services.choreography_pipeline import ChoreoGenerationPipeline, PipelineConfig
        
        # Create user-specific output directory
        user_output_dir = Path(settings.MEDIA_ROOT) / 'output' / f'user_{user_id}'
        user_temp_dir = Path(settings.MEDIA_ROOT) / 'temp' / f'user_{user_id}'
        user_output_dir.mkdir(parents=True, exist_ok=True)
        user_temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[AI Generation] Task {task_id} - Created directories: output={user_output_dir}, temp={user_temp_dir}")
        
        # Stage 1: Initializing (10%)
        update_task(
            task_id,
            status='running',
            progress=10,
            stage='initializing',
            message='Initializing AI choreography generation...'
        )
        
        # Convert parameters to pipeline format
        difficulty = parameters.difficulty or 'intermediate'
        energy_level = parameters.energy_level or 'medium'
        
        # Log AI parameters
        logger.info(f"[AI Generation] Task {task_id} - Parameters: difficulty={difficulty}, energy={energy_level}, style={parameters.style}, tempo={parameters.tempo}")
        
        # Use a default song from available songs
        # TODO: Add song selection to AI template
        from core.services.audio_storage_service import AudioStorageService
        
        logger.info(f"[AI Generation] Task {task_id} - Loading audio file")
        audio_storage = AudioStorageService()
        try:
            # Try to get Aventura.mp3, or use first available song
            if audio_storage.exists("Aventura.mp3"):
                audio_input = audio_storage.get_local_path("Aventura.mp3")
                logger.info(f"[AI Generation] Task {task_id} - Using default song: Aventura.mp3")
            else:
                # Use first available song
                available_songs = audio_storage.list_songs()
                if not available_songs:
                    raise FileNotFoundError("No songs available in storage")
                audio_input = audio_storage.get_local_path(available_songs[0])
                logger.info(f"[AI Generation] Task {task_id} - Using fallback song: {available_songs[0]}")
        except Exception as e:
            logger.error(f"[AI Generation] Task {task_id} - Audio file not found: {e}")
            update_task(
                task_id,
                status='failed',
                progress=0,
                stage='failed',
                message='Audio file not found. Please upload songs to cloud storage.',
                error=str(e)
            )
            return
        
        # Stage 2: Generating choreography (30%)
        logger.info(f"[AI Generation] Task {task_id} - Stage 2: Generating choreography")
        update_task(
            task_id,
            progress=30,
            stage='generating',
            message='Generating choreography based on your preferences...'
        )
        
        # Initialize pipeline with user-specific directories
        config = PipelineConfig(
            output_directory=str(user_output_dir),
            temp_directory=str(user_temp_dir),
            quality_mode='balanced'
        )
        pipeline = ChoreoGenerationPipeline(config)
        
        # Run the pipeline
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                pipeline.generate_choreography(
                    audio_input=audio_input,
                    difficulty=difficulty,
                    energy_level=energy_level
                )
            )
        finally:
            loop.close()
        
        if not result.success or not result.output_path:
            update_task(
                task_id,
                status='failed',
                progress=0,
                stage='failed',
                message='Choreography generation failed',
                error=result.error_message or 'Unknown error'
            )
            return
        
        # Stage 3: Generating AI explanations (70%)
        update_task(
            task_id,
            progress=70,
            stage='explaining',
            message='Generating AI explanations for your choreography...'
        )
        
        # Load metadata to get move information
        metadata_path = result.metadata_path
        explanations = []
        
        if metadata_path and Path(metadata_path).exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                moves_used = metadata.get('moves_used', [])
                
                # Generate explanations for each move (limit to first 10 for performance)
                for i, move in enumerate(moves_used[:10]):
                    try:
                        # Create context for explanation
                        context = {
                            'difficulty': difficulty,
                            'energy_level': energy_level,
                            'style': parameters.style or 'romantic',
                            'tempo': parameters.tempo or 'medium',
                            'move_position': i + 1,
                            'total_moves': len(moves_used),
                            'original_query': original_query
                        }
                        
                        # Generate explanation
                        explanation = gemini_service.explain_move_selection(move, context)
                        explanations.append(explanation)
                        
                        # Update progress
                        progress = 70 + int((i + 1) / min(len(moves_used), 10) * 20)
                        update_task(
                            task_id,
                            progress=progress,
                            message=f'Generating explanations... ({i + 1}/{min(len(moves_used), 10)})'
                        )
                        
                    except Exception as e:
                        logger.warning(f"Failed to generate explanation for move {i}: {e}")
                        # Use fallback explanation
                        explanations.append(
                            f"This move was selected to match your {difficulty} difficulty "
                            f"and {energy_level} energy preferences."
                        )
                
            except Exception as e:
                logger.error(f"Failed to load metadata for explanations: {e}")
                # Use generic explanations
                explanations = [
                    f"This choreography was generated based on your preferences: "
                    f"{difficulty} difficulty, {energy_level} energy, {parameters.style or 'romantic'} style."
                ]
        else:
            # No metadata available, use generic explanation
            explanations = [
                f"This choreography was generated based on your preferences: "
                f"{difficulty} difficulty, {energy_level} energy, {parameters.style or 'romantic'} style."
            ]
        
        # Stage 4: Finalizing (95%)
        update_task(
            task_id,
            progress=95,
            stage='finalizing',
            message='Finalizing your AI-generated choreography...'
        )
        
        # Extract filename from path
        video_filename = Path(result.output_path).name
        
        # Auto-save to collection
        saved_choreography_id = None
        auto_saved = False
        
        try:
            from django.contrib.auth import get_user_model
            from choreography.models import SavedChoreography
            
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            # Auto-save the choreography
            choreography = SavedChoreography.objects.create(
                user=user,
                title=f'AI Choreography: {original_query[:50]}',
                video_path=result.output_path,
                difficulty=difficulty,
                duration=result.sequence_duration or 0,
                music_info={
                    'source': audio_input,
                    'difficulty': difficulty,
                    'energy_level': energy_level,
                    'style': parameters.style,
                    'tempo': parameters.tempo
                },
                generation_parameters={
                    'difficulty': difficulty,
                    'energy_level': energy_level,
                    'style': parameters.style,
                    'tempo': parameters.tempo,
                    'original_query': original_query,
                    'task_id': task_id
                }
            )
            saved_choreography_id = str(choreography.id)
            auto_saved = True
            logger.info(f"[AI Generation] Auto-saved choreography {saved_choreography_id} for user {user_id}")
        except Exception as save_error:
            logger.error(f"[AI Generation] Auto-save failed for task {task_id}: {save_error}", exc_info=True)
            # Don't fail the entire task if auto-save fails
        
        # Complete
        update_task(
            task_id,
            status='completed',
            progress=100,
            stage='completed',
            message='AI choreography generated successfully!' + (' (Auto-saved to collection)' if auto_saved else ''),
            result={
                'video_path': result.output_path,
                'video_filename': video_filename,
                'processing_time': result.processing_time,
                'sequence_duration': result.sequence_duration,
                'moves_analyzed': result.moves_analyzed,
                'metadata_path': result.metadata_path,
                'explanations': explanations,
                'parameters': parameters.to_dict(),
                'original_query': original_query,
                'saved_choreography_id': saved_choreography_id,
                'auto_saved': auto_saved
            }
        )
        
        logger.info(f"[AI Generation] Task {task_id} completed successfully with {len(explanations)} explanations (auto_saved={auto_saved})")
        
    except Exception as e:
        logger.error(f"AI choreography generation failed for task {task_id}: {e}", exc_info=True)
        update_task(
            task_id,
            status='failed',
            progress=0,
            stage='failed',
            message='AI choreography generation failed',
            error=str(e)
        )


# Removed duplicate task_status function - using the one below


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



@require_http_methods(["GET"])
def task_status(request, task_id):
    """
    Get the status of a choreography generation task.
    
    Returns JSON with task progress, status, and results.
    """
    try:
        task_data = get_task(task_id)
        
        if not task_data:
            logger.warning(f"[Task Status] Task {task_id} not found")
            return JsonResponse({
                'error': 'Task not found',
                'task_id': task_id
            }, status=404)
        
        # Check if user owns this task (if authenticated)
        if request.user.is_authenticated:
            if task_data.get('user_id') != request.user.id:
                logger.warning(f"[Task Status] Unauthorized access attempt to task {task_id} by user {request.user.id}")
                return JsonResponse({
                    'error': 'Unauthorized',
                    'message': 'You do not have permission to view this task'
                }, status=403)
        
        # Log status check (only log every 10th check to avoid spam)
        import random
        if random.random() < 0.1:  # 10% sampling
            logger.debug(f"[Task Status] Task {task_id} status: {task_data.get('status')}, progress: {task_data.get('progress')}%")
        
        # Return task data
        return JsonResponse({
            'task_id': task_id,
            'status': task_data.get('status', 'unknown'),
            'progress': task_data.get('progress', 0),
            'stage': task_data.get('stage', ''),
            'message': task_data.get('message', ''),
            'result': task_data.get('result'),
            'error': task_data.get('error'),
            'created_at': task_data.get('created_at')
        })
        
    except Exception as e:
        logger.error(f"[Task Status] Error getting task status for {task_id}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)
