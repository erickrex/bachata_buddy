"""
FFmpeg Command Builder

Encapsulates FFmpeg command generation for CPU-based video encoding.
Provides a clean interface for building FFmpeg commands.

Features:
- CPU-based encoding with libx264
- Consistent command structure
- Comprehensive logging
"""

import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class FFmpegCommandBuilder:
    """
    Builder for FFmpeg commands with CPU-based encoding.
    
    This class encapsulates the complexity of FFmpeg command generation,
    providing methods for common video operations using CPU-based encoding.
    """
    
    # Default encoding settings
    DEFAULT_FRAME_RATE = 30
    DEFAULT_VIDEO_BITRATE = '2M'
    DEFAULT_AUDIO_BITRATE = '128k'
    DEFAULT_CRF = 23  # Constant Rate Factor for quality
    
    # CPU encoding presets
    CPU_PRESET = 'ultrafast'  # For speed during normalization
    CPU_PRESET_FINAL = 'medium'  # For final output quality
    
    def __init__(self):
        """
        Initialize FFmpeg command builder (CPU-only).
        """
        logger.info("FFmpegCommandBuilder initialized (CPU-only)")
    
    def build_normalize_command(
        self,
        input_file: str,
        output_file: str,
        frame_rate: int = DEFAULT_FRAME_RATE
    ) -> List[str]:
        """
        Build FFmpeg command for normalizing video frame rate.
        
        Uses libx264 with ultrafast preset for speed.
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            frame_rate: Target frame rate (default: 30)
        
        Returns:
            List of command arguments for subprocess
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
        
        logger.debug(f"Built normalize command: {' '.join(cmd)}")
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
        video_codec: str = 'libx264',
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
            video_codec: Video codec (default: libx264)
            audio_codec: Audio codec (default: aac)
            video_bitrate: Video bitrate (default: 2M)
            audio_bitrate: Audio bitrate (default: 128k)
        
        Returns:
            List of command arguments for subprocess
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
        
        logger.debug(f"Built add audio command: {' '.join(cmd)}")
        return cmd
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the FFmpeg builder configuration.
        
        Returns:
            Dictionary with configuration info
        """
        return {
            'use_gpu': False,
            'gpu_available': False,
            'cpu_preset': self.CPU_PRESET,
        }
