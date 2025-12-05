"""
Video Assembly Service

This service handles video assembly from blueprints using FFmpeg.
It integrates directly into the Django backend, eliminating the need
for a separate job container.

Key responsibilities:
- Validate blueprint structure and security
- Fetch audio and video files from storage
- Concatenate video clips using FFmpeg
- Add audio track to the concatenated video
- Upload result to storage
- Clean up temporary files

**Feature: job-integration**
"""

import os
import logging
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

from .storage.base import StorageBackend
from .ffmpeg_builder import FFmpegCommandBuilder

logger = logging.getLogger(__name__)


class VideoAssemblyError(Exception):
    """Raised when video assembly fails."""
    pass


class VideoAssemblyService:
    """
    Assembles videos from blueprints using FFmpeg.
    
    This service:
    1. Validates blueprint structure
    2. Downloads media files from storage
    3. Normalizes video clips to consistent frame rate
    4. Concatenates clips using FFmpeg
    5. Adds audio track
    6. Uploads result to storage
    7. Cleans up temporary files
    """
    
    # Required blueprint fields
    REQUIRED_FIELDS = ['task_id', 'audio_path', 'moves', 'output_config']
    REQUIRED_OUTPUT_CONFIG_FIELDS = ['output_path']
    REQUIRED_MOVE_FIELDS = ['video_path']
    
    # Security patterns to reject
    DANGEROUS_PATH_PATTERNS = ['..', '\\']
    
    # FFmpeg configuration
    DEFAULT_FRAME_RATE = 30
    FFMPEG_TIMEOUT_NORMALIZE = 60  # 1 minute per clip
    FFMPEG_TIMEOUT_CONCAT = 300  # 5 minutes
    FFMPEG_TIMEOUT_AUDIO = 600  # 10 minutes
    
    def __init__(self, storage_service: StorageBackend, temp_dir: Optional[str] = None):
        """
        Initialize with storage service.
        
        Args:
            storage_service: Storage backend for file operations
            temp_dir: Optional custom temporary directory
        """
        self.storage = storage_service
        self._temp_dir = temp_dir
        self._created_temp_dir: Optional[str] = None
        self.ffmpeg_builder = FFmpegCommandBuilder()
        
        logger.info("VideoAssemblyService initialized")
    
    @property
    def temp_dir(self) -> str:
        """Get or create temporary directory."""
        if self._temp_dir:
            os.makedirs(self._temp_dir, exist_ok=True)
            return self._temp_dir
        
        if not self._created_temp_dir:
            self._created_temp_dir = tempfile.mkdtemp(prefix='video_assembly_')
        
        return self._created_temp_dir
    
    def check_ffmpeg_available(self) -> bool:
        """
        Verify FFmpeg is available in system PATH.
        
        Returns:
            True if FFmpeg is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            version_line = result.stdout.split('\n')[0] if result.stdout else 'unknown'
            logger.debug(f"FFmpeg available: {version_line}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"FFmpeg not available: {e}")
            return False

    def validate_blueprint(self, blueprint: dict) -> Tuple[bool, Optional[str]]:
        """
        Validate blueprint structure and security.
        
        Checks:
        1. All required fields are present
        2. Moves array is not empty
        3. Each move has required fields
        4. No path traversal or absolute paths (security)
        
        Args:
            blueprint: Blueprint dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, "error description") if invalid
        """
        # Check required top-level fields
        for field in self.REQUIRED_FIELDS:
            if field not in blueprint:
                return False, f"Missing required field: {field}"
        
        # Check moves is a non-empty list
        moves = blueprint.get('moves')
        if not isinstance(moves, list):
            return False, "Field 'moves' must be a list"
        if len(moves) == 0:
            return False, "Field 'moves' cannot be empty"
        
        # Check output_config has required fields
        output_config = blueprint.get('output_config', {})
        if not isinstance(output_config, dict):
            return False, "Field 'output_config' must be a dictionary"
        
        for field in self.REQUIRED_OUTPUT_CONFIG_FIELDS:
            if field not in output_config:
                return False, f"Missing required output_config field: {field}"
        
        # Check each move has required fields
        for idx, move in enumerate(moves):
            if not isinstance(move, dict):
                return False, f"Move {idx} must be a dictionary"
            for field in self.REQUIRED_MOVE_FIELDS:
                if field not in move:
                    return False, f"Move {idx} missing required field: {field}"
        
        # Security: Check for path traversal and absolute paths
        paths_to_check = [
            ('audio_path', blueprint.get('audio_path', '')),
            ('output_config.output_path', output_config.get('output_path', ''))
        ]
        
        for idx, move in enumerate(moves):
            paths_to_check.append((f'moves[{idx}].video_path', move.get('video_path', '')))
        
        for path_name, path_value in paths_to_check:
            if not isinstance(path_value, str):
                return False, f"Path '{path_name}' must be a string"
            
            # Check for directory traversal
            for pattern in self.DANGEROUS_PATH_PATTERNS:
                if pattern in path_value:
                    return False, f"Security error: Path '{path_name}' contains invalid pattern '{pattern}'"
            
            # Check for absolute paths (Unix-style)
            if path_value.startswith('/'):
                return False, f"Security error: Path '{path_name}' cannot be an absolute path"
        
        return True, None

    def _fetch_media_files(self, blueprint: Dict) -> Tuple[str, List[str]]:
        """
        Fetch audio and video files from storage.
        
        Args:
            blueprint: Blueprint dictionary
            
        Returns:
            Tuple of (audio_file_path, list_of_video_file_paths)
            
        Raises:
            VideoAssemblyError: If fetching fails
        """
        audio_path = blueprint.get('audio_path')
        moves = blueprint.get('moves', [])
        
        logger.info(f"Fetching media files: audio={audio_path}, clips={len(moves)}")
        
        # Fetch audio file
        audio_local_path = os.path.join(self.temp_dir, 'audio' + Path(audio_path).suffix)
        
        try:
            self.storage.download_file(audio_path, audio_local_path)
            
            if not os.path.exists(audio_local_path):
                raise VideoAssemblyError(f"Audio file not found after download: {audio_path}")
            
            file_size = os.path.getsize(audio_local_path)
            if file_size == 0:
                raise VideoAssemblyError(f"Downloaded audio file is empty: {audio_path}")
            
            logger.debug(f"Audio downloaded: {audio_local_path} ({file_size} bytes)")
            
        except VideoAssemblyError:
            raise
        except Exception as e:
            raise VideoAssemblyError(f"Failed to fetch audio file '{audio_path}': {str(e)}") from e
        
        # Fetch video files
        video_clips_dir = os.path.join(self.temp_dir, 'clips')
        os.makedirs(video_clips_dir, exist_ok=True)
        
        video_files = []
        for idx, move in enumerate(moves):
            video_path = move.get('video_path')
            filename = f'clip_{idx:04d}.mp4'
            local_path = os.path.join(video_clips_dir, filename)
            
            try:
                self.storage.download_file(video_path, local_path)
                
                if not os.path.exists(local_path):
                    raise VideoAssemblyError(f"Video clip {idx} not found after download: {video_path}")
                
                file_size = os.path.getsize(local_path)
                if file_size == 0:
                    raise VideoAssemblyError(f"Video clip {idx} is empty: {video_path}")
                
                video_files.append(local_path)
                logger.debug(f"Downloaded clip {idx+1}/{len(moves)}: {video_path}")
                
            except VideoAssemblyError:
                raise
            except Exception as e:
                raise VideoAssemblyError(f"Failed to fetch video clip '{video_path}': {str(e)}") from e
        
        logger.info(f"All media files fetched: audio + {len(video_files)} clips")
        return audio_local_path, video_files
    
    def _normalize_clip_framerates(self, video_files: List[str]) -> List[str]:
        """
        Normalize all video clips to consistent frame rate.
        
        Args:
            video_files: List of source video file paths
            
        Returns:
            List of normalized video file paths
            
        Raises:
            VideoAssemblyError: If normalization fails
        """
        normalized_files = []
        normalized_dir = os.path.join(self.temp_dir, 'normalized')
        os.makedirs(normalized_dir, exist_ok=True)
        
        logger.info(f"Normalizing {len(video_files)} clips to {self.DEFAULT_FRAME_RATE} fps")
        
        for idx, video_file in enumerate(video_files):
            output_file = os.path.join(normalized_dir, f'normalized_{idx:04d}.mp4')
            
            ffmpeg_cmd = self.ffmpeg_builder.build_normalize_command(
                input_file=video_file,
                output_file=output_file,
                frame_rate=self.DEFAULT_FRAME_RATE
            )
            
            try:
                subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=self.FFMPEG_TIMEOUT_NORMALIZE
                )
                
                if not os.path.exists(output_file):
                    raise VideoAssemblyError(f"Normalized clip {idx} not created")
                
                normalized_files.append(output_file)
                
                if (idx + 1) % 10 == 0:
                    logger.info(f"Normalized {idx + 1}/{len(video_files)} clips")
                
            except subprocess.TimeoutExpired:
                raise VideoAssemblyError(f"Normalization timed out for clip {idx}")
            except subprocess.CalledProcessError as e:
                error_detail = e.stderr[-500:] if e.stderr else 'No error output'
                raise VideoAssemblyError(f"FFmpeg normalization failed for clip {idx}: {error_detail}")
        
        logger.info(f"All {len(normalized_files)} clips normalized")
        return normalized_files

    def _concatenate_videos(self, video_files: List[str], blueprint: Dict) -> str:
        """
        Concatenate video clips using FFmpeg.
        
        Args:
            video_files: List of local video file paths
            blueprint: Blueprint dictionary
            
        Returns:
            Path to concatenated video file
            
        Raises:
            VideoAssemblyError: If concatenation fails
        """
        logger.info(f"Concatenating {len(video_files)} video clips")
        
        # Validate input files exist
        for idx, video_file in enumerate(video_files):
            if not os.path.exists(video_file):
                raise VideoAssemblyError(f"Video file {idx} does not exist: {video_file}")
        
        # Normalize clips to consistent frame rate
        normalized_files = self._normalize_clip_framerates(video_files)
        
        # Create concat file
        concat_file = os.path.join(self.temp_dir, 'concat.txt')
        
        try:
            with open(concat_file, 'w') as f:
                for video_file in normalized_files:
                    abs_path = os.path.abspath(video_file)
                    f.write(f"file '{abs_path}'\n")
        except IOError as e:
            raise VideoAssemblyError(f"Failed to create concat file: {str(e)}") from e
        
        # Output file for concatenated video
        output_file = os.path.join(self.temp_dir, 'concatenated.mp4')
        
        # Build and execute FFmpeg concat command
        ffmpeg_cmd = self.ffmpeg_builder.build_concat_command(
            concat_file=concat_file,
            output_file=output_file
        )
        
        try:
            subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=self.FFMPEG_TIMEOUT_CONCAT
            )
            
            if not os.path.exists(output_file):
                raise VideoAssemblyError("Concatenated video file not created by FFmpeg")
            
            file_size = os.path.getsize(output_file)
            if file_size == 0:
                raise VideoAssemblyError("Concatenated video file is empty")
            
            logger.info(f"Videos concatenated: {output_file} ({file_size} bytes)")
            return output_file
            
        except subprocess.TimeoutExpired:
            raise VideoAssemblyError(f"FFmpeg concatenation timed out after {self.FFMPEG_TIMEOUT_CONCAT} seconds")
        except subprocess.CalledProcessError as e:
            error_detail = e.stderr[-500:] if e.stderr else 'No error output'
            raise VideoAssemblyError(f"FFmpeg concatenation failed: {error_detail}")
        except FileNotFoundError:
            raise VideoAssemblyError("FFmpeg executable not found")
    
    def _add_audio_track(
        self,
        video_file: str,
        audio_file: str,
        output_config: Dict
    ) -> str:
        """
        Add audio track to video using FFmpeg.
        
        Args:
            video_file: Path to video file (without audio)
            audio_file: Path to audio file
            output_config: Output configuration from blueprint
            
        Returns:
            Path to final video file with audio
            
        Raises:
            VideoAssemblyError: If adding audio fails
        """
        logger.info(f"Adding audio track to video")
        
        # Validate input files exist
        if not os.path.exists(video_file):
            raise VideoAssemblyError(f"Video file does not exist: {video_file}")
        if not os.path.exists(audio_file):
            raise VideoAssemblyError(f"Audio file does not exist: {audio_file}")
        
        # Output file for final video
        output_file = os.path.join(self.temp_dir, 'final_output.mp4')
        
        # Get output configuration with defaults
        video_codec = output_config.get('video_codec', 'libx264')
        audio_codec = output_config.get('audio_codec', 'aac')
        video_bitrate = output_config.get('video_bitrate', '2M')
        audio_bitrate = output_config.get('audio_bitrate', '128k')
        
        # Build and execute FFmpeg command
        ffmpeg_cmd = self.ffmpeg_builder.build_add_audio_command(
            video_file=video_file,
            audio_file=audio_file,
            output_file=output_file,
            video_codec=video_codec,
            audio_codec=audio_codec,
            video_bitrate=video_bitrate,
            audio_bitrate=audio_bitrate
        )
        
        try:
            subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=self.FFMPEG_TIMEOUT_AUDIO
            )
            
            if not os.path.exists(output_file):
                raise VideoAssemblyError("Final video file not created by FFmpeg")
            
            file_size = os.path.getsize(output_file)
            if file_size == 0:
                raise VideoAssemblyError("Final video file is empty")
            
            logger.info(f"Audio track added: {output_file} ({file_size} bytes)")
            return output_file
            
        except subprocess.TimeoutExpired:
            raise VideoAssemblyError(f"FFmpeg audio addition timed out after {self.FFMPEG_TIMEOUT_AUDIO} seconds")
        except subprocess.CalledProcessError as e:
            error_detail = e.stderr[-500:] if e.stderr else 'No error output'
            raise VideoAssemblyError(f"FFmpeg audio addition failed: {error_detail}")
        except FileNotFoundError:
            raise VideoAssemblyError("FFmpeg executable not found")

    def _upload_result(self, video_file: str, blueprint: Dict) -> str:
        """
        Upload final video to storage.
        
        Args:
            video_file: Path to final video file
            blueprint: Blueprint dictionary (for output path)
            
        Returns:
            URL or path to uploaded video
            
        Raises:
            VideoAssemblyError: If upload fails
        """
        output_config = blueprint.get('output_config', {})
        output_path = output_config.get('output_path')
        
        if not output_path:
            raise VideoAssemblyError("No output_path specified in blueprint output_config")
        
        # Validate video file exists and is not empty
        if not os.path.exists(video_file):
            raise VideoAssemblyError(f"Video file does not exist: {video_file}")
        
        file_size = os.path.getsize(video_file)
        if file_size == 0:
            raise VideoAssemblyError(f"Video file is empty: {video_file}")
        
        logger.info(f"Uploading result to storage: {output_path} ({file_size} bytes)")
        
        try:
            result_url = self.storage.upload_file(
                local_path=video_file,
                remote_path=output_path
            )
            
            logger.info(f"Result uploaded: {result_url}")
            return result_url
            
        except Exception as e:
            raise VideoAssemblyError(f"Failed to upload result to '{output_path}': {str(e)}") from e
    
    def _cleanup_temp_files(self):
        """
        Clean up temporary files.
        
        Removes all files in the temp directory.
        """
        try:
            temp_dir = self._created_temp_dir or self._temp_dir
            if temp_dir and os.path.exists(temp_dir):
                # Remove all files in temp directory
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove {item_path}: {e}")
                
                # If we created the temp dir, remove it entirely
                if self._created_temp_dir:
                    try:
                        os.rmdir(temp_dir)
                    except Exception:
                        pass  # Directory might not be empty
                
                logger.info(f"Temporary files cleaned up: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")
    
    def assemble_video(
        self,
        blueprint: Dict,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> str:
        """
        Assemble video from blueprint.
        
        Args:
            blueprint: Blueprint dictionary with assembly instructions
            progress_callback: Optional callback(stage, progress, message)
        
        Returns:
            URL to the assembled video
            
        Raises:
            VideoAssemblyError: If assembly fails
        """
        task_id = blueprint.get('task_id', 'unknown')
        
        logger.info(f"Starting video assembly for task {task_id}")
        
        # Validate blueprint first
        is_valid, error_msg = self.validate_blueprint(blueprint)
        if not is_valid:
            raise VideoAssemblyError(f"Invalid blueprint: {error_msg}")
        
        try:
            # Step 1: Fetch media files (20% progress)
            if progress_callback:
                progress_callback('fetching', 20, 'Fetching media files from storage...')
            
            audio_file, video_files = self._fetch_media_files(blueprint)
            
            # Step 2: Concatenate video clips (50% progress)
            if progress_callback:
                progress_callback('concatenating', 50, 'Concatenating video clips...')
            
            concatenated_video = self._concatenate_videos(video_files, blueprint)
            
            # Step 3: Add audio track (70% progress)
            if progress_callback:
                progress_callback('adding_audio', 70, 'Adding audio track...')
            
            output_config = blueprint.get('output_config', {})
            final_video = self._add_audio_track(
                concatenated_video,
                audio_file,
                output_config
            )
            
            # Step 4: Upload result (85% progress)
            if progress_callback:
                progress_callback('uploading', 85, 'Uploading result to storage...')
            
            result_url = self._upload_result(final_video, blueprint)
            
            # Step 5: Cleanup (95% progress)
            if progress_callback:
                progress_callback('cleanup', 95, 'Cleaning up temporary files...')
            
            self._cleanup_temp_files()
            
            # Complete (100% progress)
            if progress_callback:
                progress_callback('completed', 100, 'Video assembly completed')
            
            logger.info(f"Video assembly completed for task {task_id}: {result_url}")
            return result_url
            
        except VideoAssemblyError:
            # Cleanup on error
            try:
                self._cleanup_temp_files()
            except Exception:
                pass
            raise
        except Exception as e:
            # Cleanup on error
            try:
                self._cleanup_temp_files()
            except Exception:
                pass
            raise VideoAssemblyError(f"Video assembly failed: {str(e)}") from e
