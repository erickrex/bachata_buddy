# Design Document

## Overview

This design implements the "Select Song Template" workflow for the Bachata Buddy REST API. The solution provides endpoints to list, retrieve, and generate choreography from pre-existing songs stored locally (development) or in GCS (production). It also removes the incomplete YouTube URL functionality and fixes the OpenAPI/Swagger UI configuration.

## Architecture

### High-Level Flow

```
User → REST API → Database (Song metadata)
                ↓
                Cloud Run Job → Local/GCS Storage (Audio files)
                ↓
                Video Generation → Result Storage
```

### Storage Strategy

**Development (Local):**
- Songs stored in: `backend/data/songs/`
- Accessed via: relative paths `songs/filename.mp3`
- No cloud dependencies required

**Production (GCS):**
- Songs stored in: `gs://bachata-buddy-bucket/songs/`
- Accessed via: GCS paths `gs://bucket/songs/filename.mp3`
- Automatic detection based on environment

## Components and Interfaces

### 1. Song Model

**Location:** `backend/apps/choreography/models.py`

```python
class Song(models.Model):
    """Pre-existing song template for choreography generation."""
    
    # Primary identification
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200, db_index=True)
    artist = models.CharField(max_length=200, db_index=True)
    
    # Audio metadata
    duration = models.FloatField(help_text="Duration in seconds")
    bpm = models.IntegerField(help_text="Beats per minute", null=True, blank=True)
    genre = models.CharField(max_length=50, null=True, blank=True)
    
    # Storage path (local or GCS)
    audio_path = models.CharField(
        max_length=500,
        help_text="Local path (songs/file.mp3) or GCS path (gs://bucket/songs/file.mp3)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'songs'
        ordering = ['title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['artist']),
            models.Index(fields=['genre']),
        ]
```

### 2. Song Serializers

**Location:** `backend/apps/choreography/serializers.py`

```python
class SongSerializer(serializers.ModelSerializer):
    """Serializer for song list and detail views."""
    
    class Meta:
        model = Song
        fields = ['id', 'title', 'artist', 'duration', 'bpm', 'genre', 'created_at']
        read_only_fields = fields


class SongDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer including audio path."""
    
    class Meta:
        model = Song
        fields = ['id', 'title', 'artist', 'duration', 'bpm', 'genre', 'audio_path', 'created_at', 'updated_at']
        read_only_fields = fields


class SongGenerationSerializer(serializers.Serializer):
    """Serializer for generating choreography from a song template."""
    
    song_id = serializers.IntegerField(required=True)
    difficulty = serializers.ChoiceField(
        choices=['beginner', 'intermediate', 'advanced'],
        default='intermediate'
    )
    energy_level = serializers.ChoiceField(
        choices=['low', 'medium', 'high'],
        required=False,
        allow_blank=True
    )
    style = serializers.ChoiceField(
        choices=['traditional', 'modern', 'romantic', 'sensual'],
        required=False,
        allow_blank=True
    )
    
    def validate_song_id(self, value):
        """Validate that the song exists."""
        if not Song.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Song with ID {value} does not exist")
        return value
```

### 3. API Endpoints

**Location:** `backend/apps/choreography/views.py`

#### GET /api/choreography/songs/
List all available songs with filtering and pagination.

**Query Parameters:**
- `genre`: Filter by genre
- `bpm_min`: Minimum BPM
- `bpm_max`: Maximum BPM
- `search`: Search in title or artist
- `page`: Page number
- `page_size`: Items per page (max 100)

**Response:**
```json
{
  "count": 25,
  "next": "http://localhost:8001/api/choreography/songs/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Bachata Rosa",
      "artist": "Juan Luis Guerra",
      "duration": 245.5,
      "bpm": 120,
      "genre": "bachata",
      "created_at": "2025-11-08T10:00:00Z"
    }
  ]
}
```

#### GET /api/choreography/songs/{id}/
Get detailed information about a specific song.

**Response:**
```json
{
  "id": 1,
  "title": "Bachata Rosa",
  "artist": "Juan Luis Guerra",
  "duration": 245.5,
  "bpm": 120,
  "genre": "bachata",
  "audio_path": "songs/bachata-rosa.mp3",
  "created_at": "2025-11-08T10:00:00Z",
  "updated_at": "2025-11-08T10:00:00Z"
}
```

#### POST /api/choreography/generate-from-song/
Generate choreography from a song template.

**Request:**
```json
{
  "song_id": 1,
  "difficulty": "intermediate",
  "energy_level": "medium",
  "style": "romantic"
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "song": {
    "id": 1,
    "title": "Bachata Rosa",
    "artist": "Juan Luis Guerra"
  },
  "status": "pending",
  "message": "Choreography generation started",
  "poll_url": "/api/choreography/tasks/550e8400-e29b-41d4-a716-446655440000"
}
```

### 4. URL Configuration

**Location:** `backend/apps/choreography/urls.py`

```python
urlpatterns = [
    # Song template endpoints
    path('songs/', list_songs, name='list-songs'),
    path('songs/<int:song_id>/', song_detail, name='song-detail'),
    path('generate-from-song/', generate_from_song, name='generate-from-song'),
    
    # AI workflow (unchanged)
    path('parse-query/', parse_natural_language_query, name='parse-query'),
    path('generate-with-ai/', generate_with_ai, name='generate-with-ai'),
    
    # Task management (unchanged)
    path('tasks/', list_tasks, name='list-tasks'),
    path('tasks/<uuid:task_id>/', task_detail, name='task-detail'),
]
```

**Removed:**
- `path('generate/', generate_choreography, name='generate')` - DELETED

### 5. ChoreographyTask Model Update

**Location:** `backend/apps/choreography/models.py`

Add optional song reference to existing model:

```python
class ChoreographyTask(models.Model):
    # ... existing fields ...
    
    # Optional reference to song template (new field)
    song = models.ForeignKey(
        'Song',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text="Song template used for generation (if applicable)"
    )
```

## Data Models

### Database Schema

```sql
-- New table
CREATE TABLE songs (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    artist VARCHAR(200) NOT NULL,
    duration FLOAT NOT NULL,
    bpm INTEGER,
    genre VARCHAR(50),
    audio_path VARCHAR(500) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_songs_title ON songs(title);
CREATE INDEX idx_songs_artist ON songs(artist);
CREATE INDEX idx_songs_genre ON songs(genre);

-- Update existing table
ALTER TABLE choreography_tasks 
ADD COLUMN song_id INTEGER REFERENCES songs(id) ON DELETE SET NULL;
```

### Sample Data for Local Development

**Location:** `backend/data/songs/` (audio files)
**Location:** `backend/fixtures/songs.json` (metadata)

```json
[
  {
    "model": "choreography.song",
    "pk": 1,
    "fields": {
      "title": "Bachata Rosa",
      "artist": "Juan Luis Guerra",
      "duration": 245.5,
      "bpm": 120,
      "genre": "bachata",
      "audio_path": "songs/bachata-rosa.mp3"
    }
  },
  {
    "model": "choreography.song",
    "pk": 2,
    "fields": {
      "title": "Obsesión",
      "artist": "Aventura",
      "duration": 268.0,
      "bpm": 125,
      "genre": "bachata",
      "audio_path": "songs/obsesion.mp3"
    }
  }
]
```

## Error Handling

### Validation Errors

**Song Not Found (404):**
```json
{
  "detail": "Song with ID 999 does not exist"
}
```

**Invalid Difficulty (400):**
```json
{
  "difficulty": ["\"expert\" is not a valid choice."]
}
```

### Storage Errors

**Audio File Not Found:**
- Log error with full path
- Return 500 with generic message
- Update task status to 'failed'

## Testing Strategy

### Unit Tests

**Location:** `backend/apps/choreography/tests.py`

1. **Model Tests:**
   - Song model creation and validation
   - Song queryset filtering
   - Audio path validation

2. **Serializer Tests:**
   - SongGenerationSerializer validation
   - Song ID existence check
   - Difficulty validation

3. **View Tests:**
   - List songs with pagination
   - Filter songs by genre/BPM
   - Search songs by title/artist
   - Get song detail
   - Generate from song template
   - Authentication requirements

### Integration Tests

**Location:** `backend/test_song_workflow.py`

1. **Complete Workflow:**
   - List songs → Select song → Generate choreography → Poll status
   
2. **Error Scenarios:**
   - Invalid song ID
   - Missing authentication
   - Invalid difficulty

### Local Testing Setup

```bash
# 1. Create sample audio files
mkdir -p backend/data/songs
# Add sample MP3 files

# 2. Load fixtures
docker-compose exec api uv run python manage.py loaddata songs

# 3. Run tests
docker-compose exec api uv run pytest apps/choreography/tests.py -v

# 4. Test API manually
curl http://localhost:8001/api/choreography/songs/
```

## OpenAPI/Swagger Fix

### Problem

Swagger UI shows `localhost:8000` instead of `localhost:8001` due to Docker port mapping.

### Solution

**Location:** `backend/api/settings.py`

Already implemented in previous session:
```python
SPECTACULAR_SERVERS = [
    {'url': 'http://localhost:8001', 'description': 'Local development server'},
    {'url': 'http://127.0.0.1:8001', 'description': 'Local development server (127.0.0.1)'},
]

SPECTACULAR_SETTINGS = {
    # ... other settings ...
    'SERVERS': SPECTACULAR_SERVERS,
}
```

**Additional Fix Needed:**
- Verify CORS allows `localhost:8001` origin
- Test Swagger UI can make requests successfully
- Update schema generation if needed

## Cleanup Tasks

### Files to Delete

1. **View Function:**
   - Remove `generate_choreography()` from `backend/apps/choreography/views.py`

2. **Serializer:**
   - Remove `ChoreographyGenerationSerializer` from `backend/apps/choreography/serializers.py`

3. **URL Pattern:**
   - Remove `path('generate/', ...)` from `backend/apps/choreography/urls.py`

4. **Tests:**
   - Remove tests for `generate_choreography` endpoint
   - Update integration tests to use new workflow

5. **Documentation:**
   - Remove YouTube URL examples from README
   - Update API documentation

### Dependencies to Check

**Location:** `backend/pyproject.toml`

Review and remove if unused:
- No YouTube-specific dependencies found (yt-dlp, pytube, etc.)
- Keep all existing dependencies (they're used by other features)

## Migration Plan

### Phase 1: Add Song Model
1. Create Song model
2. Create migration
3. Run migration locally

### Phase 2: Add Song Endpoints
1. Create serializers
2. Create view functions
3. Add URL patterns
4. Add OpenAPI documentation

### Phase 3: Remove YouTube Endpoint
1. Delete `generate_choreography` view
2. Delete `ChoreographyGenerationSerializer`
3. Remove URL pattern
4. Update tests

### Phase 4: Testing
1. Load sample song data
2. Run unit tests
3. Run integration tests
4. Manual API testing

### Phase 5: Documentation
1. Update README
2. Verify Swagger UI
3. Add usage examples

## Deployment Considerations

### Local → Production Transition

**Environment Detection:**
```python
# In settings.py or service layer
USE_GCS = os.environ.get('USE_GCS_STORAGE', 'False') == 'True'

# In storage logic
if USE_GCS:
    audio_path = f"gs://{bucket}/{path}"
else:
    audio_path = f"songs/{filename}"
```

**Migration Script:**
```bash
# Upload local songs to GCS
gsutil -m cp -r backend/data/songs/* gs://bachata-buddy-bucket/songs/

# Update database paths
python manage.py migrate_song_paths_to_gcs
```

This design provides a complete, testable solution that works locally first and scales to production with minimal changes.
