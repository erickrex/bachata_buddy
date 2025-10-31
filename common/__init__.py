"""
Common app - Shared utilities and configuration.

This app contains truly shared utilities used across all other apps,
including configuration management, exception handling, and resource management.
"""

# Configuration
from .config.environment_config import (
    EnvironmentConfig,
    ElasticsearchConfig,
    YOLOv8Config,
)

# Exceptions
from .exceptions import (
    ChoreographyGenerationError,
    YouTubeDownloadError,
    MusicAnalysisError,
    MoveAnalysisError,
    VideoGenerationError,
    ValidationError,
    ResourceError,
    ServiceUnavailableError,
    get_user_friendly_message,
    ERROR_MESSAGES,
)

# Services
from .services import (
    ResourceManager,
    resource_manager,
    TempFileManager,
    temp_file_manager,
    PerformanceMonitor,
    DirectoryOrganizer,
)

__all__ = [
    # Configuration
    'EnvironmentConfig',
    'ElasticsearchConfig',
    'YOLOv8Config',
    # Exceptions
    'ChoreographyGenerationError',
    'YouTubeDownloadError',
    'MusicAnalysisError',
    'MoveAnalysisError',
    'VideoGenerationError',
    'ValidationError',
    'ResourceError',
    'ServiceUnavailableError',
    'get_user_friendly_message',
    'ERROR_MESSAGES',
    # Services
    'ResourceManager',
    'resource_manager',
    'TempFileManager',
    'temp_file_manager',
    'PerformanceMonitor',
    'DirectoryOrganizer',
]
