"""
Abstract base class for storage backends.

Defines the interface that all storage backends must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> str:
        """
        Upload a file to storage.
        
        Args:
            local_path: Path to the local file to upload
            remote_path: Destination path in storage
            
        Returns:
            Public URL or path to access the uploaded file
            
        Raises:
            Exception: If upload fails
        """
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> str:
        """
        Download a file from storage.
        
        Args:
            remote_path: Path to the file in storage
            local_path: Destination path for the downloaded file
            
        Returns:
            Path to the downloaded local file
            
        Raises:
            Exception: If download fails
        """
        pass
    
    @abstractmethod
    def get_url(self, remote_path: str, expiration: int = 3600) -> str:
        """
        Get an accessible URL for a file.
        
        Args:
            remote_path: Path to the file in storage
            expiration: URL expiration time in seconds (for signed URLs)
            
        Returns:
            URL to access the file
            
        Raises:
            Exception: If URL generation fails
        """
        pass
    
    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            remote_path: Path to the file in storage
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            remote_path: Path to the file in storage
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = "") -> list[str]:
        """
        List files in storage with optional prefix filter.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List of file paths
        """
        pass
