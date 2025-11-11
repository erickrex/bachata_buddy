"""
Cloud Storage Service for Video Processing Job

This service handles Google Cloud Storage operations for the video processing job.
Extracted from the monolith with Django dependencies removed.

Key responsibilities:
- Upload generated videos to Cloud Storage
- Download audio files from Cloud Storage or YouTube
- Download training videos from Cloud Storage
- Generate signed URLs for video access
- Manage file paths and naming conventions

Features:
- Connection pooling for efficient operations
- Retry logic with exponential backoff
- Support for both local and cloud storage
- Automatic bucket creation if needed
- Progress tracking for large uploads
"""

import logging
import time
import os
from typing import Optional, BinaryIO, Callable
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)


class StorageConfig:
    """Cloud Storage connection configuration."""
    
    def __init__(
        self,
        bucket_name: str = "bachata-buddy-videos",
        project_id: Optional[str] = None,
        use_local_storage: bool = False,
        local_storage_path: str = "/app/data",
        timeout: int = 300
    ):
        self.bucket_name = bucket_name
        self.project_id = project_id
        self.use_local_storage = use_local_storage
        self.local_storage_path = local_storage_path
        self.timeout = timeout
    
    @classmethod
    def from_env(cls) -> 'StorageConfig':
        """
        Create configuration from environment variables.
        
        Environment variables:
            GCS_BUCKET_NAME: Cloud Storage bucket name (default: bachata-buddy-videos)
            GCP_PROJECT_ID: Google Cloud project ID (optional)
            USE_LOCAL_STORAGE: Use local filesystem instead of GCS (default: false)
            LOCAL_STORAGE_PATH: Path for local storage (default: /app/data)
            STORAGE_TIMEOUT: Request timeout in seconds (default: 300)
        
        Returns:
            StorageConfig instance
        """
        # Determine if running locally
        is_local = os.getenv("K_SERVICE") is None  # K_SERVICE is set in Cloud Run
        use_local = os.getenv("USE_LOCAL_STORAGE", str(is_local)).lower() == "true"
        
        return cls(
            bucket_name=os.getenv("GCS_BUCKET_NAME", "bachata-buddy-videos"),
            project_id=os.getenv("GCP_PROJECT_ID"),
            use_local_storage=use_local,
            local_storage_path=os.getenv("LOCAL_STORAGE_PATH", "/app/data"),
            timeout=int(os.getenv("STORAGE_TIMEOUT", "300"))
        )


class StorageService:
    """
    Handles Cloud Storage operations for video processing.
    
    This is a standalone service extracted from the Django monolith,
    with all Django dependencies removed.
    
    Features:
    - Upload/download files to/from Cloud Storage
    - Retry logic with exponential backoff
    - Support for local filesystem (development)
    - Progress tracking for large files
    - Signed URL generation
    """
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # seconds
    RETRY_BACKOFF = 2.0  # exponential backoff multiplier
    
    def __init__(self, config: Optional[StorageConfig] = None):
        """
        Initialize Storage service.
        
        Args:
            config: Storage configuration (if None, loads from environment)
        """
        if config is None:
            config = StorageConfig.from_env()
        
        self.config = config
        self.client = None
        self.bucket = None
        
        if not config.use_local_storage:
            # Initialize GCS client
            try:
                from google.cloud import storage
                self.client = storage.Client(project=config.project_id)
                self.bucket = self.client.bucket(config.bucket_name)
                logger.info(
                    f"Cloud Storage service initialized. "
                    f"Bucket: {config.bucket_name}, Project: {config.project_id}"
                )
            except ImportError:
                logger.warning(
                    "google-cloud-storage not installed, falling back to local storage"
                )
                config.use_local_storage = True
            except Exception as e:
                logger.error(f"Failed to initialize Cloud Storage client: {e}")
                raise StorageError(f"Failed to initialize Cloud Storage: {e}")
        
        if config.use_local_storage:
            # Ensure local storage directory exists
            os.makedirs(config.local_storage_path, exist_ok=True)
            logger.info(
                f"Using local storage at {config.local_storage_path}"
            )
    
    def upload_file(
        self,
        local_path: str,
        destination_path: str,
        content_type: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """
        Upload a file to Cloud Storage with retry logic.
        
        Args:
            local_path: Path to local file
            destination_path: Destination path in bucket (e.g., 'choreographies/2024/11/video.mp4')
            content_type: MIME type (optional, auto-detected if not provided)
            progress_callback: Optional callback(bytes_uploaded, total_bytes)
        
        Returns:
            GCS URL (gs://bucket/path) or local path
            
        Raises:
            StorageError: If upload fails after all retries
        """
        logger.info(
            f"Upload requested",
            extra={
                'local_path': local_path,
                'destination_path': destination_path,
                'content_type': content_type
            }
        )
        
        # Validate local file exists
        if not os.path.exists(local_path):
            raise StorageError(f"Local file not found: {local_path}")
        
        file_size = os.path.getsize(local_path)
        logger.debug(f"File size: {file_size} bytes")
        
        # Local storage mode
        if self.config.use_local_storage:
            return self._upload_file_local(local_path, destination_path)
        
        # Cloud Storage mode with retry
        last_exception = None
        delay = self.RETRY_DELAY
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(
                    f"Uploading file (attempt {attempt}/{self.MAX_RETRIES})",
                    extra={
                        'local_path': local_path,
                        'destination_path': destination_path,
                        'attempt': attempt,
                        'file_size': file_size
                    }
                )
                
                url = self._upload_file_gcs(
                    local_path,
                    destination_path,
                    content_type,
                    progress_callback
                )
                
                logger.info(
                    f"File uploaded successfully: {url}",
                    extra={
                        'local_path': local_path,
                        'destination_path': destination_path,
                        'url': url,
                        'attempt': attempt
                    }
                )
                return url
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Upload attempt {attempt}/{self.MAX_RETRIES} failed: {e}",
                    extra={
                        'local_path': local_path,
                        'destination_path': destination_path,
                        'attempt': attempt,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                )
                
                # Don't retry on validation errors
                if self._is_non_retryable_error(e):
                    logger.error(f"Non-retryable error: {e}")
                    raise StorageError(f"Upload failed: {e}") from e
                
                # Wait before retry
                if attempt < self.MAX_RETRIES:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= self.RETRY_BACKOFF
        
        # All retries exhausted
        error_msg = f"Failed to upload file after {self.MAX_RETRIES} attempts: {last_exception}"
        logger.error(error_msg)
        raise StorageError(error_msg) from last_exception
    
    def _upload_file_local(self, local_path: str, destination_path: str) -> str:
        """Upload file to local storage (development mode)."""
        import shutil
        
        dest_full_path = os.path.join(self.config.local_storage_path, destination_path)
        os.makedirs(os.path.dirname(dest_full_path), exist_ok=True)
        
        shutil.copy2(local_path, dest_full_path)
        
        logger.info(f"File copied to local storage: {dest_full_path}")
        return f"file://{dest_full_path}"
    
    def _upload_file_gcs(
        self,
        local_path: str,
        destination_path: str,
        content_type: Optional[str],
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> str:
        """Upload file to Google Cloud Storage."""
        blob = self.bucket.blob(destination_path)
        
        # Set content type if provided
        if content_type:
            blob.content_type = content_type
        
        # Upload with timeout
        blob.upload_from_filename(
            local_path,
            timeout=self.config.timeout
        )
        
        # Call progress callback if provided
        if progress_callback:
            file_size = os.path.getsize(local_path)
            progress_callback(file_size, file_size)
        
        # Return GCS URL
        return f"gs://{self.config.bucket_name}/{destination_path}"
    
    def download_file(
        self,
        source_path: str,
        local_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """
        Download a file from Cloud Storage with retry logic.
        
        Args:
            source_path: Source path in bucket or GCS URL (gs://bucket/path)
            local_path: Destination local path
            progress_callback: Optional callback(bytes_downloaded, total_bytes)
        
        Returns:
            Local file path
            
        Raises:
            StorageError: If download fails after all retries
        """
        logger.info(
            f"Download requested",
            extra={
                'source_path': source_path,
                'local_path': local_path
            }
        )
        
        # Parse GCS URL if provided
        if source_path.startswith('gs://'):
            source_path = source_path.replace(f'gs://{self.config.bucket_name}/', '')
        
        # Local storage mode
        if self.config.use_local_storage or source_path.startswith('file://'):
            return self._download_file_local(source_path, local_path)
        
        # Cloud Storage mode with retry
        last_exception = None
        delay = self.RETRY_DELAY
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(
                    f"Downloading file (attempt {attempt}/{self.MAX_RETRIES})",
                    extra={
                        'source_path': source_path,
                        'local_path': local_path,
                        'attempt': attempt
                    }
                )
                
                path = self._download_file_gcs(
                    source_path,
                    local_path,
                    progress_callback
                )
                
                logger.info(
                    f"File downloaded successfully: {path}",
                    extra={
                        'source_path': source_path,
                        'local_path': local_path,
                        'attempt': attempt
                    }
                )
                return path
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Download attempt {attempt}/{self.MAX_RETRIES} failed: {e}",
                    extra={
                        'source_path': source_path,
                        'local_path': local_path,
                        'attempt': attempt,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                )
                
                # Don't retry on not found errors
                if self._is_non_retryable_error(e):
                    logger.error(f"Non-retryable error: {e}")
                    raise StorageError(f"Download failed: {e}") from e
                
                # Wait before retry
                if attempt < self.MAX_RETRIES:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= self.RETRY_BACKOFF
        
        # All retries exhausted
        error_msg = f"Failed to download file after {self.MAX_RETRIES} attempts: {last_exception}"
        logger.error(error_msg)
        raise StorageError(error_msg) from last_exception
    
    def _download_file_local(self, source_path: str, local_path: str) -> str:
        """Download file from local storage (development mode)."""
        import shutil
        
        # Handle file:// URLs
        if source_path.startswith('file://'):
            source_path = source_path.replace('file://', '')
        else:
            # Strip 'data/' prefix if present to avoid doubling
            if source_path.startswith('data/'):
                source_path = source_path[5:]  # Remove 'data/' prefix
            source_path = os.path.join(self.config.local_storage_path, source_path)
        
        if not os.path.exists(source_path):
            raise StorageError(f"Source file not found: {source_path}")
        
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(source_path, local_path)
        
        logger.info(f"File copied from local storage: {local_path}")
        return local_path
    
    def _download_file_gcs(
        self,
        source_path: str,
        local_path: str,
        progress_callback: Optional[Callable[[int, int], None]]
    ) -> str:
        """Download file from Google Cloud Storage."""
        blob = self.bucket.blob(source_path)
        
        # Check if blob exists
        if not blob.exists():
            raise StorageError(f"File not found in Cloud Storage: {source_path}")
        
        # Create directory if needed
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Download with timeout
        blob.download_to_filename(
            local_path,
            timeout=self.config.timeout
        )
        
        # Call progress callback if provided
        if progress_callback:
            file_size = os.path.getsize(local_path)
            progress_callback(file_size, file_size)
        
        return local_path
    
    def get_signed_url(
        self,
        file_path: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate a signed URL for temporary access to a file.
        
        Args:
            file_path: Path in bucket or GCS URL
            expiration: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Signed URL for file access
            
        Raises:
            StorageError: If URL generation fails
        """
        # Parse GCS URL if provided
        if file_path.startswith('gs://'):
            file_path = file_path.replace(f'gs://{self.config.bucket_name}/', '')
        
        # Local storage mode - return file:// URL
        if self.config.use_local_storage or file_path.startswith('file://'):
            if file_path.startswith('file://'):
                return file_path
            return f"file://{os.path.join(self.config.local_storage_path, file_path)}"
        
        try:
            blob = self.bucket.blob(file_path)
            
            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
            
            logger.debug(
                f"Signed URL generated",
                extra={
                    'file_path': file_path,
                    'expiration': expiration
                }
            )
            return url
            
        except Exception as e:
            logger.error(
                f"Failed to generate signed URL: {e}",
                extra={
                    'file_path': file_path,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            raise StorageError(f"Failed to generate signed URL: {e}") from e
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            file_path: Path in bucket or GCS URL
        
        Returns:
            True if file exists, False otherwise
        """
        # Parse GCS URL if provided
        if file_path.startswith('gs://'):
            file_path = file_path.replace(f'gs://{self.config.bucket_name}/', '')
        
        # Local storage mode
        if self.config.use_local_storage or file_path.startswith('file://'):
            if file_path.startswith('file://'):
                file_path = file_path.replace('file://', '')
            else:
                # Strip 'data/' prefix if present to avoid doubling
                if file_path.startswith('data/'):
                    file_path = file_path[5:]  # Remove 'data/' prefix
                file_path = os.path.join(self.config.local_storage_path, file_path)
            return os.path.exists(file_path)
        
        try:
            blob = self.bucket.blob(file_path)
            return blob.exists()
        except Exception as e:
            logger.warning(f"Error checking file existence: {e}")
            return False
    
    def download_files_parallel(
        self,
        file_paths: list,
        local_dir: str,
        max_workers: int = 10,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> list:
        """
        Download multiple files in parallel for improved performance.
        
        Args:
            file_paths: List of source paths in bucket or GCS URLs
            local_dir: Local directory to download files to
            max_workers: Maximum number of parallel downloads (default: 10)
            progress_callback: Optional callback(completed_count, total_count)
        
        Returns:
            List of local file paths in the same order as file_paths
            
        Raises:
            StorageError: If any download fails
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        logger.info(
            f"Starting parallel download of {len(file_paths)} files",
            extra={
                'file_count': len(file_paths),
                'local_dir': local_dir,
                'max_workers': max_workers
            }
        )
        
        # Ensure local directory exists
        os.makedirs(local_dir, exist_ok=True)
        
        # Prepare download tasks
        download_tasks = []
        local_paths = []
        
        for idx, source_path in enumerate(file_paths):
            # Generate local filename
            filename = f'file_{idx:04d}' + Path(source_path).suffix
            local_path = os.path.join(local_dir, filename)
            local_paths.append(local_path)
            
            download_tasks.append((idx, source_path, local_path))
        
        # Execute downloads in parallel
        completed_count = 0
        failed_downloads = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_task = {
                executor.submit(self.download_file, source_path, local_path): (idx, source_path, local_path)
                for idx, source_path, local_path in download_tasks
            }
            
            # Wait for downloads to complete
            for future in as_completed(future_to_task):
                idx, source_path, local_path = future_to_task[future]
                
                try:
                    future.result()
                    completed_count += 1
                    
                    logger.debug(
                        f"Downloaded file {completed_count}/{len(file_paths)}",
                        extra={
                            'idx': idx,
                            'source_path': source_path,
                            'local_path': local_path
                        }
                    )
                    
                    # Call progress callback
                    if progress_callback:
                        progress_callback(completed_count, len(file_paths))
                    
                except Exception as e:
                    failed_downloads.append((idx, source_path, str(e)))
                    logger.error(
                        f"Failed to download file {idx}",
                        extra={
                            'source_path': source_path,
                            'error': str(e)
                        }
                    )
        
        # Check for failures
        if failed_downloads:
            error_msg = f"Failed to download {len(failed_downloads)} files: "
            error_msg += ", ".join([f"{src} ({err})" for _, src, err in failed_downloads])
            raise StorageError(error_msg)
        
        logger.info(
            f"Parallel download completed successfully",
            extra={
                'file_count': len(file_paths),
                'completed_count': completed_count
            }
        )
        
        return local_paths
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path in bucket or GCS URL
        
        Returns:
            True if deleted successfully, False if file didn't exist
            
        Raises:
            StorageError: If deletion fails
        """
        # Parse GCS URL if provided
        if file_path.startswith('gs://'):
            file_path = file_path.replace(f'gs://{self.config.bucket_name}/', '')
        
        # Local storage mode
        if self.config.use_local_storage or file_path.startswith('file://'):
            if file_path.startswith('file://'):
                file_path = file_path.replace('file://', '')
            else:
                # Strip 'data/' prefix if present to avoid doubling
                if file_path.startswith('data/'):
                    file_path = file_path[5:]  # Remove 'data/' prefix
                file_path = os.path.join(self.config.local_storage_path, file_path)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted from local storage: {file_path}")
                return True
            return False
        
        try:
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                logger.warning(f"File not found for deletion: {file_path}")
                return False
            
            blob.delete()
            logger.info(f"File deleted from Cloud Storage: {file_path}")
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to delete file: {e}",
                extra={
                    'file_path': file_path,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            raise StorageError(f"Failed to delete file: {e}") from e
    
    def _is_non_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error should not be retried.
        
        Args:
            error: The exception that occurred
        
        Returns:
            True if error should not be retried, False otherwise
        """
        error_str = str(error).lower()
        
        # Don't retry on validation or not found errors
        non_retryable_patterns = [
            'not found',
            'does not exist',
            'invalid',
            'permission denied',
            'unauthorized',
            'forbidden',
            'bad request',
        ]
        
        return any(pattern in error_str for pattern in non_retryable_patterns)
    
    def health_check(self) -> bool:
        """
        Check if storage service is available.
        
        Returns:
            True if storage is healthy, False otherwise
        """
        try:
            if self.config.use_local_storage:
                # Check if local storage directory is accessible
                return os.path.isdir(self.config.local_storage_path)
            else:
                # Check if bucket is accessible
                return self.bucket.exists()
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return False


class StorageError(Exception):
    """Raised when storage operations fail."""
    pass
