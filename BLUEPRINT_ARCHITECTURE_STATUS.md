# Blueprint Architecture - Current Status

## Summary

**Current Status:** ✅ **BLUEPRINT ARCHITECTURE IMPLEMENTED AND WORKING!**

The blueprint-based architecture from the spec is now fully implemented and tested locally:
- ✅ API generates blueprints with real embeddings (38 moves)
- ✅ Job container assembles videos from blueprints
- ✅ Both Path 1 and Path 2 working with 8-10 moves each
- ✅ Progressive fallback strategy handles missing metadata
- ✅ Videos generating successfully (21 MB each)

**Next Step:** Deploy to Google Cloud Production

## Two User Paths

### Path 1: "Select Song" 
User selects a pre-existing song from the database.

### Path 2: "Describe Choreo"
User describes what they want in natural language (e.g., "Create a romantic bachata for beginners").

## Current Architecture (What We Just Tested) ❌

### Both Paths Currently Work The Same Way:

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │ POST /api/choreography/generate-from-song (Path 1)
       │ POST /api/choreography/generate-with-ai (Path 2)
       ▼
┌─────────────────────────────────────────────────────────┐
│                    API/Backend                          │
│                                                         │
│  1. Parse request (Gemini for Path 2)                  │
│  2. Create ChoreographyTask in database                │
│  3. Call jobs_service.create_job_execution()           │
│     with parameters:                                    │
│     - audio_input (song path)                          │
│     - difficulty                                        │
│     - energy_level                                      │
│     - style                                             │
│     - ai_mode (for Path 2)                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
       │
       │ Environment Variables (NOT a blueprint!)
       ▼
┌─────────────────────────────────────────────────────────┐
│                   Job Container                         │
│                                                         │
│  1. ✅ Connect to database                             │
│  2. ✅ Analyze audio (Librosa)                         │
│  3. ✅ Query Elasticsearch for moves                   │
│  4. ✅ Generate choreography (Gemini AI)               │
│  5. ⚠️  Assemble video (needs training videos)         │
│  6. ✅ Update database                                 │
│                                                         │
│  Dependencies: Django, DRF, Elasticsearch,              │
│                Librosa, NumPy, SciPy, Gemini           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Problem:** Job container is HEAVY and does EVERYTHING. No blueprint is used.

## Proposed Blueprint Architecture (From Spec) ✅

### Both Paths Should Work Like This:

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │ POST /api/choreography/generate-from-song (Path 1)
       │ POST /api/choreography/generate-with-ai (Path 2)
       ▼
┌─────────────────────────────────────────────────────────┐
│                    API/Backend                          │
│                                                         │
│  1. Parse request (Gemini for Path 2)                  │
│  2. ✨ Analyze audio (Librosa)                         │
│  3. ✨ Load move embeddings from database              │
│  4. ✨ Perform vector search (NumPy cosine similarity) │
│  5. ✨ Generate choreography sequence (Gemini AI)      │
│  6. ✨ CREATE BLUEPRINT JSON:                          │
│     {                                                   │
│       "task_id": "abc-123",                            │
│       "audio_path": "data/songs/Amor.mp3",            │
│       "moves": [                                        │
│         {                                               │
│           "video_path": "data/moves/basic_step.mp4",  │
│           "start_time": 0.0,                          │
│           "duration": 8.0                             │
│         },                                             │
│         ...                                            │
│       ]                                                │
│     }                                                  │
│  7. Store blueprint in database                        │
│  8. Call jobs_service with BLUEPRINT_JSON              │
│                                                         │
└─────────────────────────────────────────────────────────┘
       │
       │ BLUEPRINT_JSON (complete instructions!)
       ▼
┌─────────────────────────────────────────────────────────┐
│                   Job Container                         │
│                                                         │
│  1. Parse BLUEPRINT_JSON                                │
│  2. Fetch audio file from storage                      │
│  3. Fetch video clips from storage                     │
│  4. Assemble video with FFmpeg                         │
│  5. Upload result to storage                           │
│  6. Update database                                    │
│                                                         │
│  Dependencies: FFmpeg, psycopg2, GCS client            │
│  (NO Elasticsearch, NO Librosa, NO AI!)                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ Job container is LIGHTWEIGHT (512MB vs 2GB+)
- ✅ Job container is FAST (no audio analysis, no AI)
- ✅ Job container is SIMPLE (just video assembly)
- ✅ No Elasticsearch in job container
- ✅ Easier to test and maintain

## What We Tested Today

We tested the **NEW BLUEPRINT ARCHITECTURE** where:
- ✅ API generates blueprints with VectorSearchService (FAISS)
- ✅ API uses 38 real move embeddings from database
- ✅ API implements progressive fallback strategy
- ✅ Job container receives BLUEPRINT_JSON
- ✅ Job container assembles videos from blueprint
- ✅ Path 1: 8 intermediate moves → 21 MB video
- ✅ Path 2: 10 beginner moves → 21 MB video

This proves the **blueprint architecture works** for both paths!

## What Has Been Done ✅

### Backend Changes (API)
1. ✅ Created `VectorSearchService` with FAISS in-memory search
2. ✅ Created `BlueprintGenerator` service with progressive fallback
3. ✅ Added `MoveEmbedding` model to database
4. ✅ Added `Blueprint` model to database
5. ✅ Loaded 38 real embeddings from `data/embeddings_backup.json`
6. ✅ Implemented fallback strategy (exact → relax energy → relax style → semantic)
7. ✅ Blueprint generation working for both paths

### Job Container Changes
1. ✅ Simplified `main.py` for blueprint-based assembly
2. ✅ Blueprint parser service implemented
3. ✅ Video assembler service working
4. ✅ Storage service (local + GCS) working
5. ✅ Database service for status updates working
6. ✅ Videos assembling successfully from blueprints

### Local Testing Complete
1. ✅ Both paths tested and working
2. ✅ Videos generated (21 MB each)
3. ✅ Real embeddings in use (no mocks)
4. ✅ Fallback strategy validated

## What Needs to Be Done

### Google Cloud Deployment
1. ⏳ Deploy API container to Cloud Run
2. ⏳ Deploy Job container to Cloud Run Jobs
3. ⏳ Run database migrations on Cloud SQL
4. ⏳ Load 38 embeddings to Cloud SQL database
5. ⏳ Upload training videos to GCS bucket
6. ⏳ Upload songs to GCS bucket
7. ⏳ Update environment variables for production
8. ⏳ Test end-to-end in production

## Current vs Proposed

| Aspect | Current (Tested Today) | Proposed (Spec) |
|--------|----------------------|-----------------|
| **Blueprint Used?** | ❌ No | ✅ Yes (IMPLEMENTED) |
| **Job Does Audio Analysis?** | ✅ Yes | ❌ No (API does it) ✅ |
| **Job Queries Elasticsearch?** | ✅ Yes | ❌ No (API uses FAISS) ✅ |
| **Job Uses AI?** | ✅ Yes | ❌ No (API does it) ✅ |
| **Job Assembles Video?** | ✅ Yes | ✅ Yes (only this!) ✅ |
| **Job Container Size** | ~2GB+ | ~512MB ✅ |
| **Job Dependencies** | Heavy (Django, ES, Librosa, AI) | Light (FFmpeg, psycopg2, GCS) ✅ |
| **Both Paths Supported?** | ✅ Yes | ✅ Yes (with blueprint) ✅ |
| **Real Embeddings?** | ❌ No (3 mocks) | ✅ Yes (38 real) ✅ |
| **Fallback Strategy?** | ❌ No | ✅ Yes (4-level) ✅ |

## Answer to Your Question

**Q: Are we covering both paths of video generation?**

**A: Yes, but...**

1. **Current Implementation (What We Tested):**
   - ✅ Both paths work
   - ✅ Both paths send parameters to job
   - ❌ Neither path sends a blueprint
   - ❌ Job does everything itself

2. **Proposed Implementation (From Spec):**
   - ✅ Both paths should work
   - ✅ Both paths should generate blueprint in API
   - ✅ Both paths should send blueprint to job
   - ✅ Job only assembles video from blueprint

## Next Steps

To implement the blueprint architecture:

1. **Implement the spec tasks** (blueprint-job-refactor)
2. **Test both paths** with blueprint generation
3. **Verify job container** only does video assembly
4. **Remove heavy dependencies** from job container

The spec is well-designed and covers both paths. It just needs to be implemented!

## Testing Both Paths

### Path 1: Select Song (Current)
```bash
curl -X POST http://localhost:8001/api/choreography/generate-from-song \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "song_id": 1,
    "difficulty": "intermediate",
    "energy_level": "high",
    "style": "modern"
  }'
```

### Path 2: Describe Choreo (Current)
```bash
curl -X POST http://localhost:8001/api/choreography/generate-with-ai \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a romantic bachata for beginners with smooth transitions"
  }'
```

Both paths currently work but don't use blueprints. After implementing the spec, both will generate blueprints and send them to a lightweight job container.

---

**Status:** Blueprint architecture fully implemented and tested locally ✅  
**Local Testing:** Both paths working with 8-10 real moves each ✅  
**Next:** Deploy to Google Cloud Production ⏳

## Recent Fixes Applied

### 1. Path 2 Empty Moves Array Fix
- **Problem:** Vector search was too strict, returning 0 moves
- **Solution:** Progressive fallback strategy (4 levels)
- **Result:** Path 2 now returns 10 beginner moves

### 2. Real Embeddings Loaded
- **Problem:** Only 3 mock embeddings in database
- **Solution:** Loaded 38 real embeddings from `data/embeddings_backup.json`
- **Result:** Proper move variety and selection

### 3. Blueprint Generator Enhanced
- **Added:** Fallback strategy in `_search_matching_moves()`
- **Logs:** Clear warnings when falling back
- **Result:** Always returns moves, never empty array
