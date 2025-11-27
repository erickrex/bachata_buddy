"""
Storage Service

Provides a unified interface for file storage operations using the storage
abstraction layer. This service wraps the storage backend and provides
backward compatibility with the old GCS-based interface.
"""
import logging
from typing import Optional

from .storage.factory import get_storage_backend

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service for managing file storage.
    
    This class provides a backward-compatible interface while using the
    new storage abstraction layer underneath. It delegates all operations
    to the configured storage backend (local or S3).
    """
    
    def __init__(self):
        """Initialize storage service with the configured backend"""
        self.backend = get_storage_backend()
        logger.info(f"StorageService initialized with backend: {type(self.backend).__name__}")
    
    def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """
        Upload a file to storage.
        
        Args:
            local_path: Path to the local file to upload
            remote_path: Destination path in storage (supports legacy GCS paths)
            
        Returns:
            URL to access the uploaded file, or None on failure
        """
        try:
            url = self.backend.upload_file(local_path, remote_path)
            logger.info(f"Uploaded {local_path} to {remote_path}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload file {local_path}: {e}")
            return None
    
    def download_file(self, remote_path: str, local_path: str) -> Optional[str]:
        """
        Download a file from storage.
        
        Args:
            remote_path: Path to the file in storage (supports legacy GCS paths)
            local_path: Destination path for the downloaded file
            
        Returns:
            Path to the downloaded file, or None on failure
        """
        try:
            result = self.backend.download_file(remote_path, local_path)
            logger.info(f"Downloaded {remote_path} to {local_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to download file {remote_path}: {e}")
            return None
    
    def get_signed_url(self, remote_path: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a URL for accessing a file.
        
        Args:
            remote_path: Path to the file in storage (supports legacy GCS paths)
            expiration: URL expiration time in seconds (for signed URLs)
            
        Returns:
            URL to access the file, or None on failure
        """
        try:
            url = self.backend.get_url(remote_path, expiration)
            return url
        except Exception as e:
            logger.error(f"Failed to generate URL for {remote_path}: {e}")
            return None
    
    def get_url(self, remote_path: str, expiration: int = 3600) -> Optional[str]:
        """
        Alias for get_signed_url for backward compatibility.
        
        Args:
            remote_path: Path to the file in storage
            expiration: URL expiration time in seconds
            
        Returns:
            URL to access the file, or None on failure
        """
        return self.get_signed_url(remote_path, expiration)
    
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            remote_path: Path to the file in storage (supports legacy GCS paths)
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            return self.backend.file_exists(remote_path)
        except Exception as e:
            logger.error(f"Failed to check file existence for {remote_path}: {e}")
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            remote_path: Path to the file in storage (supports legacy GCS paths)
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            return self.backend.delete_file(remote_path)
        except Exception as e:
            logger.error(f"Failed to delete file {remote_path}: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> list[str]:
        """
        List files in storage with optional prefix filter.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List of file paths
        """
        try:
            return self.backend.list_files(prefix)
        except Exception as e:
            logger.error(f"Failed to list files with prefix '{prefix}': {e}")
            return []
