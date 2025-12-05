# Design Document

## Overview

This design refactors the video processing architecture from a complex job container that performs audio analysis, move searching, and choreography generation, to a simple blueprint-based video assembly service. The intelligence moves to the API/backend, which generates complete blueprints that the job container follows to assemble videos.

### Current State

The system currently supports two user paths:
- **Path 1: "Select Song"** (`/api/choreography/generate-from-song`) - User selects a song from database
- **Path 2: "Describe Choreo"** (`/api/choreography/generate-with-ai`) - User describes choreography in natural language

Both paths currently pass only parameters to a heavy job container that does everything (audio analysis, Elasticsearch queries, AI generation, video assembly).

### Key Changes

1. **Remove Elasticsearch** from job container - move vector search to API with in-memory FAISS operations
2. **Simplify Job Container** - reduce to minimal dependencies (FFmpeg, psycopg2, GCS client)
3. **Blueprint-Based Architecture** - API generates complete video assembly instructions for BOTH user paths
4. **Dual Storage Support** - seamless operation with local filesystem and Google Cloud Storage
5. **Unified Blueprint Schema** - Both user paths generate the same blueprint format

## Architecture

### End-to-End Video Generation Flow

#### Two User Paths

**Path 1: "Select Song"**
```
POST /api/choreography/generate-from-song
{
  "song_id": 123,
  "difficulty": "intermediate",
  "energy_level": "high",
  "style": "modern"
}
```

**Path 2: "Describe Choreo"**
```
POST /api/choreography/generate-with-ai
{
  "query": "Create a romantic bachata for beginners with smooth transitions"
}
```

#### Step-by-Step Process (Both Paths)

**2. API Processes Request (API)**
- **Path 1:** Retrieve song from database using song_id
- **Path 2:** Parse natural language query with Gemini AI to extract parameters (difficulty, energy_level, style, song preferences)
- **Path 2:** If song not specified, select appropriate song from database based on parsed parameters

**3. API Creates Task (API → Database)**
- Create `ChoreographyTask` record with status="pending"
- Link to song (if Path 1) or store parsed parameters (if Path 2)
- Return task_id to user for polling

**4. API Analyzes Audio (API → Music Analyzer)**
- Load song audio file from database (path: `data/songs/Amor.mp3`)
- Use Librosa to extract:
  - Tempo (BPM): 129.2
  - Beat positions: [0.0, 0.465, 0.93, ...]
  - Musical sections: 7 sections detected
  - Rhythm strength: 0.834
  - Syncopation level: 0.591
- Duration: 232.96 seconds

**5. API Loads Move Embeddings (API → Database)**
- Query `MoveEmbedding` table
- Load all embeddings into memory (cached for 1 hour)
- Filter by difficulty="intermediate", energy_level="high", style="modern"
- Result: ~50 candidate moves

**6. API Performs Vector Search (API → FAISS)**
- For each beat/section, create query embedding based on:
  - Current tempo
  - Energy level at that point
  - Musical features
- Use FAISS IndexFlatIP (inner product) for efficient similarity search:
  ```python
  # FAISS automatically handles normalization and returns top-k results
  distances, indices = faiss_index.search(query_emb, k=10)
  ```
- Select top 10 most similar moves for each section using FAISS's optimized search

**7. API Generates Choreography Sequence (API → Gemini AI)**
- Send to Gemini:
  - Music analysis results
  - Top matching moves for each section
  - User preferences (difficulty, energy, style)
- Gemini returns optimized sequence:
  - 29 moves total
  - Each move: 8 seconds duration
  - Smooth transitions between moves
  - Variety and flow considerations

**8. API Creates Blueprint (API → Blueprint Generator)**
```json
{
  "task_id": "abc-123",
  "song": {
    "path": "data/songs/Amor.mp3",
    "duration": 232.96
  },
  "moves_used": [
    {
      "clip_id": "move_1",
      "video_path": "data/Bachata_steps/body_roll/body_roll_1.mp4",
      "start_time": 0.0,
      "duration": 8.0
    },
    {
      "clip_id": "move_2",
      "video_path": "data/Bachata_steps/body_roll/body_roll_3.mp4",
      "start_time": 8.0,
      "duration": 8.0
    }
    // ... 27 more moves
  ],
  "video_output": {
    "output_path": "data/output/choreography_abc-123.mp4"
  }
}
```

**9. API Stores Blueprint (API → Database)**
- Save blueprint JSON to `Blueprint` table
- Link to `ChoreographyTask`

**10. API Submits Job (API → Cloud Run Jobs / Docker)**
- **Local:** `docker-compose run job` with env var `BLUEPRINT_JSON='{...}'`
- **GCP:** Create Cloud Run Job execution with env var `BLUEPRINT_JSON='{...}'`

**11. Job Container Starts (Job Container)**
- Parse `BLUEPRINT_JSON` environment variable
- Validate schema (required fields, valid paths)
- Update task status to "running" in database

**12. Job Fetches Media Files (Job Container → Storage)**
- **Local mode:**
  - Read song: `data/songs/Amor.mp3`
  - Read 29 video clips from `data/Bachata_steps/*/`
- **GCS mode:**
  - Download song from `gs://bucket/songs/Amor.mp3`
  - Download 29 video clips from `gs://bucket/Bachata_steps/*/`
- Use parallel downloads for speed

**13. Job Assembles Video (Job Container → FFmpeg)**
```bash
# Create concat file listing all clips
echo "file 'body_roll_1.mp4'" > concat.txt
echo "file 'body_roll_3.mp4'" >> concat.txt
# ... for all 29 clips

# Concatenate video clips
ffmpeg -f concat -safe 0 -i concat.txt -c copy temp_video.mp4

# Add audio track
ffmpeg -i temp_video.mp4 -i Amor.mp3 -c:v copy -c:a aac -shortest choreography_abc-123.mp4
```

**14. Job Uploads Result (Job Container → Storage)**
- **Local mode:** Save to `data/output/choreography_abc-123.mp4`
- **GCS mode:** Upload to `gs://bucket/output/choreography_abc-123.mp4`

**15. Job Updates Database (Job Container → Database)**
```sql
UPDATE choreography_tasks 
SET status='completed',
    progress=100,
    result='{"video_url": "...", "duration": 227.18, "file_size": 36992903}'
WHERE task_id='abc-123';
```

**16. User Polls Status (Frontend → API)**
```
GET /api/choreography/tasks/abc-123
Response: {
  "status": "completed",
  "video_url": "/media/output/choreography_abc-123.mp4",
  "duration": 227.18
}
```

**17. User Watches Video (Frontend → Storage)**
- Stream video from storage
- User sees their custom choreography!

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          API/Backend                             │
│                                                                   │
│  1. Receive choreography request                                 │
│  2. Analyze audio (tempo, beats, energy) - Librosa               │
│  3. Load move embeddings from database                           │
│  4. Perform in-memory vector search (FAISS similarity search)    │
│  5. Generate choreography sequence (Gemini AI)                   │
│  6. Create blueprint JSON                                        │
│  7. Store blueprint in database                                  │
│  8. Submit job to Cloud Run Jobs with blueprint                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Blueprint JSON (env var)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Job Container                              │
│                                                                   │
│  1. Receive blueprint JSON as environment variable               │
│  2. Parse and validate blueprint                                 │
│  3. Fetch song audio from storage (local/GCS)                    │
│  4. Fetch video clips from storage (parallel downloads)          │
│  5. Assemble video with FFmpeg (concat + audio)                  │
│  6. Upload result to storage (local/GCS)                         │
│  7. Update database with completion status                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### API/Backend
- Audio analysis (Librosa)
- Vector search (FAISS similarity search)
- Choreography generation (Gemini AI)
- Blueprint creation
- Job submission
- Move embedding management

#### Job Container
- Blueprint parsing
- Storage access (local/GCS)
- Video assembly (FFmpeg)
- Database status updates
- Error handling

## Components and Interfaces

### 1. Blueprint Schema

Based on the actual `ChoreographySequence` and `SelectedMove` data structures in the codebase:

```json
{
  "task_id": "uuid-string",
  "audio_path": "data/songs/Amor.mp3",
  "audio_tempo": 129.2,
  "moves": [
    {
      "clip_id": "move_1",
      "video_path": "data/Bachata_steps/body_roll/body_roll_1.mp4",
      "start_time": 0.0,
      "duration": 8.0,
      "transition_type": "cut",
      "original_duration": 8.0,
      "trim_start": 0.0,
      "trim_end": 0.0,
      "volume_adjustment": 1.0
    },
    {
      "clip_id": "move_2",
      "video_path": "data/Bachata_steps/body_roll/body_roll_3.mp4",
      "start_time": 8.0,
      "duration": 8.0,
      "transition_type": "crossfade",
      "original_duration": 8.0,
      "trim_start": 0.0,
      "trim_end": 0.0,
      "volume_adjustment": 1.0
    }
  ],
  "total_duration": 232.0,
  "difficulty_level": "intermediate",
  "generation_timestamp": "2025-11-09T00:00:00Z",
  "generation_parameters": {
    "energy_level": "high",
    "style": "modern",
    "user_id": 1
  },
  "output_config": {
    "output_path": "data/output/choreography_{task_id}.mp4",
    "output_format": "mp4",
    "video_codec": "libx264",
    "audio_codec": "aac",
    "video_bitrate": "2M",
    "audio_bitrate": "128k",
    "frame_rate": 30,
    "transition_duration": 0.5,
    "fade_duration": 0.3,
    "add_audio_overlay": true,
    "normalize_audio": true
  }
}
```

**Key Fields (matching actual code structures):**

**ChoreographySequence fields:**
- `moves` - List of SelectedMove objects (the core data)
- `total_duration` - Total duration of the choreography
- `difficulty_level` - Difficulty level (beginner/intermediate/advanced)
- `audio_path` - Path to the audio file
- `audio_tempo` - Tempo in BPM
- `generation_timestamp` - When the blueprint was created
- `generation_parameters` - Additional parameters used in generation

**SelectedMove fields (each item in moves array):**
- `clip_id` - Unique identifier for this clip instance
- `video_path` - Path to the video clip file
- `start_time` - When this clip starts in the final video
- `duration` - Duration of this clip in the final video
- `transition_type` - Type of transition (cut/crossfade/fade_black)
- `original_duration` - Original duration of the source clip
- `trim_start` - Seconds to trim from start
- `trim_end` - Seconds to trim from end
- `volume_adjustment` - Volume multiplier (0.0-1.0)

**VideoGenerationConfig fields (output_config):**
- `output_path` - Where to save the final video
- `output_format` - Video format (mp4)
- `video_codec` - Video codec (libx264)
- `audio_codec` - Audio codec (aac)
- `video_bitrate` - Video bitrate
- `audio_bitrate` - Audio bitrate
- `frame_rate` - FPS
- `transition_duration` - Duration of transitions
- `fade_duration` - Duration of fades
- `add_audio_overlay` - Whether to add audio overlay
- `normalize_audio` - Whether to normalize audio

### 2. API Blueprint Generator Service

**Location:** `backend/services/blueprint_generator.py`

```python
class BlueprintGenerator:
    """Generates video assembly blueprints from choreography requests."""
    
    def __init__(self, vector_search_service, music_analyzer, gemini_service):
        self.vector_search = vector_search_service
        self.music_analyzer = music_analyzer
        self.gemini = gemini_service
    
    def generate_blueprint(
        self,
        task_id: str,
        song_path: str,
        difficulty: str,
        energy_level: str,
        style: str
    ) -> dict:
        """
        Generate a complete blueprint for video assembly.
        
        Steps:
        1. Analyze audio features
        2. Search for matching moves
        3. Generate choreography sequence
        4. Create blueprint JSON
        """
        pass
```

### 3. In-Memory Vector Search Service

**Location:** `backend/services/vector_search_service.py`

```python
import faiss
import numpy as np

class VectorSearchService:
    """In-memory vector search using FAISS."""
    
    def __init__(self):
        self.faiss_index = None  # FAISS index for fast similarity search
        self.move_metadata = []  # Metadata for each move
        self.embedding_dimension = 512  # Dimension of embeddings
    
    def load_embeddings_from_db(self):
        """
        Load all move embeddings into memory and build FAISS index.
        
        Uses FAISS IndexFlatIP (inner product) for cosine similarity.
        Embeddings are normalized before indexing.
        """
        pass
    
    def build_faiss_index(self, embeddings: np.ndarray):
        """
        Build FAISS index from embeddings.
        
        Args:
            embeddings: numpy array of shape (n_moves, embedding_dim)
        
        Uses IndexFlatIP for exact inner product search.
        Normalizes embeddings for cosine similarity.
        """
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create FAISS index
        self.faiss_index = faiss.IndexFlatIP(self.embedding_dimension)
        self.faiss_index.add(embeddings)
    
    def search_similar_moves(
        self,
        query_embedding: np.ndarray,
        filters: dict,
        top_k: int = 10
    ) -> List[dict]:
        """
        Find similar moves using FAISS similarity search.
        
        Args:
            query_embedding: Query vector (will be normalized)
            filters: Metadata filters (difficulty, energy_level, style)
            top_k: Number of results to return
        
        Returns:
            List of similar moves with scores and metadata
        
        Uses FAISS for efficient similarity search.
        Falls back to numpy if FAISS is not available or fails.
        """
        pass
    
    def filter_by_metadata(self, indices: np.ndarray, filters: dict) -> np.ndarray:
        """
        Filter FAISS results by metadata criteria.
        
        Args:
            indices: Array of move indices from FAISS search
            filters: Dictionary of metadata filters
        
        Returns:
            Filtered array of indices
        """
        pass
    
    def _fallback_numpy_search(
        self,
        query_embedding: np.ndarray,
        filters: dict,
        top_k: int
    ) -> List[dict]:
        """
        Fallback to numpy-based cosine similarity if FAISS fails.
        
        Only used as a backup when FAISS is unavailable.
        """
        pass
```

### 4. Simplified Job Container

**Location:** `job/src/main.py`

```python
class BlueprintVideoAssembler:
    """Assembles videos from blueprints."""
    
    def __init__(self, storage_service, database_service):
        self.storage = storage_service
        self.database = database_service
    
    def process_blueprint(self, blueprint: dict):
        """
        Process a blueprint and generate video.
        
        Steps:
        1. Validate blueprint
        2. Fetch audio and video files
        3. Assemble with FFmpeg
        4. Upload result
        5. Update database
        """
        pass
    
    def validate_blueprint(self, blueprint: dict) -> bool:
        """Validate blueprint schema and required fields."""
        pass
    
    def fetch_media_files(self, blueprint: dict) -> dict:
        """Fetch all required media files from storage."""
        pass
    
    def assemble_video(self, blueprint: dict, media_files: dict) -> str:
        """
        Use FFmpeg to assemble the final video.
        
        Example FFmpeg workflow:
        
        1. Create concat file:
           file 'body_roll_1.mp4'
           file 'body_roll_3.mp4'
           file 'combination_3.mp4'
           ...
        
        2. Concatenate video clips:
           ffmpeg -f concat -safe 0 -i concat.txt -c copy temp_video.mp4
        
        3. Add audio track:
           ffmpeg -i temp_video.mp4 -i song.mp3 \
                  -c:v copy -c:a aac -b:a 192k \
                  -shortest output.mp4
        
        4. Optional: Add transitions (crossfade between clips)
           ffmpeg -i clip1.mp4 -i clip2.mp4 \
                  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=7.5" \
                  output.mp4
        """
        pass
```

### 5. Storage Service (Unchanged Interface)

**Location:** `job/src/services/storage_service.py`

```python
class StorageService:
    """Unified interface for local and GCS storage."""
    
    def __init__(self, use_gcs: bool = False, bucket_name: str = None):
        self.use_gcs = use_gcs
        self.bucket_name = bucket_name
    
    def download_file(self, remote_path: str, local_path: str):
        """Download file from storage."""
        pass
    
    def upload_file(self, local_path: str, remote_path: str):
        """Upload file to storage."""
        pass
    
    def file_exists(self, path: str) -> bool:
        """Check if file exists in storage."""
        pass
```

### 6. Database Service (Simplified)

**Location:** `job/src/services/database.py`

```python
class DatabaseService:
    """Minimal database service for status updates."""
    
    def __init__(self, connection_params: dict):
        self.pool = self._create_pool(connection_params)
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        progress: int = 0,
        message: str = "",
        result: dict = None,
        error: str = None
    ):
        """Update task status in database."""
        pass
```

## Data Models

### Move Embedding (Database)

```python
class MoveEmbedding(models.Model):
    """Store move embeddings in database for vector search."""
    
    move_id = models.CharField(max_length=100, unique=True)
    move_name = models.CharField(max_length=200)
    video_path = models.CharField(max_length=500)
    
    # Embeddings stored as JSON arrays
    pose_embedding = models.JSONField()  # 512D vector
    audio_embedding = models.JSONField()  # 128D vector
    text_embedding = models.JSONField()   # 384D vector
    
    # Metadata for filtering
    difficulty = models.CharField(max_length=20)
    energy_level = models.CharField(max_length=20)
    style = models.CharField(max_length=50)
    duration = models.FloatField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Blueprint (Database)

```python
class Blueprint(models.Model):
    """Store generated blueprints."""
    
    task = models.OneToOneField(ChoreographyTask, on_delete=models.CASCADE)
    blueprint_json = models.JSONField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Error Handling

### API Error Handling

1. **Audio Analysis Failure**
   - Log error with audio file details
   - Return 400 Bad Request with error message
   - Do not create task or blueprint

2. **Vector Search Failure**
   - Log error with search parameters
   - Fall back to random move selection
   - Continue with blueprint generation

3. **Blueprint Generation Failure**
   - Log error with task details
   - Update task status to "failed"
   - Return 500 Internal Server Error

### Job Container Error Handling

1. **Blueprint Validation Failure**
   - Log validation errors
   - Update task status to "failed" with error details
   - Exit with code 1

2. **Media File Not Found**
   - Log missing file path
   - Retry up to 3 times with exponential backoff
   - If still failing, update task status to "failed"
   - Exit with code 1

3. **FFmpeg Failure**
   - Log FFmpeg command and error output
   - Update task status to "failed" with FFmpeg error
   - Exit with code 1

4. **Storage Upload Failure**
   - Log upload error
   - Retry up to 3 times
   - If still failing, update task status to "failed"
   - Exit with code 1

## Testing Strategy

### Unit Tests

#### API Tests
- `test_blueprint_generator.py` - Blueprint generation logic
- `test_vector_search_service.py` - In-memory vector search
- `test_blueprint_validation.py` - Blueprint schema validation

#### Job Container Tests
- `test_blueprint_parser.py` - Blueprint parsing
- `test_video_assembler.py` - Video assembly logic
- `test_storage_service.py` - Storage operations
- `test_database_service.py` - Database updates

### Integration Tests

- `test_blueprint_flow.py` - Complete API → Job flow
- `test_local_storage.py` - Local filesystem operations
- `test_gcs_storage.py` - Google Cloud Storage operations
- `test_error_scenarios.py` - Error handling

### Performance Tests

- `test_blueprint_generation_speed.py` - Blueprint generation under 10s
- `test_video_assembly_speed.py` - Video assembly under 30s
- `test_memory_usage.py` - Job container under 512MB

## Migration Strategy

### Phase 1: API Changes (Backend)

1. Create `VectorSearchService` with in-memory FAISS operations
2. Create `BlueprintGenerator` service
3. Add `MoveEmbedding` model to database
4. Add `Blueprint` model to database
5. Update choreography API endpoint to generate blueprints
6. Add blueprint validation utilities
7. Add FAISS dependency to backend requirements

### Phase 2: Job Container Refactor

1. Create new simplified `main.py`
2. Remove Elasticsearch dependencies
3. Remove audio analysis dependencies
4. Remove ML/AI dependencies
5. Keep only: FFmpeg, psycopg2, GCS client, python-dotenv
6. Implement blueprint-based video assembly
7. Update Dockerfile with minimal dependencies

### Phase 3: Testing & Validation

1. Run unit tests for all new components
2. Run integration tests for complete flow
3. Test with local storage
4. Test with GCS storage
5. Performance testing
6. Load testing

### Phase 4: Deployment

1. Deploy API changes
2. Migrate move embeddings to database
3. Deploy new job container
4. Remove Elasticsearch from infrastructure
5. Update documentation
6. Monitor production metrics

## Deployment Considerations

### Environment Variables

#### API/Backend
- `MOVE_EMBEDDINGS_CACHE_TTL` - How long to cache embeddings in memory (default: 3600s)
- `VECTOR_SEARCH_TOP_K` - Number of similar moves to return (default: 20)
- `BLUEPRINT_VERSION` - Blueprint schema version (default: "1.0")
- `FAISS_USE_GPU` - Whether to use GPU acceleration for FAISS (default: false)
- `FAISS_NPROBE` - Number of clusters to search (for IVF indices, default: 1)

#### Job Container
- `BLUEPRINT_JSON` - The blueprint as a JSON string (required)
- `TASK_ID` - Task identifier (required)
- `USE_GCS` - Whether to use GCS or local storage (default: false)
- `GCS_BUCKET_NAME` - GCS bucket name (required if USE_GCS=true)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Database connection

### Resource Requirements

#### API/Backend
- Memory: 2GB (for in-memory embeddings)
- CPU: 2 cores
- Disk: 10GB

#### Job Container
- Memory: 512MB
- CPU: 1 core
- Disk: 5GB (temporary video files)
- Timeout: 5 minutes

### Monitoring

#### API Metrics
- Blueprint generation time
- Vector search time
- Number of moves found
- Blueprint size

#### Job Metrics
- Video assembly time
- FFmpeg execution time
- Storage download/upload time
- Success/failure rate

## Security Considerations

1. **Blueprint Validation** - Validate all paths to prevent directory traversal
2. **Storage Access** - Use signed URLs for GCS access
3. **Database Access** - Use connection pooling with SSL
4. **Secrets Management** - Use Google Secret Manager for credentials
5. **Input Sanitization** - Sanitize all user inputs in blueprints

## Performance Optimizations

1. **FAISS Index Caching** - Cache FAISS index in memory for 1 hour
2. **FAISS Optimization** - Use IndexFlatIP for exact search, consider IndexIVFFlat for larger datasets
3. **Parallel Downloads** - Download media files in parallel
4. **FFmpeg Optimization** - Use hardware acceleration when available
5. **Connection Pooling** - Reuse database connections
6. **Batch Operations** - Batch database updates when possible
7. **GPU Acceleration** - Optional GPU support for FAISS on larger embedding sets

## Backward Compatibility

This is a breaking change that requires:
1. Database migration for new models
2. API endpoint changes
3. Job container replacement
4. Elasticsearch removal

No backward compatibility with old job container.

## Future Enhancements

1. **Blueprint Caching** - Cache blueprints for identical requests
2. **Move Recommendation** - ML-based move recommendations
3. **Custom Transitions** - Support for custom transition effects
4. **Multi-Song Support** - Support for medleys
5. **Real-time Preview** - Generate preview before full video
