# Implementation Plan

Convert the feature design into a series of prompts for a code-generation LLM that will implement each step with incremental progress. Each task builds on previous tasks and ends with full integration.

- [x] 1. Create Song database model and migrations
  - Create Song model in `backend/apps/choreography/models.py` with fields: id, title, artist, duration, bpm, genre, audio_path, created_at, updated_at
  - Add database indexes on title, artist, and genre fields
  - Create and run Django migrations
  - Add Song model to admin interface for easy management
  - _Requirements: 5_

- [x] 2. Create song serializers
  - Create SongSerializer for list views in `backend/apps/choreography/serializers.py`
  - Create SongDetailSerializer with audio_path field
  - Create SongGenerationSerializer with song_id and difficulty validation
  - Add song_id existence validation in SongGenerationSerializer
  - _Requirements: 3, 5_

- [x] 3. Implement list songs endpoint
  - Create `list_songs()` view function in `backend/apps/choreography/views.py`
  - Add pagination support (default 20 items per page, max 100)
  - Implement filtering by genre, bpm_min, bpm_max
  - Implement search by title and artist (case-insensitive)
  - Add OpenAPI documentation with examples
  - Require authentication
  - _Requirements: 1_

- [x] 4. Implement song detail endpoint
  - Create `song_detail()` view function in `backend/apps/choreography/views.py`
  - Return complete song metadata including audio_path
  - Handle 404 for non-existent songs
  - Add OpenAPI documentation
  - Require authentication
  - _Requirements: 2_

- [x] 5. Implement generate from song endpoint
  - Create `generate_from_song()` view function in `backend/apps/choreography/views.py`
  - Validate song_id exists before creating task
  - Create ChoreographyTask with song reference
  - Retrieve song's audio_path and pass to Cloud Run Job
  - Return task_id, song info, and poll_url (202 Accepted)
  - Add OpenAPI documentation with examples
  - Require authentication
  - _Requirements: 3_

- [x] 6. Update ChoreographyTask model
  - Add optional `song` ForeignKey field to ChoreographyTask model
  - Create and run migration for the new field
  - Update task serializers to include song information when present
  - _Requirements: 7_

- [x] 7. Add URL patterns for song endpoints
  - Add `songs/` route to `backend/apps/choreography/urls.py`
  - Add `songs/<int:song_id>/` route
  - Add `generate-from-song/` route
  - Verify all routes are properly namespaced under `/api/choreography/`
  - _Requirements: 1, 2, 3_

- [x] 8. Remove /generate endpoint completely
  - Delete `generate_choreography()` view function from `backend/apps/choreography/views.py`
  - Delete `ChoreographyGenerationSerializer` from `backend/apps/choreography/serializers.py`
  - Remove `path('generate/', generate_choreography, name='generate')` from `backend/apps/choreography/urls.py`
  - Remove all tests that reference the `/api/choreography/generate/` endpoint
  - Remove any documentation or examples using this endpoint
  - Verify no other code depends on this endpoint
  - _Requirements: 4_

- [x] 9. Create sample song fixtures for local testing
  - Create `backend/fixtures/songs.json` with 3-5 sample songs
  - Include variety of genres, BPMs, and artists
  - Use local file paths (songs/filename.mp3)
  - Create `backend/data/songs/` directory structure
  - Add README explaining how to add sample audio files
  - _Requirements: 10_

- [x] 10. Write comprehensive tests for song endpoints
  - Write unit tests for Song model in `backend/apps/choreography/tests.py`
  - Write tests for song serializers (validation, song_id existence)
  - Write tests for list_songs endpoint (pagination, filtering, search)
  - Write tests for song_detail endpoint (success, 404)
  - Write tests for generate_from_song endpoint (success, invalid song_id)
  - Write integration test for complete workflow: list → select → generate
  - _Requirements: 1, 2, 3, 10_

- [x] 11. Verify and fix OpenAPI/Swagger UI configuration
  - Verify SPECTACULAR_SERVERS is set to localhost:8001 in `backend/api/settings.py`
  - Test that Swagger UI loads at http://localhost:8001/api/docs/
  - Test that API requests work from Swagger UI (no CORS errors)
  - Verify all new song endpoints appear in Swagger UI
  - Test authentication flow in Swagger UI
  - _Requirements: 9_

- [x] 12. Update API documentation
  - Update `backend/README.md` with song template workflow examples
  - Add cURL examples for all three song endpoints
  - Remove YouTube URL examples and references
  - Document local development setup with sample songs
  - Add section explaining local vs GCS storage
  - _Requirements: 8, 10_

- [x] 13. Run full test suite and verify functionality
  - Load song fixtures: `python manage.py loaddata songs`
  - Run all unit tests: `pytest apps/choreography/tests.py -v`
  - Run integration tests
  - Manually test all endpoints via cURL or Swagger UI
  - Verify task creation and status updates work correctly
  - Verify AI workflow endpoints still function correctly
  - _Requirements: 6, 10_
