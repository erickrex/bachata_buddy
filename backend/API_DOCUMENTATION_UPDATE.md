# API Documentation Update

## Summary

Complete API documentation for the blueprint-based choreography generation system. This document covers both user paths (Select Song and Describe Choreo), blueprint generation endpoints, request/response formats, and error codes.

**Last Updated:** November 9, 2025  
**Blueprint Schema Version:** 1.0  
**Status:** ✅ COMPLETE

---

## Blueprint-Based Architecture Overview

The system uses a **blueprint-based architecture** where all intelligence (audio analysis, move selection, choreography sequencing) happens in the API/backend, and the job container simply assembles videos according to the blueprint.

### Two User Paths

1. **Path 1: "Select Song"** - User selects a pre-existing song from the database
   - Endpoint: `POST /api/choreography/generate-from-song`
   - User provides: song_id, difficulty, energy_level, style
   
2. **Path 2: "Describe Choreo"** - User describes choreography in natural language
   - Endpoint: `POST /api/choreography/generate-with-ai`
   - User provides: natural language query
   - AI parses query to extract parameters

### Blueprint Generation Flow

```
User Request → API Endpoint → Blueprint Generator
                                    ↓
                            Audio Analysis (Librosa)
                                    ↓
                            Vector Search (FAISS)
                                    ↓
                            AI Sequencing (Gemini)
                                    ↓
                            Blueprint JSON
                                    ↓
                            Database Storage
                                    ↓
                            Job Submission
                                    ↓
                            Video Assembly (FFmpeg)
```

---

## Blueprint Generation Endpoints

### POST /api/choreography/generate-from-song

Generate choreography from a pre-existing song in the database.

**Authentication:** Required (JWT Bearer token)

**Request Body:**

```json
{
  "song_id": 1,
  "difficulty": "intermediate",
  "energy_level": "high",
  "style": "modern"
}
```

**Request Fields:**

| Field | Type | Required | Description | Valid Values |
|-------|------|----------|-------------|--------------|
| `song_id` | integer | Yes | ID of the song from the database | Any valid song ID |
| `difficulty` | string | Yes | Difficulty level of choreography | `beginner`, `intermediate`, `advanced` |
| `energy_level` | string | No | Energy level preference | `low`, `medium`, `high` (default: `medium`) |
| `style` | string | No | Style preference | `romantic`, `energetic`, `sensual`, `playful`, `modern` (default: `modern`) |

**Success Response (202 Accepted):**

```json
{
  "task_id": "abc-123-def-456",
  "song": {
    "id": 1,
    "title": "Bachata Rosa",
    "artist": "Juan Luis Guerra"
  },
  "status": "started",
  "message": "Choreography generation started",
  "poll_url": "/api/choreography/tasks/abc-123-def-456"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique identifier for the task (UUID) |
| `song` | object | Song information |
| `song.id` | integer | Song database ID |
| `song.title` | string | Song title |
| `song.artist` | string | Song artist |
| `status` | string | Current task status (`started`) |
| `message` | string | Human-readable status message |
| `poll_url` | string | URL to poll for task status updates |

**Error Responses:**

| Status Code | Description | Example Response |
|-------------|-------------|------------------|
| 400 Bad Request | Invalid request parameters | `{"song_id": ["This field is required."]}` |
| 400 Bad Request | Song not found | `{"song_id": ["Song with id 999 does not exist."]}` |
| 400 Bad Request | Invalid difficulty | `{"difficulty": ["Invalid difficulty. Must be one of: beginner, intermediate, advanced"]}` |
| 401 Unauthorized | Missing or invalid authentication | `{"detail": "Authentication credentials were not provided."}` |
| 500 Internal Server Error | Blueprint generation failed | `{"error": "Failed to generate blueprint"}` |
| 500 Internal Server Error | Job submission failed | `{"error": "Failed to create job execution"}` |

**Example cURL Request:**

```bash
curl -X POST http://localhost:8000/api/choreography/generate-from-song \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "song_id": 1,
    "difficulty": "intermediate",
    "energy_level": "high",
    "style": "modern"
  }'
```

**Blueprint Generation Process:**

1. **Validate Request** - Check song exists, validate parameters
2. **Create Task** - Create ChoreographyTask record with status="pending"
3. **Analyze Audio** - Extract tempo, beats, musical sections using Librosa
4. **Load Embeddings** - Load move embeddings from database into memory
5. **Vector Search** - Find matching moves using FAISS similarity search
6. **AI Sequencing** - Generate choreography sequence using Gemini AI
7. **Create Blueprint** - Generate complete blueprint JSON
8. **Store Blueprint** - Save blueprint to database
9. **Submit Job** - Create Cloud Run Job execution with blueprint
10. **Return Response** - Return task_id for polling

---

### POST /api/choreography/generate-with-ai

Generate choreography from a natural language description.

**Authentication:** Required (JWT Bearer token)

**Request Body:**

```json
{
  "query": "Create a romantic bachata for beginners with smooth transitions"
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Natural language description of desired choreography |

**Query Parsing:**

The AI (Gemini) parses the query to extract:
- **Difficulty level** - beginner, intermediate, advanced
- **Energy level** - low, medium, high
- **Style** - romantic, energetic, sensual, playful, modern
- **Song preferences** - tempo, mood, artist (if specified)
- **Special requirements** - transitions, specific moves, duration

**Example Queries:**

- `"Create a romantic bachata for beginners with smooth transitions"`
- `"I want an energetic intermediate choreography with lots of turns"`
- `"Make me an advanced sensual routine to a slow song"`
- `"Beginner-friendly playful dance with simple steps"`

**Success Response (202 Accepted):**

```json
{
  "task_id": "xyz-789-uvw-012",
  "parsed_parameters": {
    "difficulty": "beginner",
    "energy_level": "low",
    "style": "romantic",
    "special_requirements": ["smooth transitions"]
  },
  "song": {
    "id": 5,
    "title": "Propuesta Indecente",
    "artist": "Romeo Santos"
  },
  "status": "started",
  "message": "Choreography generation started",
  "poll_url": "/api/choreography/tasks/xyz-789-uvw-012"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique identifier for the task (UUID) |
| `parsed_parameters` | object | Parameters extracted from the query |
| `parsed_parameters.difficulty` | string | Extracted difficulty level |
| `parsed_parameters.energy_level` | string | Extracted energy level |
| `parsed_parameters.style` | string | Extracted style |
| `parsed_parameters.special_requirements` | array | Special requirements from query |
| `song` | object | Selected song information |
| `song.id` | integer | Song database ID |
| `song.title` | string | Song title |
| `song.artist` | string | Song artist |
| `status` | string | Current task status (`started`) |
| `message` | string | Human-readable status message |
| `poll_url` | string | URL to poll for task status updates |

**Error Responses:**

| Status Code | Description | Example Response |
|-------------|-------------|------------------|
| 400 Bad Request | Missing query | `{"query": ["This field is required."]}` |
| 400 Bad Request | Query too short | `{"query": ["Query must be at least 10 characters."]}` |
| 400 Bad Request | Query parsing failed | `{"error": "Could not parse query. Please be more specific."}` |
| 401 Unauthorized | Missing or invalid authentication | `{"detail": "Authentication credentials were not provided."}` |
| 500 Internal Server Error | Blueprint generation failed | `{"error": "Failed to generate blueprint"}` |
| 500 Internal Server Error | Job submission failed | `{"error": "Failed to create job execution"}` |

**Example cURL Request:**

```bash
curl -X POST http://localhost:8000/api/choreography/generate-with-ai \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a romantic bachata for beginners with smooth transitions"
  }'
```

**Blueprint Generation Process:**

1. **Validate Request** - Check query is present and valid
2. **Parse Query** - Use Gemini AI to extract parameters
3. **Select Song** - Choose appropriate song based on parsed parameters
4. **Create Task** - Create ChoreographyTask record with status="pending"
5. **Analyze Audio** - Extract tempo, beats, musical sections using Librosa
6. **Load Embeddings** - Load move embeddings from database into memory
7. **Vector Search** - Find matching moves using FAISS similarity search
8. **AI Sequencing** - Generate choreography sequence using Gemini AI
9. **Create Blueprint** - Generate complete blueprint JSON
10. **Store Blueprint** - Save blueprint to database
11. **Submit Job** - Create Cloud Run Job execution with blueprint
12. **Return Response** - Return task_id and parsed parameters

---

## Task Status Endpoint

### GET /api/choreography/tasks/{task_id}

Poll for the status and progress of a choreography generation task.

**Authentication:** Required (JWT Bearer token)

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | string | Task identifier (UUID) returned from generation endpoint |

**Success Response (200 OK) - Task Pending:**

```json
{
  "task_id": "abc-123-def-456",
  "status": "pending",
  "progress": 0,
  "stage": "generating_blueprint",
  "message": "Generating choreography blueprint...",
  "created_at": "2025-11-09T12:34:56Z",
  "updated_at": "2025-11-09T12:34:56Z"
}
```

**Success Response (200 OK) - Task Running:**

```json
{
  "task_id": "abc-123-def-456",
  "status": "running",
  "progress": 45,
  "stage": "video_assembly",
  "message": "Assembling video clips...",
  "created_at": "2025-11-09T12:34:56Z",
  "updated_at": "2025-11-09T12:35:23Z"
}
```

**Success Response (200 OK) - Task Completed:**

```json
{
  "task_id": "abc-123-def-456",
  "status": "completed",
  "progress": 100,
  "stage": "completed",
  "message": "Choreography generated successfully",
  "result": {
    "video_url": "/media/output/choreography_abc-123-def-456.mp4",
    "duration": 227.18,
    "file_size": 36992903,
    "num_moves": 29,
    "difficulty": "intermediate"
  },
  "created_at": "2025-11-09T12:34:56Z",
  "updated_at": "2025-11-09T12:36:12Z",
  "completed_at": "2025-11-09T12:36:12Z"
}
```

**Success Response (200 OK) - Task Failed:**

```json
{
  "task_id": "abc-123-def-456",
  "status": "failed",
  "progress": 30,
  "stage": "video_assembly",
  "message": "Video assembly failed",
  "error": "FFmpeg error: Invalid video codec",
  "created_at": "2025-11-09T12:34:56Z",
  "updated_at": "2025-11-09T12:35:45Z"
}
```

**Task Status Values:**

| Status | Description |
|--------|-------------|
| `pending` | Task created, waiting to start |
| `started` | Job submitted to Cloud Run |
| `running` | Job is actively processing |
| `completed` | Video generated successfully |
| `failed` | Task failed with error |

**Task Stage Values:**

| Stage | Description |
|-------|-------------|
| `generating_blueprint` | Creating blueprint from audio analysis and AI |
| `submitting_job` | Submitting job to Cloud Run |
| `video_assembly` | Assembling video clips with FFmpeg |
| `uploading_result` | Uploading final video to storage |
| `completed` | All processing complete |

**Error Responses:**

| Status Code | Description | Example Response |
|-------------|-------------|------------------|
| 404 Not Found | Task not found | `{"detail": "Task not found"}` |
| 401 Unauthorized | Missing or invalid authentication | `{"detail": "Authentication credentials were not provided."}` |
| 403 Forbidden | Task belongs to another user | `{"detail": "You do not have permission to access this task"}` |

**Example cURL Request:**

```bash
curl -X GET http://localhost:8000/api/choreography/tasks/abc-123-def-456 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Polling Recommendations:**

- Poll every 2-3 seconds while status is `pending` or `running`
- Stop polling when status is `completed` or `failed`
- Implement exponential backoff if polling for extended periods
- Maximum recommended polling duration: 5 minutes

---

## Blueprint Schema

Blueprints are JSON documents that contain complete instructions for video assembly. They are generated by the API and passed to the job container.

**For complete blueprint schema documentation, see:** [Blueprint Schema Documentation](../docs/BLUEPRINT_SCHEMA.md)

**Minimal Blueprint Example:**

```json
{
  "task_id": "abc-123-def-456",
  "audio_path": "data/songs/Amor.mp3",
  "moves": [
    {
      "clip_id": "move_1",
      "video_path": "data/Bachata_steps/body_roll/body_roll_1.mp4",
      "start_time": 0.0,
      "duration": 8.0
    },
    {
      "clip_id": "move_2",
      "video_path": "data/Bachata_steps/cross_body_lead/cross_body_lead_1.mp4",
      "start_time": 8.0,
      "duration": 8.0
    }
  ],
  "total_duration": 16.0,
  "output_config": {
    "output_path": "data/output/choreography_abc-123-def-456.mp4"
  }
}
```

**Key Blueprint Fields:**

- `task_id` - Links to ChoreographyTask record
- `audio_path` - Path to song audio file
- `moves` - Array of video clips with timing and transitions
- `total_duration` - Expected video duration
- `output_config` - Video encoding settings

---

## Error Codes Reference

### HTTP Status Codes

| Code | Name | Description |
|------|------|-------------|
| 200 | OK | Request successful |
| 202 | Accepted | Task created and processing started |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required or invalid |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server-side error occurred |

### Application Error Codes

#### Blueprint Generation Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Failed to generate blueprint` | Audio analysis, vector search, or AI sequencing failed | Check logs for specific error. Verify song file exists and is valid. |
| `Failed to create job execution` | Job submission to Cloud Run failed | Check Cloud Run configuration and permissions. |
| `Song with id X does not exist` | Invalid song_id provided | Use `/api/choreography/songs/` to get valid song IDs. |
| `Invalid difficulty` | Difficulty not in allowed values | Use: `beginner`, `intermediate`, or `advanced` |
| `Query must be at least 10 characters` | Query too short | Provide more detailed description. |
| `Could not parse query` | AI couldn't extract parameters from query | Be more specific about difficulty, style, and preferences. |

#### Task Status Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Task not found` | Invalid task_id or task doesn't exist | Verify task_id from generation response. |
| `You do not have permission to access this task` | Task belongs to another user | Only access your own tasks. |

#### Video Assembly Errors (in task.error field)

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Blueprint validation failed` | Invalid blueprint schema | Contact support - this is a server-side issue. |
| `Video file not found` | Missing video clip file | Contact support - missing training data. |
| `FFmpeg error: ...` | Video encoding failed | Check FFmpeg logs. May be invalid video format. |
| `Storage upload failed` | Failed to upload result video | Check storage permissions and connectivity. |

---

## Complete Endpoint Reference

### Choreography Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/choreography/songs/` | List available songs with filtering | Yes |
| GET | `/api/choreography/songs/{id}/` | Get song details | Yes |
| POST | `/api/choreography/generate-from-song` | Generate choreography from song (Path 1) | Yes |
| POST | `/api/choreography/generate-with-ai` | Generate choreography from description (Path 2) | Yes |
| GET | `/api/choreography/tasks/{task_id}/` | Get task status and progress | Yes |
| GET | `/api/choreography/tasks/` | List user's tasks | Yes |
| POST | `/api/choreography/parse-query/` | Parse natural language query (testing) | Yes |

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register/` | Register new user | No |
| POST | `/api/auth/login/` | Login and get JWT tokens | No |
| GET | `/api/auth/profile/` | Get user profile | Yes |
| PUT | `/api/auth/profile/` | Update user profile | Yes |
| GET | `/api/auth/preferences/` | Get user preferences | Yes |
| PUT | `/api/auth/preferences/` | Update user preferences | Yes |

### Collections Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/collections/` | List user's saved choreographies | Yes |
| GET | `/api/collections/{id}/` | Get collection details | Yes |
| POST | `/api/collections/save/` | Save choreography to collection | Yes |
| DELETE | `/api/collections/{id}/` | Delete from collection | Yes |
| GET | `/api/collections/stats/` | Get collection statistics | Yes |
| POST | `/api/collections/delete-all/` | Delete all collections | Yes |
| POST | `/api/collections/cleanup/` | Cleanup old collections | Yes |

### Instructor Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/instructors/class-plans/` | List class plans | Yes |
| POST | `/api/instructors/class-plans/` | Create class plan | Yes |
| GET | `/api/instructors/class-plans/{id}/` | Get class plan details | Yes |
| PUT | `/api/instructors/class-plans/{id}/` | Update class plan | Yes |
| DELETE | `/api/instructors/class-plans/{id}/` | Delete class plan | Yes |
| POST | `/api/instructors/class-plans/{id}/add-sequence/` | Add sequence to plan | Yes |
| GET | `/api/instructors/class-plans/{id}/summary/` | Get plan summary | Yes |
| GET | `/api/instructors/stats/` | Get instructor statistics | Yes |

---

## API Documentation Access

### Interactive Documentation

**Swagger UI:** `http://localhost:8000/api/docs/`

Features:
- Try out endpoints directly from browser
- See request/response examples
- View authentication requirements
- Test with your JWT token

### OpenAPI Schema

**Schema Endpoint:** `http://localhost:8000/api/schema/`  
**Schema File:** `backend/schema.yml`

Use with:
- Postman (import OpenAPI schema)
- Insomnia (import OpenAPI schema)
- Code generators (openapi-generator, swagger-codegen)
- API testing tools

---

## Frontend Developer Guide

### Getting Started

1. **View API Documentation**
   ```bash
   # Start backend
   cd backend
   uv run python manage.py runserver
   
   # Open browser
   open http://localhost:8000/api/docs/
   ```

2. **Download OpenAPI Schema**
   ```bash
   curl http://localhost:8000/api/schema/ > openapi.json
   ```

3. **Generate Client Code** (optional)
   ```bash
   # TypeScript/Axios client
   npx @openapitools/openapi-generator-cli generate \
     -i openapi.json \
     -g typescript-axios \
     -o frontend/src/api
   ```

### Authentication

All endpoints except `/api/auth/register/` and `/api/auth/login/` require JWT authentication:

```javascript
// Login
const response = await fetch('http://localhost:8000/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'user', password: 'pass' })
});
const { access, refresh } = await response.json();

// Use token in subsequent requests
const data = await fetch('http://localhost:8000/api/collections/', {
  headers: { 'Authorization': `Bearer ${access}` }
});
```

### Common Workflows

#### 1. Generate Choreography from Song (Path 1)

```javascript
// Step 1: List available songs
const songsResponse = await fetch('http://localhost:8000/api/choreography/songs/', {
  headers: { 'Authorization': `Bearer ${accessToken}` }
});
const songs = await songsResponse.json();

// Step 2: Start generation with selected song
const generateResponse = await fetch('http://localhost:8000/api/choreography/generate-from-song', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    song_id: 1,
    difficulty: 'intermediate',
    energy_level: 'high',
    style: 'modern'
  })
});
const { task_id, poll_url } = await generateResponse.json();

// Step 3: Poll for status
const pollStatus = async () => {
  const statusResponse = await fetch(`http://localhost:8000${poll_url}`, {
    headers: { 'Authorization': `Bearer ${accessToken}` }
  });
  const status = await statusResponse.json();
  
  if (status.status === 'completed') {
    console.log('Video ready:', status.result.video_url);
    return status;
  } else if (status.status === 'failed') {
    console.error('Generation failed:', status.error);
    return status;
  } else {
    // Still processing, poll again in 2 seconds
    setTimeout(pollStatus, 2000);
  }
};
pollStatus();

// Step 4: Save to collection (optional)
await fetch('http://localhost:8000/api/collections/save/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    task_id: task_id,
    title: 'My Intermediate Bachata'
  })
});
```

#### 2. Generate Choreography from Description (Path 2)

```javascript
// Step 1: Start generation with natural language query
const generateResponse = await fetch('http://localhost:8000/api/choreography/generate-with-ai', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'Create a romantic bachata for beginners with smooth transitions'
  })
});
const { task_id, parsed_parameters, song, poll_url } = await generateResponse.json();

console.log('AI parsed:', parsed_parameters);
console.log('Selected song:', song);

// Step 2: Poll for status (same as Path 1)
const pollStatus = async () => {
  const statusResponse = await fetch(`http://localhost:8000${poll_url}`, {
    headers: { 'Authorization': `Bearer ${accessToken}` }
  });
  const status = await statusResponse.json();
  
  if (status.status === 'completed') {
    console.log('Video ready:', status.result.video_url);
    return status;
  } else if (status.status === 'failed') {
    console.error('Generation failed:', status.error);
    return status;
  } else {
    setTimeout(pollStatus, 2000);
  }
};
pollStatus();
```

#### 3. Manage Collections

```javascript
// List collections with filtering
const collectionsResponse = await fetch(
  'http://localhost:8000/api/collections/?difficulty=intermediate&search=romantic',
  { headers: { 'Authorization': `Bearer ${accessToken}` } }
);
const collections = await collectionsResponse.json();

// Get statistics
const statsResponse = await fetch('http://localhost:8000/api/collections/stats/', {
  headers: { 'Authorization': `Bearer ${accessToken}` }
});
const stats = await statsResponse.json();
// Returns: { total_count, total_duration, by_difficulty, recent_count }

// Delete all collections
await fetch('http://localhost:8000/api/collections/delete-all/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ confirmation: true })
});
```

#### 4. Instructor Workflow

```javascript
// Create class plan
const planResponse = await fetch('http://localhost:8000/api/instructors/class-plans/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'Beginner Workshop',
    difficulty_level: 'beginner',
    description: 'Introduction to bachata basics'
  })
});
const plan = await planResponse.json();

// Add choreography sequence to plan
await fetch(`http://localhost:8000/api/instructors/class-plans/${plan.id}/add-sequence/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    choreography_id: task_id,
    order: 1,
    notes: 'Start with this sequence'
  })
});

// Get plan summary
const summaryResponse = await fetch(
  `http://localhost:8000/api/instructors/class-plans/${plan.id}/summary/`,
  { headers: { 'Authorization': `Bearer ${accessToken}` } }
);
const summary = await summaryResponse.json();
```

### React Example Component

```jsx
import React, { useState } from 'react';

function ChoreographyGenerator() {
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);

  const generateFromSong = async (songId, difficulty) => {
    const response = await fetch('http://localhost:8000/api/choreography/generate-from-song', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        song_id: songId,
        difficulty: difficulty,
        energy_level: 'high',
        style: 'modern'
      })
    });
    
    const data = await response.json();
    setTaskId(data.task_id);
    pollStatus(data.task_id);
  };

  const pollStatus = async (id) => {
    const response = await fetch(`http://localhost:8000/api/choreography/tasks/${id}/`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` }
    });
    
    const data = await response.json();
    setStatus(data);
    
    if (data.status === 'completed') {
      setVideoUrl(data.result.video_url);
    } else if (data.status !== 'failed') {
      setTimeout(() => pollStatus(id), 2000);
    }
  };

  return (
    <div>
      <button onClick={() => generateFromSong(1, 'intermediate')}>
        Generate Choreography
      </button>
      
      {status && (
        <div>
          <p>Status: {status.status}</p>
          <p>Progress: {status.progress}%</p>
          <p>Stage: {status.stage}</p>
          <p>Message: {status.message}</p>
        </div>
      )}
      
      {videoUrl && (
        <video src={`http://localhost:8000${videoUrl}`} controls />
      )}
    </div>
  );
}
```

---

## Performance Considerations

### Blueprint Generation

- **Expected time:** < 10 seconds for typical 3-minute song
- **Factors affecting speed:**
  - Audio analysis (Librosa): ~2-3 seconds
  - Vector search (FAISS): ~1-2 seconds
  - AI sequencing (Gemini): ~3-5 seconds
  - Blueprint creation: < 1 second

### Video Assembly

- **Expected time:** < 30 seconds for 3-minute video
- **Factors affecting speed:**
  - Number of clips: More clips = longer assembly
  - Transition types: Crossfades slower than cuts
  - Storage location: GCS slower than local
  - Video encoding settings: Higher quality = longer time

### Polling Recommendations

- Poll every 2-3 seconds during processing
- Use exponential backoff for long-running tasks
- Stop polling after 5 minutes (timeout)
- Show progress bar based on `progress` field

---

## Deployment Considerations

### Production Configuration

When deploying to production:

1. **Update Base URL** in OpenAPI schema
   ```python
   # settings.py
   SPECTACULAR_SETTINGS = {
       'SERVERS': [
           {'url': 'https://api.bachatabuddy.com', 'description': 'Production'},
           {'url': 'http://localhost:8000', 'description': 'Development'},
       ]
   }
   ```

2. **Enable CORS** for frontend domain
   ```python
   CORS_ALLOWED_ORIGINS = [
       'https://bachatabuddy.com',
       'http://localhost:3000',  # Development
   ]
   ```

3. **Configure Storage**
   - Use Google Cloud Storage for production
   - Serve videos via CDN for better performance
   - Set appropriate CORS headers on storage bucket

4. **Secure Swagger UI** (optional)
   - Add authentication to `/api/docs/`
   - Or disable in production for security

5. **Rate Limiting**
   - Implement rate limiting on generation endpoints
   - Recommended: 10 requests per hour per user
   - Prevents abuse and manages costs

---

## Troubleshooting

### Common Issues

#### 1. Blueprint Generation Fails

**Symptom:** `500 Internal Server Error` with message "Failed to generate blueprint"

**Possible Causes:**
- Audio file not found or corrupted
- Vector search service not initialized
- Gemini AI service unavailable
- Insufficient move embeddings in database

**Solutions:**
- Check logs for specific error
- Verify song file exists and is valid
- Ensure move embeddings are loaded
- Check Gemini API key and quota

#### 2. Job Submission Fails

**Symptom:** `500 Internal Server Error` with message "Failed to create job execution"

**Possible Causes:**
- Cloud Run Jobs not configured
- Insufficient permissions
- Invalid blueprint JSON
- Job container image not available

**Solutions:**
- Verify Cloud Run Jobs configuration
- Check service account permissions
- Validate blueprint schema
- Ensure job container is deployed

#### 3. Task Stuck in "Running" Status

**Symptom:** Task status remains "running" for > 5 minutes

**Possible Causes:**
- Job container crashed
- FFmpeg error not caught
- Storage upload failed
- Database connection lost

**Solutions:**
- Check Cloud Run Jobs logs
- Verify FFmpeg is working
- Check storage permissions
- Restart job if needed

#### 4. Video Not Playing

**Symptom:** Video URL returned but video won't play

**Possible Causes:**
- CORS headers not set
- Video file corrupted
- Unsupported codec
- Storage permissions issue

**Solutions:**
- Check CORS configuration
- Verify video file integrity
- Use standard codecs (H.264/AAC)
- Check storage bucket permissions

---

## Related Documentation

- [Blueprint Schema Documentation](../docs/BLUEPRINT_SCHEMA.md) - Complete blueprint schema reference
- [Job Container Documentation](../job/README.md) - Job container implementation details
- [Backend README](README.md) - Backend setup and configuration
- [Requirements Document](../.kiro/specs/blueprint-job-refactor/requirements.md) - System requirements
- [Design Document](../.kiro/specs/blueprint-job-refactor/design.md) - Architecture design

---

## Conclusion

✅ **API Documentation Complete**

The blueprint-based choreography generation API is fully documented:

1. ✅ Blueprint generation endpoints documented (both paths)
2. ✅ Request/response formats specified
3. ✅ Error codes and troubleshooting guide provided
4. ✅ Frontend developer guide with examples
5. ✅ Performance considerations documented
6. ✅ Deployment guidelines provided

The API is ready for frontend integration and production deployment.

---

**Document Version:** 2.0  
**Last Updated:** November 9, 2025  
**Blueprint Schema Version:** 1.0  
**Status:** ✅ COMPLETE
