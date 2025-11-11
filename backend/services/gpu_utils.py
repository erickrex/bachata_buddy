"""
GPU Utilities

Centralized GPU detection, configuration, and monitoring.
Provides consistent GPU availability checks across all services.
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class GPUConfig:
    """GPU configuration singleton."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._load_config()
            GPUConfig._initialized = True
    
    def _load_config(self):
        """Load GPU configuration from environment."""
        # Global GPU enable/disable
        self.enabled = os.getenv('USE_GPU', 'false').lower() == 'true'
        
        # Per-service GPU flags
        self.faiss_gpu = os.getenv('FAISS_USE_GPU', str(self.enabled)).lower() == 'true'
        self.ffmpeg_gpu = os.getenv('FFMPEG_USE_NVENC', str(self.enabled)).lower() == 'true'
        self.audio_gpu = os.getenv('AUDIO_USE_GPU', str(self.enabled)).lower() == 'true'
        
        # GPU memory settings
        self.memory_fraction = float(os.getenv('GPU_MEMORY_FRACTION', '0.8'))
        
        # Fallback settings
        self.fallback_enabled = os.getenv('GPU_FALLBACK_ENABLED', 'true').lower() == 'true'
        self.timeout_seconds = int(os.getenv('GPU_TIMEOUT_SECONDS', '30'))
        
        logger.info(
            f"GPU Config loaded: enabled={self.enabled}, "
            f"faiss={self.faiss_gpu}, ffmpeg={self.ffmpeg_gpu}, audio={self.audio_gpu}"
        )


def check_cuda_available() -> bool:
    """
    Check if CUDA is available.
    
    Returns:
        bool: True if CUDA is available and functional, False otherwise.
    """
    try:
        import torch
        available = torch.cuda.is_available()
        if available:
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            logger.info(f"CUDA available: {device_count} device(s), primary: {device_name}")
        else:
            logger.info("CUDA not available")
        return available
    except ImportError:
        logger.debug("PyTorch not available, CUDA check skipped")
        return False
    except Exception as e:
        logger.warning(f"Error checking CUDA availability: {e}")
        return False


def check_faiss_gpu_available() -> bool:
    """
    Check if FAISS GPU is available.
    
    Returns:
        bool: True if FAISS GPU is available, False otherwise.
    """
    try:
        import faiss
        gpu_count = faiss.get_num_gpus()
        available = gpu_count > 0
        if available:
            logger.info(f"FAISS GPU available: {gpu_count} device(s)")
        else:
            logger.info("FAISS GPU not available")
        return available
    except ImportError:
        logger.debug("FAISS not available")
        return False
    except AttributeError:
        # faiss-cpu doesn't have get_num_gpus
        logger.debug("FAISS CPU version detected (no GPU support)")
        return False
    except Exception as e:
        logger.warning(f"Error checking FAISS GPU: {e}")
        return False


def check_nvenc_available() -> bool:
    """
    Check if NVENC is available via FFmpeg.
    
    Returns:
        bool: True if FFmpeg has NVENC encoder support, False otherwise.
    """
    import subprocess
    try:
        result = subprocess.run(
            ['ffmpeg', '-encoders'],
            capture_output=True,
            text=True,
            timeout=5
        )
        available = 'h264_nvenc' in result.stdout
        if available:
            logger.info("NVENC available via FFmpeg")
        else:
            logger.info("NVENC not available via FFmpeg")
        return available
    except subprocess.TimeoutExpired:
        logger.warning("FFmpeg encoder check timed out")
        return False
    except FileNotFoundError:
        logger.warning("FFmpeg not found in PATH")
        return False
    except Exception as e:
        logger.warning(f"Error checking NVENC: {e}")
        return False


def get_gpu_info() -> Dict[str, Any]:
    """
    Get comprehensive GPU information.
    
    Returns:
        Dict[str, Any]: Dictionary containing GPU availability and configuration info.
    """
    info = {
        'cuda_available': check_cuda_available(),
        'faiss_gpu_available': check_faiss_gpu_available(),
        'nvenc_available': check_nvenc_available(),
        'config': {}
    }
    
    # Add config info
    try:
        config = GPUConfig()
        info['config'] = {
            'enabled': config.enabled,
            'faiss_gpu': config.faiss_gpu,
            'ffmpeg_gpu': config.ffmpeg_gpu,
            'audio_gpu': config.audio_gpu,
            'memory_fraction': config.memory_fraction,
            'fallback_enabled': config.fallback_enabled,
            'timeout_seconds': config.timeout_seconds
        }
    except Exception as e:
        logger.warning(f"Error loading GPU config: {e}")
    
    # Add CUDA device info if available
    if info['cuda_available']:
        try:
            import torch
            info['cuda_version'] = torch.version.cuda
            info['device_count'] = torch.cuda.device_count()
            info['device_name'] = torch.cuda.get_device_name(0)
            info['memory_allocated'] = torch.cuda.memory_allocated(0)
            info['memory_reserved'] = torch.cuda.memory_reserved(0)
        except Exception as e:
            logger.warning(f"Error getting CUDA info: {e}")
    
    return info
