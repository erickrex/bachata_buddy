"""
Property-based tests for FFmpeg Command Builder service.

**Feature: job-integration**

These tests verify the correctness properties of the FFmpeg command builder
as defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from .ffmpeg_builder import FFmpegCommandBuilder


# Hypothesis strategies for generating test data

@st.composite
def valid_file_path(draw):
    """Generate valid file paths (no directory traversal or absolute paths)."""
    # Generate safe path components
    components = draw(st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'),
            min_size=1,
            max_size=20
        ),
        min_size=1,
        max_size=4
    ))
    
    # Add file extension
    extension = draw(st.sampled_from(['.mp4', '.mp3', '.wav', '.avi', '.mkv', '.txt']))
    
    path = '/'.join(components) + extension
    return path


@st.composite
def valid_frame_rate(draw):
    """Generate valid frame rates."""
    return draw(st.integers(min_value=1, max_value=120))


@st.composite
def valid_bitrate(draw):
    """Generate valid bitrate strings."""
    value = draw(st.integers(min_value=1, max_value=100))
    unit = draw(st.sampled_from(['k', 'K', 'M', 'm']))
    return f"{value}{unit}"


@st.composite
def valid_codec(draw):
    """Generate valid codec names."""
    return draw(st.sampled_from([
        'libx264', 'libx265', 'h264', 'hevc', 'copy',
        'aac', 'mp3', 'opus', 'flac'
    ]))


# Property 1: FFmpeg commands are valid lists of strings
# **Validates: Requirements 3.4**

class TestFFmpegCommandBuilderProperties:
    """
    **Feature: job-integration, Property 1: Blueprint round-trip consistency**
    **Validates: Requirements 3.4**
    
    For any valid input parameters, the FFmpegCommandBuilder should produce
    commands that are valid lists of strings suitable for subprocess execution.
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        input_file=valid_file_path(),
        output_file=valid_file_path(),
        frame_rate=valid_frame_rate()
    )
    def test_normalize_command_returns_valid_list(self, input_file, output_file, frame_rate):
        """
        Property: For any valid input/output file paths and frame rate,
        build_normalize_command() should return a list of non-empty strings.
        """
        builder = FFmpegCommandBuilder()
        
        cmd = builder.build_normalize_command(input_file, output_file, frame_rate)
        
        # Verify it's a list
        assert isinstance(cmd, list), f"Command should be a list, got {type(cmd)}"
        
        # Verify all elements are non-empty strings
        for i, element in enumerate(cmd):
            assert isinstance(element, str), \
                f"Element {i} should be a string, got {type(element)}"
            assert len(element) > 0, \
                f"Element {i} should be non-empty"
        
        # Verify command starts with ffmpeg
        assert cmd[0] == 'ffmpeg', "Command should start with 'ffmpeg'"
        
        # Verify input file is in command
        assert input_file in cmd, "Input file should be in command"
        
        # Verify output file is in command
        assert output_file in cmd, "Output file should be in command"
        
        # Verify frame rate is in command
        assert str(frame_rate) in cmd, "Frame rate should be in command"
    
    @settings(max_examples=100, deadline=None)
    @given(
        concat_file=valid_file_path(),
        output_file=valid_file_path()
    )
    def test_concat_command_returns_valid_list(self, concat_file, output_file):
        """
        Property: For any valid concat file and output file paths,
        build_concat_command() should return a list of non-empty strings.
        """
        builder = FFmpegCommandBuilder()
        
        cmd = builder.build_concat_command(concat_file, output_file)
        
        # Verify it's a list
        assert isinstance(cmd, list), f"Command should be a list, got {type(cmd)}"
        
        # Verify all elements are non-empty strings
        for i, element in enumerate(cmd):
            assert isinstance(element, str), \
                f"Element {i} should be a string, got {type(element)}"
            assert len(element) > 0, \
                f"Element {i} should be non-empty"
        
        # Verify command starts with ffmpeg
        assert cmd[0] == 'ffmpeg', "Command should start with 'ffmpeg'"
        
        # Verify concat file is in command
        assert concat_file in cmd, "Concat file should be in command"
        
        # Verify output file is in command
        assert output_file in cmd, "Output file should be in command"
        
        # Verify concat format is specified
        assert 'concat' in cmd, "Concat format should be specified"
    
    @settings(max_examples=100, deadline=None)
    @given(
        video_file=valid_file_path(),
        audio_file=valid_file_path(),
        output_file=valid_file_path(),
        video_codec=valid_codec(),
        audio_codec=valid_codec(),
        video_bitrate=valid_bitrate(),
        audio_bitrate=valid_bitrate()
    )
    def test_add_audio_command_returns_valid_list(
        self, video_file, audio_file, output_file,
        video_codec, audio_codec, video_bitrate, audio_bitrate
    ):
        """
        Property: For any valid video/audio file paths and codec settings,
        build_add_audio_command() should return a list of non-empty strings.
        """
        builder = FFmpegCommandBuilder()
        
        cmd = builder.build_add_audio_command(
            video_file, audio_file, output_file,
            video_codec, audio_codec, video_bitrate, audio_bitrate
        )
        
        # Verify it's a list
        assert isinstance(cmd, list), f"Command should be a list, got {type(cmd)}"
        
        # Verify all elements are non-empty strings
        for i, element in enumerate(cmd):
            assert isinstance(element, str), \
                f"Element {i} should be a string, got {type(element)}"
            assert len(element) > 0, \
                f"Element {i} should be non-empty"
        
        # Verify command starts with ffmpeg
        assert cmd[0] == 'ffmpeg', "Command should start with 'ffmpeg'"
        
        # Verify video file is in command
        assert video_file in cmd, "Video file should be in command"
        
        # Verify audio file is in command
        assert audio_file in cmd, "Audio file should be in command"
        
        # Verify output file is in command
        assert output_file in cmd, "Output file should be in command"
        
        # Verify codecs are in command
        assert video_codec in cmd, "Video codec should be in command"
        assert audio_codec in cmd, "Audio codec should be in command"
        
        # Verify bitrates are in command
        assert video_bitrate in cmd, "Video bitrate should be in command"
        assert audio_bitrate in cmd, "Audio bitrate should be in command"
    
    @settings(max_examples=50, deadline=None)
    @given(
        input_file=valid_file_path(),
        output_file=valid_file_path()
    )
    def test_normalize_command_uses_default_frame_rate(self, input_file, output_file):
        """
        Property: When no frame rate is specified, build_normalize_command()
        should use the default frame rate (30).
        """
        builder = FFmpegCommandBuilder()
        
        cmd = builder.build_normalize_command(input_file, output_file)
        
        # Verify default frame rate is used
        assert str(FFmpegCommandBuilder.DEFAULT_FRAME_RATE) in cmd, \
            f"Default frame rate {FFmpegCommandBuilder.DEFAULT_FRAME_RATE} should be in command"
    
    @settings(max_examples=50, deadline=None)
    @given(
        video_file=valid_file_path(),
        audio_file=valid_file_path(),
        output_file=valid_file_path()
    )
    def test_add_audio_command_uses_default_codecs_and_bitrates(
        self, video_file, audio_file, output_file
    ):
        """
        Property: When no codecs or bitrates are specified, build_add_audio_command()
        should use the default values.
        """
        builder = FFmpegCommandBuilder()
        
        cmd = builder.build_add_audio_command(video_file, audio_file, output_file)
        
        # Verify default video codec is used
        assert 'libx264' in cmd, "Default video codec 'libx264' should be in command"
        
        # Verify default audio codec is used
        assert 'aac' in cmd, "Default audio codec 'aac' should be in command"
        
        # Verify default bitrates are used
        assert FFmpegCommandBuilder.DEFAULT_VIDEO_BITRATE in cmd, \
            f"Default video bitrate {FFmpegCommandBuilder.DEFAULT_VIDEO_BITRATE} should be in command"
        assert FFmpegCommandBuilder.DEFAULT_AUDIO_BITRATE in cmd, \
            f"Default audio bitrate {FFmpegCommandBuilder.DEFAULT_AUDIO_BITRATE} should be in command"
    
    def test_get_info_returns_valid_dict(self):
        """
        Property: get_info() should return a dictionary with expected keys.
        """
        builder = FFmpegCommandBuilder()
        
        info = builder.get_info()
        
        # Verify it's a dictionary
        assert isinstance(info, dict), f"Info should be a dict, got {type(info)}"
        
        # Verify expected keys are present
        assert 'use_gpu' in info, "Info should contain 'use_gpu' key"
        assert 'gpu_available' in info, "Info should contain 'gpu_available' key"
        assert 'cpu_preset' in info, "Info should contain 'cpu_preset' key"
        
        # Verify values are correct types
        assert isinstance(info['use_gpu'], bool), "use_gpu should be a boolean"
        assert isinstance(info['gpu_available'], bool), "gpu_available should be a boolean"
        assert isinstance(info['cpu_preset'], str), "cpu_preset should be a string"
