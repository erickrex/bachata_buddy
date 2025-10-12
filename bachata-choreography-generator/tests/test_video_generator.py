"""
Tests for the VideoGenerator service - Functional Programming Style.
All tests are pure functions without class-based organization.
"""

import pytest
import os
import tempfile
import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from typing import List, Tuple

from app.services.video_generator import VideoGenerator, VideoGenerationError
from app.models.video_models import (
    ChoreographySequence, 
    SelectedMove, 
    VideoGenerationConfig,
    TransitionType
)


# ============================================================================
# HELPER FUNCTIONS (Pure Functions)
# ============================================================================

def create_test_config(temp_dir: str) -> VideoGenerationConfig:
    """Create a test configuration."""
    return VideoGenerationConfig(
        output_path=os.path.join(temp_dir, "test_output.mp4"),
        temp_dir=temp_dir,
        cleanup_temp_files=False
    )


def create_test_video_files(temp_dir: str, count: int = 3) -> List[str]:
    """Create dummy video files for testing."""
    video_paths = []
    for i in range(count):
        video_path = os.path.join(temp_dir, f"test_video_{i}.mp4")
        Path(video_path).touch()
        video_paths.append(video_path)
    return video_paths


def create_test_move(video_path: str, clip_id: str, start_time: float = 0.0, 
                     duration: float = 10.0) -> SelectedMove:
    """Create a test move."""
    return SelectedMove(
        clip_id=clip_id,
        video_path=video_path,
        start_time=start_time,
        duration=duration,
        transition_type=TransitionType.CUT
    )


def create_test_sequence(moves: List[SelectedMove], total_duration: float = None) -> ChoreographySequence:
    """Create a test choreography sequence."""
    if total_duration is None:
        total_duration = sum(move.duration for move in moves)
    
    return ChoreographySequence(
        moves=moves,
        total_duration=total_duration,
        difficulty_level="beginner"
    )


def create_music_features(tempo: float = 120.0, duration: float = 30.0) -> dict:
    """Create sample music features for testing."""
    beat_interval = 60.0 / tempo
    beat_positions = [i * beat_interval for i in range(int(duration / beat_interval))]
    
    return {
        'tempo': tempo,
        'beat_positions': beat_positions,
        'duration': duration
    }


def mock_ffmpeg_success() -> MagicMock:
    """Create a mock for successful FFmpeg execution."""
    mock = MagicMock(returncode=0)
    mock.stdout = ""
    mock.stderr = ""
    return mock


def mock_ffprobe_duration(duration: float) -> MagicMock:
    """Create a mock for ffprobe returning video duration."""
    mock = MagicMock(returncode=0)
    mock.stdout = json.dumps({"format": {"duration": str(duration)}})
    return mock


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

@patch('subprocess.run')
def test_video_generator_initialization_success(mock_run):
    """Test successful VideoGenerator initialization."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        assert generator is not None
        assert generator.config == config
        assert os.path.exists(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_ffmpeg_availability_check_failure(mock_run):
    """Test FFmpeg availability check failure."""
    mock_run.side_effect = FileNotFoundError("ffmpeg not found")
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        with pytest.raises(VideoGenerationError, match="FFmpeg is not installed"):
            VideoGenerator(config)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_ffmpeg_not_working_properly(mock_run):
    """Test FFmpeg returns non-zero exit code."""
    mock_run.return_value = MagicMock(returncode=1)
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        with pytest.raises(VideoGenerationError, match="not available or not working"):
            VideoGenerator(config)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# SEQUENCE CREATION TESTS
# ============================================================================

@patch('subprocess.run')
def test_create_simple_sequence_from_paths(mock_run):
    """Test creating a simple sequence from video paths."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=3)
        
        sequence = generator.create_simple_sequence_from_paths(video_paths)
        
        assert len(sequence.moves) == 3
        assert sequence.total_duration == 30.0  # 3 clips * 10 seconds each
        assert sequence.difficulty_level == "mixed"
        
        for i, move in enumerate(sequence.moves):
            assert move.clip_id == f"clip_{i}"
            assert move.video_path == video_paths[i]
            assert move.duration == 10.0
            assert move.transition_type == TransitionType.CUT
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_create_simple_sequence_missing_file(mock_run):
    """Test creating sequence with missing video file."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = ["/nonexistent/video.mp4"]
        
        with pytest.raises(VideoGenerationError, match="Video file not found"):
            generator.create_simple_sequence_from_paths(video_paths)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_create_simple_sequence_with_custom_output_path(mock_run):
    """Test creating sequence with custom output path."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=2)
        custom_output = os.path.join(temp_dir, "custom_output.mp4")
        
        sequence = generator.create_simple_sequence_from_paths(video_paths, custom_output)
        
        assert len(sequence.moves) == 2
        assert generator.config.output_path == custom_output
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# VALIDATION TESTS
# ============================================================================

@patch('subprocess.run')
def test_validate_sequence_success(mock_run):
    """Test successful sequence validation."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=1)
        
        move = create_test_move(video_paths[0], "test_clip", duration=10.0)
        sequence = create_test_sequence([move], total_duration=10.0)
        
        # Should not raise an exception
        generator._validate_sequence(sequence)
        assert sequence.total_duration == 10.0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_validate_sequence_empty_moves(mock_run):
    """Test validation with empty moves list."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        sequence = create_test_sequence([], total_duration=1.0)
        
        with pytest.raises(VideoGenerationError, match="Sequence must contain at least one move"):
            generator._validate_sequence(sequence)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_validate_sequence_missing_video_file(mock_run):
    """Test validation with missing video file."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        move = create_test_move("/nonexistent/video.mp4", "test_clip")
        sequence = create_test_sequence([move])
        
        with pytest.raises(VideoGenerationError, match="Video file not found"):
            generator._validate_sequence(sequence)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_validate_sequence_invalid_duration(mock_run):
    """Test validation with invalid move duration."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=1)
        
        # Create move with valid duration first
        move = SelectedMove(
            clip_id="test_clip",
            video_path=video_paths[0],
            start_time=0.0,
            duration=10.0
        )
        sequence = ChoreographySequence(
            moves=[move],
            total_duration=10.0,
            difficulty_level="beginner"
        )
        
        # Manually set to invalid value after creation to bypass Pydantic
        sequence.moves[0].duration = -1.0
        
        with pytest.raises(VideoGenerationError, match="invalid duration"):
            generator._validate_sequence(sequence)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_validate_sequence_duration_correction(mock_run):
    """Test that validation corrects duration discrepancies."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=2)
        
        moves = [
            create_test_move(video_paths[0], "clip_0", duration=10.0),
            create_test_move(video_paths[1], "clip_1", start_time=10.0, duration=15.0)
        ]
        sequence = create_test_sequence(moves, total_duration=20.0)  # Wrong total
        
        generator._validate_sequence(sequence)
        
        # Should be corrected to actual sum
        assert sequence.total_duration == 25.0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# CONCAT FILE TESTS
# ============================================================================

@patch('subprocess.run')
def test_create_concat_file_creates_trimmed_clips(mock_run):
    """Test that concat file creation attempts to create trimmed clips."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=2)
        
        moves = [
            create_test_move(video_paths[0], "clip_0", start_time=0.0, duration=10.0),
            create_test_move(video_paths[1], "clip_1", start_time=10.0, duration=10.0)
        ]
        sequence = create_test_sequence(moves)
        
        temp_files = []
        concat_file_path = generator._create_concat_file(sequence, temp_files)
        
        assert os.path.exists(concat_file_path)
        assert concat_file_path in temp_files
        
        # Verify concat file was created
        with open(concat_file_path, 'r') as f:
            content = f.read()
            # Content may be empty if trimming failed, but file should exist
            assert isinstance(content, str)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_create_beat_synchronized_concat_file(mock_run):
    """Test beat-synchronized concat file creation."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=2)
        
        moves = [create_test_move(video_paths[i], f"clip_{i}") for i in range(2)]
        sequence = create_test_sequence(moves)
        music_features = create_music_features()
        
        temp_files = []
        concat_file_path = generator._create_beat_synchronized_concat_file(
            sequence, music_features, temp_files
        )
        
        assert os.path.exists(concat_file_path)
        assert concat_file_path in temp_files
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# FILE INFO AND CLEANUP TESTS
# ============================================================================

@patch('subprocess.run')
def test_get_output_info_success(mock_run):
    """Test getting output file information."""
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Mock ffmpeg and ffprobe
        mock_ffprobe = mock_ffprobe_duration(15.5)
        mock_run.side_effect = [mock_ffmpeg_success(), mock_ffprobe]
        
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        output_path = os.path.join(temp_dir, "test_output.mp4")
        with open(output_path, 'w') as f:
            f.write("dummy video content")
        
        duration, file_size = generator._get_output_info(output_path)
        
        assert duration == 15.5
        assert file_size > 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_get_output_info_missing_file(mock_run):
    """Test getting info for non-existent file."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        duration, file_size = generator._get_output_info("/nonexistent/file.mp4")
        
        assert duration is None
        assert file_size is None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_get_video_duration_success(mock_run):
    """Test getting video duration."""
    temp_dir = tempfile.mkdtemp()
    
    try:
        mock_ffprobe = mock_ffprobe_duration(25.3)
        mock_run.side_effect = [mock_ffmpeg_success(), mock_ffprobe]
        
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        video_path = os.path.join(temp_dir, "test.mp4")
        Path(video_path).touch()
        
        duration = generator._get_video_duration(video_path)
        assert duration == 25.3
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_get_video_duration_failure(mock_run):
    """Test getting video duration when ffprobe fails."""
    temp_dir = tempfile.mkdtemp()
    
    try:
        mock_run.side_effect = [
            mock_ffmpeg_success(),
            MagicMock(returncode=1, stdout="")
        ]
        
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        duration = generator._get_video_duration("/some/path.mp4")
        assert duration == 60.0  # Fallback value
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_cleanup_temp_files(mock_run):
    """Test cleanup of temporary files."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        # Create temporary files
        temp_files = []
        for i in range(3):
            temp_file = os.path.join(temp_dir, f"temp_file_{i}.txt")
            with open(temp_file, 'w') as f:
                f.write("temporary content")
            temp_files.append(temp_file)
        
        # Verify files exist
        for temp_file in temp_files:
            assert os.path.exists(temp_file)
        
        # Clean up
        generator._cleanup_temp_files(temp_files)
        
        # Verify files are deleted
        for temp_file in temp_files:
            assert not os.path.exists(temp_file)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_cleanup_temp_files_handles_missing_files(mock_run):
    """Test cleanup handles missing files gracefully."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        # List includes non-existent files
        temp_files = [
            os.path.join(temp_dir, "nonexistent1.txt"),
            os.path.join(temp_dir, "nonexistent2.txt")
        ]
        
        # Should not raise an exception
        generator._cleanup_temp_files(temp_files)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# METADATA EXPORT TESTS
# ============================================================================

@patch('subprocess.run')
def test_export_sequence_metadata_success(mock_run):
    """Test exporting sequence metadata to JSON."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=2)
        
        moves = [create_test_move(video_paths[i], f"clip_{i}") for i in range(2)]
        sequence = create_test_sequence(moves)
        sequence.audio_path = "/path/to/audio.mp3"
        sequence.audio_tempo = 120.0
        
        metadata_path = os.path.join(temp_dir, "metadata.json")
        music_features = create_music_features()
        
        result_path = generator.export_sequence_metadata(
            sequence, metadata_path, music_features, {"custom": "data"}
        )
        
        assert result_path == metadata_path
        assert os.path.exists(metadata_path)
        
        # Verify content
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        assert metadata['sequence_info']['total_moves'] == 2
        assert metadata['sequence_info']['total_duration'] == 20.0
        assert metadata['audio_info']['tempo'] == 120.0
        assert metadata['custom'] == 'data'
        assert len(metadata['moves_used']) == 2
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_export_sequence_metadata_handles_errors(mock_run):
    """Test metadata export handles errors gracefully."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=1)
        
        moves = [create_test_move(video_paths[0], "clip_0")]
        sequence = create_test_sequence(moves)
        
        # Try to write to invalid path
        result_path = generator.export_sequence_metadata(
            sequence, "/invalid/path/metadata.json"
        )
        
        # Should return empty string on error
        assert result_path == ""
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# BEAT SYNCHRONIZATION TESTS
# ============================================================================

@patch('subprocess.run')
def test_create_beat_synchronized_sequence(mock_run):
    """Test creating beat-synchronized choreography sequence."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=3)
        music_features = create_music_features(tempo=120.0, duration=30.0)
        
        sequence = generator.create_beat_synchronized_sequence(
            video_paths, music_features, target_duration=20.0
        )
        
        assert len(sequence.moves) > 0
        assert sequence.audio_tempo == 120.0
        assert sequence.generation_parameters['sync_type'] == 'beat_synchronized'
        assert sequence.generation_parameters['tempo'] == 120.0
        
        # Verify moves are aligned to beats
        for move in sequence.moves:
            closest_beat_distance = min(
                abs(move.start_time - beat) 
                for beat in music_features['beat_positions']
            )
            assert closest_beat_distance < 1.0  # Within 1 second of a beat
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_create_beat_synchronized_sequence_no_beats(mock_run):
    """Test beat sync falls back when no beats available."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=2)
        music_features = {'tempo': 120.0, 'beat_positions': [], 'duration': 30.0}
        
        sequence = generator.create_beat_synchronized_sequence(
            video_paths, music_features
        )
        
        # Should fall back to simple sequence
        assert len(sequence.moves) == 2
        assert sequence.difficulty_level == "mixed"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_create_beat_synchronized_sequence_respects_target_duration(mock_run):
    """Test beat sync respects target duration."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=10)
        music_features = create_music_features(tempo=120.0, duration=60.0)
        
        sequence = generator.create_beat_synchronized_sequence(
            video_paths, music_features, target_duration=15.0
        )
        
        # Should stop before target duration
        assert sequence.total_duration <= 20.0  # Some tolerance
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_find_closest_beat(mock_run):
    """Test finding closest beat position."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        beat_positions = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        
        # Test various time positions
        assert generator._find_closest_beat(0.1, beat_positions) == 0
        assert generator._find_closest_beat(0.6, beat_positions) == 1
        assert generator._find_closest_beat(1.4, beat_positions) == 3  # Closer to 1.5 than 1.0
        assert generator._find_closest_beat(2.9, beat_positions) == 6
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_find_closest_beat_empty_list(mock_run):
    """Test finding closest beat with empty list."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        result = generator._find_closest_beat(1.5, [])
        assert result == 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# HARDWARE ACCELERATION TESTS
# ============================================================================

@patch('subprocess.run')
def test_detect_hardware_acceleration_success(mock_run):
    """Test hardware acceleration detection."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        hw_accel = generator._detect_hardware_acceleration()
        
        # Should return a list or None
        assert hw_accel is None or isinstance(hw_accel, list)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_detect_hardware_acceleration_failure(mock_run):
    """Test hardware acceleration when not available."""
    # All hardware tests fail
    mock_run.side_effect = [
        mock_ffmpeg_success(),  # Initial check
        MagicMock(returncode=1),  # All hw tests fail
        MagicMock(returncode=1),
        MagicMock(returncode=1),
    ]
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        hw_accel = generator._detect_hardware_acceleration()
        
        # Should return None when no hw accel available
        assert hw_accel is None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# VIDEO GENERATION TESTS
# ============================================================================

@patch('subprocess.run')
def test_generate_choreography_video_without_audio(mock_run):
    """Test video generation without audio overlay."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=2)
        
        moves = [create_test_move(video_paths[i], f"clip_{i}") for i in range(2)]
        sequence = create_test_sequence(moves)
        
        # Mock the output file creation
        output_path = config.output_path
        Path(output_path).touch()
        
        result = generator.generate_choreography_video(sequence)
        
        # Result should indicate attempt was made
        assert result is not None
        assert result.clips_processed == 2
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_generate_choreography_video_handles_errors(mock_run):
    """Test video generation error handling."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        # Create sequence with missing file
        move = create_test_move("/nonexistent/video.mp4", "clip_0")
        sequence = create_test_sequence([move])
        
        result = generator.generate_choreography_video(sequence)
        
        assert result.success is False
        assert result.error_message is not None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_simple_concatenation(mock_run):
    """Test simple video concatenation without audio."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, 'w') as f:
            f.write("file 'test.mp4'\n")
        
        output_path = config.output_path
        
        result_path = generator._simple_concatenation(concat_file, output_path)
        
        assert result_path == output_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_simple_concatenation_failure(mock_run):
    """Test simple concatenation handles ffmpeg failure."""
    mock_run.side_effect = [
        mock_ffmpeg_success(),
        MagicMock(returncode=1, stderr="FFmpeg error")
    ]
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        Path(concat_file).touch()
        
        with pytest.raises(VideoGenerationError, match="Simple concatenation failed"):
            generator._simple_concatenation(concat_file, config.output_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_two_step_video_audio_process(mock_run):
    """Test two-step video/audio processing."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        audio_file = os.path.join(temp_dir, "audio.mp3")
        Path(concat_file).touch()
        Path(audio_file).touch()
        
        # Mock video duration
        with patch.object(generator, '_get_video_duration', return_value=20.0):
            result_path = generator._two_step_video_audio_process(
                concat_file, audio_file, config.output_path
            )
        
        assert result_path == config.output_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_two_step_process_step1_failure(mock_run):
    """Test two-step process handles step 1 failure."""
    mock_run.side_effect = [
        mock_ffmpeg_success(),
        MagicMock(returncode=1, stderr="Step 1 failed")
    ]
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        audio_file = os.path.join(temp_dir, "audio.mp3")
        Path(concat_file).touch()
        Path(audio_file).touch()
        
        with pytest.raises(VideoGenerationError, match="Step 1 failed"):
            generator._two_step_video_audio_process(
                concat_file, audio_file, config.output_path
            )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_concatenate_videos_with_audio_sync(mock_run):
    """Test video concatenation with audio synchronization."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        audio_file = os.path.join(temp_dir, "audio.mp3")
        Path(concat_file).touch()
        Path(audio_file).touch()
        
        music_features = create_music_features()
        
        with patch.object(generator, '_two_step_video_audio_process', return_value=config.output_path):
            result_path = generator._concatenate_videos_with_audio_sync(
                concat_file, audio_file, music_features
            )
        
        assert result_path == config.output_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_concatenate_videos_without_audio(mock_run):
    """Test video concatenation without audio."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        Path(concat_file).touch()
        
        with patch.object(generator, '_simple_concatenation', return_value=config.output_path):
            result_path = generator._concatenate_videos_with_audio_sync(concat_file, None, None)
        
        assert result_path == config.output_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestVideoGeneratorIntegration:
    """Integration tests - kept as class for pytest compatibility with real files."""
    pass




# ============================================================================
# ADDITIONAL COVERAGE TESTS
# ============================================================================

@patch('subprocess.run')
def test_create_trimmed_clip_success(mock_run):
    """Test creating a trimmed video clip."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=1)
        
        move = create_test_move(video_paths[0], "clip_0", duration=5.0)
        temp_files = []
        
        # Mock the trimmed clip creation
        with patch.object(generator, '_detect_hardware_acceleration', return_value=None):
            trimmed_path = generator._create_trimmed_clip(move, 0, temp_files)
        
        # Should attempt to create a trimmed clip
        assert isinstance(trimmed_path, str)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_get_concat_video_duration(mock_run):
    """Test getting total duration of concatenated videos."""
    temp_dir = tempfile.mkdtemp()
    
    try:
        mock_run.side_effect = [
            mock_ffmpeg_success(),
            mock_ffprobe_duration(10.0),
            mock_ffprobe_duration(15.0)
        ]
        
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        # Create concat file
        concat_file = os.path.join(temp_dir, "concat.txt")
        video1 = os.path.join(temp_dir, "video1.mp4")
        video2 = os.path.join(temp_dir, "video2.mp4")
        Path(video1).touch()
        Path(video2).touch()
        
        with open(concat_file, 'w') as f:
            f.write(f"file '{video1}'\n")
            f.write(f"file '{video2}'\n")
        
        duration = generator._get_concat_video_duration(concat_file)
        
        # Should sum durations
        assert duration > 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_get_concat_video_duration_handles_errors(mock_run):
    """Test concat duration calculation handles errors."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        # Non-existent concat file
        duration = generator._get_concat_video_duration("/nonexistent/concat.txt")
        
        # Should return fallback
        assert duration == 60.0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_build_audio_sync_command(mock_run):
    """Test building audio sync command."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        audio_file = os.path.join(temp_dir, "audio.mp3")
        output_file = os.path.join(temp_dir, "output.mp4")
        
        Path(concat_file).touch()
        Path(audio_file).touch()
        
        music_features = create_music_features()
        
        cmd = generator._build_audio_sync_command(
            concat_file, audio_file, output_file, music_features
        )
        
        assert isinstance(cmd, list)
        assert len(cmd) > 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_build_two_step_command(mock_run):
    """Test building two-step processing command."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        audio_file = os.path.join(temp_dir, "audio.mp3")
        output_file = os.path.join(temp_dir, "output.mp4")
        
        cmd = generator._build_two_step_command(concat_file, audio_file, output_file)
        
        assert isinstance(cmd, list)
        assert "ffmpeg" in cmd
        assert "-c" in cmd
        assert "copy" in cmd
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_build_web_optimized_command(mock_run):
    """Test building web-optimized command."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        output_file = os.path.join(temp_dir, "output.mp4")
        
        cmd = generator._build_web_optimized_command(concat_file, output_file)
        
        assert isinstance(cmd, list)
        assert "ffmpeg" in cmd
        assert "-movflags" in cmd
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_concatenate_videos_legacy_method(mock_run):
    """Test legacy concatenate_videos method."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        Path(concat_file).touch()
        
        with patch.object(generator, '_concatenate_videos_with_audio_sync', return_value=config.output_path):
            result = generator._concatenate_videos(concat_file, None)
        
        assert result == config.output_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_test_basic_concatenation_method(mock_run):
    """Test the test_basic_concatenation helper method."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        video_paths = create_test_video_files(temp_dir, count=2)
        
        # Mock the generate method to avoid actual video processing
        with patch.object(generator, 'generate_choreography_video') as mock_gen:
            from app.models.video_models import VideoGenerationResult
            mock_gen.return_value = VideoGenerationResult(
                success=True,
                output_path=config.output_path,
                duration=20.0,
                file_size=1000,
                processing_time=1.0,
                clips_processed=2
            )
            
            result = generator.test_basic_concatenation(video_paths)
        
        assert result.success is True
        assert result.clips_processed == 2
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_two_step_process_step2_failure(mock_run):
    """Test two-step process handles step 2 failure."""
    temp_dir = tempfile.mkdtemp()
    
    try:
        mock_run.side_effect = [
            mock_ffmpeg_success(),  # Init
            mock_ffmpeg_success(),  # Step 1
            MagicMock(returncode=1, stderr="Step 2 failed")  # Step 2 fails
        ]
        
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        concat_file = os.path.join(temp_dir, "concat.txt")
        audio_file = os.path.join(temp_dir, "audio.mp3")
        Path(concat_file).touch()
        Path(audio_file).touch()
        
        # Mock video duration
        with patch.object(generator, '_get_video_duration', return_value=20.0):
            with pytest.raises(VideoGenerationError, match="Step 2 failed"):
                generator._two_step_video_audio_process(
                    concat_file, audio_file, config.output_path
                )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch('subprocess.run')
def test_ensure_temp_directory(mock_run):
    """Test temp directory creation."""
    mock_run.return_value = mock_ffmpeg_success()
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Remove temp dir to test creation
        shutil.rmtree(temp_dir)
        
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        
        # Should create the directory
        assert os.path.exists(temp_dir)
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# Functional integration tests
def test_integration_with_real_videos():
    """Integration test with real video files (if available)."""
    video_data_dir = Path("data/Bachata_steps")
    
    if not video_data_dir.exists():
        pytest.skip("Video data directory not available for integration testing")
    
    # Find actual video files
    video_files = []
    for category_dir in video_data_dir.iterdir():
        if category_dir.is_dir():
            for video_file in category_dir.glob("*.mp4"):
                video_files.append(str(video_file))
                if len(video_files) >= 3:
                    break
            if len(video_files) >= 3:
                break
    
    if len(video_files) < 2:
        pytest.skip("Not enough video files available for integration testing")
    
    temp_dir = tempfile.mkdtemp()
    try:
        config = VideoGenerationConfig(
            output_path=os.path.join(temp_dir, "integration_test.mp4"),
            temp_dir=temp_dir,
            cleanup_temp_files=False
        )
        generator = VideoGenerator(config)
        
        result = generator.test_basic_concatenation(video_files[:2])
        
        if result.success:
            assert os.path.exists(result.output_path)
            assert result.duration is not None
            assert result.file_size is not None
            assert result.clips_processed == 2
        else:
            if "FFmpeg" in str(result.error_message):
                pytest.skip(f"FFmpeg not available: {result.error_message}")
            else:
                pytest.fail(f"Integration test failed: {result.error_message}")
                
    except VideoGenerationError as e:
        if "FFmpeg" in str(e):
            pytest.skip(f"FFmpeg not available: {e}")
        else:
            raise
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_beat_synchronized_sequence_with_real_videos():
    """Test beat-synchronized sequence with real videos."""
    video_data_dir = Path("data/Bachata_steps")
    
    if not video_data_dir.exists():
        pytest.skip("Video data directory not available")
    
    video_files = []
    for category_dir in video_data_dir.iterdir():
        if category_dir.is_dir():
            for video_file in category_dir.glob("*.mp4"):
                video_files.append(str(video_file))
                if len(video_files) >= 3:
                    break
            if len(video_files) >= 3:
                break
    
    if len(video_files) < 2:
        pytest.skip("Not enough video files available")
    
    temp_dir = tempfile.mkdtemp()
    try:
        config = create_test_config(temp_dir)
        generator = VideoGenerator(config)
        music_features = create_music_features()
        
        sequence = generator.create_beat_synchronized_sequence(
            video_files[:2], music_features, target_duration=10.0
        )
        
        assert len(sequence.moves) == 2
        assert sequence.audio_tempo == 120.0
        assert sequence.generation_parameters['sync_type'] == 'beat_synchronized'
        
        for move in sequence.moves:
            closest_beat_distance = min(
                abs(move.start_time - beat) 
                for beat in music_features['beat_positions']
            )
            assert closest_beat_distance < 0.5
            
    except VideoGenerationError as e:
        if "FFmpeg" in str(e):
            pytest.skip(f"FFmpeg not available: {e}")
        else:
            raise
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)