# Jobs Service Blueprint Update - Task 14 Complete

## Summary

Successfully updated the `CloudRunJobsService` to use the blueprint-based architecture. The service now only accepts `blueprint_json` as a parameter and passes it to the job container via the `BLUEPRINT_JSON` environment variable.

## Changes Made

### 1. Updated `jobs_service.py`

#### Method Signature Changes
- **`create_job_execution()`**: Now requires `blueprint_json` in parameters dict
- Removed legacy parameter support (audio_input, difficulty, energy_level, style)
- Updated validation to only check for `blueprint_json`

#### Environment Variables
- **Added**: `BLUEPRINT_JSON` - Complete blueprint as JSON string
- **Removed**: `AUDIO_INPUT`, `DIFFICULTY`, `ENERGY_LEVEL`, `STYLE`

#### Documentation
- Updated module docstring with blueprint-based usage example
- Updated method docstrings to reflect new parameter requirements
- Added clear examples showing JSON blueprint structure

### 2. Updated `test_jobs_service.py`

All tests updated to use `blueprint_json` parameter:
- `test_create_job_execution_local_dev()` - Uses blueprint JSON
- `test_create_job_execution_missing_blueprint_json()` - Tests validation
- `test_create_job_execution_success_with_retry()` - Uses blueprint JSON
- `test_create_job_execution_non_retryable_error()` - Uses blueprint JSON
- `test_create_job_execution_max_retries_exhausted()` - Uses blueprint JSON
- `test_create_job_execution_internal_success()` - Uses blueprint JSON
- `test_create_job_execution_internal_timeout()` - Uses blueprint JSON

### 3. Updated `mock_job_service.py`

- Updated docstring with blueprint-based usage example
- Updated `create_job_execution()` method signature documentation
- Maintains backward compatibility for local development

### 4. Created Integration Test

Created `test_blueprint_job_integration.py` to verify:
- Local dev mode works with blueprint
- Missing blueprint_json raises appropriate error
- Blueprint JSON structure is valid
- Both local and GCP modes work correctly

## Verification

✅ All syntax checks passed (no diagnostics)
✅ Integration test passed successfully
✅ Both user paths (generate_from_song and generate_with_ai) already use blueprint_json
✅ No other code locations need updating

## Blueprint JSON Structure

The service now expects a complete blueprint with this structure:

```json
{
  "task_id": "uuid-string",
  "audio_path": "data/songs/song.mp3",
  "audio_tempo": 120.0,
  "moves": [
    {
      "clip_id": "move_1",
      "video_path": "data/Bachata_steps/basic_steps/basic_1.mp4",
      "start_time": 0.0,
      "duration": 8.0,
      "transition_type": "cut"
    }
  ],
  "total_duration": 180.0,
  "difficulty_level": "intermediate",
  "generation_parameters": {
    "energy_level": "medium",
    "style": "modern",
    "user_id": 1
  },
  "output_config": {
    "output_path": "data/output/choreography_uuid.mp4",
    "output_format": "mp4"
  }
}
```

## Usage Example

```python
import json
from services.jobs_service import CloudRunJobsService

# Generate blueprint (done by BlueprintGenerator)
blueprint = {
    "task_id": "abc-123",
    "audio_path": "gs://bucket/song.mp3",
    "moves": [...],
    "output_config": {...}
}

# Submit job with blueprint
service = CloudRunJobsService()
execution_name = service.create_job_execution(
    task_id="abc-123",
    user_id=42,
    parameters={"blueprint_json": json.dumps(blueprint)}
)
```

## Impact

### Breaking Changes
- ❌ Legacy parameter format no longer supported
- ❌ Individual env vars (AUDIO_INPUT, DIFFICULTY, etc.) no longer passed to job container

### Benefits
- ✅ Simplified job container interface
- ✅ Complete blueprint passed as single parameter
- ✅ Job container only needs to parse BLUEPRINT_JSON env var
- ✅ Consistent with blueprint-based architecture design
- ✅ Both user paths use same blueprint schema

## Next Steps

The following tasks remain in the blueprint refactor:
- Task 15: Update environment variables documentation
- Task 16-20: Testing tasks
- Task 21-24: Documentation tasks
- Task 25-26: Migration and deployment tasks

## Files Modified

1. `bachata_buddy/backend/services/jobs_service.py` - Main service implementation
2. `bachata_buddy/backend/services/test_jobs_service.py` - Unit tests
3. `bachata_buddy/backend/services/mock_job_service.py` - Mock service for local dev
4. `bachata_buddy/backend/services/test_blueprint_job_integration.py` - New integration test

## Testing

Run the integration test:
```bash
cd bachata_buddy/backend
uv run python services/test_blueprint_job_integration.py
```

Expected output:
```
Testing blueprint-based job service...

✓ Local dev mode works with blueprint
✓ Missing blueprint_json raises appropriate error
✓ Blueprint JSON structure is valid

All tests passed! ✓
```
