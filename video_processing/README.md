# Video Processing App

## Purpose

The `video_processing` app handles all video-related operations for the Bachata Buddy choreography generation system. It provides services for video generation, storage, pose detection, music analysis, and the complete choreography pipeline that orchestrates all these components.

This app is the core processing layer that:
- Detects and tracks dancers using YOLOv8 pose estimation
- Extracts pose features and generates embeddings
- Analyzes music for tempo, beat, and energy
- Generates choreography videos by stitching move clips
- Manages video and audio storage (local and Google Cloud Storage)
- Orchestrates the end-to-end choreography generation pipeline

## Architecture

The video processing layer sits at the heart of the choreography generation system:

```
User Input → Choreography Pipeline → Video Generator → Output Video
                ↓                          ↓
         Music Analyzer            Move Clips (GCS/Local)
         Pose Detector
         Embedding Generator
                ↓
         AI Services (Recommendations)
```

**Dependency Flow:**
- **Depends on:** `common` (config, exceptions), `ai_services` (recommendations, embeddings)
- **Used by:** `choreography` (views, forms), `instructors` (dashboard)


## Services

### Core Pipeline

#### 1. **ChoreographyPipeline** (`choreography_pipeline.py`)

Orchestrates the complete choreography generation workflow with caching, parallel processing, and optimization.

**Features:**
- End-to-end pipeline from user query to generated video
- Multi-level caching (music analysis, pose embeddings, recommendations)
- Parallel move analysis for faster processing
- Smart service initialization (lazy loading)
- Memory management and cleanup
- Detailed performance metrics

**Pipeline Stages:**
1. Music analysis (tempo, beat detection, energy)
2. Move analysis (pose detection, feature extraction)
3. Recommendation scoring (AI-powered move selection)
4. Video generation (stitching clips with transitions)

**Usage:**
```python
from video_processing.services.choreography_pipeline import (
    ChoreographyPipeline, PipelineConfig, PipelineResult
)

# Initialize pipeline with configuration
config = PipelineConfig(
    quality_mode="balanced",
    enable_caching=True,
    max_workers=4
)
pipeline = ChoreographyPipeline(config)

# Generate choreography
result = await pipeline.generate_choreography(
    audio_path="data/songs/Amor.mp3",
    user_query="romantic slow dance for beginners",
    num_moves=8,
    difficulty="beginner",
    output_filename="my_choreography.mp4",
    user_id="123"
)

# Check results
if result.success:
    print(f"Video generated: {result.output_path}")
    print(f"Processing time: {result.processing_time:.2f}s")
    print(f"Cache hits: {result.cache_hits}")
else:
    print(f"Error: {result.error_message}")
```

**Configuration Options:**
- `quality_mode`: "fast", "balanced", or "high_quality"
- `target_fps`: Frame rate for processing (default: 15)
- `enable_caching`: Enable result caching (default: True)
- `max_workers`: Parallel processing threads (default: 4)
- `enable_parallel_move_analysis`: Analyze moves in parallel (default: True)

**Dependencies:**
- `video_processing.services.music_analyzer`
- `video_processing.services.yolov8_couple_detector`
- `video_processing.services.pose_embedding_generator`
- `video_processing.services.video_generator`
- `ai_services.services.recommendation_engine`

---


### Video Generation

#### 2. **VideoGenerator** (`video_generator.py`)

Generates choreography videos by stitching together move clips using FFmpeg.

**Features:**
- FFmpeg-based video concatenation
- Multiple transition types (cut, crossfade, fade to black)
- Audio overlay and synchronization
- Support for local and Google Cloud Storage
- Automatic temporary file cleanup
- Video trimming and volume adjustment
- Configurable quality settings

**Usage:**
```python
from video_processing.services.video_generator import VideoGenerator
from video_processing.models import (
    VideoGenerationConfig, ChoreographySequence, SelectedMove, TransitionType
)

# Create configuration
config = VideoGenerationConfig(
    output_path="output/my_dance.mp4",
    video_codec="libx264",
    video_bitrate="2M",
    frame_rate=30,
    transition_duration=0.5
)

# Initialize generator
generator = VideoGenerator(config)

# Create choreography sequence
sequence = ChoreographySequence(
    moves=[
        SelectedMove(
            clip_id="basic_step_1",
            video_path="data/Bachata_steps/basic_steps/basic_step_1.mp4",
            start_time=0.0,
            duration=4.0,
            transition_type=TransitionType.CROSSFADE
        ),
        SelectedMove(
            clip_id="cross_body_lead_1",
            video_path="data/Bachata_steps/cross_body_lead/cross_body_lead_1.mp4",
            start_time=4.0,
            duration=5.0,
            transition_type=TransitionType.CUT
        )
    ],
    total_duration=9.0,
    difficulty_level="beginner",
    audio_path="data/songs/Amor.mp3"
)

# Generate video
result = generator.generate_video(
    sequence=sequence,
    audio_path="data/songs/Amor.mp3"
)

if result.success:
    print(f"Video created: {result.output_path}")
    print(f"Duration: {result.duration}s")
    print(f"File size: {result.file_size / 1024 / 1024:.2f} MB")
```

**Supported Transitions:**
- `CUT`: Instant transition between clips
- `CROSSFADE`: Smooth blend between clips
- `FADE_BLACK`: Fade to black, then fade in next clip

**Dependencies:**
- `ffmpeg` (system requirement)
- `google-cloud-storage` (for GCS support)
- `video_processing.models.video_models`

---


### Pose Detection & Analysis

#### 3. **YOLOv8CoupleDetector** (`yolov8_couple_detector.py`)

Multi-person pose detection using Ultralytics YOLOv8-Pose for tracking both dancers.

**Features:**
- Real-time pose detection with 17 COCO keypoints per person
- IoU-based person tracking across frames
- Automatic lead/follow dancer identification
- Confidence-based filtering
- Batch processing for efficiency
- GPU acceleration support

**Keypoint Format (COCO):**
```
0: nose, 1-2: eyes, 3-4: ears, 5-6: shoulders,
7-8: elbows, 9-10: wrists, 11-12: hips,
13-14: knees, 15-16: ankles
```

**Usage:**
```python
from video_processing.services.yolov8_couple_detector import (
    YOLOv8CoupleDetector, CouplePose
)
from common.config.environment_config import EnvironmentConfig

# Initialize detector
config = EnvironmentConfig.load()
detector = YOLOv8CoupleDetector(config.yolov8)

# Detect poses in video
couple_poses = detector.detect_couple(
    video_path="data/Bachata_steps/basic_steps/basic_step_1.mp4",
    target_fps=15
)

# Process results
for pose in couple_poses:
    if pose.has_both_dancers:
        print(f"Frame {pose.frame_idx}: Both dancers detected")
        print(f"Lead confidence: {pose.lead_pose.confidence:.2f}")
        print(f"Follow confidence: {pose.follow_pose.confidence:.2f}")
```

**Configuration:**
- `model_name`: YOLOv8 model variant (default: 'yolov8n-pose.pt')
- `confidence_threshold`: Minimum detection confidence (default: 0.3)
- `device`: 'cpu' or 'cuda' (default: 'cpu')
- `iou_threshold`: IoU threshold for NMS (default: 0.5)
- `max_det`: Maximum detections per frame (default: 10)

**Dependencies:**
- `ultralytics>=8.0.0` (YOLOv8)
- `opencv-python>=4.5.0`
- `scipy>=1.11.0` (for Hungarian algorithm)
- `common.config.environment_config`

---

#### 4. **PoseFeatureExtractor** (`pose_feature_extractor.py`)

Extracts temporal pose features from detected poses for movement analysis.

**Features:**
- Joint angle computation
- Velocity and acceleration tracking
- Movement direction analysis
- Rhythm and timing features
- Energy level estimation
- Complexity scoring

**Usage:**
```python
from video_processing.services.pose_feature_extractor import PoseFeatureExtractor

extractor = PoseFeatureExtractor()

# Extract features from detected poses
temporal_features = extractor.extract_temporal_features(
    couple_poses=couple_poses,
    fps=15
)

# Access features
print(f"Lead velocity: {temporal_features.lead_velocity}")
print(f"Follow velocity: {temporal_features.follow_velocity}")
print(f"Energy level: {temporal_features.energy_level}")
```

**Dependencies:**
- `numpy>=1.21.0`
- `video_processing.services.yolov8_couple_detector`

---

#### 5. **CoupleInteractionAnalyzer** (`couple_interaction_analyzer.py`)

Analyzes spatial relationships and interactions between lead and follow dancers.

**Features:**
- Distance tracking between dancers
- Relative positioning analysis
- Synchronization metrics
- Connection point detection
- Interaction pattern recognition

**Usage:**
```python
from video_processing.services.couple_interaction_analyzer import (
    CoupleInteractionAnalyzer
)

analyzer = CoupleInteractionAnalyzer()

# Analyze couple interactions
interactions = analyzer.analyze_interactions(
    couple_poses=couple_poses,
    fps=15
)

# Access interaction metrics
print(f"Average distance: {interactions.avg_distance:.2f}")
print(f"Synchronization score: {interactions.sync_score:.2f}")
```

**Dependencies:**
- `numpy>=1.21.0`
- `video_processing.services.yolov8_couple_detector`

---

#### 6. **PoseEmbeddingGenerator** (`pose_embedding_generator.py`)

Generates embeddings from pose sequences for similarity search and recommendation.

**Features:**
- Generates 512D embeddings for lead and follow dancers
- Generates 256D interaction embeddings
- Temporal aggregation of pose features
- Normalization and quality validation

**Embedding Structure:**
```
lead_embedding: 512D (lead dancer movements)
follow_embedding: 512D (follow dancer movements)
interaction_embedding: 256D (couple dynamics)
```

**Usage:**
```python
from video_processing.services.pose_embedding_generator import (
    PoseEmbeddingGenerator
)

generator = PoseEmbeddingGenerator()

# Generate embeddings from video
embeddings = generator.generate_embeddings(
    video_path="data/Bachata_steps/basic_steps/basic_step_1.mp4"
)

print(f"Lead embedding shape: {embeddings.lead_embedding.shape}")
print(f"Follow embedding shape: {embeddings.follow_embedding.shape}")
print(f"Interaction embedding shape: {embeddings.interaction_embedding.shape}")
```

**Dependencies:**
- `video_processing.services.yolov8_couple_detector`
- `video_processing.services.pose_feature_extractor`
- `video_processing.services.couple_interaction_analyzer`
- `ai_services.services.quality_metrics`

---


### Music Analysis

#### 7. **MusicAnalyzer** (`music_analyzer.py`)

Analyzes audio files to extract musical features for choreography generation.

**Features:**
- Tempo (BPM) detection
- Beat tracking and timing
- Energy level estimation
- Spectral features (MFCCs, chroma)
- Key and mode detection
- Danceability scoring

**Usage:**
```python
from video_processing.services.music_analyzer import MusicAnalyzer

analyzer = MusicAnalyzer()

# Analyze audio file
features = analyzer.analyze(
    audio_path="data/songs/Amor.mp3"
)

print(f"Tempo: {features.tempo} BPM")
print(f"Energy: {features.energy_level}")
print(f"Danceability: {features.danceability:.2f}")
print(f"Key: {features.key}")

# Extract audio embedding for similarity search
audio_embedding = analyzer.extract_features(
    audio_path="data/songs/Amor.mp3"
)
# Returns: 128D numpy array
```

**Extracted Features:**
- `tempo`: Beats per minute
- `beat_times`: Timestamps of detected beats
- `energy_level`: "low", "medium", or "high"
- `danceability`: Score 0-1 indicating dance suitability
- `key`: Musical key (e.g., "C major")
- `mode`: Major or minor
- `spectral_centroid`: Brightness of sound
- `mfccs`: Mel-frequency cepstral coefficients

**Dependencies:**
- `librosa>=0.10.0` (audio analysis)
- `numpy>=1.21.0`
- `scipy>=1.11.0`

---


### Storage Services

#### 8. **VideoStorageService** (`video_storage_service.py`)

Manages video file storage with support for local filesystem and Google Cloud Storage.

**Features:**
- Unified interface for local and cloud storage
- Automatic GCS upload/download
- Signed URL generation for secure access
- Batch operations
- Storage quota management
- Automatic cleanup of temporary files

**Usage:**
```python
from video_processing.services.video_storage_service import VideoStorageService

storage = VideoStorageService()

# Upload video to GCS
gcs_path = storage.upload_video(
    local_path="output/my_dance.mp4",
    destination_path="user_videos/123/my_dance.mp4"
)

# Download video from GCS
local_path = storage.download_video(
    gcs_path="user_videos/123/my_dance.mp4",
    local_path="temp/downloaded.mp4"
)

# Generate signed URL for temporary access
url = storage.get_signed_url(
    gcs_path="user_videos/123/my_dance.mp4",
    expiration_minutes=60
)

# List user videos
videos = storage.list_user_videos(user_id="123")
```

**Dependencies:**
- `google-cloud-storage` (for GCS support)
- `common.config.environment_config`

---

#### 9. **AudioStorageService** (`audio_storage_service.py`)

Manages audio file storage with support for local filesystem and Google Cloud Storage.

**Features:**
- Unified interface for local and cloud storage
- Audio format conversion
- Metadata extraction
- Batch operations
- Storage quota management

**Usage:**
```python
from video_processing.services.audio_storage_service import AudioStorageService

storage = AudioStorageService()

# Upload audio to GCS
gcs_path = storage.upload_audio(
    local_path="data/songs/Amor.mp3",
    destination_path="songs/Amor.mp3"
)

# Download audio from GCS
local_path = storage.download_audio(
    gcs_path="songs/Amor.mp3",
    local_path="temp/song.mp3"
)

# Get audio metadata
metadata = storage.get_audio_metadata(
    audio_path="data/songs/Amor.mp3"
)
print(f"Duration: {metadata['duration']}s")
print(f"Sample rate: {metadata['sample_rate']} Hz")
```

**Dependencies:**
- `google-cloud-storage` (for GCS support)
- `librosa>=0.10.0` (for metadata extraction)
- `common.config.environment_config`

---

#### 10. **YouTubeService** (`youtube_service.py`)

Downloads and processes YouTube videos for choreography analysis.

**Features:**
- YouTube video download using yt-dlp
- Format selection (best quality)
- Audio extraction
- Metadata retrieval
- Error handling for restricted/unavailable videos
- Progress tracking

**Usage:**
```python
from video_processing.services.youtube_service import YouTubeService

service = YouTubeService(output_dir="data/temp")

# Download YouTube video
result = service.download_video(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    output_filename="dance_video"
)

if result['success']:
    print(f"Downloaded: {result['video_path']}")
    print(f"Duration: {result['duration']}s")
    print(f"Title: {result['title']}")
else:
    print(f"Error: {result['error']}")

# Extract audio only
audio_path = service.download_audio(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    output_filename="song"
)
```

**Dependencies:**
- `yt-dlp>=2023.0.0` (YouTube downloader)
- `common.exceptions` (for error handling)

---


## Models

The `video_processing.models` module provides Pydantic models for video generation and choreography sequences.

### Data Models

#### **TransitionType** (Enum)
Defines transition types between video clips:
- `CUT`: Instant transition
- `CROSSFADE`: Smooth blend
- `FADE_BLACK`: Fade to black, then fade in

#### **SelectedMove** (Model)
Represents a selected move clip in a choreography sequence.

**Fields:**
- `clip_id`: Unique identifier for the move clip
- `video_path`: Path to the video file
- `start_time`: Start time in final video (seconds)
- `duration`: Duration of the clip (seconds)
- `transition_type`: Transition to next clip
- `trim_start`: Seconds to trim from start (optional)
- `trim_end`: Seconds to trim from end (optional)
- `volume_adjustment`: Volume factor 0.0-2.0 (optional)

#### **ChoreographySequence** (Model)
Complete choreography sequence with selected moves.

**Fields:**
- `moves`: List of SelectedMove objects
- `total_duration`: Total duration in seconds
- `difficulty_level`: Overall difficulty
- `audio_path`: Path to audio file (optional)
- `audio_tempo`: Detected tempo in BPM (optional)
- `generation_timestamp`: When generated (optional)
- `generation_parameters`: Generation parameters (optional)

**Properties:**
- `move_count`: Number of moves in sequence
- `get_moves_by_transition_type()`: Filter moves by transition

#### **VideoGenerationConfig** (Model)
Configuration for video generation process.

**Fields:**
- `output_path`: Path for generated video
- `output_format`: Video format (default: "mp4")
- `video_codec`: Video codec (default: "libx264")
- `audio_codec`: Audio codec (default: "aac")
- `video_bitrate`: Video bitrate (default: "2M")
- `audio_bitrate`: Audio bitrate (default: "128k")
- `frame_rate`: Output frame rate (default: 30)
- `transition_duration`: Transition duration (default: 0.5s)
- `fade_duration`: Fade duration (default: 0.3s)
- `temp_dir`: Temporary files directory
- `preserve_aspect_ratio`: Preserve aspect ratio (default: True)
- `add_audio_overlay`: Add audio track (default: True)
- `normalize_audio`: Normalize audio levels (default: True)
- `cleanup_temp_files`: Clean up after generation (default: True)

#### **VideoGenerationResult** (Model)
Result of video generation process.

**Fields:**
- `success`: Whether generation succeeded
- `output_path`: Path to generated video
- `duration`: Video duration in seconds
- `file_size`: File size in bytes
- `processing_time`: Time taken (seconds)
- `clips_processed`: Number of clips processed
- `error_message`: Error message if failed
- `warnings`: Warning messages

**Usage:**
```python
from video_processing.models import (
    TransitionType,
    SelectedMove,
    ChoreographySequence,
    VideoGenerationConfig,
    VideoGenerationResult
)

# Create a choreography sequence
sequence = ChoreographySequence(
    moves=[
        SelectedMove(
            clip_id="basic_step_1",
            video_path="data/Bachata_steps/basic_steps/basic_step_1.mp4",
            start_time=0.0,
            duration=4.0,
            transition_type=TransitionType.CROSSFADE
        )
    ],
    total_duration=4.0,
    difficulty_level="beginner"
)

# Access properties
print(f"Number of moves: {sequence.move_count}")
crossfade_moves = sequence.get_moves_by_transition_type(TransitionType.CROSSFADE)
```

---


## Dependencies

### Required Python Packages

```toml
# Video Processing
opencv-python>=4.5.0           # Video I/O and processing
ffmpeg-python>=0.2.0           # FFmpeg wrapper (optional)

# Pose Detection
ultralytics>=8.0.0             # YOLOv8 pose estimation
mediapipe                      # Alternative pose detection (via ai_services)

# Audio Analysis
librosa>=0.10.0                # Music analysis and feature extraction
soundfile>=0.12.0              # Audio file I/O

# YouTube Support
yt-dlp>=2023.0.0               # YouTube video download

# Cloud Storage
google-cloud-storage           # Google Cloud Storage integration

# Scientific Computing
numpy>=1.21.0                  # Numerical operations
scipy>=1.11.0                  # Scientific computing (Hungarian algorithm)

# Utilities
tqdm>=4.62.0                   # Progress bars
```

### System Requirements

- **FFmpeg**: Required for video generation and processing
  ```bash
  # macOS
  brew install ffmpeg
  
  # Ubuntu/Debian
  sudo apt-get install ffmpeg
  
  # Verify installation
  ffmpeg -version
  ```

- **YOLOv8 Model**: Download pose estimation model
  ```bash
  # Model is automatically downloaded on first use
  # Or manually download to project root:
  wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt
  ```

### Internal Dependencies

```python
# From common app
from common.config.environment_config import EnvironmentConfig, YOLOv8Config
from common.exceptions import (
    VideoGenerationError,
    MusicAnalysisError,
    MoveAnalysisError,
    ResourceError
)
from common.services.resource_manager import resource_manager
from common.services.temp_file_manager import temp_file_manager

# From ai_services app
from ai_services.services.recommendation_engine import RecommendationEngine
from ai_services.services.quality_metrics import QualityMetrics
from ai_services.services.elasticsearch_service import ElasticsearchService

# From choreography app
from choreography.services.annotation_interface import AnnotationInterface
```

---

## Configuration

Video processing services are configured through environment variables and the `EnvironmentConfig` class:

```bash
# .env file

# Environment
ENVIRONMENT=local  # or 'cloud'

# YOLOv8 Configuration
YOLOV8_MODEL=yolov8n-pose.pt
YOLOV8_CONFIDENCE=0.3
YOLOV8_DEVICE=cpu  # or 'cuda' for GPU
YOLOV8_IOU_THRESHOLD=0.5
YOLOV8_MAX_DET=10

# Google Cloud Storage (for cloud environment)
GCS_BUCKET_NAME=your-bucket-name
GCP_PROJECT_ID=your-project-id

# Storage Paths
VIDEO_STORAGE_PATH=data/Bachata_steps
AUDIO_STORAGE_PATH=data/songs
OUTPUT_PATH=data/output
TEMP_PATH=data/temp
```

```python
# Usage in code
from common.config.environment_config import EnvironmentConfig

config = EnvironmentConfig.load()

# Access YOLOv8 configuration
yolo_config = config.yolov8
print(f"Model: {yolo_config.model_name}")
print(f"Device: {yolo_config.device}")
print(f"Confidence: {yolo_config.confidence_threshold}")
```

---


## Testing

Tests for video processing services are located in `tests/services/` and `tests/integration/`:

```bash
# Run all video processing tests
uv run pytest tests/services/test_yolov8_couple_detector.py
uv run pytest tests/services/test_pose_feature_extractor.py
uv run pytest tests/services/test_couple_interaction_analyzer.py

# Run integration tests
uv run pytest tests/integration/test_embedding_pipeline_integration.py
uv run pytest tests/integration/test_integration.py

# Run choreography tests
uv run pytest tests/choreography/
```

**Key Test Files:**
- `test_yolov8_couple_detector.py` - Pose detection tests
- `test_pose_feature_extractor.py` - Feature extraction tests
- `test_couple_interaction_analyzer.py` - Interaction analysis tests
- `test_embedding_pipeline_integration.py` - End-to-end pipeline tests
- `test_ai_choreography_generation.py` - Choreography generation tests

---

## Common Usage Patterns

### 1. End-to-End Choreography Generation

```python
from video_processing.services.choreography_pipeline import (
    ChoreographyPipeline, PipelineConfig
)

# Initialize pipeline
config = PipelineConfig(
    quality_mode="balanced",
    enable_caching=True,
    max_workers=4
)
pipeline = ChoreographyPipeline(config)

# Generate choreography
result = await pipeline.generate_choreography(
    audio_path="data/songs/Amor.mp3",
    user_query="romantic slow dance for beginners",
    num_moves=8,
    difficulty="beginner",
    output_filename="my_choreography.mp4",
    user_id="123"
)

if result.success:
    print(f"✓ Video: {result.output_path}")
    print(f"✓ Duration: {result.sequence_duration:.1f}s")
    print(f"✓ Processing time: {result.processing_time:.1f}s")
    print(f"✓ Moves: {result.moves_analyzed}")
```

### 2. Analyze a Dance Video

```python
from video_processing.services.yolov8_couple_detector import YOLOv8CoupleDetector
from video_processing.services.pose_feature_extractor import PoseFeatureExtractor
from video_processing.services.pose_embedding_generator import PoseEmbeddingGenerator
from common.config.environment_config import EnvironmentConfig

# Initialize services
config = EnvironmentConfig.load()
detector = YOLOv8CoupleDetector(config.yolov8)
extractor = PoseFeatureExtractor()
generator = PoseEmbeddingGenerator()

# Detect poses
video_path = "data/Bachata_steps/basic_steps/basic_step_1.mp4"
couple_poses = detector.detect_couple(video_path, target_fps=15)

# Extract features
temporal_features = extractor.extract_temporal_features(couple_poses, fps=15)

# Generate embeddings
embeddings = generator.generate_embeddings(video_path)

print(f"Frames processed: {len(couple_poses)}")
print(f"Detection rate: {sum(1 for p in couple_poses if p.has_both_dancers) / len(couple_poses):.2%}")
print(f"Lead embedding: {embeddings.lead_embedding.shape}")
print(f"Follow embedding: {embeddings.follow_embedding.shape}")
```

### 3. Analyze Music

```python
from video_processing.services.music_analyzer import MusicAnalyzer

analyzer = MusicAnalyzer()

# Analyze audio
features = analyzer.analyze("data/songs/Amor.mp3")

print(f"Tempo: {features.tempo:.1f} BPM")
print(f"Energy: {features.energy_level}")
print(f"Danceability: {features.danceability:.2f}")
print(f"Key: {features.key}")
print(f"Beats detected: {len(features.beat_times)}")

# Extract embedding for similarity search
audio_embedding = analyzer.extract_features("data/songs/Amor.mp3")
print(f"Audio embedding: {audio_embedding.shape}")  # (128,)
```

### 4. Generate Custom Video

```python
from video_processing.services.video_generator import VideoGenerator
from video_processing.models import (
    VideoGenerationConfig,
    ChoreographySequence,
    SelectedMove,
    TransitionType
)

# Configure video generation
config = VideoGenerationConfig(
    output_path="output/custom_dance.mp4",
    video_codec="libx264",
    video_bitrate="3M",
    frame_rate=30,
    transition_duration=0.5
)

generator = VideoGenerator(config)

# Create sequence
sequence = ChoreographySequence(
    moves=[
        SelectedMove(
            clip_id="basic_step_1",
            video_path="data/Bachata_steps/basic_steps/basic_step_1.mp4",
            start_time=0.0,
            duration=4.0,
            transition_type=TransitionType.CROSSFADE
        ),
        SelectedMove(
            clip_id="cross_body_lead_1",
            video_path="data/Bachata_steps/cross_body_lead/cross_body_lead_1.mp4",
            start_time=4.0,
            duration=5.0,
            transition_type=TransitionType.CUT
        ),
        SelectedMove(
            clip_id="body_roll_1",
            video_path="data/Bachata_steps/body_roll/body_roll_1.mp4",
            start_time=9.0,
            duration=4.0,
            transition_type=TransitionType.FADE_BLACK
        )
    ],
    total_duration=13.0,
    difficulty_level="intermediate",
    audio_path="data/songs/Amor.mp3"
)

# Generate video
result = generator.generate_video(
    sequence=sequence,
    audio_path="data/songs/Amor.mp3"
)

if result.success:
    print(f"✓ Video created: {result.output_path}")
    print(f"✓ Duration: {result.duration:.1f}s")
    print(f"✓ Size: {result.file_size / 1024 / 1024:.1f} MB")
    print(f"✓ Processing time: {result.processing_time:.1f}s")
```

### 5. Download and Process YouTube Video

```python
from video_processing.services.youtube_service import YouTubeService
from video_processing.services.yolov8_couple_detector import YOLOv8CoupleDetector

# Download video
youtube = YouTubeService(output_dir="data/temp")
result = youtube.download_video(
    url="https://www.youtube.com/watch?v=example",
    output_filename="dance_tutorial"
)

if result['success']:
    # Analyze the downloaded video
    detector = YOLOv8CoupleDetector()
    poses = detector.detect_couple(result['video_path'])
    
    print(f"Downloaded: {result['title']}")
    print(f"Duration: {result['duration']}s")
    print(f"Frames analyzed: {len(poses)}")
```

---


## Performance Considerations

### Pipeline Optimization

- **Caching**: Enable caching to avoid reprocessing music and pose analysis
  - Music analysis cached by audio file hash
  - Pose embeddings cached by video file hash
  - Cache TTL: 24 hours (configurable)

- **Parallel Processing**: Use `max_workers` to process moves in parallel
  - Default: 4 workers
  - Recommended: Number of CPU cores - 1

- **Quality Modes**:
  - `fast`: 10 FPS, lower confidence threshold (0.3)
  - `balanced`: 15 FPS, medium confidence (0.4) - **recommended**
  - `high_quality`: 20 FPS, high confidence (0.5)

- **Lazy Loading**: Services are initialized only when needed
  - YOLOv8 model loaded on first detection
  - Recommendation engine initialized on first query

### Video Generation Optimization

- **FFmpeg Settings**:
  - Use hardware acceleration when available (h264_videotoolbox on macOS)
  - Adjust bitrate based on quality needs (1M-5M)
  - Use preset "fast" or "medium" for encoding speed

- **Transition Optimization**:
  - `CUT` transitions are fastest (no processing)
  - `CROSSFADE` adds ~0.5s per transition
  - Minimize `FADE_BLACK` transitions for speed

### Pose Detection Optimization

- **Frame Rate**: Lower FPS = faster processing
  - 10 FPS: Fast, good for simple moves
  - 15 FPS: Balanced, recommended for most cases
  - 20+ FPS: High quality, needed for fast movements

- **GPU Acceleration**: Use CUDA for 5-10x speedup
  ```python
  config = YOLOv8Config(device='cuda')
  ```

- **Batch Processing**: Process multiple videos in parallel
  ```python
  with ThreadPoolExecutor(max_workers=4) as executor:
      futures = [executor.submit(detector.detect_couple, path) for path in video_paths]
  ```

### Memory Management

- **Cleanup**: Enable automatic cleanup to free memory
  ```python
  config = PipelineConfig(cleanup_after_generation=True)
  ```

- **Cache Size**: Limit cache size to prevent disk overflow
  ```python
  config = PipelineConfig(max_cache_size_mb=500)
  ```

- **Temporary Files**: Use context managers for automatic cleanup
  ```python
  from common.services.temp_file_manager import temp_file_manager
  
  async with temp_file_manager.temp_file(suffix=".mp4") as temp_path:
      # Use temp file
      pass  # Automatically cleaned up
  ```

---

## Troubleshooting

### Common Issues

#### 1. FFmpeg Not Found

```bash
# Error: FFmpeg is not installed or not in PATH

# Solution: Install FFmpeg
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Verify
ffmpeg -version
```

#### 2. YOLOv8 Model Not Found

```python
# Error: Model file 'yolov8n-pose.pt' not found

# Solution: Model downloads automatically on first use
# Or manually download:
from ultralytics import YOLO
model = YOLO('yolov8n-pose.pt')  # Downloads if not present

# Or download directly:
# wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt
```

#### 3. Low Pose Detection Rate

```python
# Issue: Many frames have no detections or only one dancer

# Solutions:
# 1. Lower confidence threshold
config = YOLOv8Config(confidence_threshold=0.2)

# 2. Check video quality
# - Ensure dancers are clearly visible
# - Good lighting
# - Minimal occlusions

# 3. Increase frame rate
couple_poses = detector.detect_couple(video_path, target_fps=20)

# 4. Check detection statistics
detection_rate = sum(1 for p in couple_poses if p.has_both_dancers) / len(couple_poses)
print(f"Detection rate: {detection_rate:.2%}")
```

#### 4. Video Generation Fails

```python
# Error: FFmpeg encoding failed

# Common causes:
# 1. Invalid video paths - check all files exist
# 2. Incompatible video formats - ensure all clips are same format
# 3. Insufficient disk space - check available space
# 4. Corrupted video files - validate input files

# Debug:
import subprocess
result = subprocess.run(
    ["ffmpeg", "-i", "input.mp4"],
    capture_output=True,
    text=True
)
print(result.stderr)  # Check for errors
```

#### 5. Memory Issues

```python
# Error: Out of memory during processing

# Solutions:
# 1. Reduce frame rate
config = PipelineConfig(target_fps=10)

# 2. Enable cleanup
config = PipelineConfig(cleanup_after_generation=True)

# 3. Process videos in smaller batches
# 4. Limit cache size
config = PipelineConfig(max_cache_size_mb=200)

# 5. Use resource manager
from common.services.resource_manager import resource_manager
resources = resource_manager.get_system_resources()
print(f"Memory usage: {resources['memory']['percent_used']}%")
```

#### 6. Slow Processing

```python
# Issue: Pipeline takes too long

# Solutions:
# 1. Enable caching
config = PipelineConfig(enable_caching=True)

# 2. Use parallel processing
config = PipelineConfig(
    max_workers=4,
    enable_parallel_move_analysis=True
)

# 3. Use fast quality mode
config = PipelineConfig(quality_mode="fast")

# 4. Use GPU acceleration
yolo_config = YOLOv8Config(device='cuda')

# 5. Reduce frame rate
config = PipelineConfig(target_fps=10)
```

#### 7. GCS Upload/Download Errors

```python
# Error: Failed to upload/download from Google Cloud Storage

# Solutions:
# 1. Check credentials
# export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# 2. Verify bucket exists and you have permissions
from google.cloud import storage
client = storage.Client()
bucket = client.bucket('your-bucket-name')
print(bucket.exists())

# 3. Check environment variables
import os
print(f"Environment: {os.environ.get('ENVIRONMENT')}")
print(f"Bucket: {os.environ.get('GCS_BUCKET_NAME')}")

# 4. Fall back to local storage
# Set ENVIRONMENT=local to use local filesystem
```

---


## Migration Guide

If you're migrating from the old `core.services` structure:

### Old Import Paths
```python
# Deprecated
from core.services.video_generator import VideoGenerator
from core.services.choreography_pipeline import ChoreographyPipeline
from core.services.yolov8_couple_detector import YOLOv8CoupleDetector
from core.services.pose_feature_extractor import PoseFeatureExtractor
from core.services.pose_embedding_generator import PoseEmbeddingGenerator
from core.services.couple_interaction_analyzer import CoupleInteractionAnalyzer
from core.services.music_analyzer import MusicAnalyzer
from core.services.video_storage_service import VideoStorageService
from core.services.audio_storage_service import AudioStorageService
from core.services.youtube_service import YouTubeService
from core.models.video_models import ChoreographySequence, SelectedMove
```

### New Import Paths
```python
# Current
from video_processing.services.video_generator import VideoGenerator
from video_processing.services.choreography_pipeline import ChoreographyPipeline
from video_processing.services.yolov8_couple_detector import YOLOv8CoupleDetector
from video_processing.services.pose_feature_extractor import PoseFeatureExtractor
from video_processing.services.pose_embedding_generator import PoseEmbeddingGenerator
from video_processing.services.couple_interaction_analyzer import CoupleInteractionAnalyzer
from video_processing.services.music_analyzer import MusicAnalyzer
from video_processing.services.video_storage_service import VideoStorageService
from video_processing.services.audio_storage_service import AudioStorageService
from video_processing.services.youtube_service import YouTubeService
from video_processing.models import ChoreographySequence, SelectedMove
```

All functionality remains the same - only import paths have changed.

### Configuration Changes

Configuration has moved from `core.config` to `common.config`:

```python
# Old
from core.config.environment_config import EnvironmentConfig, YOLOv8Config

# New
from common.config.environment_config import EnvironmentConfig, YOLOv8Config
```

### Exception Changes

Exceptions have moved from `core.exceptions` to `common.exceptions`:

```python
# Old
from core.exceptions import VideoGenerationError, MusicAnalysisError

# New
from common.exceptions import VideoGenerationError, MusicAnalysisError
```

---

## Contributing

When adding new video processing services:

1. Place service files in `video_processing/services/`
2. Add comprehensive docstrings with features and usage examples
3. Include type hints for all function parameters and returns
4. Add tests in `tests/services/test_<service_name>.py`
5. Update this README with service documentation
6. Follow the existing service patterns for consistency
7. Consider performance implications (caching, parallel processing)
8. Handle errors gracefully with appropriate exceptions
9. Support both local and cloud storage when applicable
10. Add logging for debugging and monitoring

### Service Template

```python
"""
Brief description of the service.

Detailed explanation of what the service does and when to use it.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ServiceResult:
    """Result of service operation."""
    success: bool
    data: Optional[any] = None
    error_message: Optional[str] = None


class MyService:
    """
    Service for doing something specific.
    
    Features:
    - Feature 1
    - Feature 2
    - Feature 3
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize the service.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        logger.info("MyService initialized")
    
    def process(self, input_data: str) -> ServiceResult:
        """
        Process input data.
        
        Args:
            input_data: Data to process
            
        Returns:
            ServiceResult with processing results
            
        Raises:
            ValueError: If input_data is invalid
        """
        try:
            # Implementation
            result = self._do_processing(input_data)
            return ServiceResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return ServiceResult(success=False, error_message=str(e))
    
    def _do_processing(self, data: str) -> any:
        """Internal processing logic."""
        # Implementation
        pass
```

---

## Related Documentation

- [Common App README](../common/README.md) - Shared utilities and configuration
- [AI Services README](../ai_services/README.md) - AI and ML services
- [Architecture Diagrams](../../ARCHITECTURE_DIAGRAMS.md) - System architecture overview
- [Deployment Guide](../../DEPLOYMENT.md) - Deployment instructions
- [Video Generation Fixes](../../VIDEO_GENERATION_FIXES.md) - Known issues and fixes

---

## Performance Benchmarks

Typical processing times on a MacBook Pro (M1, 16GB RAM):

| Operation | Duration | Notes |
|-----------|----------|-------|
| Music Analysis | 2-5s | Per 3-minute song |
| Pose Detection (15 FPS) | 3-8s | Per 5-second clip |
| Pose Detection (GPU) | 1-3s | 3-5x faster with CUDA |
| Embedding Generation | 1-2s | Per clip |
| Video Generation (8 moves) | 10-20s | Depends on transitions |
| Full Pipeline (cached) | 15-30s | With cache hits |
| Full Pipeline (no cache) | 45-90s | First run |

---

## License

See [LICENSE](../../LICENSE) file in the project root.

