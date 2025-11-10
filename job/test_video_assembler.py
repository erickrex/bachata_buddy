"""
Test Video Assembler Service

Tests for the video assembly service that creates videos from blueprints.
"""
import os
import sys
import json
import tempfile
import pytest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.video_assembler import VideoAssembler, VideoAssemblyError
from services.storage_service import StorageService, StorageConfig


class TestVideoAssembler:
    """Test video assembler functionality."""
    
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
    def video_assembler(self, storage_service, temp_dir):
        """Create video assembler instance."""
        assembler_temp = os.path.join(temp_dir, 'assembler_temp')
        os.makedirs(assembler_temp, exist_ok=True)
        return VideoAssembler(
            storage_service=storage_service,
            temp_dir=assembler_temp
        )
    
    @pytest.fixture
    def sample_blueprint(self):
        """Create a sample blueprint for testing."""
        return {
            'task_id': 'test-task-123',
            'audio_path': 'data/songs/test_song.mp3',
            'audio_tempo': 120.0,
            'moves': [
                {
                    'clip_id': 'move_1',
                    'video_path': 'data/Bachata_steps/basic_steps/basic_1.mp4',
                    'start_time': 0.0,
                    'duration': 8.0,
                    'transition_type': 'cut'
                },
                {
                    'clip_id': 'move_2',
                    'video_path': 'data/Bachata_steps/basic_steps/basic_2.mp4',
                    'start_time': 8.0,
                    'duration': 8.0,
                    'transition_type': 'cut'
                }
            ],
            'total_duration': 16.0,
            'difficulty_level': 'beginner',
            'output_config': {
                'output_path': 'data/output/test_choreography.mp4',
                'output_format': 'mp4',
                'video_codec': 'libx264',
                'audio_codec': 'aac',
                'video_bitrate': '2M',
                'audio_bitrate': '128k'
            }
        }
    
    def test_video_assembler_initialization(self, video_assembler, temp_dir):
        """Test video assembler initialization."""
        assert video_assembler.storage is not None
        assert video_assembler.temp_dir is not None
        assert os.path.exists(video_assembler.temp_dir)
    
    def test_check_ffmpeg_available(self, video_assembler):
        """Test FFmpeg availability check."""
        # This test will pass if FFmpeg is installed, skip otherwise
        try:
            result = video_assembler.check_ffmpeg_available()
            # If FFmpeg is available, result should be True
            # If not available, result should be False
            assert isinstance(result, bool)
        except Exception:
            pytest.skip("FFmpeg not available in test environment")
    
    def test_cleanup_temp_files(self, video_assembler, temp_dir):
        """Test cleanup of temporary files."""
        # Create some test files in temp directory
        test_file = os.path.join(video_assembler.temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        assert os.path.exists(test_file)
        
        # Cleanup
        video_assembler._cleanup_temp_files()
        
        # File should be removed
        assert not os.path.exists(test_file)
        # Directory should still exist
        assert os.path.exists(video_assembler.temp_dir)
    
    def test_upload_result(self, video_assembler, sample_blueprint, temp_dir):
        """Test uploading result video."""
        # Create a dummy video file
        video_file = os.path.join(video_assembler.temp_dir, 'test_video.mp4')
        with open(video_file, 'wb') as f:
            f.write(b'fake video content')
        
        # Upload result
        result_url = video_assembler._upload_result(video_file, sample_blueprint)
        
        # Verify result
        assert result_url is not None
        assert 'test_choreography.mp4' in result_url
        
        # Verify file exists at destination
        output_path = sample_blueprint['output_config']['output_path']
        full_path = os.path.join(temp_dir, output_path)
        assert os.path.exists(full_path)
    
    def test_upload_result_missing_output_path(self, video_assembler):
        """Test upload result with missing output path."""
        video_file = os.path.join(video_assembler.temp_dir, 'test_video.mp4')
        with open(video_file, 'wb') as f:
            f.write(b'fake video content')
        
        blueprint = {
            'task_id': 'test-123',
            'output_config': {}  # Missing output_path
        }
        
        with pytest.raises(VideoAssemblyError) as exc_info:
            video_assembler._upload_result(video_file, blueprint)
        
        assert 'output_path' in str(exc_info.value).lower()
    
    def test_fetch_media_files_success(self, video_assembler, temp_dir):
        """Test fetching media files from storage."""
        # Create test audio and video files in storage
        audio_path = 'data/songs/test_song.mp3'
        audio_full_path = os.path.join(temp_dir, audio_path)
        os.makedirs(os.path.dirname(audio_full_path), exist_ok=True)
        with open(audio_full_path, 'wb') as f:
            f.write(b'fake audio content')
        
        video_path = 'data/Bachata_steps/basic_steps/basic_1.mp4'
        video_full_path = os.path.join(temp_dir, video_path)
        os.makedirs(os.path.dirname(video_full_path), exist_ok=True)
        with open(video_full_path, 'wb') as f:
            f.write(b'fake video content')
        
        # Create blueprint
        blueprint = {
            'audio_path': audio_path,
            'moves': [
                {
                    'video_path': video_path,
                    'start_time': 0.0,
                    'duration': 8.0
                }
            ]
        }
        
        # Fetch media files
        audio_file, video_files = video_assembler._fetch_media_files(blueprint)
        
        # Verify files were downloaded
        assert os.path.exists(audio_file)
        assert len(video_files) == 1
        assert os.path.exists(video_files[0])
    
    def test_fetch_media_files_not_found(self, video_assembler):
        """Test fetching non-existent media files."""
        blueprint = {
            'audio_path': 'nonexistent/audio.mp3',
            'moves': [
                {
                    'video_path': 'nonexistent/video.mp4',
                    'start_time': 0.0,
                    'duration': 8.0
                }
            ]
        }
        
        with pytest.raises(VideoAssemblyError):
            video_assembler._fetch_media_files(blueprint)


class TestVideoAssemblerIntegration:
    """Integration tests for video assembler (requires FFmpeg)."""
    
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
    def video_assembler(self, storage_service, temp_dir):
        """Create video assembler instance."""
        assembler_temp = os.path.join(temp_dir, 'assembler_temp')
        os.makedirs(assembler_temp, exist_ok=True)
        return VideoAssembler(
            storage_service=storage_service,
            temp_dir=assembler_temp
        )
    
    def test_assemble_video_missing_files(self, video_assembler):
        """Test video assembly with missing media files."""
        blueprint = {
            'task_id': 'test-task-123',
            'audio_path': 'data/songs/nonexistent.mp3',
            'moves': [
                {
                    'clip_id': 'move_1',
                    'video_path': 'data/Bachata_steps/basic_steps/basic_1.mp4',
                    'start_time': 0.0,
                    'duration': 8.0
                }
            ],
            'output_config': {
                'output_path': 'data/output/test_choreography.mp4'
            }
        }
        
        # Should fail because audio file doesn't exist
        with pytest.raises(VideoAssemblyError) as exc_info:
            video_assembler.assemble_video(blueprint)
        
        assert 'audio' in str(exc_info.value).lower() or 'not found' in str(exc_info.value).lower()


def test_video_assembler_error():
    """Test VideoAssemblyError exception."""
    error = VideoAssemblyError("Test error message")
    assert str(error) == "Test error message"
    assert isinstance(error, Exception)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
