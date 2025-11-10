# Blueprint Schema Consistency Verification

## Overview

This document verifies that both user paths (Path 1: Select Song and Path 2: Describe Choreo) generate blueprints with the same schema format, ensuring the job container can process them identically.

## Verification Date

November 9, 2025

## Paths Tested

### Path 1: Select Song
- **Endpoint:** `/api/choreography/generate-from-song/`
- **Input:** Song ID + choreography parameters (difficulty, energy_level, style)
- **Process:** Direct blueprint generation from song selection

### Path 2: Describe Choreo (AI)
- **Endpoint:** `/api/choreography/generate-with-ai/`
- **Input:** Natural language query
- **Process:** Query parsing → parameter extraction → blueprint generation

## Common Architecture

Both paths use the **same blueprint generation service**:

```python
from services.blueprint_generator import BlueprintGenerator

# Both paths use identical initialization
blueprint_gen = BlueprintGenerator(
    vector_search_service=vector_search,
    music_analyzer=music_analyzer,
    gemini_service=gemini
)

# Both paths call the same method
blueprint = blueprint_gen.generate_blueprint(
    task_id=task_id,
    song_path=song.audio_path,
    difficulty=difficulty,
    energy_level=energy_level,
    style=style,
    user_id=request.user.id
)
```

## Schema Structure

### Core Blueprint Fields (Identical in Both Paths)

```json
{
  "task_id": "string",
  "audio_path": "string",
  "audio_tempo": "number",
  "moves": [
    {
      "clip_id": "string",
      "video_path": "string",
      "start_time": "number",
      "duration": "number",
      "transition_type": "string",
      "original_duration": "number",
      "trim_start": "number",
      "trim_end": "number",
      "volume_adjustment": "number"
    }
  ],
  "total_duration": "number",
  "difficulty_level": "string",
  "generation_timestamp": "string",
  "generation_parameters": {
    "energy_level": "string",
    "style": "string",
    "user_id": "number"
  },
  "output_config": {
    "output_path": "string",
    "output_format": "string",
    "video_codec": "string",
    "audio_codec": "string",
    "video_bitrate": "string",
    "audio_bitrate": "string",
    "frame_rate": "number",
    "transition_duration": "number",
    "fade_duration": "number",
    "add_audio_overlay": "boolean",
    "normalize_audio": "boolean"
  }
}
```

### Path 2 Additional Fields (AI-Specific Metadata)

Path 2 adds **only two additional fields** to `generation_parameters`:

```json
{
  "generation_parameters": {
    "energy_level": "string",
    "style": "string",
    "user_id": "number",
    "ai_mode": true,              // ← Added by Path 2
    "original_query": "string"    // ← Added by Path 2
  }
}
```

These fields are:
- **Metadata only** - not used by the job container
- **Backward compatible** - job container ignores unknown fields
- **Audit trail** - useful for debugging and analytics

## Verification Results

### Test Results

```bash
$ uv run pytest test_blueprint_flow.py::BlueprintSchemaConsistencyTests -v

test_blueprint_flow.py::BlueprintSchemaConsistencyTests::test_both_paths_generate_same_schema PASSED
test_blueprint_flow.py::BlueprintSchemaConsistencyTests::test_schema_consistency_with_different_parameters PASSED

============================== 2 passed in 14.50s ===============================
```

### Schema Comparison

```bash
$ uv run python verify_blueprint_schema_consistency.py

================================================================================
Blueprint Schema Consistency Verification
================================================================================

1. Validating Path 1 blueprint schema...
   ✓ Path 1 blueprint is valid

2. Validating Path 2 blueprint schema...
   ✓ Path 2 blueprint is valid

3. Comparing blueprint schemas...
   Common keys: 32
   Keys only in Path 1: 0
   Keys only in Path 2: 2

   Path 2 additional keys:
     - generation_parameters.ai_mode (expected)
     - generation_parameters.original_query (expected)

4. Schema Compatibility Check...
   ✓ Schemas are compatible!
   ✓ Both paths generate the same blueprint structure
   ✓ Path 2 only adds expected AI-specific metadata

================================================================================
VERIFICATION PASSED
================================================================================
```

## Key Findings

### ✓ Schema Compatibility Confirmed

1. **Identical Core Structure**
   - Both paths generate blueprints with the same 32 core fields
   - All required fields are present in both paths
   - All field types match exactly

2. **Consistent Move Structure**
   - Both paths use the same move object schema
   - All 9 move fields are identical (clip_id, video_path, start_time, duration, etc.)
   - Transition types are consistent

3. **Consistent Output Configuration**
   - Both paths use the same output_config schema
   - All 11 output fields are identical
   - Video/audio codec settings match

4. **Expected Differences Only**
   - Path 2 adds only 2 AI-specific metadata fields
   - These fields are in `generation_parameters` (not used by job container)
   - No unexpected schema differences

### ✓ Job Container Compatibility

The job container can process blueprints from both paths identically because:

1. **Same Required Fields**
   - Job container only reads core fields (task_id, audio_path, moves, output_config)
   - Both paths provide all required fields

2. **Ignores Unknown Fields**
   - Job container ignores `generation_parameters` (metadata only)
   - AI-specific fields (ai_mode, original_query) are safely ignored

3. **Same Processing Logic**
   - Blueprint parser validates the same schema for both paths
   - Video assembler uses the same fields from both paths
   - No conditional logic based on path origin

## Implementation Details

### Path 1: generate_from_song()

```python
# Generate blueprint using BlueprintGenerator
blueprint = blueprint_gen.generate_blueprint(
    task_id=task_id,
    song_path=song.audio_path,
    difficulty=difficulty,
    energy_level=energy_level,
    style=style,
    user_id=request.user.id
)

# Store blueprint in database
Blueprint.objects.create(
    task=task,
    blueprint_json=blueprint
)

# Submit job with blueprint
jobs_service.create_job_execution(
    task_id=task_id,
    user_id=request.user.id,
    parameters={'blueprint_json': json.dumps(blueprint)}
)
```

### Path 2: generate_with_ai()

```python
# Parse natural language query
parsed = gemini_svc.parse_choreography_request(query)
parameters = parsed.to_dict()

# Generate blueprint using BlueprintGenerator (same service as Path 1)
blueprint = blueprint_gen.generate_blueprint(
    task_id=task_id,
    song_path=song.audio_path,
    difficulty=parameters['difficulty'],
    energy_level=parameters['energy_level'],
    style=parameters['style'],
    user_id=request.user.id
)

# Add AI-specific metadata
blueprint['generation_parameters']['ai_mode'] = True
blueprint['generation_parameters']['original_query'] = query

# Store blueprint in database
Blueprint.objects.create(
    task=task,
    blueprint_json=blueprint
)

# Submit job with blueprint (same as Path 1)
jobs_service.create_job_execution(
    task_id=task_id,
    user_id=request.user.id,
    parameters={'blueprint_json': json.dumps(blueprint)}
)
```

## Test Coverage

### Unit Tests

1. **test_both_paths_generate_same_schema**
   - Validates both paths generate blueprints with identical structure
   - Compares all core fields and types
   - Verifies move structure consistency
   - Confirms output_config consistency

2. **test_schema_consistency_with_different_parameters**
   - Tests schema consistency across different difficulty levels
   - Tests schema consistency across different energy levels
   - Verifies structure remains the same regardless of parameter values

### Integration Tests

The existing integration tests in `test_blueprint_flow.py` cover:
- Path 1 complete flow (song selection → blueprint → job)
- Path 2 complete flow (query → parsing → blueprint → job)
- Blueprint validation
- Job submission
- Error handling

## Conclusion

**✓ VERIFIED:** Both Path 1 (Select Song) and Path 2 (Describe Choreo) generate blueprints with the same schema format.

### Summary

- **32 common fields** across both paths
- **2 additional fields** in Path 2 (AI metadata only)
- **0 unexpected differences**
- **100% job container compatibility**

### Benefits

1. **Simplified Job Container**
   - Single blueprint parser for both paths
   - No conditional logic based on path origin
   - Consistent error handling

2. **Maintainability**
   - Changes to blueprint schema affect both paths equally
   - Single source of truth (BlueprintGenerator)
   - Easier testing and validation

3. **Extensibility**
   - New paths can use the same BlueprintGenerator
   - Additional metadata can be added without breaking compatibility
   - Job container remains decoupled from API logic

## Related Documentation

- [Blueprint Schema Documentation](../../docs/BLUEPRINT_SCHEMA.md)
- [API Documentation](API_DOCUMENTATION_UPDATE.md)
- [Job Container Documentation](../../job/README.md)
- [Blueprint Generator Service](services/blueprint_generator.py)

## Verification Scripts

- **Test Suite:** `test_blueprint_flow.py::BlueprintSchemaConsistencyTests`
- **Verification Script:** `verify_blueprint_schema_consistency.py`

Run verification:
```bash
# Run tests
uv run pytest test_blueprint_flow.py::BlueprintSchemaConsistencyTests -v

# Run verification script
uv run python verify_blueprint_schema_consistency.py
```
