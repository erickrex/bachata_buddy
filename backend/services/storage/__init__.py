"""
Storage abstraction layer for Bachata Buddy.

Provides a unified interface for file storage operations that works with
both local filesystem and cloud storage (AWS S3).
"""

from .factory import get_storage_backend

__all__ = ['get_storage_backend']
