"""
Services package for blueprint-based video assembly job

This package contains service modules for:
- Blueprint parsing and validation
- Video assembly with FFmpeg
- Database operations (status updates)
- Storage operations (local/S3)
"""

from .blueprint_parser import BlueprintParser, BlueprintValidationError
from .video_assembler import VideoAssembler, VideoAssemblyError
from .database import update_task_status, close_connection_pool
from .storage import (
    StorageBackend,
    LocalStorageBackend,
    S3StorageBackend,
    get_storage_backend,
    reset_storage_backend
)

__all__ = [
    # Blueprint
    "BlueprintParser",
    "BlueprintValidationError",
    # Video Assembly
    "VideoAssembler",
    "VideoAssemblyError",
    # Database
    "update_task_status",
    "close_connection_pool",
    # Storage
    "StorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "get_storage_backend",
    "reset_storage_backend",
]
