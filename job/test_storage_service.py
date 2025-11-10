"""
Test Storage Service

Tests for the Cloud Storage service used by the video processing job.
"""
import os
import tempfile
import pytest
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.storage_service import StorageService, StorageConfig, StorageError


class TestStorageServiceLocal:
    """Test storage service in local mode (no GCS required)."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def storage_service(self, temp_dir):
        """Create storage service in local mode."""
        config = StorageConfig(
            use_local_storage=True,
            local_storage_path=temp_dir
        )
        return StorageService(config)
    
    @pytest.fixture
    def test_file(self, temp_dir):
        """Create a test file."""
        test_file_path = os.path.join(temp_dir, "test_input.txt")
        with open(test_file_path, 'w') as f:
            f.write("Test content for storage service")
        return test_file_path
    
    def test_upload_file_local(self, storage_service, test_file, temp_dir):
        """Test uploading a file in local mode."""
        destination_path = "uploads/test_file.txt"
        
        # Upload file
        result_url = storage_service.upload_file(test_file, destination_path)
        
        # Verify result
        assert result_url.startswith("file://")
        assert "test_file.txt" in result_url
        
        # Verify file exists at destination
        expected_path = os.path.join(temp_dir, destination_path)
        assert os.path.exists(expected_path)
        
        # Verify content
        with open(expected_path, 'r') as f:
            content = f.read()
        assert content == "Test content for storage service"
    
    def test_download_file_local(self, storage_service, test_file, temp_dir):
        """Test downloading a file in local mode."""
        # First upload a file
        destination_path = "uploads/test_file.txt"
        storage_service.upload_file(test_file, destination_path)
        
        # Download to different location
        download_path = os.path.join(temp_dir, "downloaded_file.txt")
        result_path = storage_service.download_file(destination_path, download_path)
        
        # Verify result
        assert result_path == download_path
        assert os.path.exists(download_path)
        
        # Verify content
        with open(download_path, 'r') as f:
            content = f.read()
        assert content == "Test content for storage service"
    
    def test_file_exists_local(self, storage_service, test_file, temp_dir):
        """Test checking if file exists in local mode."""
        destination_path = "uploads/test_file.txt"
        
        # File doesn't exist yet
        assert not storage_service.file_exists(destination_path)
        
        # Upload file
        storage_service.upload_file(test_file, destination_path)
        
        # File exists now
        assert storage_service.file_exists(destination_path)
    
    def test_delete_file_local(self, storage_service, test_file, temp_dir):
        """Test deleting a file in local mode."""
        destination_path = "uploads/test_file.txt"
        
        # Upload file
        storage_service.upload_file(test_file, destination_path)
        assert storage_service.file_exists(destination_path)
        
        # Delete file
        result = storage_service.delete_file(destination_path)
        assert result is True
        
        # File no longer exists
        assert not storage_service.file_exists(destination_path)
        
        # Deleting non-existent file returns False
        result = storage_service.delete_file(destination_path)
        assert result is False
    
    def test_get_signed_url_local(self, storage_service, test_file, temp_dir):
        """Test generating signed URL in local mode."""
        destination_path = "uploads/test_file.txt"
        
        # Upload file
        storage_service.upload_file(test_file, destination_path)
        
        # Get signed URL (in local mode, returns file:// URL)
        url = storage_service.get_signed_url(destination_path)
        
        assert url.startswith("file://")
        assert "test_file.txt" in url
    
    def test_upload_nonexistent_file(self, storage_service):
        """Test uploading a file that doesn't exist."""
        with pytest.raises(StorageError) as exc_info:
            storage_service.upload_file("/nonexistent/file.txt", "uploads/test.txt")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_download_nonexistent_file(self, storage_service, temp_dir):
        """Test downloading a file that doesn't exist."""
        download_path = os.path.join(temp_dir, "downloaded.txt")
        
        with pytest.raises(StorageError) as exc_info:
            storage_service.download_file("nonexistent/file.txt", download_path)
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_health_check_local(self, storage_service):
        """Test health check in local mode."""
        assert storage_service.health_check() is True
    
    def test_upload_with_subdirectories(self, storage_service, test_file, temp_dir):
        """Test uploading to nested subdirectories."""
        destination_path = "choreographies/2024/11/video.mp4"
        
        # Upload file
        result_url = storage_service.upload_file(test_file, destination_path)
        
        # Verify file exists
        expected_path = os.path.join(temp_dir, destination_path)
        assert os.path.exists(expected_path)
        
        # Verify parent directories were created
        assert os.path.isdir(os.path.join(temp_dir, "choreographies"))
        assert os.path.isdir(os.path.join(temp_dir, "choreographies/2024"))
        assert os.path.isdir(os.path.join(temp_dir, "choreographies/2024/11"))
    
    def test_download_files_parallel(self, storage_service, temp_dir):
        """Test parallel download of multiple files."""
        # Create multiple test files
        test_files = []
        for i in range(5):
            file_path = os.path.join(temp_dir, f"source_file_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"Test content {i}")
            test_files.append(file_path)
        
        # Upload files to storage
        uploaded_paths = []
        for i, test_file in enumerate(test_files):
            dest_path = f"clips/clip_{i}.txt"
            storage_service.upload_file(test_file, dest_path)
            uploaded_paths.append(dest_path)
        
        # Download files in parallel
        download_dir = os.path.join(temp_dir, "downloads")
        local_paths = storage_service.download_files_parallel(
            file_paths=uploaded_paths,
            local_dir=download_dir,
            max_workers=3
        )
        
        # Verify all files were downloaded
        assert len(local_paths) == 5
        
        for i, local_path in enumerate(local_paths):
            assert os.path.exists(local_path)
            
            # Verify content
            with open(local_path, 'r') as f:
                content = f.read()
            assert content == f"Test content {i}"
    
    def test_download_files_parallel_with_progress(self, storage_service, temp_dir):
        """Test parallel download with progress callback."""
        # Create test files
        test_files = []
        for i in range(3):
            file_path = os.path.join(temp_dir, f"source_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"Content {i}")
            test_files.append(file_path)
        
        # Upload files
        uploaded_paths = []
        for i, test_file in enumerate(test_files):
            dest_path = f"files/file_{i}.txt"
            storage_service.upload_file(test_file, dest_path)
            uploaded_paths.append(dest_path)
        
        # Track progress
        progress_calls = []
        
        def progress_callback(completed, total):
            progress_calls.append((completed, total))
        
        # Download with progress tracking
        download_dir = os.path.join(temp_dir, "parallel_downloads")
        local_paths = storage_service.download_files_parallel(
            file_paths=uploaded_paths,
            local_dir=download_dir,
            max_workers=2,
            progress_callback=progress_callback
        )
        
        # Verify progress was tracked
        assert len(progress_calls) == 3
        assert progress_calls[-1] == (3, 3)  # Final call should be (3, 3)
        
        # Verify all files downloaded
        assert len(local_paths) == 3
        for local_path in local_paths:
            assert os.path.exists(local_path)
    
    def test_download_files_parallel_failure(self, storage_service, temp_dir):
        """Test parallel download with missing files."""
        # Create one valid file
        test_file = os.path.join(temp_dir, "valid.txt")
        with open(test_file, 'w') as f:
            f.write("Valid content")
        
        storage_service.upload_file(test_file, "valid/file.txt")
        
        # Try to download mix of valid and invalid files
        file_paths = [
            "valid/file.txt",
            "nonexistent/file1.txt",
            "nonexistent/file2.txt"
        ]
        
        download_dir = os.path.join(temp_dir, "failed_downloads")
        
        with pytest.raises(StorageError) as exc_info:
            storage_service.download_files_parallel(
                file_paths=file_paths,
                local_dir=download_dir,
                max_workers=2
            )
        
        assert "Failed to download" in str(exc_info.value)


class TestStorageConfig:
    """Test storage configuration."""
    
    def test_config_from_env_local(self, monkeypatch):
        """Test creating config from environment variables (local mode)."""
        monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")
        monkeypatch.setenv("USE_LOCAL_STORAGE", "true")
        monkeypatch.setenv("LOCAL_STORAGE_PATH", "/tmp/test")
        
        config = StorageConfig.from_env()
        
        assert config.bucket_name == "test-bucket"
        assert config.use_local_storage is True
        assert config.local_storage_path == "/tmp/test"
    
    def test_config_from_env_cloud(self, monkeypatch):
        """Test creating config from environment variables (cloud mode)."""
        monkeypatch.setenv("GCS_BUCKET_NAME", "prod-bucket")
        monkeypatch.setenv("GCP_PROJECT_ID", "my-project")
        monkeypatch.setenv("USE_LOCAL_STORAGE", "false")
        monkeypatch.setenv("K_SERVICE", "video-processor")  # Cloud Run indicator
        
        config = StorageConfig.from_env()
        
        assert config.bucket_name == "prod-bucket"
        assert config.project_id == "my-project"
        assert config.use_local_storage is False
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = StorageConfig()
        
        assert config.bucket_name == "bachata-buddy-videos"
        assert config.timeout == 300
        assert config.local_storage_path == "/app/data"


def test_storage_service_initialization_local():
    """Test storage service initialization in local mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = StorageConfig(
            use_local_storage=True,
            local_storage_path=tmpdir
        )
        service = StorageService(config)
        
        assert service.config.use_local_storage is True
        assert service.client is None
        assert service.bucket is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
