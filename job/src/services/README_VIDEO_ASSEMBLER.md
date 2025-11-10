# Video Assembler Service

## Overview

The Video Assembler service is responsible for assembling final choreography videos from blueprints. It fetches media files from storage, uses FFmpeg to concatenate video clips with audio, and uploads the result.

## Features

- **Parallel Downloads**: Downloads multiple video clips simultaneously for faster processing
- **FFmpeg Integration**: Uses FFmpeg for professional video concatenation and audio mixing
- **Dual Storage Support**: Works with both local filesystem and Google Cloud Storage
- **Progress Tracking**: Provides progress callbacks for status updates
- **Error Handling**: Comprehensive error handling with retry logic via storage service
- **Automatic Cleanup**: Cleans up temporary files after processing

## Architecture

```
Blueprint → Fetch Media → Concatenate Videos → Add Audio → Upload Result
```

### Step-by-Step Process

1. **Fetch Media Files** (20-50% progress)
   - Download audio file from storage
   - Download all video clips in parallel (up to 10 concurrent downloads)
   - Store in temporary directory

2. **Concatenate Videos** (50-70% progress)
   - Create FFmpeg concat file listing all clips
   - Use FFmpeg concat demuxer to merge clips
   - Fast operation using codec copy (no re-encoding)

3. **Add Audio Track** (70-85% progress)
   - Combine concatenated video with audio track
   - Re-encode with specified codecs and bitrates
   - Match shortest input duration

4. **Upload Result** (85-95% progress)
   - Upload final video to storage
   - Return URL or path to result

5. **Cleanup** (95-100% progress)
   - Remove all temporary files
   - Keep temp directory for reuse

## Usage

```python
from services.video_assembler import VideoAssembler
from services.storage_service import StorageService, StorageConfig

# Initialize storage service
storage_config = StorageConfig(
    use_local_storage=True,
    local_storage_path='/app/data'
)
storage_service = StorageService(config=storage_config)

# Initialize video assembler
assembler = VideoAssembler(storage_service=storage_service)

# Check FFmpeg availability
if not assembler.check_ffmpeg_available():
    raise RuntimeError("FFmpeg not available")

# Assemble video from blueprint
def progress_callback(stage, progress, message):
    print(f"[{progress}%] {stage}: {message}")

result_url = assembler.assemble_video(
    blueprint=blueprint_dict,
    progress_callback=progress_callback
)

print(f"Video assembled: {result_url}")
```

## Blueprint Requirements

The video assembler expects a blueprint with the following structure:

```json
{
  "task_id": "abc-123",
  "audio_path": "data/songs/song.mp3",
  "moves": [
    {
      "clip_id": "move_1",
      "video_path": "data/Bachata_steps/basic_steps/basic_1.mp4",
      "start_time": 0.0,
      "duration": 8.0
    }
  ],
  "output_config": {
    "output_path": "data/output/choreography_abc-123.mp4",
    "video_codec": "libx264",
    "audio_codec": "aac",
    "video_bitrate": "2M",
    "audio_bitrate": "128k"
  }
}
```

## FFmpeg Commands

### Concatenate Videos

```bash
# Create concat file
echo "file '/path/to/clip1.mp4'" > concat.txt
echo "file '/path/to/clip2.mp4'" >> concat.txt

# Concatenate (no re-encoding)
ffmpeg -f concat -safe 0 -i concat.txt -c copy output.mp4
```

### Add Audio Track

```bash
# Add audio and re-encode
ffmpeg -i video.mp4 -i audio.mp3 \
  -c:v libx264 -b:v 2M \
  -c:a aac -b:a 128k \
  -shortest \
  output.mp4
```

## Configuration

### Default Settings

- **Video Codec**: libx264 (H.264)
- **Audio Codec**: aac
- **Video Bitrate**: 2M
- **Audio Bitrate**: 128k
- **Frame Rate**: 30 fps
- **Max Parallel Downloads**: 10

### Environment Variables

- `LOCAL_STORAGE_PATH`: Path for local storage (default: /app/data)
- `USE_GCS`: Use Google Cloud Storage (default: false)
- `GCS_BUCKET_NAME`: GCS bucket name
- `GCP_PROJECT_ID`: GCP project ID

## Error Handling

The service raises `VideoAssemblyError` for all failures:

- **Missing Media Files**: Audio or video files not found in storage
- **FFmpeg Failures**: Concatenation or audio mixing errors
- **Upload Failures**: Cannot upload result to storage
- **Invalid Blueprint**: Missing required fields or invalid paths

All errors are logged with detailed context for debugging.

## Performance

- **Parallel Downloads**: Up to 10 concurrent downloads for faster media fetching
- **Codec Copy**: Fast concatenation without re-encoding when possible
- **Temporary Files**: Uses local temp directory for intermediate files
- **Cleanup**: Automatic cleanup prevents disk space issues

### Expected Performance

- **3-minute video**: ~30 seconds assembly time
- **Memory usage**: <512MB
- **Disk usage**: ~2x final video size (temporary files)

## Testing

Run tests with:

```bash
uv run pytest test_video_assembler.py -v
```

Tests cover:
- Service initialization
- FFmpeg availability check
- Media file downloads
- Result upload
- Error handling
- Cleanup operations

## Dependencies

- **FFmpeg**: Required for video processing
- **Storage Service**: For file operations
- **Python Standard Library**: tempfile, subprocess, concurrent.futures

## Integration

The video assembler is integrated into the main job container:

```python
# In main.py
from services.video_assembler import VideoAssembler

assembler = VideoAssembler(storage_service=storage_service)
result_url = assembler.assemble_video(blueprint, progress_callback)
```

See `src/main.py` for complete integration example.
