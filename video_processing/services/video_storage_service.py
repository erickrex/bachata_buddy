"""
Video Storage Service

Unified interface for accessing videos from both local filesystem and Google Cloud Storage.
Automatically detects environment and uses appropriate storage backend.

This service ensures training videos work in both:
- Local development (reads from data/Bachata_steps)
- Cloud Run production (reads from GCS)
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class VideoStorageService:
    """
    Unified video storage service supporting local and GCS backends.
    
    Usage:
        storage = VideoStorageService()
        
        # Get local path (downloads from GCS if needed)
        local_path = storage.get_local_path("training_videos/basic/basic_1.mp4")
        
        # Check if video exists
        exists = storage.exists("training_videos/basic/basic_1.mp4")
    """
    
    def __init__(self):
        """Initialize storage service based on environment."""
        self.use_gcs = os.environ.get('GCS_BUCKET_NAME') and os.environ.get('ENVIRONMENT') == 'cloud'
        
        if self.use_gcs:
            self.bucket_name = os.environ.get('GCS_BUCKET_NAME')
            self.gcp_project_id = os.environ.get('GCP_PROJECT_ID')
            
            # Initialize GCS client
            try:
                from google.cloud import storage
                self.storage_client = storage.Client(project=self.gcp_project_id)
                self.bucket = self.storage_client.bucket(self.bucket_name)
                logger.info(f"✅ GCS storage initialized: gs://{self.bucket_name}/")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise
        else:
            # Local development
            self.local_base_dir = Path('data')
            logger.info(f"✅ Local storage initialized: {self.local_base_dir}/")
        
        # Cache for downloaded files (in Cloud Run)
        self._download_cache = {}
    
    def is_gcs_url(self, path: str) -> bool:
        """
        Check if path is a GCS URL.
        
        Args:
            path: File path or URL
            
        Returns:
            True if GCS URL, False otherwise
        """
        return path.startswith('https://storage.googleapis.com/') or path.startswith('gs://')
    
    def normalize_path(self, path: str) -> str:
        """
        Normalize video path for current environment.
        
        Args:
            path: Video path (local or GCS URL)
            
        Returns:
            Normalized path for current environment
        """
        # If already a GCS URL and we're using GCS, return as-is
        if self.is_gcs_url(path) and self.use_gcs:
            return path
        
        # If local path and we're local, normalize it
        if not self.is_gcs_url(path) and not self.use_gcs:
            # Remove 'data/' prefix if present
            normalized = path.replace('data/', '')
            return str(self.local_base_dir / normalized)
        
        # Otherwise, return as-is and let get_local_path handle it
        return path
    
    def exists(self, path: str) -> bool:
        """
        Check if video exists in storage.
        
        Args:
            path: Video path (local or GCS URL)
            
        Returns:
            True if exists, False otherwise
        """
        try:
            if self.is_gcs_url(path):
                # Extract blob name from URL
                blob_name = self._extract_blob_name(path)
                blob = self.bucket.blob(blob_name)
                return blob.exists()
            else:
                # Local file
                normalized_path = self.normalize_path(path)
                return Path(normalized_path).exists()
        except Exception as e:
            logger.error(f"Error checking if video exists: {path} - {e}")
            return False
    
    def get_local_path(self, path: str) -> Optional[str]:
        """
        Get local filesystem path for video.
        
        For local development: Returns path to local file
        For Cloud Run: Downloads from GCS to /tmp and returns temp path
        
        Args:
            path: Video path (local or GCS URL)
            
        Returns:
            Local filesystem path, or None if failed
        """
        try:
            if self.is_gcs_url(path):
                # Download from GCS
                return self._download_from_gcs(path)
            else:
                # Local file
                normalized_path = self.normalize_path(path)
                if Path(normalized_path).exists():
                    return normalized_path
                else:
                    logger.error(f"Local video not found: {normalized_path}")
                    return None
        except Exception as e:
            logger.error(f"Error getting local path for {path}: {e}")
            return None
    
    def _extract_blob_name(self, gcs_url: str) -> str:
        """
        Extract blob name from GCS URL.
        
        Args:
            gcs_url: GCS URL (https://storage.googleapis.com/bucket/path or gs://bucket/path)
            
        Returns:
            Blob name (path within bucket)
        """
        if gcs_url.startswith('gs://'):
            # gs://bucket/path -> path
            parts = gcs_url.replace('gs://', '').split('/', 1)
            return parts[1] if len(parts) > 1 else ''
        else:
            # https://storage.googleapis.com/bucket/path -> path
            parsed = urlparse(gcs_url)
            path_parts = parsed.path.strip('/').split('/', 1)
            return path_parts[1] if len(path_parts) > 1 else ''
    
    def _download_from_gcs(self, gcs_url: str) -> Optional[str]:
        """
        Download video from GCS to local temp file.
        
        Args:
            gcs_url: GCS URL
            
        Returns:
            Path to downloaded temp file, or None if failed
        """
        # Check cache first
        if gcs_url in self._download_cache:
            cached_path = self._download_cache[gcs_url]
            if Path(cached_path).exists():
                logger.debug(f"Using cached download: {cached_path}")
                return cached_path
        
        try:
            # Extract blob name
            blob_name = self._extract_blob_name(gcs_url)
            
            # Create temp file
            suffix = Path(blob_name).suffix or '.mp4'
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
                dir='/tmp'
            )
            temp_path = temp_file.name
            temp_file.close()
            
            # Download from GCS
            logger.info(f"Downloading from GCS: {blob_name} -> {temp_path}")
            blob = self.bucket.blob(blob_name)
            blob.download_to_filename(temp_path)
            
            # Cache the path
            self._download_cache[gcs_url] = temp_path
            
            logger.info(f"✅ Downloaded: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to download from GCS: {gcs_url} - {e}")
            return None
    
    def cleanup_cache(self):
        """Clean up downloaded temp files."""
        for gcs_url, temp_path in self._download_cache.items():
            try:
                if Path(temp_path).exists():
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_path}: {e}")
        
        self._download_cache.clear()


# Global singleton instance
_storage_service = None


def get_video_storage() -> VideoStorageService:
    """
    Get global video storage service instance.
    
    Returns:
        VideoStorageService singleton
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = VideoStorageService()
    return _storage_service
