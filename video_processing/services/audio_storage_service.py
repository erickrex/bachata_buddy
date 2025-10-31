"""
Audio Storage Service

Unified interface for accessing audio files from both local filesystem and Google Cloud Storage.
Automatically detects environment and uses appropriate storage backend.

This service ensures songs work in both:
- Local development (reads from data/songs)
- Cloud Run production (reads from GCS)
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class AudioStorageService:
    """
    Unified audio storage service supporting local and GCS backends.
    
    Usage:
        storage = AudioStorageService()
        
        # Get local path (downloads from GCS if needed)
        local_path = storage.get_local_path("Aventura.mp3")
        
        # List available songs
        songs = storage.list_songs()
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
                logger.info(f"✅ GCS audio storage initialized: gs://{self.bucket_name}/songs/")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise
        else:
            # Local development
            self.local_songs_dir = Path('data/songs')
            logger.info(f"✅ Local audio storage initialized: {self.local_songs_dir}/")
        
        # Cache for downloaded files (in Cloud Run)
        self._download_cache = {}
    
    def get_local_path(self, song_name: str) -> str:
        """
        Get local path to audio file, downloading from GCS if needed.
        
        Args:
            song_name: Song filename (e.g., "Aventura.mp3")
            
        Returns:
            Local file path
            
        Raises:
            FileNotFoundError: If song doesn't exist
        """
        if self.use_gcs:
            # Check cache first
            if song_name in self._download_cache:
                cached_path = self._download_cache[song_name]
                if os.path.exists(cached_path):
                    logger.debug(f"Using cached audio: {song_name}")
                    return cached_path
            
            # Download from GCS
            gcs_path = f"songs/{song_name}"
            blob = self.bucket.blob(gcs_path)
            
            if not blob.exists():
                raise FileNotFoundError(f"Audio file not found in GCS: {gcs_path}")
            
            # Download to temp file
            temp_dir = Path(tempfile.gettempdir()) / 'bachata_songs'
            temp_dir.mkdir(exist_ok=True)
            local_path = temp_dir / song_name
            
            logger.info(f"Downloading audio from GCS: {gcs_path} -> {local_path}")
            blob.download_to_filename(str(local_path))
            
            # Cache the path
            self._download_cache[song_name] = str(local_path)
            
            return str(local_path)
        else:
            # Local development
            local_path = self.local_songs_dir / song_name
            
            if not local_path.exists():
                raise FileNotFoundError(f"Audio file not found: {local_path}")
            
            return str(local_path)
    
    def exists(self, song_name: str) -> bool:
        """
        Check if audio file exists in storage.
        
        Args:
            song_name: Song filename
            
        Returns:
            True if exists, False otherwise
        """
        if self.use_gcs:
            gcs_path = f"songs/{song_name}"
            blob = self.bucket.blob(gcs_path)
            return blob.exists()
        else:
            local_path = self.local_songs_dir / song_name
            return local_path.exists()
    
    def list_songs(self) -> List[str]:
        """
        List all available songs.
        
        Returns:
            List of song filenames (excludes macOS metadata files)
        """
        if self.use_gcs:
            # List blobs in songs/ prefix
            blobs = self.bucket.list_blobs(prefix='songs/')
            songs = []
            for blob in blobs:
                # Extract filename from path
                filename = blob.name.replace('songs/', '')
                # Skip macOS metadata files and empty names
                if filename and filename.endswith('.mp3') and not filename.startswith('._'):
                    songs.append(filename)
            return sorted(songs)
        else:
            # List local files
            if not self.local_songs_dir.exists():
                return []
            # Skip macOS metadata files (._*)
            songs = [f.name for f in self.local_songs_dir.glob('*.mp3') if not f.name.startswith('._')]
            return sorted(songs)
    
    def get_gcs_url(self, song_name: str) -> Optional[str]:
        """
        Get public GCS URL for a song (if using GCS).
        
        Args:
            song_name: Song filename
            
        Returns:
            Public URL or None if not using GCS
        """
        if self.use_gcs:
            return f"https://storage.googleapis.com/{self.bucket_name}/songs/{song_name}"
        return None
