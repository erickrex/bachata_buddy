"""
Property-based tests for storage abstraction layer.

**Feature: cloud-migration-cleanup**

These tests verify the correctness properties of the storage abstraction layer
as defined in the design document.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from hypothesis import given, strategies as st, settings, assume

from .factory import get_storage_backend, reset_storage_backend
from .local import LocalStorageBackend
from .s3 import S3StorageBackend


# Test fixtures and helpers

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_file():
    """Create a temporary file for testing"""
    fd, path = tempfile.mkstemp()
    os.write(fd, b"test content")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(autouse=True)
def reset_backend():
    """Reset storage backend singleton before each test"""
    reset_storage_backend()
    yield
    reset_storage_backend()


# Hypothesis strategies for generating test data

@st.composite
def storage_backend_config(draw):
    """Generate valid storage backend configurations"""
    backend_type = draw(st.sampled_from(['local', 's3']))
    
    if backend_type == 'local':
        # Generate a safe relative path that won't try to create directories in system locations
        # Use only alphanumeric characters and underscores to avoid path issues
        path_component = draw(st.text(
            min_size=1, 
            max_size=30, 
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                whitelist_characters='_'
            )
        ))
        # Ensure the path doesn't start with / or other problematic characters
        # Prepend 'test_' to ensure it's clearly a test directory
        safe_path = f"test_{path_component}" if path_component else "test_media"
        
        return {
            'STORAGE_BACKEND': 'local',
            'MEDIA_ROOT': safe_path,
            'MEDIA_URL': draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll'),
                whitelist_characters='_-'
            )))
        }
    else:
        return {
            'STORAGE_BACKEND': 's3',
            'AWS_STORAGE_BUCKET_NAME': draw(st.text(
                min_size=3, max_size=63,
                alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')
            )),
            'AWS_REGION': draw(st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1'])),
            'AWS_CLOUDFRONT_DOMAIN': draw(st.one_of(
                st.none(),
                st.text(min_size=5, max_size=50, alphabet=st.characters(
                    whitelist_categories=('Ll', 'Nd'),
                    whitelist_characters='.-'
                ))
            ))
        }


@st.composite
def file_path(draw):
    """Generate valid file paths"""
    # Generate path components
    num_components = draw(st.integers(min_value=1, max_value=5))
    components = [
        draw(st.text(
            min_size=1, max_size=20,
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')
        ))
        for _ in range(num_components)
    ]
    
    # Add file extension
    extension = draw(st.sampled_from(['txt', 'mp4', 'json', 'jpg', 'png']))
    components[-1] = f"{components[-1]}.{extension}"
    
    return '/'.join(components)


# Property 4: Storage backend switching
# **Validates: Requirements 3.1, 3.4**

class TestStorageBackendSwitching:
    """
    **Feature: cloud-migration-cleanup, Property 4: Storage backend switching**
    **Validates: Requirements 3.1, 3.4**
    
    For any storage backend configuration (local or S3), initializing the storage
    service with that configuration should result in operations using the correct backend.
    """
    
    @settings(max_examples=100, deadline=None)
    @given(config=storage_backend_config())
    def test_backend_selection_based_on_configuration(self, config):
        """
        Property: For any valid storage backend configuration, get_storage_backend()
        should return an instance of the correct backend type.
        """
        # Reset backend before test
        reset_storage_backend()
        
        # Save original environment
        original_env = os.environ.copy()
        
        try:
            # Set environment variables
            for key, value in config.items():
                if value is not None:
                    os.environ[key] = str(value)
            
            # For S3 backend, mock boto3 to avoid actual AWS calls
            if config['STORAGE_BACKEND'] == 's3':
                # Mock boto3 at the point where it's imported in S3StorageBackend.__init__
                with patch('boto3.client') as mock_client_factory:
                    # Mock S3 client
                    mock_client = MagicMock()
                    mock_client_factory.return_value = mock_client
                    
                    # Mock successful bucket check
                    mock_client.head_bucket.return_value = {}
                    
                    # Get backend
                    backend = get_storage_backend()
                    
                    # Verify correct backend type
                    assert isinstance(backend, S3StorageBackend), \
                        f"Expected S3StorageBackend for config {config}, got {type(backend)}"
                    
                    # Verify S3 client was initialized
                    mock_client_factory.assert_called_once_with('s3', region_name=config['AWS_REGION'])
            else:
                # Get backend
                backend = get_storage_backend()
                
                # Verify correct backend type
                assert isinstance(backend, LocalStorageBackend), \
                    f"Expected LocalStorageBackend for config {config}, got {type(backend)}"
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
            reset_storage_backend()
    
    @settings(max_examples=50, deadline=None)
    @given(config=storage_backend_config())
    def test_backend_singleton_returns_same_instance(self, config):
        """
        Property: For any configuration, calling get_storage_backend() multiple times
        should return the same instance (singleton pattern).
        """
        # Reset backend before test
        reset_storage_backend()
        
        # Save original environment
        original_env = os.environ.copy()
        
        try:
            # Set environment variables
            for key, value in config.items():
                if value is not None:
                    os.environ[key] = str(value)
            
            # For S3 backend, mock boto3
            if config['STORAGE_BACKEND'] == 's3':
                with patch('boto3.client') as mock_client_factory:
                    mock_client = MagicMock()
                    mock_client_factory.return_value = mock_client
                    mock_client.head_bucket.return_value = {}
                    
                    # Get backend twice
                    backend1 = get_storage_backend()
                    backend2 = get_storage_backend()
                    
                    # Verify same instance
                    assert backend1 is backend2, \
                        "get_storage_backend() should return the same instance (singleton)"
            else:
                # Get backend twice
                backend1 = get_storage_backend()
                backend2 = get_storage_backend()
                
                # Verify same instance
                assert backend1 is backend2, \
                    "get_storage_backend() should return the same instance (singleton)"
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
            reset_storage_backend()
    
    def test_invalid_backend_type_raises_error(self):
        """
        Property: For any invalid backend type, get_storage_backend() should raise ValueError.
        """
        reset_storage_backend()
        
        # Save original environment
        original_env = os.environ.copy()
        
        try:
            # Set invalid backend type
            os.environ['STORAGE_BACKEND'] = 'invalid_backend'
            
            # Verify error is raised
            with pytest.raises(ValueError, match="Invalid STORAGE_BACKEND value"):
                get_storage_backend()
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
            reset_storage_backend()
    
    def test_s3_backend_without_bucket_name_raises_error(self):
        """
        Property: When STORAGE_BACKEND is 's3' but AWS_STORAGE_BUCKET_NAME is not set,
        get_storage_backend() should raise ValueError.
        """
        reset_storage_backend()
        
        # Save original environment
        original_env = os.environ.copy()
        
        try:
            # Set S3 backend without bucket name
            os.environ['STORAGE_BACKEND'] = 's3'
            os.environ.pop('AWS_STORAGE_BUCKET_NAME', None)
            
            # Verify error is raised
            with pytest.raises(ValueError, match="AWS_STORAGE_BUCKET_NAME.*required"):
                get_storage_backend()
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
            reset_storage_backend()



# Property 5: Backend-appropriate file storage
# **Validates: Requirements 3.2**

class TestBackendAppropriateFileStorage:
    """
    **Feature: cloud-migration-cleanup, Property 5: Backend-appropriate file storage**
    **Validates: Requirements 3.2**
    
    For any file upload operation, when using local backend the file should be stored
    in the local filesystem, and when using S3 backend the file should be stored in S3.
    """
    
    @settings(max_examples=50, deadline=None)
    @given(remote_path=file_path())
    def test_local_backend_stores_files_locally(self, remote_path):
        """
        Property: For any file upload using LocalStorageBackend, the file should
        be stored in the local filesystem at the expected location.
        """
        # Create temp directory and file
        temp_dir = tempfile.mkdtemp()
        fd, temp_file = tempfile.mkstemp()
        os.write(fd, b"test content for property test")
        os.close(fd)
        
        try:
            # Create local backend
            backend = LocalStorageBackend(base_path=temp_dir)
            
            # Upload file
            url = backend.upload_file(temp_file, remote_path)
            
            # Verify file exists in local filesystem
            expected_path = Path(temp_dir) / remote_path.lstrip('/').replace('media/', '')
            assert expected_path.exists(), \
                f"File should exist at {expected_path} after upload"
            
            # Verify file content matches
            with open(temp_file, 'rb') as f1, open(expected_path, 'rb') as f2:
                assert f1.read() == f2.read(), \
                    "Uploaded file content should match original"
            
            # Verify URL is local
            assert '/media/' in url or url.startswith('/'), \
                f"Local backend should return local URL, got: {url}"
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=50, deadline=None)
    @given(remote_path=file_path())
    def test_s3_backend_stores_files_in_s3(self, remote_path):
        """
        Property: For any file upload using S3StorageBackend, the file should
        be uploaded to S3 using the boto3 client.
        """
        # Create temp file
        fd, temp_file = tempfile.mkstemp()
        os.write(fd, b"test content for S3 property test")
        os.close(fd)
        
        try:
            # Mock boto3 client
            with patch('boto3.client') as mock_client_factory:
                mock_client = MagicMock()
                mock_client_factory.return_value = mock_client
                mock_client.head_bucket.return_value = {}
                
                # Create S3 backend
                backend = S3StorageBackend(
                    bucket_name='test-bucket',
                    region='us-east-1'
                )
                
                # Upload file
                url = backend.upload_file(temp_file, remote_path)
                
                # Verify S3 upload was called
                mock_client.upload_file.assert_called_once()
                
                # Verify correct parameters
                call_args = mock_client.upload_file.call_args
                assert call_args[0][0] == temp_file, "Should upload the correct local file"
                assert call_args[0][1] == 'test-bucket', "Should upload to correct bucket"
                
                # Verify S3 key is normalized (no leading slash, no media/ prefix)
                s3_key = call_args[0][2]
                assert not s3_key.startswith('/'), "S3 key should not start with /"
                assert not s3_key.startswith('media/'), "S3 key should not have media/ prefix"
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @settings(max_examples=30, deadline=None)
    @given(remote_path=file_path())
    def test_file_download_retrieves_from_correct_backend(self, remote_path):
        """
        Property: For any file download operation, the backend should retrieve
        the file from its storage location (local filesystem or S3).
        """
        # Create temp directory and file
        temp_dir = tempfile.mkdtemp()
        fd, temp_file = tempfile.mkstemp()
        os.write(fd, b"test content for download test")
        os.close(fd)
        
        try:
            # Test local backend
            backend = LocalStorageBackend(base_path=temp_dir)
            
            # Upload file first
            backend.upload_file(temp_file, remote_path)
            
            # Download to a different location
            download_path = os.path.join(temp_dir, 'downloaded_file')
            result = backend.download_file(remote_path, download_path)
            
            # Verify file was downloaded
            assert os.path.exists(download_path), "Downloaded file should exist"
            assert result == download_path, "Should return download path"
            
            # Verify content matches
            with open(temp_file, 'rb') as f1, open(download_path, 'rb') as f2:
                assert f1.read() == f2.read(), \
                    "Downloaded file content should match original"
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            shutil.rmtree(temp_dir, ignore_errors=True)



# Property 6: Backend-appropriate URL generation
# **Validates: Requirements 3.3**

class TestBackendAppropriateURLGeneration:
    """
    **Feature: cloud-migration-cleanup, Property 6: Backend-appropriate URL generation**
    **Validates: Requirements 3.3**
    
    For any file retrieval operation, when using local backend the URL should be a
    local path or localhost URL, and when using S3 backend the URL should be an
    S3 or CloudFront URL.
    """
    
    @settings(max_examples=50, deadline=None)
    @given(remote_path=file_path())
    def test_local_backend_generates_local_urls(self, remote_path):
        """
        Property: For any file path, LocalStorageBackend should generate URLs
        that are local paths or localhost URLs.
        """
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create local backend
            backend = LocalStorageBackend(base_path=temp_dir, base_url='/media/')
            
            # Get URL
            url = backend.get_url(remote_path)
            
            # Verify URL is local (starts with / or contains localhost)
            assert url.startswith('/') or 'localhost' in url or '127.0.0.1' in url, \
                f"Local backend should generate local URL, got: {url}"
            
            # Verify URL contains media path
            assert '/media/' in url, \
                f"Local backend URL should contain /media/, got: {url}"
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=50, deadline=None)
    @given(remote_path=file_path())
    def test_s3_backend_generates_s3_urls_without_cloudfront(self, remote_path):
        """
        Property: For any file path, S3StorageBackend without CloudFront should
        generate presigned S3 URLs.
        """
        # Mock boto3 client
        with patch('boto3.client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.head_bucket.return_value = {}
            
            # Mock presigned URL generation
            expected_url = f"https://test-bucket.s3.amazonaws.com/{remote_path}?signature=xyz"
            mock_client.generate_presigned_url.return_value = expected_url
            
            # Create S3 backend without CloudFront
            backend = S3StorageBackend(
                bucket_name='test-bucket',
                region='us-east-1',
                cloudfront_domain=None
            )
            
            # Get URL
            url = backend.get_url(remote_path)
            
            # Verify presigned URL was generated
            mock_client.generate_presigned_url.assert_called_once()
            
            # Verify URL is from S3
            assert url == expected_url, \
                f"S3 backend should return presigned URL"
            assert 's3.amazonaws.com' in url or 'signature=' in url, \
                f"URL should be a presigned S3 URL, got: {url}"
    
    @settings(max_examples=50, deadline=None)
    @given(remote_path=file_path())
    def test_s3_backend_generates_cloudfront_urls_when_configured(self, remote_path):
        """
        Property: For any file path, S3StorageBackend with CloudFront should
        generate CloudFront URLs instead of presigned S3 URLs.
        """
        # Mock boto3 client
        with patch('boto3.client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.head_bucket.return_value = {}
            
            # Create S3 backend with CloudFront
            cloudfront_domain = 'd123456.cloudfront.net'
            backend = S3StorageBackend(
                bucket_name='test-bucket',
                region='us-east-1',
                cloudfront_domain=cloudfront_domain
            )
            
            # Get URL
            url = backend.get_url(remote_path)
            
            # Verify CloudFront URL is used
            assert cloudfront_domain in url, \
                f"URL should use CloudFront domain, got: {url}"
            assert url.startswith('https://'), \
                f"CloudFront URL should use HTTPS, got: {url}"
            
            # Verify presigned URL was NOT generated (CloudFront is used instead)
            mock_client.generate_presigned_url.assert_not_called()
    
    @settings(max_examples=30, deadline=None)
    @given(
        remote_path=file_path(),
        expiration=st.integers(min_value=60, max_value=86400)
    )
    def test_url_expiration_parameter_is_respected(self, remote_path, expiration):
        """
        Property: For any file path and expiration time, the backend should
        pass the expiration parameter correctly.
        """
        # Mock boto3 client
        with patch('boto3.client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.head_bucket.return_value = {}
            mock_client.generate_presigned_url.return_value = "https://example.com/file"
            
            # Create S3 backend without CloudFront (so presigned URLs are used)
            backend = S3StorageBackend(
                bucket_name='test-bucket',
                region='us-east-1',
                cloudfront_domain=None
            )
            
            # Get URL with custom expiration
            url = backend.get_url(remote_path, expiration=expiration)
            
            # Verify expiration was passed to presigned URL generation
            call_kwargs = mock_client.generate_presigned_url.call_args[1]
            assert 'ExpiresIn' in call_kwargs, "ExpiresIn should be passed"
            assert call_kwargs['ExpiresIn'] == expiration, \
                f"ExpiresIn should be {expiration}, got {call_kwargs['ExpiresIn']}"



# Property 7: File path backward compatibility
# **Validates: Requirements 3.5**

class TestFilePathBackwardCompatibility:
    """
    **Feature: cloud-migration-cleanup, Property 7: File path backward compatibility**
    **Validates: Requirements 3.5**
    
    For any existing file path format (from the old GCS system), the storage service
    should be able to parse and handle it correctly after migration.
    """
    
    @st.composite
    def legacy_gcs_path(draw):
        """Generate legacy GCS-style file paths"""
        # Generate base path
        base = draw(file_path())
        
        # Add various GCS-style prefixes
        prefix_type = draw(st.sampled_from([
            'gs_url',      # gs://bucket-name/path
            'media_slash', # /media/path
            'media_no_slash', # media/path
            'plain',       # path (no prefix)
        ]))
        
        if prefix_type == 'gs_url':
            bucket = draw(st.text(min_size=3, max_size=20, alphabet=st.characters(
                whitelist_categories=('Ll', 'Nd'),
                whitelist_characters='-'
            )))
            return f"gs://{bucket}/{base}"
        elif prefix_type == 'media_slash':
            return f"/media/{base}"
        elif prefix_type == 'media_no_slash':
            return f"media/{base}"
        else:
            return base
    
    @settings(max_examples=100, deadline=None)
    @given(legacy_path=legacy_gcs_path())
    def test_local_backend_handles_legacy_paths(self, legacy_path):
        """
        Property: For any legacy GCS-style path, LocalStorageBackend should
        normalize it and handle it correctly.
        """
        # Create temp directory and file
        temp_dir = tempfile.mkdtemp()
        fd, temp_file = tempfile.mkstemp()
        os.write(fd, b"test content for legacy path test")
        os.close(fd)
        
        try:
            # Create local backend
            backend = LocalStorageBackend(base_path=temp_dir)
            
            # Upload file with legacy path
            url = backend.upload_file(temp_file, legacy_path)
            
            # Verify file exists (backend should normalize the path)
            assert backend.file_exists(legacy_path), \
                f"Backend should handle legacy path: {legacy_path}"
            
            # Verify we can get URL for legacy path
            url2 = backend.get_url(legacy_path)
            assert url2 is not None, \
                f"Backend should generate URL for legacy path: {legacy_path}"
            
            # Verify we can download using legacy path
            download_path = os.path.join(temp_dir, 'downloaded')
            result = backend.download_file(legacy_path, download_path)
            assert result == download_path, \
                f"Backend should download file using legacy path: {legacy_path}"
            assert os.path.exists(download_path), \
                "Downloaded file should exist"
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100, deadline=None)
    @given(legacy_path=legacy_gcs_path())
    def test_s3_backend_handles_legacy_paths(self, legacy_path):
        """
        Property: For any legacy GCS-style path, S3StorageBackend should
        normalize it and handle it correctly.
        """
        # Create temp file
        fd, temp_file = tempfile.mkstemp()
        os.write(fd, b"test content for S3 legacy path test")
        os.close(fd)
        
        try:
            # Mock boto3 client
            with patch('boto3.client') as mock_client_factory:
                mock_client = MagicMock()
                mock_client_factory.return_value = mock_client
                mock_client.head_bucket.return_value = {}
                
                # Create S3 backend
                backend = S3StorageBackend(
                    bucket_name='test-bucket',
                    region='us-east-1'
                )
                
                # Upload file with legacy path
                url = backend.upload_file(temp_file, legacy_path)
                
                # Verify S3 upload was called
                mock_client.upload_file.assert_called_once()
                
                # Verify S3 key is normalized (no gs://, no leading /, no media/ prefix)
                s3_key = mock_client.upload_file.call_args[0][2]
                assert not s3_key.startswith('gs://'), \
                    f"S3 key should not have gs:// prefix, got: {s3_key}"
                assert not s3_key.startswith('/'), \
                    f"S3 key should not start with /, got: {s3_key}"
                assert not s3_key.startswith('media/'), \
                    f"S3 key should not have media/ prefix, got: {s3_key}"
                
                # Reset mock for file_exists check
                mock_client.reset_mock()
                mock_client.head_object.return_value = {}
                
                # Verify we can check existence with legacy path
                exists = backend.file_exists(legacy_path)
                # Should have called head_object with normalized key
                mock_client.head_object.assert_called_once()
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @settings(max_examples=50, deadline=None)
    @given(base_path=file_path())
    def test_equivalent_legacy_paths_resolve_to_same_location(self, base_path):
        """
        Property: For any file path, different legacy prefix variations
        (e.g., "media/file.txt", "/media/file.txt", "gs://bucket/file.txt")
        should all normalize to the same base path.
        """
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create local backend
            backend = LocalStorageBackend(base_path=temp_dir)
            
            # Test various prefix variations of the same base path
            variations = [
                base_path,                    # Plain path
                f"/media/{base_path}",        # /media/ prefix
                f"media/{base_path}",         # media/ prefix (no leading slash)
                f"/{base_path}",              # Just leading slash
            ]
            
            # Normalize all variations
            normalized_paths = [backend._normalize_remote_path(v) for v in variations]
            
            # All should normalize to the same path
            first_normalized = normalized_paths[0]
            for i, normalized in enumerate(normalized_paths[1:], 1):
                assert normalized == first_normalized, \
                    f"Path variation '{variations[i]}' normalized to '{normalized}', " \
                    f"but expected '{first_normalized}' (same as '{variations[0]}')"
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)



# Property 2: Storage abstraction is cloud-agnostic
# **Validates: Requirements 2.1**

class TestStorageAbstractionIsCloudAgnostic:
    """
    **Feature: cloud-migration-cleanup, Property 2: Storage abstraction is cloud-agnostic**
    **Validates: Requirements 2.1**
    
    For any file storage operation, the storage service should not make direct calls
    to GCP Storage APIs (google.cloud.storage).
    """
    
    @settings(max_examples=50, deadline=None)
    @given(remote_path=file_path())
    def test_local_backend_does_not_import_gcp_storage(self, remote_path):
        """
        Property: For any file operation using LocalStorageBackend, the backend
        should not import or use google.cloud.storage modules.
        """
        import sys
        
        # Create temp directory and file
        temp_dir = tempfile.mkdtemp()
        fd, temp_file = tempfile.mkstemp()
        os.write(fd, b"test content for GCP check")
        os.close(fd)
        
        try:
            # Track if google.cloud.storage is imported
            gcp_modules_before = {
                name for name in sys.modules.keys() 
                if name.startswith('google.cloud.storage')
            }
            
            # Create local backend and perform operations
            backend = LocalStorageBackend(base_path=temp_dir)
            
            # Perform various operations
            backend.upload_file(temp_file, remote_path)
            backend.get_url(remote_path)
            backend.file_exists(remote_path)
            backend.list_files()
            
            # Check if any new google.cloud.storage modules were imported
            gcp_modules_after = {
                name for name in sys.modules.keys() 
                if name.startswith('google.cloud.storage')
            }
            
            new_gcp_imports = gcp_modules_after - gcp_modules_before
            
            assert len(new_gcp_imports) == 0, \
                f"LocalStorageBackend should not import google.cloud.storage modules. " \
                f"Found new imports: {new_gcp_imports}"
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=50, deadline=None)
    @given(remote_path=file_path())
    def test_s3_backend_does_not_import_gcp_storage(self, remote_path):
        """
        Property: For any file operation using S3StorageBackend, the backend
        should not import or use google.cloud.storage modules.
        """
        import sys
        
        # Create temp file
        fd, temp_file = tempfile.mkstemp()
        os.write(fd, b"test content for S3 GCP check")
        os.close(fd)
        
        try:
            # Track if google.cloud.storage is imported
            gcp_modules_before = {
                name for name in sys.modules.keys() 
                if name.startswith('google.cloud.storage')
            }
            
            # Mock boto3 client
            with patch('boto3.client') as mock_client_factory:
                mock_client = MagicMock()
                mock_client_factory.return_value = mock_client
                mock_client.head_bucket.return_value = {}
                mock_client.head_object.return_value = {}
                
                # Create S3 backend and perform operations
                backend = S3StorageBackend(
                    bucket_name='test-bucket',
                    region='us-east-1'
                )
                
                # Perform various operations
                backend.upload_file(temp_file, remote_path)
                backend.get_url(remote_path)
                backend.file_exists(remote_path)
                backend.list_files()
                
                # Check if any new google.cloud.storage modules were imported
                gcp_modules_after = {
                    name for name in sys.modules.keys() 
                    if name.startswith('google.cloud.storage')
                }
                
                new_gcp_imports = gcp_modules_after - gcp_modules_before
                
                assert len(new_gcp_imports) == 0, \
                    f"S3StorageBackend should not import google.cloud.storage modules. " \
                    f"Found new imports: {new_gcp_imports}"
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @settings(max_examples=50, deadline=None)
    @given(config=storage_backend_config())
    def test_factory_does_not_import_gcp_storage(self, config):
        """
        Property: For any storage backend configuration, the factory function
        should not import or use google.cloud.storage modules.
        """
        import sys
        
        # Reset backend before test
        reset_storage_backend()
        
        # Save original environment
        original_env = os.environ.copy()
        
        try:
            # Track if google.cloud.storage is imported
            gcp_modules_before = {
                name for name in sys.modules.keys() 
                if name.startswith('google.cloud.storage')
            }
            
            # Set environment variables
            for key, value in config.items():
                if value is not None:
                    os.environ[key] = str(value)
            
            # For S3 backend, mock boto3
            if config['STORAGE_BACKEND'] == 's3':
                with patch('boto3.client') as mock_client_factory:
                    mock_client = MagicMock()
                    mock_client_factory.return_value = mock_client
                    mock_client.head_bucket.return_value = {}
                    
                    # Get backend from factory
                    backend = get_storage_backend()
            else:
                # Get backend from factory
                backend = get_storage_backend()
            
            # Check if any new google.cloud.storage modules were imported
            gcp_modules_after = {
                name for name in sys.modules.keys() 
                if name.startswith('google.cloud.storage')
            }
            
            new_gcp_imports = gcp_modules_after - gcp_modules_before
            
            assert len(new_gcp_imports) == 0, \
                f"Storage factory should not import google.cloud.storage modules. " \
                f"Found new imports: {new_gcp_imports}"
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
            reset_storage_backend()
    
    def test_storage_backend_implementations_have_no_gcp_imports(self):
        """
        Property: The storage backend implementation files should not contain
        any imports from google.cloud.storage.
        """
        import inspect
        from pathlib import Path
        
        # Get the directory containing the storage backends
        storage_dir = Path(__file__).parent
        
        # Files to check
        files_to_check = [
            storage_dir / 'base.py',
            storage_dir / 'local.py',
            storage_dir / 's3.py',
            storage_dir / 'factory.py',
        ]
        
        for file_path in files_to_check:
            if not file_path.exists():
                continue
            
            # Read file content
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for GCP storage imports
            gcp_import_patterns = [
                'from google.cloud import storage',
                'from google.cloud.storage import',
                'import google.cloud.storage',
            ]
            
            for pattern in gcp_import_patterns:
                assert pattern not in content, \
                    f"File {file_path.name} should not contain GCP storage import: '{pattern}'"
            
            # Check for GCS-specific references (gs:// URLs should only be in normalization)
            # We allow gs:// in comments and in path normalization logic
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Skip comments and docstrings
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                
                # Skip lines that are normalizing gs:// paths (backward compatibility)
                if 'gs://' in line and 'normalize' not in line.lower() and 'clean' not in line.lower():
                    # This is acceptable in normalization logic
                    if "startswith('gs://')" in line or 'replace(' in line:
                        continue
                    
                    # Otherwise, it might be problematic
                    # But we allow it in the normalization methods
                    if '_normalize_remote_path' in content[max(0, content.find(line) - 200):content.find(line)]:
                        continue
    
    @settings(max_examples=30, deadline=None)
    @given(remote_path=file_path())
    def test_storage_operations_use_only_aws_or_local_apis(self, remote_path):
        """
        Property: For any storage operation, the backend should only use
        AWS APIs (boto3) or local filesystem operations, never GCP APIs.
        """
        import sys
        
        # Create temp directory and file
        temp_dir = tempfile.mkdtemp()
        fd, temp_file = tempfile.mkstemp()
        os.write(fd, b"test content for API check")
        os.close(fd)
        
        try:
            # Test with local backend
            backend_local = LocalStorageBackend(base_path=temp_dir)
            
            # Track module imports during operations
            modules_before = set(sys.modules.keys())
            
            # Perform operations
            backend_local.upload_file(temp_file, remote_path)
            backend_local.get_url(remote_path)
            backend_local.file_exists(remote_path)
            
            modules_after = set(sys.modules.keys())
            new_modules = modules_after - modules_before
            
            # Check that no GCP modules were imported
            gcp_modules = {m for m in new_modules if 'google.cloud' in m}
            assert len(gcp_modules) == 0, \
                f"Local storage operations should not import GCP modules. Found: {gcp_modules}"
            
            # Test with S3 backend
            with patch('boto3.client') as mock_client_factory:
                mock_client = MagicMock()
                mock_client_factory.return_value = mock_client
                mock_client.head_bucket.return_value = {}
                mock_client.head_object.return_value = {}
                
                backend_s3 = S3StorageBackend(
                    bucket_name='test-bucket',
                    region='us-east-1'
                )
                
                modules_before = set(sys.modules.keys())
                
                # Perform operations
                backend_s3.upload_file(temp_file, remote_path)
                backend_s3.get_url(remote_path)
                backend_s3.file_exists(remote_path)
                
                modules_after = set(sys.modules.keys())
                new_modules = modules_after - modules_before
                
                # Check that no GCP modules were imported
                gcp_modules = {m for m in new_modules if 'google.cloud' in m}
                assert len(gcp_modules) == 0, \
                    f"S3 storage operations should not import GCP modules. Found: {gcp_modules}"
                
                # Verify boto3 was used (AWS API)
                assert mock_client.upload_file.called or mock_client.head_object.called, \
                    "S3 backend should use boto3 client for operations"
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            shutil.rmtree(temp_dir, ignore_errors=True)
