"""
Local filesystem storage backend.

Stores files in the local filesystem, suitable for development and testing.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from .base import StorageBackend

logger = logging.getLogger(__name__)


class LocalStorageBackend(StorageBackend):
    """Storage backend using local filesystem"""
    
    def __init__(self, base_path: str = None, base_url: str = None):
        """
        Initialize local storage backend.
        
        Args:
            base_path: Base directory for file storage (defaults to media/)
            base_url: Base URL for accessing files (defaults to /media/)
        """
        self.base_path = Path(base_path) if base_path else Path("media")
        self.base_url = base_url or "/media/"
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"LocalStorageBackend initialized with base_path={self.base_path}")
    
    def _get_full_path(self, remote_path: str) -> Path:
        """Get full filesystem path for a remote path"""
        # Remove leading slashes and known prefixes if present
        clean_path = remote_path.lstrip('/')
        if clean_path.startswith('media/'):
            clean_path = clean_path[6:]
        elif clean_path.startswith('data/'):
            clean_path = clean_path[5:]
        
        return self.base_path / clean_path
    
    def _normalize_remote_path(self, remote_path: str) -> str:
        """Normalize remote path by removing prefixes"""
        clean_path = remote_path.lstrip('/')
        if clean_path.startswith('media/'):
            clean_path = clean_path[6:]
        elif clean_path.startswith('data/'):
            clean_path = clean_path[5:]
        return clean_path
    
    def upload_file(self, local_path: str, remote_path: str) -> str:
        """Upload a file to local storage"""
        try:
            full_path = self._get_full_path(remote_path)
            
            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file to destination
            shutil.copy2(local_path, full_path)
            
            logger.info(f"Uploaded {local_path} to {full_path}")
            
            # Return URL for accessing the file
            normalized_path = self._normalize_remote_path(remote_path)
            return urljoin(self.base_url, normalized_path)
            
        except Exception as e:
            logger.error(f"Failed to upload file {local_path} to {remote_path}: {e}")
            raise
    
    def download_file(self, remote_path: str, local_path: str) -> str:
        """Download a file from local storage"""
        try:
            full_path = self._get_full_path(remote_path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {remote_path}")
            
            # Create parent directories for destination if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file to destination
            shutil.copy2(full_path, local_path)
            
            logger.info(f"Downloaded {full_path} to {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download file {remote_path} to {local_path}: {e}")
            raise
    
    def get_url(self, remote_path: str, expiration: int = 3600) -> str:
        """Get URL for accessing a file (expiration not used for local storage)"""
        normalized_path = self._normalize_remote_path(remote_path)
        url = urljoin(self.base_url, normalized_path)
        logger.debug(f"Generated URL for {remote_path}: {url}")
        return url
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in local storage"""
        try:
            full_path = self._get_full_path(remote_path)
            exists = full_path.exists() and full_path.is_file()
            logger.debug(f"File existence check for {remote_path}: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check file existence for {remote_path}: {e}")
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from local storage"""
        try:
            full_path = self._get_full_path(remote_path)
            
            if not full_path.exists():
                logger.warning(f"File not found for deletion: {remote_path}")
                return False
            
            full_path.unlink()
            logger.info(f"Deleted file: {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {remote_path}: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> list[str]:
        """List files in local storage with optional prefix filter"""
        try:
            search_path = self._get_full_path(prefix) if prefix else self.base_path
            
            if not search_path.exists():
                return []
            
            files = []
            if search_path.is_file():
                # If prefix points to a file, return just that file
                files = [self._normalize_remote_path(prefix)]
            else:
                # List all files recursively under the path
                for file_path in search_path.rglob('*'):
                    if file_path.is_file():
                        # Get relative path from base_path
                        rel_path = file_path.relative_to(self.base_path)
                        files.append(str(rel_path))
            
            logger.debug(f"Listed {len(files)} files with prefix '{prefix}'")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files with prefix '{prefix}': {e}")
            return []
