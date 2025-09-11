"""
Choreography controller for dance sequence generation and task management.
"""
import asyncio
import json
import uuid
from typing import Dict, Optional
from pathlib import Path

from fastapi import HTTPException, BackgroundTasks, Form, Depends
from pydantic import BaseModel

from .base_controller import BaseController
from app.services.choreography_pipeline import ChoreoGenerationPipeline, PipelineConfig
from app.exceptions import (
    ChoreographyGenerationError, YouTubeDownloadError, MusicAnalysisError,
    VideoGenerationError, ValidationError, ResourceError, ServiceUnavailableError
)
from app.validation import ChoreographyRequestValidator, validate_system_requirements, validate_youtube_url_async
from app.services.resource_manager import resource_manager
from app.middleware.auth_middleware import AuthenticatedUser, CurrentUser
from app.models.database_models import User

class ChoreographyResponse(BaseModel):
    """Response model for choreography generation."""
    task_id: str
    status: str
    message: str

class TaskStatus(BaseModel):
    """Model for task status response."""
    task_id: str
    status: str
    progress: int
    stage: str
    message: str
    result: Optional[Dict] = None
    error: Optional[str] = None

class YouTubeValidationRequest(BaseModel):
    """Request model for YouTube URL validation."""
    url: str

class ChoreographyController(BaseController):
    """Controller for choreography generation endpoints."""
    
    def __init__(self):
        super().__init__(prefix="/api", tags=["choreography"])
        self.pipeline = None
        self.active_tasks: Dict[str, Dict] = {}
        self._setup_routes()
    
    def get_pipeline(self) -> ChoreoGenerationPipeline:
        """Get or create the global pipeline instance."""
        if self.pipeline is None:
            config = PipelineConfig(
                quality_mode="balanced",
                enable_caching=True,
                max_workers=4,
                cleanup_after_generation=True
            )
            self.pipeline = ChoreoGenerationPipeline(config)
            self.logger.info("Choreography pipeline initialized")
        return self.pipeline
    
    def _setup_routes(self):
        """Set up choreography-related routes."""
        
        @self.router.post("/choreography", response_model=ChoreographyResponse)
        async def create_choreography(
            background_tasks: BackgroundTasks,
            current_user: AuthenticatedUser,
            youtube_url: str = Form(...),
            difficulty: str = Form(default="intermediate"),
            quality_mode: str = Form(default="balanced"),
            energy_level: str = Form(default="medium"),
            auto_save: bool = Form(default=True)
        ):
            """
            Create a new choreography from a YouTube URL.
            
            This endpoint starts the choreography generation process in the background
            and returns a task ID for tracking progress.
            """
            try:
                self.log_request("create_choreography", {
                    "url": youtube_url,
                    "difficulty": difficulty,
                    "quality_mode": quality_mode
                })
                
                # Pre-flight system checks
                system_check = validate_system_requirements()
                if not system_check["valid"]:
                    raise ResourceError(
                        message="System requirements not met for choreography generation",
                        resource_type="system",
                        details=system_check
                    )
                
                # Enhanced YouTube URL validation
                url_validation = await validate_youtube_url_async(youtube_url)
                if not url_validation["valid"]:
                    raise YouTubeDownloadError(
                        message=url_validation.get("message", "Invalid YouTube URL"),
                        url=youtube_url,
                        details=url_validation
                    )
                
                # Check for too many concurrent tasks
                active_count = len([t for t in self.active_tasks.values() if t["status"] in ["started", "running"]])
                if active_count >= 3:  # Limit concurrent generations
                    raise ResourceError(
                        message="Too many concurrent generations. Please try again in a few minutes.",
                        resource_type="concurrency",
                        details={"active_tasks": active_count, "limit": 3}
                    )
                
                # Generate unique task ID
                task_id = str(uuid.uuid4())
                
                # Initialize task status with enhanced info including user context
                self.active_tasks[task_id] = {
                    "status": "started",
                    "progress": 0,
                    "stage": "initializing",
                    "message": "Starting choreography generation...",
                    "result": None,
                    "error": None,
                    "created_at": asyncio.get_event_loop().time(),
                    "user_id": current_user.id,
                    "user_email": current_user.email,
                    "request_params": {
                        "difficulty": difficulty,
                        "quality_mode": quality_mode,
                        "energy_level": energy_level,
                        "auto_save": auto_save
                    },
                    "video_info": url_validation.get("details", {})
                }
                
                # Start background task with enhanced error handling
                background_tasks.add_task(
                    self._generate_choreography_task_safe,
                    task_id,
                    current_user.id,
                    youtube_url,
                    difficulty,
                    energy_level,
                    quality_mode,
                    auto_save
                )
                
                self.logger.info(f"Started choreography generation task {task_id} for URL: {youtube_url}")
                self.logger.info(f"Video info: {url_validation.get('details', {})}")
                
                return ChoreographyResponse(
                    task_id=task_id,
                    status="started",
                    message="Choreography generation started. Use the task ID to track progress."
                )
                
            except (YouTubeDownloadError, ResourceError, ValidationError) as e:
                # These are expected errors that should be returned to the user
                self.logger.warning(f"Choreography generation rejected: {e.message}")
                raise
            except Exception as e:
                self.log_error("create_choreography", e)
                raise ServiceUnavailableError(
                    message="Unable to start choreography generation due to an internal error",
                    service_name="choreography_api",
                    details={"error": str(e)}
                )
        
        @self.router.get("/task/{task_id}", response_model=TaskStatus)
        async def get_task_status(task_id: str):
            """Get the status of a choreography generation task."""
            if task_id not in self.active_tasks:
                raise HTTPException(status_code=404, detail="Task not found")
            
            task_data = self.active_tasks[task_id]
            
            return TaskStatus(
                task_id=task_id,
                status=task_data["status"],
                progress=task_data["progress"],
                stage=task_data["stage"],
                message=task_data["message"],
                result=task_data["result"],
                error=task_data["error"]
            )
        
        @self.router.delete("/task/{task_id}")
        async def cancel_task(task_id: str):
            """Cancel a running task (cleanup only, cannot stop running generation)."""
            try:
                if not task_id or not isinstance(task_id, str):
                    raise HTTPException(status_code=400, detail="Invalid task ID")
                
                if task_id not in self.active_tasks:
                    raise HTTPException(status_code=404, detail="Task not found")
                
                task_status = self.active_tasks[task_id]["status"]
                
                # Remove from active tasks
                del self.active_tasks[task_id]
                
                self.logger.info(f"Task {task_id} removed from tracking (was {task_status})")
                
                return {
                    "message": "Task removed from tracking",
                    "task_id": task_id,
                    "previous_status": task_status
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("cancel_task", e)
                raise HTTPException(status_code=500, detail="Error cancelling task")
        
        @self.router.get("/tasks")
        async def list_tasks():
            """List all active tasks with filtering options."""
            try:
                # Clean up old completed/failed tasks (older than 1 hour)
                current_time = asyncio.get_event_loop().time()
                tasks_to_remove = []
                
                for task_id, task_data in self.active_tasks.items():
                    task_age = current_time - task_data.get("created_at", current_time)
                    if task_age > 3600 and task_data["status"] in ["completed", "failed"]:  # 1 hour
                        tasks_to_remove.append(task_id)
                
                for task_id in tasks_to_remove:
                    del self.active_tasks[task_id]
                    self.logger.debug(f"Cleaned up old task: {task_id}")
                
                # Return task summary
                task_summary = {
                    "total_tasks": len(self.active_tasks),
                    "running_tasks": len([t for t in self.active_tasks.values() if t["status"] == "running"]),
                    "completed_tasks": len([t for t in self.active_tasks.values() if t["status"] == "completed"]),
                    "failed_tasks": len([t for t in self.active_tasks.values() if t["status"] == "failed"]),
                    "tasks": self.active_tasks
                }
                
                return task_summary
                
            except Exception as e:
                self.log_error("list_tasks", e)
                raise HTTPException(status_code=500, detail="Error retrieving tasks")
        
        @self.router.post("/validate/youtube")
        async def validate_youtube_url(request: YouTubeValidationRequest):
            """Validate a YouTube URL without starting generation."""
            try:
                if not request.url:
                    raise HTTPException(status_code=400, detail="URL is required")
                
                validation_result = await validate_youtube_url_async(request.url)
                
                return {
                    "valid": validation_result["valid"],
                    "message": validation_result.get("message"),
                    "details": validation_result.get("details", {}),
                    "error_type": validation_result.get("error_type")
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("validate_youtube_url", e)
                raise HTTPException(status_code=500, detail="Error validating YouTube URL")
        
        @self.router.get("/video/{filename}")
        async def serve_video(filename: str, current_user: CurrentUser = None):
            """Serve generated video files."""
            from fastapi.responses import FileResponse
            from pathlib import Path
            import os
            
            try:
                # Sanitize filename to prevent directory traversal
                filename = os.path.basename(filename)
                
                # Verify it's a video file
                if not filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    raise HTTPException(status_code=400, detail="Invalid file type")
                
                video_path = None
                
                # If user is authenticated, check their user-specific directory first
                if current_user:
                    user_video_path = Path("data/output") / f"user_{current_user.id}" / filename
                    if user_video_path.exists() and user_video_path.is_file():
                        video_path = user_video_path
                
                # Fall back to general output directory for backward compatibility
                if not video_path:
                    general_video_path = Path("data/output") / filename
                    if general_video_path.exists() and general_video_path.is_file():
                        video_path = general_video_path
                
                if not video_path:
                    raise HTTPException(status_code=404, detail="Video file not found")
                
                return FileResponse(
                    path=str(video_path),
                    media_type="video/mp4",
                    filename=filename
                )
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("serve_video", e)
                raise HTTPException(status_code=500, detail="Error serving video file")
        
        @self.router.get("/task/progress")
        async def get_current_task_progress():
            """Get progress for the most recent active task (for HTMX polling)."""
            from fastapi.responses import HTMLResponse
            
            try:
                # Find the most recent active task
                active_tasks = [
                    (task_id, task_data) for task_id, task_data in self.active_tasks.items()
                    if task_data["status"] in ["started", "running"]
                ]
                
                if not active_tasks:
                    return HTMLResponse("""
                    <script>
                        const container = document.querySelector('[x-data*="choreographyGenerator"]');
                        if (container && container._x_dataStack) {
                            const data = container._x_dataStack[0];
                            data.isGenerating = false;
                        }
                    </script>
                    """)
                
                # Get the most recent task
                task_id, task_data = max(active_tasks, key=lambda x: x[1].get("created_at", 0))
                
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
                            const errorMsg = '{task_data.get('error', 'Generation failed').replace("'", "\\'").replace('"', '\\"')}';
                            data.showError(errorMsg);
                        }}
                    }}
                </script>
                """
                
                return HTMLResponse(progress_script)
                
            except Exception as e:
                self.log_error("get_current_task_progress", e)
                return HTMLResponse("""
                <script>
                    const container = document.querySelector('[x-data*="choreographyGenerator"]');
                    if (container && container._x_dataStack) {
                        const data = container._x_dataStack[0];
                        data.showError('Error checking progress');
                    }
                </script>
                """)
    
    async def _generate_choreography_task_safe(
        self,
        task_id: str,
        user_id: str,
        youtube_url: str,
        difficulty: str,
        energy_level: Optional[str],
        quality_mode: str,
        auto_save: bool = True
    ):
        """
        Safe wrapper for choreography generation with comprehensive error handling.
        """
        try:
            await self._generate_choreography_task(
                task_id, user_id, youtube_url, difficulty, energy_level, quality_mode, auto_save
            )
        except Exception as e:
            self.logger.error(f"Critical error in task {task_id}: {e}", exc_info=True)
            
            # Ensure task status is updated even on critical failure
            if task_id in self.active_tasks:
                self.active_tasks[task_id].update({
                    "status": "failed",
                    "progress": 0,
                    "stage": "failed",
                    "message": "Critical system error occurred",
                    "error": "Internal system error - please try again later"
                })
    
    async def _generate_choreography_task(
        self,
        task_id: str,
        user_id: str,
        youtube_url: str,
        difficulty: str,
        energy_level: Optional[str],
        quality_mode: str,
        auto_save: bool = True
    ):
        """
        Background task for generating choreography with enhanced error handling.
        
        This function runs the complete choreography generation pipeline
        and updates the task status throughout the process.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Update task status
            self.active_tasks[task_id].update({
                "status": "running",
                "progress": 5,
                "stage": "downloading",
                "message": "Downloading audio from YouTube..."
            })
            
            # Create user-specific output directory
            user_output_dir = Path("data/output") / f"user_{user_id}"
            user_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create user-specific temp directory
            user_temp_dir = Path("data/temp") / f"user_{user_id}" / task_id
            user_temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Get pipeline with specified quality mode and user-specific paths
            config = PipelineConfig(
                quality_mode=quality_mode,
                enable_caching=True,
                max_workers=4,
                cleanup_after_generation=True,
                output_directory=str(user_output_dir),
                temp_directory=str(user_temp_dir)
            )
            task_pipeline = ChoreoGenerationPipeline(config)
            
            # Progress tracking with more granular updates
            progress_stages = [
                (10, "downloading", "Downloading audio from YouTube..."),
                (25, "analyzing", "Analyzing musical structure and tempo..."),
                (40, "selecting", "Analyzing dance moves and selecting sequences..."),
                (70, "generating", "Generating choreography video..."),
                (90, "finalizing", "Finalizing video and metadata...")
            ]
            
            # Simulate progress updates during generation
            for progress, stage, message in progress_stages:
                self.active_tasks[task_id].update({
                    "progress": progress,
                    "stage": stage,
                    "message": message
                })
                
                # Small delay to allow progress updates to be visible
                await asyncio.sleep(0.1)
            
            # Generate choreography
            result = await task_pipeline.generate_choreography(
                audio_input=youtube_url,
                difficulty=difficulty,
                energy_level=energy_level
            )
            
            if result.success:
                # Attempt automatic saving if requested and user preferences allow it
                saved_choreography_id = None
                should_auto_save = auto_save and await self._should_auto_save_for_user(user_id)
                
                if should_auto_save:
                    try:
                        saved_choreography_id = await self._auto_save_choreography(
                            user_id, result, youtube_url, difficulty, quality_mode, energy_level
                        )
                        self.logger.info(f"Automatically saved choreography {saved_choreography_id} for user {user_id}")
                    except Exception as save_error:
                        self.logger.warning(f"Auto-save failed for task {task_id}: {save_error}")
                        # Don't fail the entire task if auto-save fails
                
                # Update with success
                self.active_tasks[task_id].update({
                    "status": "completed",
                    "progress": 100,
                    "stage": "completed",
                    "message": "Choreography generation completed successfully!" + 
                              (" (Saved to collection)" if saved_choreography_id else ""),
                    "completed_at": asyncio.get_event_loop().time(),
                    "total_time": asyncio.get_event_loop().time() - start_time,
                    "result": {
                        "video_path": result.output_path,
                        "metadata_path": result.metadata_path,
                        "processing_time": result.processing_time,
                        "sequence_duration": result.sequence_duration,
                        "moves_analyzed": result.moves_analyzed,
                        "recommendations_generated": result.recommendations_generated,
                        "cache_hits": result.cache_hits,
                        "cache_misses": result.cache_misses,
                        "video_filename": Path(result.output_path).name if result.output_path else None,
                        "saved_choreography_id": saved_choreography_id,
                        "auto_saved": auto_save and saved_choreography_id is not None
                    }
                })
                
                self.logger.info(f"Task {task_id} completed successfully in {result.processing_time:.2f}s")
                
                # Clean up temporary files after successful generation
                try:
                    cleanup_stats = await resource_manager.cleanup_temporary_files()
                    if cleanup_stats["files_removed"] > 0:
                        self.logger.info(f"Post-generation cleanup: {cleanup_stats['files_removed']} temp files removed")
                except Exception as cleanup_error:
                    self.logger.warning(f"Post-generation cleanup failed: {cleanup_error}")
                
            else:
                # Categorize the error for better user feedback
                error_message = result.error_message or "Unknown error occurred"
                user_message = self._get_user_friendly_error_message(error_message)
                
                # Update with failure
                self.active_tasks[task_id].update({
                    "status": "failed",
                    "progress": 0,
                    "stage": "failed",
                    "message": user_message,
                    "error": error_message,
                    "failed_at": asyncio.get_event_loop().time(),
                    "total_time": asyncio.get_event_loop().time() - start_time
                })
                
                self.logger.error(f"Task {task_id} failed: {error_message}")
        
        except YouTubeDownloadError as e:
            self.active_tasks[task_id].update({
                "status": "failed",
                "progress": 0,
                "stage": "failed",
                "message": e.message,
                "error": f"YouTube download failed: {e.message}",
                "failed_at": asyncio.get_event_loop().time()
            })
            self.logger.error(f"Task {task_id} - YouTube download error: {e.message}")
        
        except MusicAnalysisError as e:
            self.active_tasks[task_id].update({
                "status": "failed",
                "progress": 0,
                "stage": "failed",
                "message": e.message,
                "error": f"Music analysis failed: {e.message}",
                "failed_at": asyncio.get_event_loop().time()
            })
            self.logger.error(f"Task {task_id} - Music analysis error: {e.message}")
        
        except VideoGenerationError as e:
            self.active_tasks[task_id].update({
                "status": "failed",
                "progress": 0,
                "stage": "failed",
                "message": e.message,
                "error": f"Video generation failed: {e.message}",
                "failed_at": asyncio.get_event_loop().time()
            })
            self.logger.error(f"Task {task_id} - Video generation error: {e.message}")
        
        except ResourceError as e:
            self.active_tasks[task_id].update({
                "status": "failed",
                "progress": 0,
                "stage": "failed",
                "message": e.message,
                "error": f"Resource error: {e.message}",
                "failed_at": asyncio.get_event_loop().time()
            })
            self.logger.error(f"Task {task_id} - Resource error: {e.message}")
        
        except Exception as e:
            # Generic error handling
            error_message = str(e)
            user_message = "An unexpected error occurred during generation. Please try again."
            
            self.active_tasks[task_id].update({
                "status": "failed",
                "progress": 0,
                "stage": "failed", 
                "message": user_message,
                "error": error_message,
                "failed_at": asyncio.get_event_loop().time()
            })
            
            self.logger.error(f"Task {task_id} failed with unexpected exception: {e}", exc_info=True)
        
        finally:
            # Always attempt cleanup after task completion (success or failure)
            try:
                # Clean up user-specific temporary files
                from app.services.temp_file_manager import temp_file_manager
                await temp_file_manager.cleanup_user_temp_files(user_id)
                
                # General cleanup
                cleanup_stats = await resource_manager.cleanup_temporary_files()
                if cleanup_stats["files_removed"] > 0:
                    self.logger.debug(f"Task cleanup: {cleanup_stats['files_removed']} temp files removed")
            except Exception as cleanup_error:
                self.logger.warning(f"Task cleanup failed: {cleanup_error}")
    
    async def _should_auto_save_for_user(self, user_id: str) -> bool:
        """
        Check if auto-save is enabled for the user based on their preferences.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            bool: True if auto-save should be performed, False otherwise
        """
        try:
            from app.database import get_database_session
            from app.models.database_models import User
            
            # Get database session
            db_gen = get_database_session()
            db = next(db_gen)
            
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False
                
                # Check user preferences
                preferences = user.preferences or {}
                return preferences.get("auto_save_choreographies", True)  # Default to True
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.warning(f"Failed to check auto-save preference for user {user_id}: {e}")
            return True  # Default to auto-save on error
    
    async def _auto_save_choreography(
        self,
        user_id: str,
        result,
        youtube_url: str,
        difficulty: str,
        quality_mode: str,
        energy_level: str
    ) -> Optional[str]:
        """
        Automatically save a generated choreography to the user's collection.
        
        Args:
            user_id: User's unique identifier
            result: Pipeline generation result
            youtube_url: Original YouTube URL
            difficulty: Difficulty level used
            quality_mode: Quality mode used
            energy_level: Energy level used
            
        Returns:
            Optional[str]: Saved choreography ID if successful, None otherwise
        """
        try:
            from app.services.collection_service import CollectionService
            from app.models.collection_models import SaveChoreographyRequest
            from app.database import get_database_session
            
            # Extract metadata from result
            metadata = {}
            if result.metadata_path and Path(result.metadata_path).exists():
                try:
                    import json
                    with open(result.metadata_path, 'r') as f:
                        metadata = json.load(f)
                except Exception as e:
                    self.logger.warning(f"Failed to load metadata from {result.metadata_path}: {e}")
            
            # Generate title from YouTube URL or metadata
            title = self._generate_choreography_title(youtube_url, metadata, difficulty)
            
            # Create music info
            music_info = {
                "youtube_url": youtube_url,
                "title": metadata.get("title", "Unknown"),
                "duration": result.sequence_duration,
                "tempo": metadata.get("tempo"),
                "energy_level": energy_level
            }
            
            # Create generation parameters
            generation_parameters = {
                "difficulty": difficulty,
                "quality_mode": quality_mode,
                "energy_level": energy_level,
                "processing_time": result.processing_time,
                "moves_analyzed": result.moves_analyzed,
                "recommendations_generated": result.recommendations_generated
            }
            
            # Generate thumbnail if possible
            thumbnail_path = await self._generate_video_thumbnail(result.output_path)
            
            # Create save request
            save_request = SaveChoreographyRequest(
                title=title,
                video_path=result.output_path,
                thumbnail_path=thumbnail_path,
                difficulty=difficulty,
                duration=result.sequence_duration,
                music_info=music_info,
                generation_parameters=generation_parameters
            )
            
            # Save to collection
            collection_service = CollectionService("data")
            
            # Get database session
            db_gen = get_database_session()
            db = next(db_gen)
            
            try:
                saved_choreography = await collection_service.save_choreography(
                    db, user_id, save_request
                )
                return saved_choreography.id
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Auto-save failed for user {user_id}: {e}")
            return None
    
    def _generate_choreography_title(self, youtube_url: str, metadata: Dict, difficulty: str) -> str:
        """
        Generate a title for the choreography based on available information.
        
        Args:
            youtube_url: Original YouTube URL
            metadata: Extracted metadata
            difficulty: Difficulty level
            
        Returns:
            str: Generated title
        """
        # Try to extract title from metadata
        if metadata.get("title"):
            base_title = metadata["title"]
            # Clean up the title
            base_title = base_title.replace("(Official Video)", "").replace("(Official Audio)", "")
            base_title = base_title.replace("[Official Video]", "").replace("[Official Audio]", "")
            base_title = base_title.strip()
        else:
            # Extract from URL or use generic title
            try:
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(youtube_url)
                video_id = parse_qs(parsed.query).get('v', ['Unknown'])[0]
                base_title = f"YouTube Video {video_id[:8]}"
            except:
                base_title = "Bachata Choreography"
        
        # Add difficulty level
        title = f"{base_title} ({difficulty.title()})"
        
        # Ensure title is not too long
        if len(title) > 200:
            title = title[:197] + "..."
        
        return title
    
    async def _generate_video_thumbnail(self, video_path: str) -> Optional[str]:
        """
        Generate a thumbnail for the video.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Optional[str]: Path to generated thumbnail, None if failed
        """
        try:
            import subprocess
            from pathlib import Path
            
            video_file = Path(video_path)
            if not video_file.exists():
                return None
            
            # Generate thumbnail filename
            thumbnail_path = video_file.parent / f"{video_file.stem}_thumb.jpg"
            
            # Use FFmpeg to generate thumbnail at 2 seconds
            cmd = [
                "ffmpeg", "-i", str(video_file),
                "-ss", "00:00:02",  # Seek to 2 seconds
                "-vframes", "1",    # Extract 1 frame
                "-q:v", "2",        # High quality
                "-y",               # Overwrite output
                str(thumbnail_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and thumbnail_path.exists():
                return str(thumbnail_path)
            else:
                self.logger.warning(f"Thumbnail generation failed: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.warning(f"Failed to generate thumbnail for {video_path}: {e}")
            return None
    
    def _get_user_friendly_error_message(self, error_message: str) -> str:
        """Convert technical error messages to user-friendly messages."""
        error_lower = error_message.lower()
        
        if "youtube" in error_lower and ("download" in error_lower or "fetch" in error_lower):
            return "Unable to download audio from YouTube. Please check the URL and try again."
        elif "music analysis" in error_lower or "librosa" in error_lower:
            return "Unable to analyze the music. The audio may be corrupted or in an unsupported format."
        elif "move analysis" in error_lower or "mediapipe" in error_lower:
            return "Unable to analyze dance moves. Please contact support if this persists."
        elif "video generation" in error_lower or "ffmpeg" in error_lower:
            return "Unable to generate the choreography video. Please try again."
        elif "memory" in error_lower or "disk" in error_lower:
            return "Insufficient system resources. Please try again later."
        elif "timeout" in error_lower:
            return "Generation took too long and was cancelled. Please try with a shorter song."
        else:
            return "An unexpected error occurred. Please try again or contact support."