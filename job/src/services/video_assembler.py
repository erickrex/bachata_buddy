"""
Video Assembly Service

This service handles video assembly from blueprints using FFmpeg.
It fetches media files from storage, concatenates video clips with audio,
and applies transitions as specified in the blueprint.

Key responsibilities:
- Fetch audio and video files from storage (parallel downloads)
- Create FFmpeg concat file for video clips
- Concatenate video clips using FFmpeg
- Add audio track to the concatenated video
- Apply transitions between clips (optional)
- Upload result to storage
- Clean up temporary files

Features:
- Parallel downloads for faster media fetching
- Retry logic for storage operations
- Progress tracking and status updates
- Comprehensive error handling
- Support for both local and GCS storage
"""

import os
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VideoAssemblyError(Exception):
    """Raised when video assembly fails."""
    pass


class VideoAssembler:
    """
    Assembles videos from blueprints using FFmpeg.
    
    This service:
    1. Fetches audio and video files from storage
    2. Uses FFmpeg to concatenate clips with audio
    3. Applies transitions if specified
    4. Uploads result to storage
    """
    
    # FFmpeg configuration
    DEFAULT_VIDEO_CODEC = 'libx264'
    DEFAULT_AUDIO_CODEC = 'aac'
    DEFAULT_VIDEO_BITRATE = '2M'
    DEFAULT_AUDIO_BITRATE = '128k'
    DEFAULT_FRAME_RATE = 30
    
    # Parallel download configuration
    MAX_PARALLEL_DOWNLOADS = 10
    
    def __init__(self, storage_service, temp_dir: Optional[str] = None, use_gpu: Optional[bool] = None):
        """
        Initialize video assembler.
        
        Args:
            storage_service: Storage service instance for file operations
            temp_dir: Temporary directory for intermediate files (optional)
            use_gpu: Whether to use GPU acceleration (None = auto-detect)
        """
        self.storage = storage_service
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix='video_assembly_')
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # GPU configuration
        self.use_gpu = self._should_use_gpu(use_gpu)
        
        # Initialize FFmpeg command builder
        try:
            from services.ffmpeg_builder import FFmpegCommandBuilder
            self.ffmpeg_builder = FFmpegCommandBuilder(use_gpu=self.use_gpu)
            logger.info(f"FFmpeg builder initialized (GPU: {self.ffmpeg_builder.use_gpu})")
        except Exception as e:
            logger.warning(f"Failed to initialize FFmpeg builder: {e}")
            self.ffmpeg_builder = None
        
        logger.info(
            f"Video assembler initialized",
            extra={
                'temp_dir': self.temp_dir,
                'storage_mode': 'GCS' if not storage_service.config.use_local_storage else 'Local',
                'use_gpu': self.use_gpu
            }
        )
    
    def _should_use_gpu(self, use_gpu: Optional[bool]) -> bool:
        """
        Determine if GPU should be used for video encoding.
        
        Args:
            use_gpu: Explicit GPU preference (None = auto-detect)
        
        Returns:
            True if GPU should be used, False otherwise
        """
        # If explicitly set, use that value
        if use_gpu is not None:
            return use_gpu
        
        # Auto-detect from environment
        return os.getenv('FFMPEG_USE_NVENC', 'false').lower() == 'true'
    
    def assemble_video(
        self,
        blueprint: Dict,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Assemble video from blueprint.
        
        Args:
            blueprint: Blueprint dictionary with video assembly instructions
            progress_callback: Optional callback(stage, progress, message)
        
        Returns:
            Path to the assembled video (local or GCS URL)
            
        Raises:
            VideoAssemblyError: If assembly fails
        """
        task_id = blueprint.get('task_id', 'unknown')
        
        logger.info(
            f"Starting video assembly",
            extra={
                'task_id': task_id,
                'moves_count': len(blueprint.get('moves', [])),
                'audio_path': blueprint.get('audio_path')
            }
        )
        
        try:
            # Step 1: Fetch media files (20-50% progress)
            if progress_callback:
                progress_callback('fetching', 20, 'Fetching media files from storage...')
            
            audio_file, video_files = self._fetch_media_files(blueprint)
            
            logger.info(
                f"Media files fetched",
                extra={
                    'task_id': task_id,
                    'audio_file': audio_file,
                    'video_files_count': len(video_files)
                }
            )
            
            # Step 2: Concatenate video clips (50-70% progress)
            if progress_callback:
                progress_callback('concatenating', 50, 'Concatenating video clips...')
            
            concatenated_video = self._concatenate_videos(video_files, blueprint)
            
            logger.info(
                f"Videos concatenated",
                extra={
                    'task_id': task_id,
                    'concatenated_video': concatenated_video
                }
            )
            
            # Step 3: Add audio track (70-85% progress)
            if progress_callback:
                progress_callback('adding_audio', 70, 'Adding audio track...')
            
            output_config = blueprint.get('output_config', {})
            final_video = self._add_audio_track(
                concatenated_video,
                audio_file,
                output_config
            )
            
            logger.info(
                f"Audio track added",
                extra={
                    'task_id': task_id,
                    'final_video': final_video
                }
            )
            
            # Step 4: Upload result (85-95% progress)
            if progress_callback:
                progress_callback('uploading', 85, 'Uploading result to storage...')
            
            result_url = self._upload_result(final_video, blueprint)
            
            logger.info(
                f"Video assembly completed",
                extra={
                    'task_id': task_id,
                    'result_url': result_url
                }
            )
            
            # Step 5: Cleanup (95-100% progress)
            if progress_callback:
                progress_callback('cleanup', 95, 'Cleaning up temporary files...')
            
            self._cleanup_temp_files()
            
            return result_url
            
        except Exception as e:
            logger.error(
                f"Video assembly failed: {str(e)}",
                extra={
                    'task_id': task_id,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            
            # Cleanup on error
            try:
                self._cleanup_temp_files()
            except Exception:
                pass
            
            raise VideoAssemblyError(f"Video assembly failed: {str(e)}") from e
    
    def _fetch_media_files(self, blueprint: Dict) -> Tuple[str, List[str]]:
        """
        Fetch audio and video files from storage.
        
        Uses parallel downloads for video clips to improve performance.
        Includes retry logic via storage service.
        
        Args:
            blueprint: Blueprint dictionary
            
        Returns:
            Tuple of (audio_file_path, list_of_video_file_paths)
            
        Raises:
            VideoAssemblyError: If fetching fails after retries
        """
        audio_path = blueprint.get('audio_path')
        moves = blueprint.get('moves', [])
        
        logger.info(
            f"Fetching media files",
            extra={
                'audio_path': audio_path,
                'video_clips_count': len(moves)
            }
        )
        
        # Fetch audio file with automatic retry via storage service
        audio_local_path = os.path.join(self.temp_dir, 'audio' + Path(audio_path).suffix)
        
        try:
            logger.debug(
                f"Downloading audio file",
                extra={
                    'source_path': audio_path,
                    'destination': audio_local_path
                }
            )
            
            self.storage.download_file(audio_path, audio_local_path)
            
            if not os.path.exists(audio_local_path):
                error_msg = f"Audio file not found after download: {audio_path}"
                logger.error(
                    error_msg,
                    extra={
                        'audio_path': audio_path,
                        'expected_local_path': audio_local_path
                    }
                )
                raise VideoAssemblyError(error_msg)
            
            # Verify file is not empty
            file_size = os.path.getsize(audio_local_path)
            if file_size == 0:
                error_msg = f"Downloaded audio file is empty: {audio_path}"
                logger.error(
                    error_msg,
                    extra={
                        'audio_path': audio_path,
                        'local_path': audio_local_path
                    }
                )
                raise VideoAssemblyError(error_msg)
            
            logger.info(
                f"Audio file downloaded successfully",
                extra={
                    'audio_path': audio_path,
                    'local_path': audio_local_path,
                    'file_size': file_size
                }
            )
            
        except VideoAssemblyError:
            # Re-raise our own errors
            raise
        except Exception as e:
            error_msg = f"Failed to fetch audio file '{audio_path}': {str(e)}"
            logger.error(
                error_msg,
                extra={
                    'audio_path': audio_path,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise VideoAssemblyError(error_msg) from e
        
        # Fetch video files in parallel using storage service's parallel download
        # Storage service includes automatic retry logic
        try:
            video_paths = [move.get('video_path') for move in moves]
            video_clips_dir = os.path.join(self.temp_dir, 'clips')
            
            logger.info(
                f"Starting parallel download of video clips",
                extra={
                    'video_clips_count': len(video_paths),
                    'max_workers': self.MAX_PARALLEL_DOWNLOADS
                }
            )
            
            video_files = self.storage.download_files_parallel(
                file_paths=video_paths,
                local_dir=video_clips_dir,
                max_workers=self.MAX_PARALLEL_DOWNLOADS
            )
            
            # Verify all video files exist and are not empty
            for idx, video_file in enumerate(video_files):
                if not os.path.exists(video_file):
                    error_msg = f"Video clip {idx} not found after download: {video_paths[idx]}"
                    logger.error(
                        error_msg,
                        extra={
                            'clip_index': idx,
                            'source_path': video_paths[idx],
                            'expected_local_path': video_file
                        }
                    )
                    raise VideoAssemblyError(error_msg)
                
                file_size = os.path.getsize(video_file)
                if file_size == 0:
                    error_msg = f"Video clip {idx} is empty: {video_paths[idx]}"
                    logger.error(
                        error_msg,
                        extra={
                            'clip_index': idx,
                            'source_path': video_paths[idx],
                            'local_path': video_file
                        }
                    )
                    raise VideoAssemblyError(error_msg)
            
            logger.info(
                f"All media files fetched successfully",
                extra={
                    'audio_file': audio_local_path,
                    'video_files_count': len(video_files),
                    'total_size': sum(os.path.getsize(f) for f in video_files) + os.path.getsize(audio_local_path)
                }
            )
            
            return audio_local_path, video_files
            
        except VideoAssemblyError:
            # Re-raise our own errors
            raise
        except Exception as e:
            error_msg = f"Failed to fetch video clips: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    'video_clips_count': len(video_paths),
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise VideoAssemblyError(error_msg) from e
    
    def _normalize_clip_framerates(self, video_files: List[str]) -> List[str]:
        """
        Normalize all video clips to exactly 30 fps.
        
        This pre-processing step is CRITICAL for smooth playback when concatenating
        many clips with mixed frame rates (29.97 fps vs 30 fps).
        
        Uses GPU acceleration if available for 6-8x speedup.
        
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
        
        encoding_type = "GPU (NVENC)" if (self.ffmpeg_builder and self.ffmpeg_builder.use_gpu) else "CPU"
        logger.info(f"Normalizing {len(video_files)} clips to 30 fps using {encoding_type}...")
        
        for idx, video_file in enumerate(video_files):
            output_file = os.path.join(normalized_dir, f'normalized_{idx:04d}.mp4')
            
            # Build FFmpeg command using builder (GPU or CPU)
            if self.ffmpeg_builder:
                ffmpeg_cmd = self.ffmpeg_builder.build_normalize_command(
                    input_file=video_file,
                    output_file=output_file,
                    frame_rate=self.DEFAULT_FRAME_RATE
                )
            else:
                # Fallback to CPU command if builder not available
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-i', video_file,
                    '-c:v', 'libx264',
                    '-r', '30',
                    '-preset', 'ultrafast',
                    '-crf', '18',
                    '-pix_fmt', 'yuv420p',
                    '-an',
                    '-y',
                    output_file
                ]
            
            try:
                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60  # 1 minute per clip
                )
                
                if not os.path.exists(output_file):
                    raise VideoAssemblyError(f"Normalized clip {idx} not created")
                
                normalized_files.append(output_file)
                
                if (idx + 1) % 10 == 0:
                    logger.info(f"Normalized {idx + 1}/{len(video_files)} clips")
                
            except subprocess.TimeoutExpired:
                error_msg = f"Normalization timed out for clip {idx}"
                logger.error(error_msg)
                
                # Try CPU fallback if GPU failed
                if self.ffmpeg_builder and self.ffmpeg_builder.use_gpu:
                    logger.info(f"Retrying clip {idx} with CPU encoding...")
                    try:
                        normalized_files.append(
                            self._normalize_clip_cpu_fallback(video_file, output_file, idx)
                        )
                        continue
                    except Exception:
                        pass
                
                raise VideoAssemblyError(error_msg)
            except subprocess.CalledProcessError as e:
                error_msg = f"FFmpeg normalization failed for clip {idx}: {e.stderr[-500:] if e.stderr else ''}"
                logger.error(error_msg)
                
                # Try CPU fallback if GPU failed
                if self.ffmpeg_builder and self.ffmpeg_builder.use_gpu:
                    logger.info(f"Retrying clip {idx} with CPU encoding...")
                    try:
                        normalized_files.append(
                            self._normalize_clip_cpu_fallback(video_file, output_file, idx)
                        )
                        continue
                    except Exception:
                        pass
                
                raise VideoAssemblyError(error_msg)
        
        logger.info(f"All {len(normalized_files)} clips normalized successfully using {encoding_type}")
        return normalized_files
    
    def _normalize_clip_cpu_fallback(self, video_file: str, output_file: str, idx: int) -> str:
        """
        Fallback to CPU encoding for a single clip.
        
        Args:
            video_file: Input video file
            output_file: Output video file
            idx: Clip index for logging
        
        Returns:
            Path to normalized file
        
        Raises:
            VideoAssemblyError: If CPU fallback also fails
        """
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_file,
            '-c:v', 'libx264',
            '-r', '30',
            '-preset', 'ultrafast',
            '-crf', '18',
            '-pix_fmt', 'yuv420p',
            '-an',
            '-y',
            output_file
        ]
        
        try:
            subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )
            
            if not os.path.exists(output_file):
                raise VideoAssemblyError(f"CPU fallback: Normalized clip {idx} not created")
            
            logger.info(f"Clip {idx} normalized successfully with CPU fallback")
            return output_file
            
        except Exception as e:
            error_msg = f"CPU fallback also failed for clip {idx}: {str(e)}"
            logger.error(error_msg)
            raise VideoAssemblyError(error_msg)

    def _concatenate_videos(self, video_files: List[str], blueprint: Dict) -> str:
        """
        Concatenate video clips using FFmpeg.
        
        Pre-processes each clip to normalize frame rate, then concatenates.
        This two-step approach ensures smooth playback with many clips.
        
        Args:
            video_files: List of local video file paths
            blueprint: Blueprint dictionary (for transition info)
            
        Returns:
            Path to concatenated video file
            
        Raises:
            VideoAssemblyError: If concatenation fails
        """
        logger.info(
            f"Concatenating video clips",
            extra={
                'video_clips_count': len(video_files)
            }
        )
        
        # Validate input files exist
        for idx, video_file in enumerate(video_files):
            if not os.path.exists(video_file):
                error_msg = f"Video file {idx} does not exist: {video_file}"
                logger.error(
                    error_msg,
                    extra={
                        'clip_index': idx,
                        'video_file': video_file
                    }
                )
                raise VideoAssemblyError(error_msg)
        
        # STEP 1: Pre-process clips to normalize frame rate
        # This is CRITICAL for smooth playback with many clips
        logger.info("Pre-processing clips to normalize frame rate to 30 fps...")
        normalized_files = self._normalize_clip_framerates(video_files)
        
        # STEP 2: Create concat file with normalized clips
        concat_file = os.path.join(self.temp_dir, 'concat.txt')
        
        try:
            with open(concat_file, 'w') as f:
                for video_file in normalized_files:
                    # FFmpeg concat format requires absolute paths
                    abs_path = os.path.abspath(video_file)
                    f.write(f"file '{abs_path}'\n")
            
            logger.debug(
                f"Concat file created",
                extra={
                    'concat_file': concat_file,
                    'video_count': len(video_files)
                }
            )
            
        except IOError as e:
            error_msg = f"Failed to create concat file: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    'concat_file': concat_file,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise VideoAssemblyError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error creating concat file: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise VideoAssemblyError(error_msg) from e
        
        # Output file for concatenated video
        output_file = os.path.join(self.temp_dir, 'concatenated.mp4')
        
        # STEP 3: Concatenate normalized clips
        # Since clips are already normalized to 30 fps, we can use copy codec
        # This is MUCH faster and produces smoother results than re-encoding
        if self.ffmpeg_builder:
            ffmpeg_cmd = self.ffmpeg_builder.build_concat_command(
                concat_file=concat_file,
                output_file=output_file
            )
        else:
            # Fallback command if builder not available
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',
                output_file
            ]
        
        logger.debug(
            f"Executing FFmpeg concatenation",
            extra={
                'command': ' '.join(ffmpeg_cmd),
                'input_file': concat_file,
                'output_file': output_file
            }
        )
        
        # Execute FFmpeg
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout
            )
            
            logger.debug(
                f"FFmpeg concatenation completed",
                extra={
                    'stdout_length': len(result.stdout),
                    'stderr_length': len(result.stderr)
                }
            )
            
            # Verify output file exists
            if not os.path.exists(output_file):
                error_msg = "Concatenated video file not created by FFmpeg"
                logger.error(
                    error_msg,
                    extra={
                        'expected_output': output_file,
                        'ffmpeg_stdout': result.stdout[-500:] if result.stdout else '',
                        'ffmpeg_stderr': result.stderr[-500:] if result.stderr else ''
                    }
                )
                raise VideoAssemblyError(error_msg)
            
            # Verify output file is not empty
            file_size = os.path.getsize(output_file)
            if file_size == 0:
                error_msg = "Concatenated video file is empty"
                logger.error(
                    error_msg,
                    extra={
                        'output_file': output_file
                    }
                )
                raise VideoAssemblyError(error_msg)
            
            logger.info(
                f"Videos concatenated successfully",
                extra={
                    'output_file': output_file,
                    'file_size': file_size
                }
            )
            
            return output_file
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"FFmpeg concatenation timed out after 300 seconds"
            logger.error(
                error_msg,
                extra={
                    'timeout': 300,
                    'video_clips_count': len(video_files)
                }
            )
            raise VideoAssemblyError(error_msg) from e
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg concatenation failed with exit code {e.returncode}"
            logger.error(
                error_msg,
                extra={
                    'returncode': e.returncode,
                    'stdout': e.stdout[-1000:] if e.stdout else '',
                    'stderr': e.stderr[-1000:] if e.stderr else '',
                    'command': ' '.join(ffmpeg_cmd)
                }
            )
            # Include stderr in error message for user
            raise VideoAssemblyError(
                f"{error_msg}: {e.stderr[-500:] if e.stderr else 'No error output'}"
            ) from e
        except FileNotFoundError as e:
            error_msg = "FFmpeg executable not found"
            logger.error(
                error_msg,
                extra={
                    'error_message': str(e)
                }
            )
            raise VideoAssemblyError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during video concatenation: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise VideoAssemblyError(error_msg) from e
    
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
        logger.info(
            f"Adding audio track to video",
            extra={
                'video_file': video_file,
                'audio_file': audio_file
            }
        )
        
        # Validate input files exist
        if not os.path.exists(video_file):
            error_msg = f"Video file does not exist: {video_file}"
            logger.error(error_msg)
            raise VideoAssemblyError(error_msg)
        
        if not os.path.exists(audio_file):
            error_msg = f"Audio file does not exist: {audio_file}"
            logger.error(error_msg)
            raise VideoAssemblyError(error_msg)
        
        # Output file for final video
        output_file = os.path.join(self.temp_dir, 'final_output.mp4')
        
        # Get output configuration with defaults
        video_codec = output_config.get('video_codec', self.DEFAULT_VIDEO_CODEC)
        audio_codec = output_config.get('audio_codec', self.DEFAULT_AUDIO_CODEC)
        video_bitrate = output_config.get('video_bitrate', self.DEFAULT_VIDEO_BITRATE)
        audio_bitrate = output_config.get('audio_bitrate', self.DEFAULT_AUDIO_BITRATE)
        
        logger.debug(
            f"Output configuration",
            extra={
                'video_codec': video_codec,
                'audio_codec': audio_codec,
                'video_bitrate': video_bitrate,
                'audio_bitrate': audio_bitrate
            }
        )
        
        # Build FFmpeg command using builder (GPU or CPU)
        if self.ffmpeg_builder:
            ffmpeg_cmd = self.ffmpeg_builder.build_add_audio_command(
                video_file=video_file,
                audio_file=audio_file,
                output_file=output_file,
                video_codec=video_codec,
                audio_codec=audio_codec,
                video_bitrate=video_bitrate,
                audio_bitrate=audio_bitrate
            )
        else:
            # Fallback command if builder not available
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', video_file,
                '-i', audio_file,
                '-c:v', video_codec,
                '-b:v', video_bitrate,
                '-c:a', audio_codec,
                '-b:a', audio_bitrate,
                '-shortest',
                '-y',
                output_file
            ]
        
        encoding_type = "GPU (NVENC)" if (self.ffmpeg_builder and self.ffmpeg_builder.use_gpu) else "CPU"
        logger.debug(
            f"Executing FFmpeg audio addition using {encoding_type}",
            extra={
                'command': ' '.join(ffmpeg_cmd),
                'video_input': video_file,
                'audio_input': audio_file,
                'output_file': output_file
            }
        )
        
        # Execute FFmpeg
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=600  # 10 minute timeout for encoding
            )
            
            logger.debug(
                f"FFmpeg audio addition completed",
                extra={
                    'stdout_length': len(result.stdout),
                    'stderr_length': len(result.stderr)
                }
            )
            
            # Verify output file exists
            if not os.path.exists(output_file):
                error_msg = "Final video file not created by FFmpeg"
                logger.error(
                    error_msg,
                    extra={
                        'expected_output': output_file,
                        'ffmpeg_stdout': result.stdout[-500:] if result.stdout else '',
                        'ffmpeg_stderr': result.stderr[-500:] if result.stderr else ''
                    }
                )
                raise VideoAssemblyError(error_msg)
            
            # Verify output file is not empty
            file_size = os.path.getsize(output_file)
            if file_size == 0:
                error_msg = "Final video file is empty"
                logger.error(
                    error_msg,
                    extra={
                        'output_file': output_file
                    }
                )
                raise VideoAssemblyError(error_msg)
            
            logger.info(
                f"Audio track added successfully",
                extra={
                    'output_file': output_file,
                    'file_size': file_size,
                    'video_codec': video_codec,
                    'audio_codec': audio_codec
                }
            )
            
            return output_file
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"FFmpeg audio addition timed out after 600 seconds"
            logger.error(
                error_msg,
                extra={
                    'timeout': 600,
                    'video_file': video_file,
                    'audio_file': audio_file
                }
            )
            raise VideoAssemblyError(error_msg) from e
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg audio addition failed with exit code {e.returncode}"
            logger.error(
                error_msg,
                extra={
                    'returncode': e.returncode,
                    'stdout': e.stdout[-1000:] if e.stdout else '',
                    'stderr': e.stderr[-1000:] if e.stderr else '',
                    'command': ' '.join(ffmpeg_cmd)
                }
            )
            # Include stderr in error message for user
            raise VideoAssemblyError(
                f"{error_msg}: {e.stderr[-500:] if e.stderr else 'No error output'}"
            ) from e
        except FileNotFoundError as e:
            error_msg = "FFmpeg executable not found"
            logger.error(
                error_msg,
                extra={
                    'error_message': str(e)
                }
            )
            raise VideoAssemblyError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error adding audio track: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise VideoAssemblyError(error_msg) from e
    
    def _upload_result(self, video_file: str, blueprint: Dict) -> str:
        """
        Upload final video to storage with retry logic.
        
        Storage service includes automatic retry with exponential backoff.
        
        Args:
            video_file: Path to final video file
            blueprint: Blueprint dictionary (for output path)
            
        Returns:
            URL or path to uploaded video
            
        Raises:
            VideoAssemblyError: If upload fails after retries
        """
        output_config = blueprint.get('output_config', {})
        output_path = output_config.get('output_path')
        
        if not output_path:
            error_msg = "No output_path specified in blueprint output_config"
            logger.error(
                error_msg,
                extra={
                    'output_config': output_config
                }
            )
            raise VideoAssemblyError(error_msg)
        
        # Validate video file exists and is not empty
        if not os.path.exists(video_file):
            error_msg = f"Video file does not exist: {video_file}"
            logger.error(error_msg)
            raise VideoAssemblyError(error_msg)
        
        file_size = os.path.getsize(video_file)
        if file_size == 0:
            error_msg = f"Video file is empty: {video_file}"
            logger.error(error_msg)
            raise VideoAssemblyError(error_msg)
        
        logger.info(
            f"Uploading result to storage",
            extra={
                'local_path': video_file,
                'destination_path': output_path,
                'file_size': file_size
            }
        )
        
        try:
            # Storage service includes automatic retry logic (3 retries with exponential backoff)
            result_url = self.storage.upload_file(
                local_path=video_file,
                destination_path=output_path,
                content_type='video/mp4'
            )
            
            logger.info(
                f"Result uploaded successfully",
                extra={
                    'result_url': result_url,
                    'output_path': output_path,
                    'file_size': file_size
                }
            )
            
            return result_url
            
        except Exception as e:
            error_msg = f"Failed to upload result to '{output_path}': {str(e)}"
            logger.error(
                error_msg,
                extra={
                    'local_path': video_file,
                    'destination_path': output_path,
                    'file_size': file_size,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise VideoAssemblyError(error_msg) from e
    
    def _cleanup_temp_files(self):
        """
        Clean up temporary files.
        
        Removes all files in the temp directory but keeps the directory itself.
        """
        try:
            import shutil
            
            if os.path.exists(self.temp_dir):
                # Remove all files in temp directory
                for item in os.listdir(self.temp_dir):
                    item_path = os.path.join(self.temp_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove {item_path}: {e}")
                
                logger.info(f"Temporary files cleaned up: {self.temp_dir}")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")
    
    def check_ffmpeg_available(self) -> bool:
        """
        Check if FFmpeg is available.
        
        Returns:
            True if FFmpeg is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"FFmpeg version: {result.stdout.split()[2]}")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("FFmpeg not found or not executable")
            return False
