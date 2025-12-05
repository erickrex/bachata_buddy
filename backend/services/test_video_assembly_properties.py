"""
Property-based tests for Video Assembly Service.

**Feature: job-integration**

These tests verify the correctness properties of the VideoAssemblyService
as defined in the design document.
"""

import os
import pytest
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume

from .video_assembly_service import VideoAssemblyService, VideoAssemblyError
from .storage.base import StorageBackend


# =============================================================================
# Hypothesis Strategies for generating test data
# =============================================================================

@st.composite
def valid_task_id(draw):
    """Generate valid task IDs (UUID-like strings)."""
    chars = 'abcdef0123456789'
    parts = [
        draw(st.text(alphabet=chars, min_size=8, max_size=8)),
        draw(st.text(alphabet=chars, min_size=4, max_size=4)),
        draw(st.text(alphabet=chars, min_size=4, max_size=4)),
        draw(st.text(alphabet=chars, min_size=4, max_size=4)),
        draw(st.text(alphabet=chars, min_size=12, max_size=12)),
    ]
    return '-'.join(parts)


@st.composite
def safe_path_component(draw):
    """Generate safe path components (no special characters)."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'),
        min_size=1,
        max_size=20
    ))


@st.composite
def valid_file_path(draw):
    """Generate valid file paths (no directory traversal or absolute paths)."""
    components = draw(st.lists(safe_path_component(), min_size=1, max_size=4))
    extension = draw(st.sampled_from(['.mp4', '.mp3', '.wav', '.avi']))
    return '/'.join(components) + extension


@st.composite
def valid_move(draw):
    """Generate a valid move dictionary."""
    return {
        'video_path': draw(valid_file_path()),
        'start_time': draw(st.floats(min_value=0.0, max_value=300.0)),
        'duration': draw(st.floats(min_value=0.5, max_value=30.0))
    }


@st.composite
def valid_output_config(draw):
    """Generate a valid output_config dictionary."""
    return {
        'output_path': draw(valid_file_path()),
        'video_codec': draw(st.sampled_from(['libx264', 'libx265', 'copy'])),
        'audio_codec': draw(st.sampled_from(['aac', 'mp3', 'opus'])),
        'video_bitrate': draw(st.sampled_from(['1M', '2M', '4M'])),
        'audio_bitrate': draw(st.sampled_from(['128k', '192k', '256k']))
    }


@st.composite
def valid_blueprint(draw):
    """Generate a complete valid blueprint."""
    return {
        'task_id': draw(valid_task_id()),
        'audio_path': draw(valid_file_path()),
        'moves': draw(st.lists(valid_move(), min_size=1, max_size=10)),
        'output_config': draw(valid_output_config())
    }


@st.composite
def path_with_traversal(draw):
    """Generate paths containing directory traversal patterns."""
    base = draw(valid_file_path())
    traversal = draw(st.sampled_from(['../', '../..', 'foo/../bar', 'a/../../b']))
    position = draw(st.sampled_from(['prefix', 'middle', 'suffix']))
    
    if position == 'prefix':
        return traversal + '/' + base
    elif position == 'middle':
        parts = base.split('/')
        if len(parts) > 1:
            return parts[0] + '/' + traversal + '/' + '/'.join(parts[1:])
        return traversal + '/' + base
    else:
        return base.rsplit('.', 1)[0] + '/' + traversal + '.mp4'


@st.composite
def absolute_path(draw):
    """Generate absolute paths (starting with /)."""
    base = draw(valid_file_path())
    return '/' + base


# =============================================================================
# Mock Storage Backend for testing
# =============================================================================

class MockStorageBackend(StorageBackend):
    """Mock storage backend for testing."""
    
    def upload_file(self, local_path: str, remote_path: str) -> str:
        return f"https://storage.example.com/{remote_path}"
    
    def download_file(self, remote_path: str, local_path: str) -> str:
        # Create parent directory if needed
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        # Create a dummy file
        with open(local_path, 'wb') as f:
            f.write(b'dummy content')
        return local_path
    
    def get_url(self, remote_path: str, expiration: int = 3600) -> str:
        return f"https://storage.example.com/{remote_path}"
    
    def file_exists(self, remote_path: str) -> bool:
        return True
    
    def delete_file(self, remote_path: str) -> bool:
        return True
    
    def list_files(self, prefix: str = "") -> list[str]:
        return []


# =============================================================================
# Property 2: Blueprint validation rejects missing fields
# **Validates: Requirements 3.2**
# =============================================================================

class TestBlueprintValidationMissingFields:
    """
    **Feature: job-integration, Property 2: Blueprint validation rejects missing fields**
    **Validates: Requirements 3.2**
    
    For any blueprint missing one or more required fields (task_id, audio_path, 
    moves, output_config), validation SHALL return is_valid=False with a 
    descriptive error message.
    """
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_missing_task_id_rejected(self, blueprint):
        """
        Property: Blueprints missing task_id should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Remove task_id
        del blueprint['task_id']
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, "Blueprint without task_id should be invalid"
        assert error_msg is not None, "Error message should be provided"
        assert 'task_id' in error_msg.lower(), f"Error should mention task_id: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_missing_audio_path_rejected(self, blueprint):
        """
        Property: Blueprints missing audio_path should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Remove audio_path
        del blueprint['audio_path']
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, "Blueprint without audio_path should be invalid"
        assert error_msg is not None, "Error message should be provided"
        assert 'audio_path' in error_msg.lower(), f"Error should mention audio_path: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_missing_moves_rejected(self, blueprint):
        """
        Property: Blueprints missing moves should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Remove moves
        del blueprint['moves']
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, "Blueprint without moves should be invalid"
        assert error_msg is not None, "Error message should be provided"
        assert 'moves' in error_msg.lower(), f"Error should mention moves: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_missing_output_config_rejected(self, blueprint):
        """
        Property: Blueprints missing output_config should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Remove output_config
        del blueprint['output_config']
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, "Blueprint without output_config should be invalid"
        assert error_msg is not None, "Error message should be provided"
        assert 'output_config' in error_msg.lower(), f"Error should mention output_config: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_empty_moves_rejected(self, blueprint):
        """
        Property: Blueprints with empty moves array should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Set moves to empty list
        blueprint['moves'] = []
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, "Blueprint with empty moves should be invalid"
        assert error_msg is not None, "Error message should be provided"
        assert 'moves' in error_msg.lower() or 'empty' in error_msg.lower(), \
            f"Error should mention moves or empty: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_missing_output_path_rejected(self, blueprint):
        """
        Property: Blueprints missing output_config.output_path should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Remove output_path from output_config
        del blueprint['output_config']['output_path']
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, "Blueprint without output_path should be invalid"
        assert error_msg is not None, "Error message should be provided"
        assert 'output_path' in error_msg.lower(), f"Error should mention output_path: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_missing_video_path_in_move_rejected(self, blueprint):
        """
        Property: Blueprints with moves missing video_path should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Remove video_path from first move
        del blueprint['moves'][0]['video_path']
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, "Blueprint with move missing video_path should be invalid"
        assert error_msg is not None, "Error message should be provided"
        assert 'video_path' in error_msg.lower(), f"Error should mention video_path: {error_msg}"


# =============================================================================
# Property 3: Blueprint validation rejects invalid paths
# **Validates: Requirements 3.3**
# =============================================================================

class TestBlueprintValidationInvalidPaths:
    """
    **Feature: job-integration, Property 3: Blueprint validation rejects invalid paths**
    **Validates: Requirements 3.3**
    
    For any blueprint containing paths with directory traversal sequences (..) 
    or absolute paths starting with /, validation SHALL return is_valid=False 
    with a security error.
    """
    
    @settings(max_examples=5, deadline=None)
    @given(
        blueprint=valid_blueprint(),
        bad_path=path_with_traversal()
    )
    def test_audio_path_with_traversal_rejected(self, blueprint, bad_path):
        """
        Property: Blueprints with directory traversal in audio_path should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Set audio_path to path with traversal
        blueprint['audio_path'] = bad_path
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, f"Blueprint with traversal in audio_path should be invalid: {bad_path}"
        assert error_msg is not None, "Error message should be provided"
        assert 'security' in error_msg.lower() or '..' in error_msg, \
            f"Error should mention security or traversal pattern: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(
        blueprint=valid_blueprint(),
        bad_path=absolute_path()
    )
    def test_audio_path_absolute_rejected(self, blueprint, bad_path):
        """
        Property: Blueprints with absolute audio_path should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Set audio_path to absolute path
        blueprint['audio_path'] = bad_path
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, f"Blueprint with absolute audio_path should be invalid: {bad_path}"
        assert error_msg is not None, "Error message should be provided"
        assert 'security' in error_msg.lower() or 'absolute' in error_msg.lower(), \
            f"Error should mention security or absolute: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(
        blueprint=valid_blueprint(),
        bad_path=path_with_traversal()
    )
    def test_output_path_with_traversal_rejected(self, blueprint, bad_path):
        """
        Property: Blueprints with directory traversal in output_path should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Set output_path to path with traversal
        blueprint['output_config']['output_path'] = bad_path
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, f"Blueprint with traversal in output_path should be invalid: {bad_path}"
        assert error_msg is not None, "Error message should be provided"
        assert 'security' in error_msg.lower() or '..' in error_msg, \
            f"Error should mention security or traversal pattern: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(
        blueprint=valid_blueprint(),
        bad_path=absolute_path()
    )
    def test_output_path_absolute_rejected(self, blueprint, bad_path):
        """
        Property: Blueprints with absolute output_path should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Set output_path to absolute path
        blueprint['output_config']['output_path'] = bad_path
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, f"Blueprint with absolute output_path should be invalid: {bad_path}"
        assert error_msg is not None, "Error message should be provided"
        assert 'security' in error_msg.lower() or 'absolute' in error_msg.lower(), \
            f"Error should mention security or absolute: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(
        blueprint=valid_blueprint(),
        bad_path=path_with_traversal()
    )
    def test_video_path_with_traversal_rejected(self, blueprint, bad_path):
        """
        Property: Blueprints with directory traversal in move video_path should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Set first move's video_path to path with traversal
        blueprint['moves'][0]['video_path'] = bad_path
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, f"Blueprint with traversal in video_path should be invalid: {bad_path}"
        assert error_msg is not None, "Error message should be provided"
        assert 'security' in error_msg.lower() or '..' in error_msg, \
            f"Error should mention security or traversal pattern: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(
        blueprint=valid_blueprint(),
        bad_path=absolute_path()
    )
    def test_video_path_absolute_rejected(self, blueprint, bad_path):
        """
        Property: Blueprints with absolute move video_path should be rejected.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        # Set first move's video_path to absolute path
        blueprint['moves'][0]['video_path'] = bad_path
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is False, f"Blueprint with absolute video_path should be invalid: {bad_path}"
        assert error_msg is not None, "Error message should be provided"
        assert 'security' in error_msg.lower() or 'absolute' in error_msg.lower(), \
            f"Error should mention security or absolute: {error_msg}"
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_valid_blueprint_accepted(self, blueprint):
        """
        Property: Valid blueprints with safe paths should be accepted.
        """
        storage = MockStorageBackend()
        service = VideoAssemblyService(storage)
        
        is_valid, error_msg = service.validate_blueprint(blueprint)
        
        assert is_valid is True, f"Valid blueprint should be accepted, got error: {error_msg}"
        assert error_msg is None, f"No error message expected for valid blueprint: {error_msg}"


# =============================================================================
# Property 4: Successful assembly returns valid URL
# **Validates: Requirements 1.2**
# =============================================================================

class TestSuccessfulAssemblyReturnsURL:
    """
    **Feature: job-integration, Property 4: Successful assembly returns valid URL**
    **Validates: Requirements 1.2**
    
    For any valid blueprint with existing source files, video assembly SHALL 
    return a non-empty string URL pointing to the output location.
    """
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_successful_assembly_returns_url(self, blueprint):
        """
        Property: Successful video assembly should return a non-empty URL string.
        """
        # Create a mock storage that simulates successful operations
        mock_storage = Mock(spec=StorageBackend)
        
        # Track temp directory for cleanup verification
        temp_dir = tempfile.mkdtemp(prefix='test_assembly_')
        
        try:
            service = VideoAssemblyService(mock_storage, temp_dir=temp_dir)
            
            # Mock download_file to create actual files
            def mock_download(remote_path, local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(b'dummy video content')
                return local_path
            
            mock_storage.download_file.side_effect = mock_download
            
            # Mock upload_file to return a URL
            expected_url = f"https://storage.example.com/{blueprint['output_config']['output_path']}"
            mock_storage.upload_file.return_value = expected_url
            
            # Mock FFmpeg subprocess calls
            with patch('subprocess.run') as mock_run:
                # Make subprocess.run create the expected output files
                def mock_subprocess_run(cmd, **kwargs):
                    # Find the output file (last argument before -y flag or last argument)
                    output_file = cmd[-1]
                    if output_file.endswith('.mp4'):
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                        with open(output_file, 'wb') as f:
                            f.write(b'mock video output')
                    
                    result = Mock()
                    result.returncode = 0
                    result.stdout = ''
                    result.stderr = ''
                    return result
                
                mock_run.side_effect = mock_subprocess_run
                
                # Execute assembly
                result_url = service.assemble_video(blueprint)
                
                # Verify result is a non-empty string
                assert isinstance(result_url, str), f"Result should be a string, got {type(result_url)}"
                assert len(result_url) > 0, "Result URL should not be empty"
                assert result_url == expected_url, f"Expected {expected_url}, got {result_url}"
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


# =============================================================================
# Property 5: Failed assembly includes error details
# **Validates: Requirements 1.3, 6.2**
# =============================================================================

class TestFailedAssemblyIncludesErrorDetails:
    """
    **Feature: job-integration, Property 5: Failed assembly includes error details**
    **Validates: Requirements 1.3, 6.2**
    
    For any blueprint that causes assembly failure (missing files, FFmpeg errors), 
    the error response SHALL contain a non-empty error message describing the failure.
    """
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_download_failure_includes_error_details(self, blueprint):
        """
        Property: When file download fails, error should include details about which file failed.
        """
        mock_storage = Mock(spec=StorageBackend)
        temp_dir = tempfile.mkdtemp(prefix='test_assembly_')
        
        try:
            service = VideoAssemblyService(mock_storage, temp_dir=temp_dir)
            
            # Mock download_file to fail
            failed_path = blueprint['audio_path']
            mock_storage.download_file.side_effect = Exception(f"File not found: {failed_path}")
            
            # Execute assembly and expect error
            with pytest.raises(VideoAssemblyError) as exc_info:
                service.assemble_video(blueprint)
            
            error_msg = str(exc_info.value)
            
            # Verify error message is non-empty and descriptive
            assert len(error_msg) > 0, "Error message should not be empty"
            assert failed_path in error_msg or 'audio' in error_msg.lower(), \
                f"Error should mention the failed file: {error_msg}"
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_ffmpeg_failure_includes_error_details(self, blueprint):
        """
        Property: When FFmpeg fails, error should include FFmpeg error output.
        """
        mock_storage = Mock(spec=StorageBackend)
        temp_dir = tempfile.mkdtemp(prefix='test_assembly_')
        
        try:
            service = VideoAssemblyService(mock_storage, temp_dir=temp_dir)
            
            # Mock download_file to succeed
            def mock_download(remote_path, local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(b'dummy content')
                return local_path
            
            mock_storage.download_file.side_effect = mock_download
            
            # Mock FFmpeg to fail
            with patch('subprocess.run') as mock_run:
                import subprocess
                mock_run.side_effect = subprocess.CalledProcessError(
                    returncode=1,
                    cmd=['ffmpeg'],
                    stderr='FFmpeg error: Invalid input file format'
                )
                
                # Execute assembly and expect error
                with pytest.raises(VideoAssemblyError) as exc_info:
                    service.assemble_video(blueprint)
                
                error_msg = str(exc_info.value)
                
                # Verify error message is non-empty
                assert len(error_msg) > 0, "Error message should not be empty"
                # Error should mention FFmpeg or the failure
                assert 'ffmpeg' in error_msg.lower() or 'failed' in error_msg.lower(), \
                    f"Error should mention FFmpeg or failure: {error_msg}"
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


# =============================================================================
# Property 6: Temporary files cleaned up on success
# **Validates: Requirements 8.4**
# =============================================================================

class TestCleanupOnSuccess:
    """
    **Feature: job-integration, Property 6: Temporary files cleaned up on success**
    **Validates: Requirements 8.4**
    
    For any successful video assembly, the temporary directory used for 
    intermediate files SHALL be empty or deleted after completion.
    """
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_temp_files_cleaned_on_success(self, blueprint):
        """
        Property: After successful assembly, temp directory should be empty or deleted.
        """
        mock_storage = Mock(spec=StorageBackend)
        temp_dir = tempfile.mkdtemp(prefix='test_assembly_')
        
        try:
            service = VideoAssemblyService(mock_storage, temp_dir=temp_dir)
            
            # Mock download_file to create actual files
            def mock_download(remote_path, local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(b'dummy content')
                return local_path
            
            mock_storage.download_file.side_effect = mock_download
            mock_storage.upload_file.return_value = "https://storage.example.com/output.mp4"
            
            # Mock FFmpeg subprocess calls
            with patch('subprocess.run') as mock_run:
                def mock_subprocess_run(cmd, **kwargs):
                    output_file = cmd[-1]
                    if output_file.endswith('.mp4'):
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                        with open(output_file, 'wb') as f:
                            f.write(b'mock video output')
                    
                    result = Mock()
                    result.returncode = 0
                    result.stdout = ''
                    result.stderr = ''
                    return result
                
                mock_run.side_effect = mock_subprocess_run
                
                # Execute assembly
                service.assemble_video(blueprint)
                
                # Verify temp directory is empty or doesn't exist
                if os.path.exists(temp_dir):
                    contents = os.listdir(temp_dir)
                    assert len(contents) == 0, \
                        f"Temp directory should be empty after success, found: {contents}"
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


# =============================================================================
# Property 7: Temporary files cleaned up on error
# **Validates: Requirements 6.5**
# =============================================================================

class TestCleanupOnError:
    """
    **Feature: job-integration, Property 7: Temporary files cleaned up on error**
    **Validates: Requirements 6.5**
    
    For any video assembly that fails with an error, the temporary directory 
    used for intermediate files SHALL be empty or deleted before the error is raised.
    """
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_temp_files_cleaned_on_download_error(self, blueprint):
        """
        Property: After failed download, temp directory should be empty or deleted.
        """
        mock_storage = Mock(spec=StorageBackend)
        temp_dir = tempfile.mkdtemp(prefix='test_assembly_')
        
        try:
            service = VideoAssemblyService(mock_storage, temp_dir=temp_dir)
            
            # Mock download_file to fail after creating some files
            call_count = [0]
            def mock_download(remote_path, local_path):
                call_count[0] += 1
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                # Create file first, then fail on second call
                if call_count[0] > 1:
                    raise Exception("Download failed")
                with open(local_path, 'wb') as f:
                    f.write(b'dummy content')
                return local_path
            
            mock_storage.download_file.side_effect = mock_download
            
            # Execute assembly and expect error
            with pytest.raises(VideoAssemblyError):
                service.assemble_video(blueprint)
            
            # Verify temp directory is empty or doesn't exist
            if os.path.exists(temp_dir):
                contents = os.listdir(temp_dir)
                assert len(contents) == 0, \
                    f"Temp directory should be empty after error, found: {contents}"
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_temp_files_cleaned_on_ffmpeg_error(self, blueprint):
        """
        Property: After FFmpeg failure, temp directory should be empty or deleted.
        """
        mock_storage = Mock(spec=StorageBackend)
        temp_dir = tempfile.mkdtemp(prefix='test_assembly_')
        
        try:
            service = VideoAssemblyService(mock_storage, temp_dir=temp_dir)
            
            # Mock download_file to succeed and create files
            def mock_download(remote_path, local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(b'dummy content')
                return local_path
            
            mock_storage.download_file.side_effect = mock_download
            
            # Mock FFmpeg to fail
            with patch('subprocess.run') as mock_run:
                import subprocess
                mock_run.side_effect = subprocess.CalledProcessError(
                    returncode=1,
                    cmd=['ffmpeg'],
                    stderr='FFmpeg error'
                )
                
                # Execute assembly and expect error
                with pytest.raises(VideoAssemblyError):
                    service.assemble_video(blueprint)
                
                # Verify temp directory is empty or doesn't exist
                if os.path.exists(temp_dir):
                    contents = os.listdir(temp_dir)
                    assert len(contents) == 0, \
                        f"Temp directory should be empty after error, found: {contents}"
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    def test_temp_files_cleaned_on_upload_error(self, blueprint):
        """
        Property: After upload failure, temp directory should be empty or deleted.
        """
        mock_storage = Mock(spec=StorageBackend)
        temp_dir = tempfile.mkdtemp(prefix='test_assembly_')
        
        try:
            service = VideoAssemblyService(mock_storage, temp_dir=temp_dir)
            
            # Mock download_file to succeed
            def mock_download(remote_path, local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(b'dummy content')
                return local_path
            
            mock_storage.download_file.side_effect = mock_download
            
            # Mock upload to fail
            mock_storage.upload_file.side_effect = Exception("Upload failed")
            
            # Mock FFmpeg subprocess calls to succeed
            with patch('subprocess.run') as mock_run:
                def mock_subprocess_run(cmd, **kwargs):
                    output_file = cmd[-1]
                    if output_file.endswith('.mp4'):
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                        with open(output_file, 'wb') as f:
                            f.write(b'mock video output')
                    
                    result = Mock()
                    result.returncode = 0
                    result.stdout = ''
                    result.stderr = ''
                    return result
                
                mock_run.side_effect = mock_subprocess_run
                
                # Execute assembly and expect error
                with pytest.raises(VideoAssemblyError):
                    service.assemble_video(blueprint)
                
                # Verify temp directory is empty or doesn't exist
                if os.path.exists(temp_dir):
                    contents = os.listdir(temp_dir)
                    assert len(contents) == 0, \
                        f"Temp directory should be empty after error, found: {contents}"
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


# =============================================================================
# Property 8: Task error recording
# **Validates: Requirements 4.3**
# =============================================================================

class TestTaskErrorRecording:
    """
    **Feature: job-integration, Property 8: Task error recording**
    **Validates: Requirements 4.3**
    
    For any video assembly error, the corresponding ChoreographyTask record 
    SHALL have a non-empty error field containing the error details.
    """
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    @pytest.mark.django_db
    def test_task_error_recorded_on_download_failure(self, blueprint):
        """
        Property: When download fails, task error field should contain error details.
        """
        from django.contrib.auth import get_user_model
        from apps.choreography.models import ChoreographyTask
        
        User = get_user_model()
        
        # Create a test user
        user = User.objects.create_user(
            username=f"testuser_{blueprint['task_id'][:8]}",
            email=f"test_{blueprint['task_id'][:8]}@example.com",
            password="testpass123"
        )
        
        # Create a task
        task = ChoreographyTask.objects.create(
            task_id=blueprint['task_id'],
            user=user,
            status='started',
            progress=0,
            stage='initializing'
        )
        
        mock_storage = Mock(spec=StorageBackend)
        temp_dir = tempfile.mkdtemp(prefix='test_assembly_')
        
        try:
            service = VideoAssemblyService(mock_storage, temp_dir=temp_dir)
            
            # Mock download_file to fail
            error_message = f"Failed to download file: {blueprint['audio_path']}"
            mock_storage.download_file.side_effect = Exception(error_message)
            
            # Create a progress callback that updates the task
            def progress_callback(stage, progress, message):
                task.stage = stage
                task.progress = progress
                task.message = message
                task.save()
            
            # Execute assembly and expect error
            try:
                service.assemble_video(blueprint, progress_callback=progress_callback)
                assert False, "Expected VideoAssemblyError to be raised"
            except VideoAssemblyError as e:
                # Update task with error
                task.status = 'failed'
                task.error = str(e)
                task.save()
            
            # Refresh task from database
            task.refresh_from_db()
            
            # Verify error field is non-empty and contains details
            assert task.error is not None, "Task error field should not be None"
            assert len(task.error) > 0, "Task error field should not be empty"
            assert task.status == 'failed', f"Task status should be 'failed', got {task.status}"
            
            # Error should contain meaningful information
            assert 'download' in task.error.lower() or 'file' in task.error.lower() or \
                   blueprint['audio_path'] in task.error, \
                   f"Error should mention download or file path: {task.error}"
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            task.delete()
            user.delete()
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    @pytest.mark.django_db
    def test_task_error_recorded_on_ffmpeg_failure(self, blueprint):
        """
        Property: When FFmpeg fails, task error field should contain FFmpeg error details.
        """
        from django.contrib.auth import get_user_model
        from apps.choreography.models import ChoreographyTask
        
        User = get_user_model()
        
        # Create a test user
        user = User.objects.create_user(
            username=f"testuser_{blueprint['task_id'][:8]}",
            email=f"test_{blueprint['task_id'][:8]}@example.com",
            password="testpass123"
        )
        
        # Create a task
        task = ChoreographyTask.objects.create(
            task_id=blueprint['task_id'],
            user=user,
            status='started',
            progress=0,
            stage='initializing'
        )
        
        mock_storage = Mock(spec=StorageBackend)
        temp_dir = tempfile.mkdtemp(prefix='test_assembly_')
        
        try:
            service = VideoAssemblyService(mock_storage, temp_dir=temp_dir)
            
            # Mock download_file to succeed
            def mock_download(remote_path, local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(b'dummy content')
                return local_path
            
            mock_storage.download_file.side_effect = mock_download
            
            # Create a progress callback that updates the task
            def progress_callback(stage, progress, message):
                task.stage = stage
                task.progress = progress
                task.message = message
                task.save()
            
            # Mock FFmpeg to fail
            with patch('subprocess.run') as mock_run:
                import subprocess
                ffmpeg_error = 'FFmpeg error: Invalid codec parameters'
                mock_run.side_effect = subprocess.CalledProcessError(
                    returncode=1,
                    cmd=['ffmpeg'],
                    stderr=ffmpeg_error
                )
                
                # Execute assembly and expect error
                try:
                    service.assemble_video(blueprint, progress_callback=progress_callback)
                    assert False, "Expected VideoAssemblyError to be raised"
                except VideoAssemblyError as e:
                    # Update task with error
                    task.status = 'failed'
                    task.error = str(e)
                    task.save()
                
                # Refresh task from database
                task.refresh_from_db()
                
                # Verify error field is non-empty and contains details
                assert task.error is not None, "Task error field should not be None"
                assert len(task.error) > 0, "Task error field should not be empty"
                assert task.status == 'failed', f"Task status should be 'failed', got {task.status}"
                
                # Error should mention FFmpeg or the failure
                assert 'ffmpeg' in task.error.lower() or 'failed' in task.error.lower(), \
                       f"Error should mention FFmpeg or failure: {task.error}"
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            task.delete()
            user.delete()
    
    @settings(max_examples=5, deadline=None)
    @given(blueprint=valid_blueprint())
    @pytest.mark.django_db
    def test_task_error_recorded_on_validation_failure(self, blueprint):
        """
        Property: When blueprint validation fails, task error field should contain validation error.
        """
        from django.contrib.auth import get_user_model
        from apps.choreography.models import ChoreographyTask
        
        User = get_user_model()
        
        # Create a test user
        user = User.objects.create_user(
            username=f"testuser_{blueprint['task_id'][:8]}",
            email=f"test_{blueprint['task_id'][:8]}@example.com",
            password="testpass123"
        )
        
        # Create a task
        task = ChoreographyTask.objects.create(
            task_id=blueprint['task_id'],
            user=user,
            status='started',
            progress=0,
            stage='initializing'
        )
        
        mock_storage = Mock(spec=StorageBackend)
        temp_dir = tempfile.mkdtemp(prefix='test_assembly_')
        
        try:
            service = VideoAssemblyService(mock_storage, temp_dir=temp_dir)
            
            # Make blueprint invalid by removing required field
            del blueprint['audio_path']
            
            # Validate blueprint first
            is_valid, error_msg = service.validate_blueprint(blueprint)
            
            if not is_valid:
                # Update task with validation error
                task.status = 'failed'
                task.error = f"Blueprint validation failed: {error_msg}"
                task.save()
                
                # Refresh task from database
                task.refresh_from_db()
                
                # Verify error field is non-empty and contains details
                assert task.error is not None, "Task error field should not be None"
                assert len(task.error) > 0, "Task error field should not be empty"
                assert task.status == 'failed', f"Task status should be 'failed', got {task.status}"
                
                # Error should mention validation
                assert 'validation' in task.error.lower() or 'audio_path' in task.error.lower(), \
                       f"Error should mention validation or missing field: {task.error}"
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            task.delete()
            user.delete()
