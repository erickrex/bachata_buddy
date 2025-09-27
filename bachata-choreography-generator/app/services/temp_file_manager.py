"""
Temporary file management with automatic cleanup.
"""
import asyncio
import logging
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional, Set

logger = logging.getLogger(__name__)

class TempFileManager:
    """Manages temporary files with automatic cleanup."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_files: Set[Path] = set()
        self.temp_base_dir = Path("data/temp")
        self.temp_base_dir.mkdir(parents=True, exist_ok=True)
    
    @asynccontextmanager
    async def temp_file(
        self, 
        suffix: str = "", 
        prefix: str = "temp_", 
        directory: Optional[Path] = None,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[Path, None]:
        """
        Context manager for temporary files with automatic cleanup.
        
        Args:
            suffix: File suffix (e.g., ".mp3", ".mp4")
            prefix: File prefix
            directory: Directory to create file in (defaults to data/temp)
            
        Yields:
            Path to the temporary file
        """
        if directory is None:
            if user_id:
                directory = self.temp_base_dir / f"user_{user_id}"
            else:
                directory = self.temp_base_dir
        
        directory.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{prefix}{unique_id}{suffix}"
        temp_path = directory / filename
        
        try:
            # Track the file
            self.active_files.add(temp_path)
            self.logger.debug(f"Created temporary file: {temp_path}")
            
            yield temp_path
            
        finally:
            # Cleanup
            await self._cleanup_file(temp_path)
    
    @asynccontextmanager
    async def temp_directory(
        self, 
        prefix: str = "temp_dir_", 
        parent: Optional[Path] = None,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[Path, None]:
        """
        Context manager for temporary directories with automatic cleanup.
        
        Args:
            prefix: Directory prefix
            parent: Parent directory (defaults to data/temp)
            
        Yields:
            Path to the temporary directory
        """
        if parent is None:
            if user_id:
                parent = self.temp_base_dir / f"user_{user_id}"
            else:
                parent = self.temp_base_dir
        
        parent.mkdir(parents=True, exist_ok=True)
        
        # Generate unique directory name
        unique_id = str(uuid.uuid4())[:8]
        dir_name = f"{prefix}{unique_id}"
        temp_dir = parent / dir_name
        
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created temporary directory: {temp_dir}")
            
            yield temp_dir
            
        finally:
            # Cleanup directory and all contents
            await self._cleanup_directory(temp_dir)
    
    async def _cleanup_file(self, file_path: Path):
        """Clean up a single temporary file."""
        try:
            if file_path in self.active_files:
                self.active_files.remove(file_path)
            
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"Cleaned up temporary file: {file_path}")
                
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")
    
    async def _cleanup_directory(self, dir_path: Path):
        """Clean up a temporary directory and all its contents."""
        try:
            if dir_path.exists() and dir_path.is_dir():
                import shutil
                shutil.rmtree(dir_path)
                self.logger.debug(f"Cleaned up temporary directory: {dir_path}")
                
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temporary directory {dir_path}: {e}")
    
    async def cleanup_all_active_files(self):
        """Clean up all currently tracked temporary files."""
        files_to_cleanup = list(self.active_files)
        
        for file_path in files_to_cleanup:
            await self._cleanup_file(file_path)
        
        if files_to_cleanup:
            self.logger.info(f"Cleaned up {len(files_to_cleanup)} active temporary files")
    
    def get_active_file_count(self) -> int:
        """Get the number of currently tracked temporary files."""
        return len(self.active_files)
    
    async def cleanup_user_temp_files(self, user_id: str):
        """Clean up all temporary files for a specific user."""
        user_temp_dir = self.temp_base_dir / f"user_{user_id}"
        
        if user_temp_dir.exists():
            try:
                import shutil
                shutil.rmtree(user_temp_dir)
                self.logger.info(f"Cleaned up user temp directory: {user_temp_dir}")
                
                # Remove any tracked files in this directory
                files_to_remove = [f for f in self.active_files if str(f).startswith(str(user_temp_dir))]
                for file_path in files_to_remove:
                    self.active_files.discard(file_path)
                    
            except Exception as e:
                self.logger.warning(f"Failed to cleanup user temp directory {user_temp_dir}: {e}")
    
    def get_user_temp_directory(self, user_id: str) -> Path:
        """Get the temporary directory path for a specific user."""
        user_temp_dir = self.temp_base_dir / f"user_{user_id}"
        user_temp_dir.mkdir(parents=True, exist_ok=True)
        return user_temp_dir

# Global temp file manager instance
temp_file_manager = TempFileManager()