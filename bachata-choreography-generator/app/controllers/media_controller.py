"""
Media controller for video serving, file management, and system utilities.
"""
import asyncio
import os
import psutil
from pathlib import Path
from typing import Dict

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from .base_controller import BaseController
from app.validation import validate_system_requirements
from app.services.resource_manager import resource_manager

class MediaController(BaseController):
    """Controller for media serving and utility endpoints."""
    
    def __init__(self):
        super().__init__(prefix="", tags=["media", "system"])
        self.templates = Jinja2Templates(directory="app/templates")
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up media and utility routes."""
        
        @self.router.get("/", response_class=HTMLResponse)
        async def root(request: Request):
            """Serve the main application page."""
            return self.templates.TemplateResponse("index.html", {"request": request})
        
        @self.router.get("/collection", response_class=HTMLResponse)
        async def collection_page(request: Request):
            """Serve the collection management page."""
            return self.templates.TemplateResponse("collection.html", {"request": request})
        
        @self.router.get("/instructor", response_class=HTMLResponse)
        async def instructor_page(request: Request):
            """Serve the instructor dashboard page."""
            return self.templates.TemplateResponse("instructor.html", {"request": request})
        
        @self.router.get("/health")
        async def health_check():
            """Comprehensive health check endpoint."""
            try:
                # Basic system info
                health_status = {
                    "status": "healthy",
                    "version": "0.1.0",
                    "timestamp": str(asyncio.get_event_loop().time()),
                    "pipeline_initialized": True  # Will be updated when pipeline is integrated
                }
                
                # System resources
                try:
                    memory = psutil.virtual_memory()
                    disk = psutil.disk_usage('.')
                    
                    health_status["system"] = {
                        "memory_percent": memory.percent,
                        "memory_available_gb": round(memory.available / (1024**3), 2),
                        "disk_percent": disk.percent,
                        "disk_free_gb": round(disk.free / (1024**3), 2)
                    }
                except Exception as e:
                    health_status["system"] = {"error": str(e)}
                
                # Service status
                health_status["services"] = {
                    "youtube_service": True,  # Will be updated when services are integrated
                    "active_tasks": 0,  # Will be updated when choreography controller is integrated
                    "pipeline_cache_enabled": True
                }
                
                # Quick system validation
                system_check = validate_system_requirements()
                health_status["system_validation"] = {
                    "valid": system_check["valid"],
                    "issues_count": len(system_check["issues"]),
                    "warnings_count": len(system_check.get("warnings", []))
                }
                
                return health_status
                
            except Exception as e:
                self.log_error("health_check", e)
                return {
                    "status": "unhealthy",
                    "version": "0.1.0",
                    "error": str(e)
                }
        
        @self.router.get("/api/video/{filename}")
        async def serve_video(filename: str):
            """
            Serve generated choreography videos with proper headers for browser playback.
            
            This endpoint serves video files with appropriate headers for streaming
            and browser compatibility.
            """
            try:
                # Input validation
                if not filename or not isinstance(filename, str):
                    raise HTTPException(status_code=400, detail="Invalid filename")
                
                # Security: sanitize filename (prevent path traversal)
                safe_filename = os.path.basename(filename)
                if safe_filename != filename:
                    self.logger.warning(f"Potential path traversal attempt: {filename}")
                    raise HTTPException(status_code=400, detail="Invalid filename format")
                
                # Only allow specific file extensions
                allowed_extensions = {'.mp4', '.webm', '.mov'}
                file_ext = Path(safe_filename).suffix.lower()
                if file_ext not in allowed_extensions:
                    raise HTTPException(status_code=400, detail="Unsupported file type")
                
                # Security: only allow serving from output directory
                video_path = Path("data/output") / safe_filename
                
                # Validate file exists and is in the correct directory
                if not video_path.exists() or not video_path.is_file():
                    self.logger.info(f"Video file not found: {video_path}")
                    raise HTTPException(status_code=404, detail="Video not found")
                
                # Double-check path security (prevent path traversal)
                try:
                    video_path_resolved = video_path.resolve()
                    output_dir_resolved = Path("data/output").resolve()
                    
                    if not str(video_path_resolved).startswith(str(output_dir_resolved)):
                        self.logger.warning(f"Path traversal attempt blocked: {video_path}")
                        raise HTTPException(status_code=403, detail="Access denied")
                except Exception as e:
                    self.logger.error(f"Path resolution error for {video_path}: {e}")
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Get file info
                try:
                    file_stat = video_path.stat()
                    file_size = file_stat.st_size
                    
                    # Check if file is too large (prevent serving corrupted/incomplete files)
                    if file_size > 500 * 1024 * 1024:  # 500MB limit
                        self.logger.warning(f"File too large: {video_path} ({file_size} bytes)")
                        raise HTTPException(status_code=413, detail="File too large")
                    
                    if file_size == 0:
                        self.logger.warning(f"Empty file: {video_path}")
                        raise HTTPException(status_code=404, detail="Video file is empty")
                        
                except OSError as e:
                    self.logger.error(f"Error accessing file {video_path}: {e}")
                    raise HTTPException(status_code=500, detail="Error accessing video file")
                
                # Determine media type
                media_type_map = {
                    '.mp4': 'video/mp4',
                    '.webm': 'video/webm',
                    '.mov': 'video/quicktime'
                }
                media_type = media_type_map.get(file_ext, 'video/mp4')
                
                # Return video file with proper headers
                return FileResponse(
                    path=str(video_path),
                    media_type=media_type,
                    headers={
                        "Content-Length": str(file_size),
                        "Accept-Ranges": "bytes",
                        "Cache-Control": "public, max-age=3600",
                        "X-Content-Type-Options": "nosniff"
                    }
                )
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("serve_video", e)
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.router.get("/api/videos")
        async def list_videos():
            """List all available generated choreography videos."""
            try:
                output_dir = Path("data/output")
                videos = []
                
                if output_dir.exists():
                    for video_file in output_dir.glob("*.mp4"):
                        stat = video_file.stat()
                        videos.append({
                            "filename": video_file.name,
                            "size": stat.st_size,
                            "created": stat.st_ctime,
                            "url": f"/api/video/{video_file.name}"
                        })
                
                return {"videos": videos}
                
            except Exception as e:
                self.log_error("list_videos", e)
                raise HTTPException(status_code=500, detail="Error listing videos")
        
        @self.router.get("/api/songs")
        async def list_songs():
            """List all available local songs."""
            try:
                songs_dir = Path("data/songs")
                songs = []
                
                if songs_dir.exists():
                    for song_file in songs_dir.glob("*.mp3"):
                        stat = song_file.stat()
                        # Create a friendly display name from filename
                        display_name = song_file.stem.replace('_', ' ').title()
                        songs.append({
                            "filename": song_file.name,
                            "display_name": display_name,
                            "path": str(song_file),
                            "size": stat.st_size,
                            "created": stat.st_ctime
                        })
                
                # Sort by display name
                songs.sort(key=lambda x: x['display_name'])
                
                return {"songs": songs}
                
            except Exception as e:
                self.log_error("list_songs", e)
                raise HTTPException(status_code=500, detail="Error listing songs")
        
        @self.router.get("/api/system/status")
        async def system_status():
            """Get detailed system status and diagnostics."""
            try:
                status = {
                    "timestamp": asyncio.get_event_loop().time(),
                    "system_validation": validate_system_requirements(),
                    "active_tasks": 0,  # Will be updated when choreography controller is integrated
                    "pipeline_status": {
                        "initialized": True,  # Will be updated when pipeline is integrated
                        "cache_enabled": True,
                        "quality_mode": "balanced"
                    }
                }
                
                # Add system resources if available
                try:
                    memory = psutil.virtual_memory()
                    disk = psutil.disk_usage('.')
                    
                    status["resources"] = {
                        "memory": {
                            "total_gb": round(memory.total / (1024**3), 2),
                            "available_gb": round(memory.available / (1024**3), 2),
                            "percent_used": memory.percent
                        },
                        "disk": {
                            "total_gb": round(disk.total / (1024**3), 2),
                            "free_gb": round(disk.free / (1024**3), 2),
                            "percent_used": disk.percent
                        }
                    }
                except Exception as e:
                    status["resources"] = {"error": str(e)}
                
                return status
                
            except Exception as e:
                self.log_error("system_status", e)
                raise HTTPException(status_code=500, detail="Error retrieving system status")
        
        @self.router.post("/api/system/cleanup")
        async def manual_cleanup():
            """Manually trigger system cleanup."""
            try:
                temp_stats = await resource_manager.cleanup_temporary_files()
                cache_stats = await resource_manager.cleanup_cache_directory()
                
                return {
                    "message": "Cleanup completed successfully",
                    "temporary_files": temp_stats,
                    "cache_cleanup": cache_stats,
                    "total_files_removed": temp_stats["files_removed"] + cache_stats["files_removed"],
                    "total_bytes_freed": temp_stats["bytes_freed"] + cache_stats["bytes_freed"]
                }
                
            except Exception as e:
                self.log_error("manual_cleanup", e)
                raise HTTPException(status_code=500, detail="Error during cleanup")
        
        @self.router.get("/api/system/resources")
        async def get_system_resources():
            """Get detailed system resource information."""
            try:
                resources = resource_manager.get_system_resources()
                return resources
                
            except Exception as e:
                self.log_error("get_system_resources", e)
                raise HTTPException(status_code=500, detail="Error retrieving system resources")