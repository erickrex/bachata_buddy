"""
FFmpeg Command Builder

Encapsulates FFmpeg command generation for both CPU and GPU encoding.
Provides a clean interface for building FFmpeg commands with automatic
GPU detection and CPU fallback.

Features:
- GPU-accelerated encoding with NVENC (h264_nvenc)
- Hardware-accelerated decoding with CUDA
- CPU fallback for compatibility
- Consistent command structure
- Comprehensive logging
"""

import os
import logging
import subprocess
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class FFmpegCommandBuilder:
    """
    Builder for FFmpeg commands with GPU/CPU support.
    
    This class encapsulates the complexity of FFmpeg command generation,
    providing methods for common video operations with automatic GPU
    detection and CPU fallback.
    """
    
    # Default encoding settings
    DEFAULT_FRAME_RATE = 30
    DEFAULT_VIDEO_BITRATE = '2M'
    DEFAULT_AUDIO_BITRATE = '128k'
    DEFAULT_CRF = 23  # Constant Rate Factor for quality
    
    # GPU encoding presets (NVENC)
    GPU_PRESET = 'p4'  # p1-p7, p4 is balanced speed/quality
    
    # CPU encoding presets
    CPU_PRESET = 'ultrafast'  # For speed during normalization
    CPU_PRESET_FINAL = 'medium'  # For final output quality
    
    def __init__(self, use_gpu: Optional[bool] = None):
        """
        Initialize FFmpeg command builder.
        
        Args:
            use_gpu: Whether to use GPU acceleration (None = auto-detect)
        """
        self.use_gpu = self._should_use_gpu(use_gpu)
        self.gpu_available = self._check_nvenc_available() if self.use_gpu else False
        
        # If GPU was requested but not available, fall back to CPU
        if self.use_gpu and not self.gpu_available:
            logger.warning("GPU requested but NVENC not available, falling back to CPU")
            self.use_gpu = False
        
        logger.info(
            f"FFmpegCommandBuilder initialized (GPU: {self.use_gpu}, "
            f"NVENC available: {self.gpu_available})"
        )
    
    def _should_use_gpu(self, use_gpu: Optional[bool]) -> bool:
        """
        Determine if GPU should be used for FFmpeg.
        
        Args:
            use_gpu: Explicit GPU preference (None = auto-detect)
        
        Returns:
            True if GPU should be used, False otherwise
        """
        # If explicitly set, use that value
        if use_gpu is not None:
            return use_gpu
        
        # Auto-detect from configuration
        try:
            # Import here to avoid circular dependencies
            import sys
            sys.path.insert(0, '/app')
            from backend.services.gpu_utils import GPUConfig
            
            config = GPUConfig()
            if not config.ffmpeg_gpu:
                logger.debug("FFmpeg GPU disabled in configuration")
                return False
            
            logger.info("FFmpeg GPU enabled in configuration")
            return True
            
        except Exception as e:
            logger.warning(f"Error checking GPU configuration: {e}")
            # Check environment variable as fallback
            return os.getenv('FFMPEG_USE_NVENC', 'false').lower() == 'true'
    
    def _check_nvenc_available(self) -> bool:
        """
        Check if NVENC is available via FFmpeg.
        
        Returns:
            True if NVENC encoder is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-encoders'],
                capture_output=True,
                text=True,
                timeout=5
            )
            available = 'h264_nvenc' in result.stdout
            if available:
                logger.info("NVENC encoder detected in FFmpeg")
            else:
                logger.info("NVENC encoder not available in FFmpeg")
            return available
            
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg encoder check timed out")
            return False
        except FileNotFoundError:
            logger.warning("FFmpeg not found in PATH")
            return False
        except Exception as e:
            logger.warning(f"Error checking NVENC availability: {e}")
            return False
    
    def build_normalize_command(
        self,
        input_file: str,
        output_file: str,
        frame_rate: int = DEFAULT_FRAME_RATE
    ) -> List[str]:
        """
        Build FFmpeg command for normalizing video frame rate.
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            frame_rate: Target frame rate (default: 30)
        
        Returns:
            List of command arguments for subprocess
        """
        if self.use_gpu and self.gpu_available:
            return self._build_gpu_normalize_command(input_file, output_file, frame_rate)
        else:
            return self._build_cpu_normalize_command(input_file, output_file, frame_rate)
    
    def _build_gpu_normalize_command(
        self,
        input_file: str,
        output_file: str,
        frame_rate: int
    ) -> List[str]:
        """
        Build GPU-accelerated normalization command.
        
        Uses hardware-accelerated decoding and NVENC encoding.
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            frame_rate: Target frame rate
        
        Returns:
            FFmpeg command as list
        """
        cmd = [
            'ffmpeg',
            '-hwaccel', 'cuda',  # Hardware-accelerated decoding
            '-hwaccel_output_format', 'cuda',  # Keep frames on GPU
            '-i', input_file,
            '-c:v', 'h264_nvenc',  # NVENC encoder
            '-preset', self.GPU_PRESET,  # NVENC preset
            '-r', str(frame_rate),  # Target frame rate
            '-pix_fmt', 'yuv420p',  # Pixel format
            '-an',  # No audio
            '-y',  # Overwrite output
            output_file
        ]
        
        logger.debug(f"Built GPU normalize command: {' '.join(cmd)}")
        return cmd
    
    def _build_cpu_normalize_command(
        self,
        input_file: str,
        output_file: str,
        frame_rate: int
    ) -> List[str]:
        """
        Build CPU normalization command.
        
        Uses libx264 with ultrafast preset for speed.
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            frame_rate: Target frame rate
        
        Returns:
            FFmpeg command as list
        """
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-c:v', 'libx264',  # CPU encoder
            '-preset', self.CPU_PRESET,  # Fast preset
            '-r', str(frame_rate),  # Target frame rate
            '-crf', '18',  # High quality
            '-pix_fmt', 'yuv420p',  # Pixel format
            '-an',  # No audio
            '-y',  # Overwrite output
            output_file
        ]
        
        logger.debug(f"Built CPU normalize command: {' '.join(cmd)}")
        return cmd
    
    def build_concat_command(
        self,
        concat_file: str,
        output_file: str
    ) -> List[str]:
        """
        Build FFmpeg command for concatenating videos.
        
        Since videos are pre-normalized, we can use copy codec for speed.
        
        Args:
            concat_file: Path to concat.txt file
            output_file: Output video file path
        
        Returns:
            List of command arguments for subprocess
        """
        # For concatenation, we use copy codec regardless of GPU
        # since the clips are already encoded
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',  # Copy codec - no re-encoding
            '-y',  # Overwrite output
            output_file
        ]
        
        logger.debug(f"Built concat command: {' '.join(cmd)}")
        return cmd
    
    def build_add_audio_command(
        self,
        video_file: str,
        audio_file: str,
        output_file: str,
        video_codec: Optional[str] = None,
        audio_codec: str = 'aac',
        video_bitrate: str = DEFAULT_VIDEO_BITRATE,
        audio_bitrate: str = DEFAULT_AUDIO_BITRATE
    ) -> List[str]:
        """
        Build FFmpeg command for adding audio to video.
        
        Args:
            video_file: Input video file path
            audio_file: Input audio file path
            output_file: Output video file path
            video_codec: Video codec (None = auto-select based on GPU)
            audio_codec: Audio codec (default: aac)
            video_bitrate: Video bitrate (default: 2M)
            audio_bitrate: Audio bitrate (default: 128k)
        
        Returns:
            List of command arguments for subprocess
        """
        if self.use_gpu and self.gpu_available:
            return self._build_gpu_add_audio_command(
                video_file, audio_file, output_file,
                audio_codec, video_bitrate, audio_bitrate
            )
        else:
            return self._build_cpu_add_audio_command(
                video_file, audio_file, output_file,
                video_codec or 'libx264',
                audio_codec, video_bitrate, audio_bitrate
            )
    
    def _build_gpu_add_audio_command(
        self,
        video_file: str,
        audio_file: str,
        output_file: str,
        audio_codec: str,
        video_bitrate: str,
        audio_bitrate: str
    ) -> List[str]:
        """
        Build GPU-accelerated audio addition command.
        
        Args:
            video_file: Input video file path
            audio_file: Input audio file path
            output_file: Output video file path
            audio_codec: Audio codec
            video_bitrate: Video bitrate
            audio_bitrate: Audio bitrate
        
        Returns:
            FFmpeg command as list
        """
        cmd = [
            'ffmpeg',
            '-hwaccel', 'cuda',  # Hardware-accelerated decoding
            '-i', video_file,
            '-i', audio_file,
            '-c:v', 'h264_nvenc',  # NVENC encoder
            '-preset', self.GPU_PRESET,  # NVENC preset
            '-b:v', video_bitrate,  # Video bitrate
            '-c:a', audio_codec,  # Audio codec
            '-b:a', audio_bitrate,  # Audio bitrate
            '-shortest',  # Match shortest input
            '-y',  # Overwrite output
            output_file
        ]
        
        logger.debug(f"Built GPU add audio command: {' '.join(cmd)}")
        return cmd
    
    def _build_cpu_add_audio_command(
        self,
        video_file: str,
        audio_file: str,
        output_file: str,
        video_codec: str,
        audio_codec: str,
        video_bitrate: str,
        audio_bitrate: str
    ) -> List[str]:
        """
        Build CPU audio addition command.
        
        Args:
            video_file: Input video file path
            audio_file: Input audio file path
            output_file: Output video file path
            video_codec: Video codec
            audio_codec: Audio codec
            video_bitrate: Video bitrate
            audio_bitrate: Audio bitrate
        
        Returns:
            FFmpeg command as list
        """
        cmd = [
            'ffmpeg',
            '-i', video_file,
            '-i', audio_file,
            '-c:v', video_codec,  # CPU encoder
            '-b:v', video_bitrate,  # Video bitrate
            '-c:a', audio_codec,  # Audio codec
            '-b:a', audio_bitrate,  # Audio bitrate
            '-shortest',  # Match shortest input
            '-y',  # Overwrite output
            output_file
        ]
        
        logger.debug(f"Built CPU add audio command: {' '.join(cmd)}")
        return cmd
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the FFmpeg builder configuration.
        
        Returns:
            Dictionary with configuration info
        """
        return {
            'use_gpu': self.use_gpu,
            'gpu_available': self.gpu_available,
            'gpu_preset': self.GPU_PRESET if self.use_gpu else None,
            'cpu_preset': self.CPU_PRESET if not self.use_gpu else None,
        }
