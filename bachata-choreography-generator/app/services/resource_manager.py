"""
Resource management service for file cleanup and system resource monitoring.
"""
import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional
import psutil

logger = logging.getLogger(__name__)

class ResourceManager:
    """Manages system resources, file cleanup, and monitoring."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cleanup_tasks: List[asyncio.Task] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.temp_directories = [
            Path("data/temp"),
            Path("data/cache"),
            Path("data/output")
        ]
        self.max_temp_age_hours = 24  # Clean files older than 24 hours
        self.max_cache_size_gb = 5.0  # Maximum cache size in GB
        self.memory_warning_threshold = 85  # Warn when memory usage > 85%
        self.disk_warning_threshold = 90   # Warn when disk usage > 90%
        
    async def start_monitoring(self):
        """Start background resource monitoring."""
        if self.monitoring_task is None or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitor_resources())
            self.logger.info("Resource monitoring started")
    
    async def stop_monitoring(self):
        """Stop background resource monitoring."""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Resource monitoring stopped")
    
    async def cleanup_temporary_files(self, force: bool = False) -> Dict[str, int]:
        """
        Clean up temporary files older than the specified age.
        
        Args:
            force: If True, clean all temporary files regardless of age
            
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "files_removed": 0,
            "bytes_freed": 0,
            "directories_processed": 0
        }
        
        current_time = time.time()
        max_age_seconds = 0 if force else self.max_temp_age_hours * 3600
        
        for temp_dir in self.temp_directories:
            if not temp_dir.exists():
                continue
                
            stats["directories_processed"] += 1
            
            try:
                for file_path in temp_dir.rglob("*"):
                    if not file_path.is_file():
                        continue
                    
                    # Check file age
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            stats["files_removed"] += 1
                            stats["bytes_freed"] += file_size
                            self.logger.debug(f"Removed temporary file: {file_path}")
                        except Exception as e:
                            self.logger.warning(f"Failed to remove {file_path}: {e}")
                            
            except Exception as e:
                self.logger.error(f"Error processing directory {temp_dir}: {e}")
        
        if stats["files_removed"] > 0:
            self.logger.info(
                f"Cleanup completed: {stats['files_removed']} files removed, "
                f"{stats['bytes_freed'] / (1024*1024):.1f} MB freed"
            )
        
        return stats
    
    async def cleanup_cache_directory(self) -> Dict[str, int]:
        """
        Clean up cache directory if it exceeds size limit.
        Removes oldest files first.
        """
        cache_dir = Path("data/cache")
        if not cache_dir.exists():
            return {"files_removed": 0, "bytes_freed": 0}
        
        # Get all cache files with their sizes and modification times
        cache_files = []
        total_size = 0
        
        try:
            for file_path in cache_dir.glob("*.pkl"):
                if file_path.is_file():
                    stat = file_path.stat()
                    cache_files.append({
                        "path": file_path,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime
                    })
                    total_size += stat.st_size
        except Exception as e:
            self.logger.error(f"Error scanning cache directory: {e}")
            return {"files_removed": 0, "bytes_freed": 0}
        
        # Check if cleanup is needed
        total_size_gb = total_size / (1024**3)
        if total_size_gb <= self.max_cache_size_gb:
            return {"files_removed": 0, "bytes_freed": 0}
        
        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda x: x["mtime"])
        
        # Remove files until we're under the size limit
        stats = {"files_removed": 0, "bytes_freed": 0}
        target_size = self.max_cache_size_gb * 0.8 * (1024**3)  # Clean to 80% of limit
        
        for file_info in cache_files:
            if total_size <= target_size:
                break
                
            try:
                file_info["path"].unlink()
                stats["files_removed"] += 1
                stats["bytes_freed"] += file_info["size"]
                total_size -= file_info["size"]
                self.logger.debug(f"Removed cache file: {file_info['path']}")
            except Exception as e:
                self.logger.warning(f"Failed to remove cache file {file_info['path']}: {e}")
        
        if stats["files_removed"] > 0:
            self.logger.info(
                f"Cache cleanup: {stats['files_removed']} files removed, "
                f"{stats['bytes_freed'] / (1024*1024):.1f} MB freed"
            )
        
        return stats
    
    def get_system_resources(self) -> Dict[str, any]:
        """Get current system resource usage."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            return {
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent_used": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "percent_used": disk.percent
                },
                "temp_directories": self._get_directory_sizes()
            }
        except Exception as e:
            self.logger.error(f"Error getting system resources: {e}")
            return {"error": str(e)}
    
    def _get_directory_sizes(self) -> Dict[str, Dict[str, any]]:
        """Get sizes of temporary directories."""
        directory_info = {}
        
        for temp_dir in self.temp_directories:
            if not temp_dir.exists():
                directory_info[str(temp_dir)] = {
                    "exists": False,
                    "size_mb": 0,
                    "file_count": 0
                }
                continue
            
            try:
                total_size = 0
                file_count = 0
                
                for file_path in temp_dir.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        file_count += 1
                
                directory_info[str(temp_dir)] = {
                    "exists": True,
                    "size_mb": round(total_size / (1024*1024), 2),
                    "file_count": file_count
                }
            except Exception as e:
                directory_info[str(temp_dir)] = {
                    "exists": True,
                    "error": str(e)
                }
        
        return directory_info
    
    async def _monitor_resources(self):
        """Background task to monitor system resources."""
        while True:
            try:
                resources = self.get_system_resources()
                
                # Check memory usage
                if "memory" in resources:
                    memory_percent = resources["memory"]["percent_used"]
                    if memory_percent > self.memory_warning_threshold:
                        self.logger.warning(
                            f"High memory usage: {memory_percent:.1f}% "
                            f"({resources['memory']['used_gb']:.1f}GB used)"
                        )
                
                # Check disk usage
                if "disk" in resources:
                    disk_percent = resources["disk"]["percent_used"]
                    if disk_percent > self.disk_warning_threshold:
                        self.logger.warning(
                            f"High disk usage: {disk_percent:.1f}% "
                            f"({resources['disk']['used_gb']:.1f}GB used)"
                        )
                
                # Automatic cleanup if resources are low
                if ("memory" in resources and 
                    resources["memory"]["percent_used"] > 90):
                    self.logger.info("High memory usage detected, running cleanup")
                    await self.cleanup_temporary_files()
                    await self.cleanup_cache_directory()
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def schedule_cleanup(self, interval_hours: int = 6):
        """Schedule periodic cleanup of temporary files."""
        cleanup_task = asyncio.create_task(self._periodic_cleanup(interval_hours))
        self.cleanup_tasks.append(cleanup_task)
        self.logger.info(f"Scheduled cleanup every {interval_hours} hours")
    
    async def _periodic_cleanup(self, interval_hours: int):
        """Periodic cleanup task."""
        while True:
            try:
                await asyncio.sleep(interval_hours * 3600)
                await self.cleanup_temporary_files()
                await self.cleanup_cache_directory()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")
    
    async def shutdown(self):
        """Clean shutdown of resource manager."""
        self.logger.info("Shutting down resource manager")
        
        # Stop monitoring
        await self.stop_monitoring()
        
        # Cancel cleanup tasks
        for task in self.cleanup_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.cleanup_tasks:
            await asyncio.gather(*self.cleanup_tasks, return_exceptions=True)
        
        # Final cleanup
        await self.cleanup_temporary_files()
        
        # Clean up any active temporary files from temp file manager
        try:
            from .temp_file_manager import temp_file_manager
            await temp_file_manager.cleanup_all_active_files()
        except Exception as e:
            self.logger.warning(f"Error cleaning up temp file manager: {e}")
        
        self.logger.info("Resource manager shutdown complete")

# Global resource manager instance
resource_manager = ResourceManager()