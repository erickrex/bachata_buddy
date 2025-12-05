# Implementation Plan

## Overview

This plan refactors the video processing architecture to use a blueprint-based approach, removing Elasticsearch from the job container and moving all intelligence to the API/backend.

## Tasks

- [x] 1. Backend: Create vector search service with in-memory operations
  - Create `backend/services/vector_search_service.py` with FAISS-based similarity search
  - Implement `load_embeddings_from_db()` to load move embeddings into memory
  - Implement `build_faiss_index()` to create FAISS IndexFlatIP for cosine similarity
  - Implement `search_similar_moves()` with FAISS search and filtering by difficulty, energy, style
  - Add fallback to NumPy-based search if FAISS fails
  - Add caching mechanism for FAISS index (1-hour TTL)
  - Add FAISS dependency to backend requirements
  - _Requirements: 2.3, 2.4, 6.2, 6.3_

- [x] 2. Backend: Create blueprint generator service
  - Create `backend/services/blueprint_generator.py`
  - Implement `generate_blueprint()` method that orchestrates the full flow
  - Integrate music analyzer for audio analysis
  - Integrate vector search for move selection
  - Integrate Gemini AI for choreography sequencing
  - Generate blueprint JSON matching the schema
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.5_

- [x] 3. Backend: Create move embeddings database model
  - Create `backend/apps/choreography/models.py` - `MoveEmbedding` model
  - Add fields: move_id, move_name, video_path, pose_embedding (JSON), audio_embedding (JSON), text_embedding (JSON)
  - Add metadata fields: difficulty, energy_level, style, duration
  - Create database migration
  - _Requirements: 2.3_

- [x] 4. Backend: Create blueprint database model
  - Add `Blueprint` model to `backend/apps/choreography/models.py`
  - Add OneToOne relationship with `ChoreographyTask`
  - Add `blueprint_json` JSONField
  - Create database migration
  - _Requirements: 6.5_

- [x] 5. Backend: Update choreography API endpoints for both user paths
  - Modify `backend/apps/choreography/views.py` - `generate_from_song` endpoint (Path 1: Select Song)
    - Retrieve song from database
    - Use `BlueprintGenerator` to create blueprint
    - Store blueprint in database
    - Pass blueprint JSON to job service via `BLUEPRINT_JSON` environment variable
  - Modify `backend/apps/choreography/views.py` - `generate_with_ai` endpoint (Path 2: Describe Choreo)
    - Parse natural language query with Gemini (keep existing logic)
    - Use `BlueprintGenerator` to create blueprint with parsed parameters
    - Store blueprint in database
    - Pass blueprint JSON to job service via `BLUEPRINT_JSON` environment variable
  - Remove Elasticsearch dependencies from both endpoints
  - Ensure both paths use the same blueprint schema
  - _Requirements: 1.1, 1.2, 6.1, 6.2, 6.5, 6.6, 6.7_

- [x] 6. Job Container: Create simplified main.py
  - Create new `job/src/main.py` with minimal dependencies
  - Implement `BlueprintVideoAssembler` class
  - Parse blueprint from environment variable `BLUEPRINT_JSON`
  - Validate blueprint schema
  - Orchestrate video assembly flow
  - _Requirements: 1.2, 1.3, 1.4, 7.1_

- [x] 7. Job Container: Implement blueprint parser and validator
  - Create `job/src/services/blueprint_parser.py`
  - Implement JSON schema validation
  - Validate required fields (task_id, song, moves_used, video_output)
  - Validate file paths for security (no directory traversal)
  - Return structured validation errors
  - _Requirements: 7.1, 9.1_

- [x] 8. Job Container: Implement video assembly service
  - Create `job/src/services/video_assembler.py`
  - Fetch song audio file from storage
  - Fetch all video clip files from storage (parallel downloads)
  - Use FFmpeg to concatenate clips with audio
  - Apply any transitions if specified
  - Save output video to storage
  - _Requirements: 7.2, 7.3, 7.4, 7.5_

- [x] 9. Job Container: Simplify storage service
  - Keep existing `job/src/services/storage_service.py` interface
  - Remove any Elasticsearch-related code
  - Ensure dual support for local filesystem and GCS
  - Add parallel download capability
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 10. Job Container: Simplify database service
  - Keep existing `job/src/services/database.py`
  - Remove any complex queries
  - Keep only `update_task_status()` method
  - Ensure connection pooling works
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 11. Job Container: Update Dockerfile with minimal dependencies
  - Modify `job/Dockerfile`
  - Remove: Django, DRF, Elasticsearch, Librosa, NumPy, SciPy, ML libraries, FAISS
  - Keep: FFmpeg, psycopg2-binary, google-cloud-storage, python-dotenv
  - Note: FAISS is only needed in backend, not in job container
  - Optimize for size and build speed
  - Target build time under 2 minutes
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 12. Job Container: Implement error handling
  - Add try-catch blocks for all major operations
  - Log errors to stdout with structured logging
  - Update database with error messages
  - Implement retry logic for storage operations (3 retries with exponential backoff)
  - Exit with appropriate error codes
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 13. Infrastructure: Remove Elasticsearch from docker-compose
  - Remove `elasticsearch` service from `docker-compose.yml`
  - Remove Elasticsearch volume
  - Update service dependencies
  - Remove Elasticsearch health checks
  - _Requirements: 2.2, 2.5_

- [x] 14. Backend: Update jobs service to pass blueprint
  - Modify `backend/services/jobs_service.py` - `CloudRunJobsService.create_job_execution()`
  - Change method signature to accept `blueprint_json` parameter instead of individual parameters
  - Pass blueprint as `BLUEPRINT_JSON` environment variable to job container
  - Remove individual parameter env vars (audio_input, difficulty, energy_level, style, ai_mode)
  - Update for both local (docker-compose) and GCP (Cloud Run Jobs) modes
  - _Requirements: 1.2, 1.3_

- [x] 15. Infrastructure: Update environment variables
  - Remove Elasticsearch-related env vars from `.env.example`
  - Add `BLUEPRINT_JSON` to job container env vars in docker-compose.yml
  - Add `MOVE_EMBEDDINGS_CACHE_TTL` to API env vars
  - Add `VECTOR_SEARCH_TOP_K` to API env vars
  - Add `FAISS_USE_GPU` to API env vars (optional GPU acceleration)
  - Add `FAISS_NPROBE` to API env vars (for IVF indices)
  - Update documentation
  - _Requirements: 1.2_

- [x] 16. Testing: Create unit tests for vector search service
  - Create `backend/services/test_vector_search_service.py`
  - Test embedding loading from database
  - Test FAISS index building and normalization
  - Test FAISS similarity search with various query embeddings
  - Test move filtering by difficulty, energy, style
  - Test caching mechanism for FAISS index
  - Test fallback to NumPy when FAISS fails
  - _Requirements: 11.1_

- [x] 17. Testing: Create unit tests for blueprint generator
  - Create `backend/services/test_blueprint_generator.py`
  - Test blueprint generation with various inputs
  - Test blueprint schema validation
  - Test integration with music analyzer
  - Test integration with vector search
  - _Requirements: 11.1_

- [x] 18. Testing: Create unit tests for job container
  - Create `job/test_blueprint_parser.py` - test blueprint parsing and validation
  - Create `job/test_video_assembler.py` - test video assembly logic
  - Update `job/test_storage_service.py` - test storage operations
  - Update `job/test_database_service.py` - test database updates
  - _Requirements: 11.2_

- [x] 19. Testing: Create integration tests for both user paths
  - Create `tests/test_blueprint_flow.py` - test complete API → Job flow
  - Test Path 1 (Select Song): `/api/choreography/generate-from-song` → blueprint generation → job execution
  - Test Path 2 (Describe Choreo): `/api/choreography/generate-with-ai` → query parsing → blueprint generation → job execution
  - Verify both paths generate the same blueprint schema
  - Test with local storage mode
  - Test with GCS storage mode
  - Test error scenarios (missing files, invalid blueprint, FFmpeg failure)
  - _Requirements: 1.7, 11.3, 11.4_

- [x] 20. Testing: Create performance tests
  - Create `tests/test_blueprint_performance.py`
  - Test blueprint generation completes under 10 seconds
  - Test video assembly completes under 30 seconds for 3-minute video
  - Test job container memory usage stays under 512MB
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.5_

- [x] 21. Documentation: Create blueprint schema documentation
  - Create `docs/BLUEPRINT_SCHEMA.md`
  - Document all fields with types and descriptions
  - Provide example blueprints
  - Document validation rules
  - _Requirements: 12.1, 12.4_

- [x] 22. Documentation: Update API documentation
  - Update `backend/API_DOCUMENTATION_UPDATE.md`
  - Document blueprint generation endpoint
  - Document new request/response formats
  - Document error codes
  - _Requirements: 12.2_

- [x] 23. Documentation: Update job container documentation
  - Update `job/README.md`
  - Document blueprint-based architecture
  - Document environment variables
  - Document local vs GCS modes
  - Provide usage examples
  - _Requirements: 12.3_

- [x] 24. Documentation: Create troubleshooting guide
  - Create `docs/TROUBLESHOOTING.md`
  - Document common errors and solutions
  - Document debugging techniques
  - Document performance tuning
  - _Requirements: 12.5_

- [x] 25. Migration: Create data migration script
  - Create `scripts/migrate_to_blueprint_architecture.py`
  - Migrate existing move data to `MoveEmbedding` model
  - Create sample blueprints for testing
  - Verify data integrity
  - _Requirements: N/A (migration support)_

- [x] 26. Deployment: Update deployment configurations
  - Update Cloud Run Job configuration
  - Update environment variables in GCP
  - Update resource limits (512MB memory, 1 CPU)
  - Update timeout to 5 minutes
  - Remove Elasticsearch infrastructure
  - _Requirements: N/A (deployment)_

## Testing Checklist

After implementation, verify:

- [x] **Path 1 (Select Song):** Blueprint generation works when user selects a song from database
- [x] **Path 2 (Describe Choreo):** Blueprint generation works when user describes choreography in natural language
- [x] **Both Paths:** Generate the same blueprint schema format
- [x] **Both Paths:** Successfully trigger job container with BLUEPRINT_JSON
- [x] Vector search returns relevant moves
- [x] Job container assembles videos correctly from blueprints
- [x] Local storage mode works
- [x] GCS storage mode works
- [x] Error handling works for all failure scenarios
- [x] Performance meets requirements (< 30s blueprint, < 120s video)
- [x] Memory usage stays under 512MB
- [x] All tests pass with > 80% coverage
- [ ] Documentation is complete and accurate

## Rollback Plan

If issues arise:

1. Keep old job container image available
2. Keep Elasticsearch running temporarily
3. Feature flag to switch between old and new architecture
4. Monitor error rates and performance metrics
5. Rollback if error rate > 5% or performance degrades > 50%
