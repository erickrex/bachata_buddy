"""
Pytest tests for MusicAnalyzer service - Functional Programming Style.
All tests are pure functions without class-based organization.
"""
import pytest
import numpy as np
from pathlib import Path
from typing import Optional
from app.services.music_analyzer import MusicAnalyzer, MusicFeatures


# ============================================================================
# HELPER FUNCTIONS (Pure Functions)
# ============================================================================

def get_test_audio_path() -> Optional[str]:
    """Get path to a test audio file if it exists."""
    audio_path = Path("data/songs/Amor.mp3")
    if audio_path.exists():
        return str(audio_path)
    return None


def get_any_test_audio_path() -> Optional[str]:
    """Get any available test audio file."""
    songs_dir = Path("data/songs")
    if not songs_dir.exists():
        return None
    
    mp3_files = list(songs_dir.glob("*.mp3"))
    if mp3_files:
        return str(mp3_files[0])
    return None


def assert_valid_music_features(features: MusicFeatures) -> None:
    """Assert that MusicFeatures object has valid data."""
    assert isinstance(features, MusicFeatures)
    assert features.tempo > 0
    assert features.duration > 0
    assert len(features.beat_positions) > 0
    assert features.mfcc_features is not None
    assert features.chroma_features is not None


def assert_valid_tempo(tempo: float, min_bpm: float = 80, max_bpm: float = 180) -> None:
    """Assert that tempo is within reasonable range."""
    assert min_bpm <= tempo <= max_bpm, f"Tempo {tempo} outside range [{min_bpm}, {max_bpm}]"


def assert_beats_ascending(beat_positions: list) -> None:
    """Assert that beat positions are in ascending order."""
    for i in range(len(beat_positions) - 1):
        assert beat_positions[i] < beat_positions[i + 1], \
            f"Beats not in ascending order at index {i}"


def assert_valid_array_shape(array: np.ndarray, min_rows: int = 1, 
                             min_cols: int = 1, expected_rows: Optional[int] = None) -> None:
    """Assert that numpy array has valid shape."""
    assert array.shape[0] >= min_rows, f"Array has {array.shape[0]} rows, expected >= {min_rows}"
    if len(array.shape) > 1:
        assert array.shape[1] >= min_cols, f"Array has {array.shape[1]} cols, expected >= {min_cols}"
    if expected_rows is not None:
        assert array.shape[0] == expected_rows, \
            f"Array has {array.shape[0]} rows, expected {expected_rows}"


def assert_values_in_range(values: np.ndarray, min_val: float, max_val: float) -> None:
    """Assert that all values in array are within range."""
    assert np.all(values >= min_val), f"Some values below {min_val}"
    assert np.all(values <= max_val), f"Some values above {max_val}"


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

@pytest.mark.service
def test_music_analyzer_initialization():
    """Test MusicAnalyzer initializes correctly."""
    analyzer = MusicAnalyzer()
    
    assert analyzer is not None
    assert hasattr(analyzer, 'sample_rate')
    assert hasattr(analyzer, 'hop_length')
    assert analyzer.sample_rate > 0
    assert analyzer.hop_length > 0


@pytest.mark.service
def test_music_analyzer_default_parameters():
    """Test MusicAnalyzer has sensible default parameters."""
    analyzer = MusicAnalyzer()
    
    # Check common audio processing parameters
    assert analyzer.sample_rate == 22050  # Common sample rate
    assert analyzer.hop_length == 512  # Common hop length


@pytest.mark.service
def test_music_analyzer_has_required_methods():
    """Test MusicAnalyzer has all required methods."""
    analyzer = MusicAnalyzer()
    
    assert hasattr(analyzer, 'analyze_audio')
    assert callable(analyzer.analyze_audio)
    assert hasattr(analyzer, 'validate_tempo_accuracy')
    assert callable(analyzer.validate_tempo_accuracy)


# ============================================================================
# ANALYSIS TESTS (with real audio)
# ============================================================================

@pytest.mark.service
@pytest.mark.slow
def test_analyze_music_success():
    """Test successful music analysis."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert_valid_music_features(result)


@pytest.mark.service
@pytest.mark.slow
def test_analyze_returns_correct_type():
    """Test that analyze returns MusicFeatures instance."""
    audio_path = get_any_test_audio_path()
    if not audio_path:
        pytest.skip("No test audio files found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert isinstance(result, MusicFeatures)


@pytest.mark.service
@pytest.mark.slow
def test_analyze_multiple_files():
    """Test analyzing multiple audio files."""
    songs_dir = Path("data/songs")
    if not songs_dir.exists():
        pytest.skip("Songs directory not found")
    
    mp3_files = list(songs_dir.glob("*.mp3"))[:3]  # Test first 3 files
    if len(mp3_files) < 2:
        pytest.skip("Not enough audio files for testing")
    
    analyzer = MusicAnalyzer()
    
    for audio_path in mp3_files:
        result = analyzer.analyze_audio(str(audio_path))
        assert_valid_music_features(result)


# ============================================================================
# TEMPO DETECTION TESTS
# ============================================================================

@pytest.mark.service
@pytest.mark.slow
def test_tempo_detection():
    """Test tempo detection is within reasonable range for Bachata."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    # Bachata tempo typically ranges from 110-140 BPM, but allow wider range
    assert_valid_tempo(result.tempo, min_bpm=80, max_bpm=180)


@pytest.mark.service
@pytest.mark.slow
def test_tempo_is_positive():
    """Test that detected tempo is always positive."""
    audio_path = get_any_test_audio_path()
    if not audio_path:
        pytest.skip("No test audio files found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert result.tempo > 0


@pytest.mark.service
@pytest.mark.slow
def test_tempo_validation():
    """Test tempo validation method."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    is_valid = analyzer.validate_tempo_accuracy(result.tempo)
    assert isinstance(is_valid, bool)


@pytest.mark.service
def test_tempo_validation_edge_cases():
    """Test tempo validation with edge case values."""
    analyzer = MusicAnalyzer()
    
    # Test various tempo values
    assert analyzer.validate_tempo_accuracy(120) is True  # Typical Bachata
    assert analyzer.validate_tempo_accuracy(50) is False  # Too slow
    assert analyzer.validate_tempo_accuracy(200) is False  # Too fast


# ============================================================================
# BEAT DETECTION TESTS
# ============================================================================

@pytest.mark.service
@pytest.mark.slow
def test_beat_detection():
    """Test beat detection produces valid results."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert len(result.beat_positions) > 0
    assert all(isinstance(beat, (int, float, np.integer, np.floating)) 
              for beat in result.beat_positions)


@pytest.mark.service
@pytest.mark.slow
def test_beats_in_ascending_order():
    """Test that beat positions are in ascending order."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert_beats_ascending(result.beat_positions)


@pytest.mark.service
@pytest.mark.slow
def test_beats_within_duration():
    """Test that all beat positions are within audio duration."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert all(0 <= beat <= result.duration for beat in result.beat_positions)


@pytest.mark.service
@pytest.mark.slow
def test_beat_density():
    """Test that beat density is reasonable."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    # Calculate beats per second
    beats_per_second = len(result.beat_positions) / result.duration
    
    # Should have at least 1 beat per second, but not more than 4
    assert 1.0 <= beats_per_second <= 4.0


# ============================================================================
# FEATURE EXTRACTION TESTS
# ============================================================================

@pytest.mark.service
@pytest.mark.slow
def test_mfcc_feature_extraction():
    """Test MFCC feature extraction produces valid arrays."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert_valid_array_shape(result.mfcc_features, min_rows=1, min_cols=1)


@pytest.mark.service
@pytest.mark.slow
def test_chroma_feature_extraction():
    """Test chroma feature extraction produces valid arrays."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    # Chroma features should have 12 pitch classes
    assert_valid_array_shape(result.chroma_features, expected_rows=12, min_cols=1)



# ============================================================================
# ENERGY PROFILE TESTS
# ============================================================================

@pytest.mark.service
@pytest.mark.slow
def test_energy_profile_calculation():
    """Test energy profile calculation."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert len(result.energy_profile) > 0
    assert all(isinstance(e, (int, float, np.integer, np.floating)) 
              for e in result.energy_profile)


@pytest.mark.service
@pytest.mark.slow
def test_energy_profile_non_negative():
    """Test that energy profile values are non-negative."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert all(e >= 0 for e in result.energy_profile)


@pytest.mark.service
@pytest.mark.slow
def test_energy_profile_statistics():
    """Test energy profile has reasonable statistics."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    energy_array = np.array(result.energy_profile)
    
    # Should have some variation (not all same value)
    assert np.std(energy_array) > 0
    
    # Max should be greater than min
    assert np.max(energy_array) > np.min(energy_array)


# ============================================================================
# MUSICAL SECTIONS TESTS
# ============================================================================

@pytest.mark.service
@pytest.mark.slow
def test_musical_sections_detection():
    """Test musical section detection."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert len(result.sections) > 0


@pytest.mark.service
@pytest.mark.slow
def test_sections_have_valid_times():
    """Test that sections have valid start and end times."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    for section in result.sections:
        assert hasattr(section, 'start_time')
        assert hasattr(section, 'end_time')
        assert section.end_time > section.start_time
        assert section.start_time >= 0
        assert section.end_time <= result.duration


@pytest.mark.service
@pytest.mark.slow
def test_sections_have_metadata():
    """Test that sections have required metadata."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    for section in result.sections:
        assert hasattr(section, 'section_type')
        assert hasattr(section, 'energy_level')
        assert hasattr(section, 'recommended_move_types')


@pytest.mark.service
@pytest.mark.slow
def test_sections_cover_audio():
    """Test that sections cover the audio duration."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    # First section should start near beginning
    assert result.sections[0].start_time < result.duration * 0.1
    
    # Last section should end near the end
    assert result.sections[-1].end_time > result.duration * 0.9


# ============================================================================
# RHYTHM ANALYSIS TESTS
# ============================================================================

@pytest.mark.service
@pytest.mark.slow
def test_rhythm_pattern_strength():
    """Test rhythm pattern strength calculation."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert hasattr(result, 'rhythm_pattern_strength')
    assert_values_in_range(np.array([result.rhythm_pattern_strength]), 0, 1)


@pytest.mark.service
@pytest.mark.slow
def test_syncopation_level():
    """Test syncopation level calculation."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert hasattr(result, 'syncopation_level')
    assert_values_in_range(np.array([result.syncopation_level]), 0, 1)


@pytest.mark.service
@pytest.mark.slow
def test_rhythm_features_are_numeric():
    """Test that rhythm features are numeric values."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert isinstance(result.rhythm_pattern_strength, (int, float, np.integer, np.floating))
    assert isinstance(result.syncopation_level, (int, float, np.integer, np.floating))


# ============================================================================
# AUDIO EMBEDDING TESTS
# ============================================================================

@pytest.mark.service
@pytest.mark.slow
def test_audio_embedding_generation():
    """Test audio embedding generation."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert hasattr(result, 'audio_embedding')
    assert result.audio_embedding is not None
    assert len(result.audio_embedding) == 128  # Expected embedding dimension


@pytest.mark.service
@pytest.mark.slow
def test_embedding_values_are_numeric():
    """Test that embedding values are numeric."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    assert all(isinstance(v, (int, float, np.integer, np.floating)) 
              for v in result.audio_embedding)


@pytest.mark.service
@pytest.mark.slow
def test_embedding_not_all_zeros():
    """Test that embedding contains actual data."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    # Should have at least some non-zero values
    non_zero_count = sum(1 for v in result.audio_embedding if abs(v) > 1e-6)
    assert non_zero_count > 0


@pytest.mark.service
@pytest.mark.slow
def test_embedding_has_variation():
    """Test that embedding has variation (not all same value)."""
    audio_path = get_test_audio_path()
    if not audio_path:
        pytest.skip("Test audio file not found")
    
    analyzer = MusicAnalyzer()
    result = analyzer.analyze_audio(audio_path)
    
    embedding_array = np.array(result.audio_embedding)
    assert np.std(embedding_array) > 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.service
def test_analyze_nonexistent_file():
    """Test analyzing non-existent file raises error."""
    analyzer = MusicAnalyzer()
    
    with pytest.raises(Exception):
        analyzer.analyze_audio("/nonexistent/file.mp3")


@pytest.mark.service
def test_analyze_invalid_path():
    """Test analyzing with invalid path raises error."""
    analyzer = MusicAnalyzer()
    
    with pytest.raises(Exception):
        analyzer.analyze_audio("")


@pytest.mark.service
def test_analyze_directory_path():
    """Test analyzing directory path raises error."""
    analyzer = MusicAnalyzer()
    
    with pytest.raises(Exception):
        analyzer.analyze_audio("data/songs")


@pytest.mark.service
def test_analyze_non_audio_file():
    """Test analyzing non-audio file raises error."""
    analyzer = MusicAnalyzer()
    
    # Try to analyze a Python file
    with pytest.raises(Exception):
        analyzer.analyze_audio("conftest.py")
