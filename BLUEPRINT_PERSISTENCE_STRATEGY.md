# Blueprint Persistence Strategy

## Overview

Blueprints are **PERMANENTLY SAVED** in the PostgreSQL database and are **NOT LOST** after being sent to the job container. This document explains the complete blueprint lifecycle in both development and production.

---

## Blueprint Lifecycle

### 1. Generation (Backend API)
```
User Request → API Endpoint → Blueprint Generator → PostgreSQL Database
```

**Location:** `backend/apps/choreography/views.py`

```python
# Generate blueprint
blueprint = blueprint_gen.generate_blueprint(
    task_id=task_id,
    song_path=song.audio_path,
    difficulty=difficulty,
    energy_level=energy_level,
    style=style,
    user_id=request.user.id
)

# Store blueprint in database (PERMANENT STORAGE)
from .models import Blueprint
Blueprint.objects.create(
    task=task,
    blueprint_json=blueprint
)
```

### 2. Transmission (To Job Container)
```
PostgreSQL Database → API → Cloud Run Job (Environment Variable)
```

**Location:** `backend/apps/choreography/views.py`

```python
# Pass blueprint to job container via environment variable
import json
execution_name = jobs_service.create_job_execution(
    task_id=task_id,
    user_id=request.user.id,
    parameters={'blueprint_json': json.dumps(blueprint)}
)
```

### 3. Persistence (After Job Completion)
```
PostgreSQL Database (PERMANENT) ← Blueprint remains stored
```

**The blueprint stays in the database forever** (or until explicitly deleted).

---

## Database Schema

### Table: `blueprints`

```sql
CREATE TABLE blueprints (
    task_id VARCHAR(36) PRIMARY KEY,  -- Foreign key to choreography_tasks
    blueprint_json JSONB NOT NULL,     -- Complete blueprint specification
    created_at TIMESTAMP NOT NULL,     -- When blueprint was created
    updated_at TIMESTAMP NOT NULL,     -- Last update time
    FOREIGN KEY (task_id) REFERENCES choreography_tasks(task_id) ON DELETE CASCADE
);
```

### Blueprint JSON Structure

```json
{
  "task_id": "uuid",
  "song": {
    "id": 7,
    "title": "Este_secreto",
    "artist": "Melvin War",
    "audio_path": "gs://bucket/songs/este_secreto.mp3",
    "bpm": 134,
    "duration": 265.3
  },
  "moves": [
    {
      "move_id": "move_001",
      "move_name": "Basic Step",
      "video_path": "gs://bucket/moves/basic_step.mp4",
      "start_time": 0.0,
      "end_time": 5.2,
      "duration": 5.2,
      "difficulty": "advanced",
      "energy_level": "high",
      "style": "modern"
    }
    // ... more moves
  ],
  "generation_parameters": {
    "difficulty_level": "advanced",
    "energy_level": "high",
    "style": "modern",
    "ai_mode": false,
    "user_id": 47
  },
  "total_duration": 263.3,
  "output_config": {
    "video_format": "mp4",
    "resolution": "1280x720",
    "fps": 30,
    "video_codec": "libx264",
    "audio_codec": "aac"
  }
}
```

---

## Production Architecture

### Development (Local)
```
┌─────────────────────────────────────────────────────────────┐
│                     LOCAL DEVELOPMENT                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. API generates blueprint                                  │
│     └─> Saves to PostgreSQL (localhost:5432)               │
│                                                              │
│  2. API passes blueprint to job container                    │
│     └─> Via docker-compose environment variable             │
│                                                              │
│  3. Job container assembles video                            │
│     └─> Reads blueprint from environment variable           │
│     └─> Saves video to data/choreographies/                 │
│                                                              │
│  4. Blueprint remains in PostgreSQL                          │
│     └─> Can be retrieved anytime via API                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Production (Google Cloud)
```
┌─────────────────────────────────────────────────────────────┐
│                    GOOGLE CLOUD PRODUCTION                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Cloud Run API generates blueprint                        │
│     └─> Saves to Cloud SQL PostgreSQL                       │
│     └─> Connection: Unix socket /cloudsql/...               │
│                                                              │
│  2. Cloud Run API triggers Cloud Run Job                     │
│     └─> Passes blueprint via environment variable           │
│     └─> Job execution created with blueprint JSON           │
│                                                              │
│  3. Cloud Run Job assembles video                            │
│     └─> Reads blueprint from environment variable           │
│     └─> Connects to Cloud SQL for status updates            │
│     └─> Saves video to Google Cloud Storage                 │
│                                                              │
│  4. Blueprint remains in Cloud SQL                           │
│     └─> Permanent storage                                   │
│     └─> Accessible via Cloud Run API                        │
│     └─> Backed up automatically by Cloud SQL                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Why Blueprints Are Saved in Database

### 1. **Audit Trail**
- Track what was generated for each task
- Debug issues by examining the exact blueprint used
- Reproduce videos if needed

### 2. **Analytics**
- Analyze which moves are most popular
- Track difficulty distribution
- Monitor generation patterns

### 3. **Regeneration**
- Regenerate videos without re-running AI/analysis
- Modify blueprints and regenerate
- A/B testing different video assembly parameters

### 4. **User History**
- Users can see what choreographies they've generated
- Display move sequences in UI
- Show generation parameters

### 5. **Debugging**
- When videos fail, examine the blueprint
- Verify move selection logic
- Check timing calculations

---

## Blueprint Retrieval

### Via API Endpoint (Future Feature)
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_blueprint(request, task_id):
    """Retrieve blueprint for a task"""
    task = get_object_or_404(ChoreographyTask, task_id=task_id, user=request.user)
    
    try:
        blueprint = task.blueprint
        return Response({
            'task_id': task_id,
            'blueprint': blueprint.blueprint_json,
            'created_at': blueprint.created_at
        })
    except Blueprint.DoesNotExist:
        return Response(
            {'error': 'Blueprint not found'},
            status=status.HTTP_404_NOT_FOUND
        )
```

### Via Database Query
```sql
-- Get blueprint for specific task
SELECT blueprint_json 
FROM blueprints 
WHERE task_id = '63ec74aa-c4a6-4afd-b4ac-c419151f8978';

-- Get all blueprints for a user
SELECT b.task_id, b.blueprint_json, b.created_at
FROM blueprints b
JOIN choreography_tasks t ON b.task_id = t.task_id
WHERE t.user_id = 47
ORDER BY b.created_at DESC;

-- Get blueprint statistics
SELECT 
    COUNT(*) as total_blueprints,
    AVG(jsonb_array_length(blueprint_json->'moves')) as avg_moves,
    AVG((blueprint_json->>'total_duration')::float) as avg_duration
FROM blueprints;
```

---

## Storage Locations by Environment

### Development
| Component | Storage Location |
|-----------|-----------------|
| Blueprints | PostgreSQL (localhost:5432) |
| Videos | `data/choreographies/` (local filesystem) |
| Songs | `data/songs/` (local filesystem) |
| Move Videos | `data/Bachata_steps/` (local filesystem) |

### Production
| Component | Storage Location |
|-----------|-----------------|
| Blueprints | Cloud SQL PostgreSQL |
| Videos | Google Cloud Storage (`gs://bachata-buddy-videos/choreographies/`) |
| Songs | Google Cloud Storage (`gs://bachata-buddy-videos/songs/`) |
| Move Videos | Google Cloud Storage (`gs://bachata-buddy-videos/moves/`) |

---

## Blueprint Retention Policy

### Current Policy
- **Retention:** Indefinite (never deleted automatically)
- **Backup:** Included in database backups
- **Size:** ~8-13 KB per blueprint (JSON)

### Recommended Production Policy
```python
# Optional: Clean up old blueprints after 90 days
from datetime import timedelta
from django.utils import timezone

def cleanup_old_blueprints():
    """Delete blueprints older than 90 days"""
    cutoff_date = timezone.now() - timedelta(days=90)
    old_blueprints = Blueprint.objects.filter(created_at__lt=cutoff_date)
    count = old_blueprints.count()
    old_blueprints.delete()
    return count
```

---

## Verification Commands

### Check Blueprint Exists
```bash
# Development
docker exec bachata_db psql -U postgres -d bachata_vibes -c \
  "SELECT task_id, created_at FROM blueprints WHERE task_id = 'YOUR_TASK_ID';"

# Production
gcloud sql connect bachata-db --user=postgres --database=bachata_vibes
SELECT task_id, created_at FROM blueprints WHERE task_id = 'YOUR_TASK_ID';
```

### Retrieve Blueprint JSON
```bash
# Development
docker exec bachata_db psql -U postgres -d bachata_vibes -t -c \
  "SELECT blueprint_json FROM blueprints WHERE task_id = 'YOUR_TASK_ID';" \
  | jq '.'

# Production
gcloud sql connect bachata-db --user=postgres --database=bachata_vibes
\x
SELECT blueprint_json FROM blueprints WHERE task_id = 'YOUR_TASK_ID';
```

### Count Blueprints
```bash
# Development
docker exec bachata_db psql -U postgres -d bachata_vibes -c \
  "SELECT COUNT(*) as total_blueprints FROM blueprints;"

# Production
gcloud sql connect bachata-db --user=postgres --database=bachata_vibes
SELECT COUNT(*) as total_blueprints FROM blueprints;
```

---

## Current Status

### Blueprints in Database (as of Nov 10, 2025)
```sql
SELECT task_id, created_at, LENGTH(blueprint_json::text) as json_size 
FROM blueprints 
ORDER BY created_at DESC 
LIMIT 5;
```

**Results:**
| Task ID | Created At | JSON Size |
|---------|------------|-----------|
| ab6d6846... | 2025-11-10 01:23:12 | 8,755 bytes |
| 63ec74aa... | 2025-11-10 01:23:01 | 8,091 bytes |
| 2dc58b54... | 2025-11-10 00:48:48 | 13,119 bytes |
| 3b3e0611... | 2025-11-10 00:48:38 | 11,357 bytes |
| f55f74fc... | 2025-11-10 00:45:15 | 13,119 bytes |

**Total Blueprints:** 5  
**Average Size:** ~10.5 KB  
**Total Storage:** ~52 KB  

---

## Benefits of Database Persistence

### 1. **Reliability**
- ✅ Blueprints survive container restarts
- ✅ Blueprints survive job failures
- ✅ Blueprints survive API restarts

### 2. **Traceability**
- ✅ Complete audit trail of all generations
- ✅ Can trace back to exact parameters used
- ✅ Debug issues by examining blueprints

### 3. **Efficiency**
- ✅ No need to regenerate blueprints
- ✅ Can retry video assembly without re-analysis
- ✅ Fast retrieval via database index

### 4. **Scalability**
- ✅ PostgreSQL handles millions of blueprints
- ✅ JSONB type allows efficient querying
- ✅ Automatic backups via Cloud SQL

---

## Conclusion

**Blueprints are PERMANENTLY SAVED in PostgreSQL and are NOT LOST after being sent to the job container.**

### Storage Flow:
1. ✅ Blueprint generated in API
2. ✅ Blueprint saved to PostgreSQL (PERMANENT)
3. ✅ Blueprint passed to job container (TEMPORARY - via environment variable)
4. ✅ Job container uses blueprint to assemble video
5. ✅ Blueprint remains in PostgreSQL (PERMANENT)

### Production Storage:
- **Database:** Cloud SQL PostgreSQL (permanent, backed up)
- **Transmission:** Environment variable (temporary, for job execution)
- **Retention:** Indefinite (or configurable cleanup policy)

**Your blueprints are safe and will always be available for retrieval, analysis, and debugging!** 🎉

---

**Document Version:** 1.0  
**Last Updated:** November 10, 2025  
**Status:** ✅ Verified in Production
