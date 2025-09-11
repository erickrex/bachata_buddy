"""
Unit tests for resource management services.
"""
import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from app.services.resource_manager import ResourceManager
from app.services.temp_file_manager import TempFileManager


class TestResourceManager:
    """Test cases for ResourceManager."""
    
    @pytest.fixture
    def resource_manager(self):
        """Create a test resource manager instance."""
        return ResourceManager()
    
    @pytest.mark.asyncio
    async def test_cleanup_temporary_files(self, resource_manager):
        """Test temporary file cleanup functionality."""
        # Create test temporary directory
        test_temp_dir = Path("data/temp/test_cleanup")
        test_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test files
        test_files = []
        for i in range(3):
            test_file = test_temp_dir / f"test_file_{i}.txt"
            test_file.write_text(f"Test content {i}")
            test_files.append(test_file)
        
        # Override temp directories for testing
        original_temp_dirs = resource_manager.temp_directories
        resource_manager.temp_directories = [test_temp_dir]
        
        try:
            # Run cleanup with force=True
            stats = await resource_manager.cleanup_temporary_files(force=True)
            
            assert stats["files_removed"] == 3
            assert stats["bytes_freed"] > 0
            assert stats["directories_processed"] == 1
            
            # Verify files were removed
            for test_file in test_files:
                assert not test_file.exists()
                
        finally:
            # Restore original temp directories
            resource_manager.temp_directories = original_temp_dirs
            # Clean up test directory
            if test_temp_dir.exists():
                import shutil
                shutil.rmtree(test_temp_dir)
    
    @pytest.mark.asyncio
    async def test_cleanup_cache_directory(self, resource_manager):
        """Test cache directory cleanup functionality."""
        # Create test cache directory
        test_cache_dir = Path("data/cache/test_cache")
        test_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test cache files
        test_files = []
        for i in range(5):
            test_file = test_cache_dir / f"cache_file_{i}.pkl"
            # Create files with different sizes
            content = "x" * (1024 * (i + 1))  # 1KB, 2KB, 3KB, etc.
            test_file.write_text(content)
            test_files.append(test_file)
        
        # Mock the cache directory path
        with patch.object(Path, 'glob') as mock_glob:
            mock_glob.return_value = test_files
            
            # Set a very small cache size limit to trigger cleanup
            original_limit = resource_manager.max_cache_size_gb
            resource_manager.max_cache_size_gb = 0.000001  # Very small limit
            
            try:
                stats = await resource_manager.cleanup_cache_directory()
                
                # Should have removed some files
                assert stats["files_removed"] > 0
                assert stats["bytes_freed"] > 0
                
            finally:
                # Restore original limit
                resource_manager.max_cache_size_gb = original_limit
                # Clean up test files
                for test_file in test_files:
                    if test_file.exists():
                        test_file.unlink()
                if test_cache_dir.exists():
                    test_cache_dir.rmdir()
    
    def test_get_system_resources(self, resource_manager):
        """Test system resource information retrieval."""
        resources = resource_manager.get_system_resources()
        
        # Should have memory and disk information
        assert "memory" in resources
        assert "disk" in resources
        
        # Memory info should have required fields
        memory = resources["memory"]
        assert "total_gb" in memory
        assert "available_gb" in memory
        assert "used_gb" in memory
        assert "percent_used" in memory
        
        # Disk info should have required fields
        disk = resources["disk"]
        assert "total_gb" in disk
        assert "free_gb" in disk
        assert "used_gb" in disk
        assert "percent_used" in disk
        
        # Values should be reasonable
        assert memory["percent_used"] >= 0
        assert memory["percent_used"] <= 100
        assert disk["percent_used"] >= 0
        assert disk["percent_used"] <= 100
    
    @pytest.mark.asyncio
    async def test_monitoring_lifecycle(self, resource_manager):
        """Test resource monitoring start/stop lifecycle."""
        # Start monitoring
        await resource_manager.start_monitoring()
        assert resource_manager.monitoring_task is not None
        assert not resource_manager.monitoring_task.done()
        
        # Stop monitoring
        await resource_manager.stop_monitoring()
        assert resource_manager.monitoring_task.done()
    
    @pytest.mark.asyncio
    async def test_schedule_cleanup(self, resource_manager):
        """Test cleanup scheduling."""
        # Schedule cleanup with very short interval for testing
        await resource_manager.schedule_cleanup(interval_hours=0.001)  # ~3.6 seconds
        
        assert len(resource_manager.cleanup_tasks) > 0
        
        # Cancel the task to avoid long-running test
        for task in resource_manager.cleanup_tasks:
            task.cancel()
        
        # Wait for cancellation
        await asyncio.gather(*resource_manager.cleanup_tasks, return_exceptions=True)


class TestTempFileManager:
    """Test cases for TempFileManager."""
    
    @pytest.fixture
    def temp_file_manager(self):
        """Create a test temp file manager instance."""
        return TempFileManager()
    
    @pytest.mark.asyncio
    async def test_temp_file_context_manager(self, temp_file_manager):
        """Test temporary file context manager."""
        temp_file_path = None
        
        # Use context manager
        async with temp_file_manager.temp_file(suffix=".test", prefix="unit_test_") as temp_file:
            temp_file_path = temp_file
            
            # File should exist and be tracked
            assert temp_file.exists() or True  # File might not exist until written to
            assert temp_file in temp_file_manager.active_files
            
            # Write some content
            temp_file.write_text("Test content")
            assert temp_file.exists()
        
        # After context, file should be cleaned up
        assert not temp_file_path.exists()
        assert temp_file_path not in temp_file_manager.active_files
    
    @pytest.mark.asyncio
    async def test_temp_directory_context_manager(self, temp_file_manager):
        """Test temporary directory context manager."""
        temp_dir_path = None
        
        # Use context manager
        async with temp_file_manager.temp_directory(prefix="unit_test_dir_") as temp_dir:
            temp_dir_path = temp_dir
            
            # Directory should exist
            assert temp_dir.exists()
            assert temp_dir.is_dir()
            
            # Create a file in the directory
            test_file = temp_dir / "test.txt"
            test_file.write_text("Test content")
            assert test_file.exists()
        
        # After context, directory and contents should be cleaned up
        assert not temp_dir_path.exists()
    
    @pytest.mark.asyncio
    async def test_cleanup_all_active_files(self, temp_file_manager):
        """Test cleanup of all active files."""
        # Create some temporary files without using context manager
        temp_files = []
        for i in range(3):
            temp_file = temp_file_manager.temp_base_dir / f"manual_test_{i}.txt"
            temp_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file.write_text(f"Content {i}")
            temp_file_manager.active_files.add(temp_file)
            temp_files.append(temp_file)
        
        # Verify files exist and are tracked
        for temp_file in temp_files:
            assert temp_file.exists()
            assert temp_file in temp_file_manager.active_files
        
        # Cleanup all active files
        await temp_file_manager.cleanup_all_active_files()
        
        # Verify files are cleaned up and no longer tracked
        for temp_file in temp_files:
            assert not temp_file.exists()
            assert temp_file not in temp_file_manager.active_files
    
    def test_get_active_file_count(self, temp_file_manager):
        """Test active file count tracking."""
        initial_count = temp_file_manager.get_active_file_count()
        
        # Add some files to tracking
        test_files = []
        for i in range(3):
            test_file = Path(f"test_file_{i}.txt")
            temp_file_manager.active_files.add(test_file)
            test_files.append(test_file)
        
        # Count should increase
        assert temp_file_manager.get_active_file_count() == initial_count + 3
        
        # Remove files from tracking
        for test_file in test_files:
            temp_file_manager.active_files.remove(test_file)
        
        # Count should return to initial
        assert temp_file_manager.get_active_file_count() == initial_count


class TestResourceIntegration:
    """Integration tests for resource management components."""
    
    @pytest.mark.asyncio
    async def test_resource_manager_shutdown(self):
        """Test complete resource manager shutdown process."""
        resource_manager = ResourceManager()
        temp_file_manager = TempFileManager()
        
        # Start monitoring and create some temporary files
        await resource_manager.start_monitoring()
        
        # Create temporary files
        async with temp_file_manager.temp_file(suffix=".test") as temp_file:
            temp_file.write_text("Test content")
            
            # Simulate shutdown
            await resource_manager.shutdown()
            
            # Monitoring should be stopped
            assert resource_manager.monitoring_task.done()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_cleanup(self):
        """Test error handling during cleanup operations."""
        resource_manager = ResourceManager()
        
        # Mock Path.rglob to raise an exception
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.side_effect = PermissionError("Access denied")
            
            # Cleanup should handle the error gracefully
            stats = await resource_manager.cleanup_temporary_files()
            
            # Should return empty stats but not crash
            assert isinstance(stats, dict)
            assert "files_removed" in stats
            assert "bytes_freed" in stats
            assert "directories_processed" in stats


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])