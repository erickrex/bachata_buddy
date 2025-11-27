"""
Storage abstraction layer for the job container.

Provides a unified interface for file storage operations that works with
both local filesystem and AWS S3.
"""

from .base import StorageBackend
from .local import LocalStorageBackend
from .s3 import S3StorageBackend
from .factory import get_storage_backend, reset_storage_backend

__all__ = [
    'StorageBackend',
    'LocalStorageBackend',
    'S3StorageBackend',
    'get_storage_backend',
    'reset_storage_backend',
]
