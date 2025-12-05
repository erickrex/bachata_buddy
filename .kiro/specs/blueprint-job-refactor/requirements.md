# Requirements Document

## Introduction

This specification defines the refactoring of the video processing job container to use a blueprint-based approach. The current architecture has the job container performing complex operations including audio analysis, Elasticsearch queries, and choreography generation. The new architecture moves all intelligence to the API/backend, with the job container becoming a simple video assembly service that follows a pre-computed blueprint.

### Current Architecture (To Be Replaced)

The system currently supports two user paths, both using the same heavy job container:

**Path 1: "Select Song"** - User selects a pre-existing song from the database via `/api/choreography/generate-from-song`

**Path 2: "Describe Choreo"** - User describes choreography in natural language via `/api/choreography/generate-with-ai`

In both paths, the API only passes parameters (audio_input, difficulty, energy_level, style) to the job container, which then performs ALL operations: audio analysis, Elasticsearch queries, AI choreography generation, and video assembly. This results in a heavy job container with many dependencies (Django, Elasticsearch, Librosa, NumPy, SciPy, Gemini AI).

### New Blueprint-Based Architecture

Both user paths will be refactored to generate a complete blueprint in the API/backend before submitting to the job container. The job container will only perform video assembly from the blueprint, making it lightweight and fast.

## Glossary

- **Blueprint**: A JSON document containing the complete specification for video generation, including song selection, video clip paths, timing, transitions, and all metadata needed to assemble the final video
- **Job Container**: The Docker container that runs as a Cloud Run Job to generate videos from blueprints
- **API/Backend**: The Django REST API that creates blueprints and submits jobs
- **Vector Search**: In-memory similarity search for matching dance moves based on embeddings
- **Video Clip**: A short video file showing a specific dance move
- **Storage Service**: Abstraction layer for accessing files from local filesystem or Google Cloud Storage

## Requirements

### Requirement 1: Blueprint-Based Job Architecture for Both User Paths

**User Story:** As a system architect, I want the job container to be a simple video assembly service for both "Select Song" and "Describe Choreo" paths, so that it's lightweight, fast, and easy to maintain.

#### Acceptance Criteria

1. WHEN the API receives a request via `/api/choreography/generate-from-song` (Path 1), THE API SHALL generate a complete blueprint containing all video generation instructions
2. WHEN the API receives a request via `/api/choreography/generate-with-ai` (Path 2), THE API SHALL parse the natural language query, generate a complete blueprint containing all video generation instructions
3. WHEN the job container starts, THE Job Container SHALL receive the blueprint as a JSON parameter via the BLUEPRINT_JSON environment variable
4. THE Job Container SHALL NOT perform audio analysis, move searching, or choreography generation
5. THE Job Container SHALL ONLY assemble videos according to the blueprint specifications
6. THE Blueprint SHALL include song paths, video clip paths, timing information, and transition specifications
7. BOTH user paths SHALL use the same blueprint schema and job container implementation

### Requirement 2: Elasticsearch Removal

**User Story:** As a developer, I want to remove Elasticsearch dependency from the job container, so that the container is simpler and has fewer dependencies.

#### Acceptance Criteria

1. THE Job Container SHALL NOT depend on Elasticsearch client libraries
2. THE Job Container SHALL NOT connect to Elasticsearch services
3. THE API/Backend SHALL perform all vector search operations in-memory
4. THE API/Backend SHALL use numpy or similar libraries for vector similarity calculations
5. THE docker-compose.yml SHALL NOT include Elasticsearch service for job container operation

### Requirement 3: Minimal Job Container Dependencies

**User Story:** As a DevOps engineer, I want the job container to have minimal dependencies, so that it builds faster and uses less memory.

#### Acceptance Criteria

1. THE Job Container SHALL include ONLY these dependencies: FFmpeg, psycopg2-binary, google-cloud-storage, python-dotenv
2. THE Job Container SHALL NOT include Django, DRF, Elasticsearch, Librosa, NumPy, SciPy, or ML libraries
3. THE Job Container Dockerfile SHALL be optimized for size and build speed
4. THE Job Container SHALL use python:3.12-slim base image
5. THE Job Container build time SHALL be under 2 minutes

### Requirement 4: Dual Storage Support

**User Story:** As a developer, I want the job container to work with both local filesystem and Google Cloud Storage, so that it works in development and production environments.

#### Acceptance Criteria

1. WHEN running locally, THE Job Container SHALL read video clips from the data/ directory
2. WHEN running in GCP, THE Job Container SHALL read video clips from Google Cloud Storage buckets
3. WHEN running locally, THE Job Container SHALL write output videos to the data/ directory
4. WHEN running in GCP, THE Job Container SHALL write output videos to Google Cloud Storage buckets
5. THE Storage Service SHALL automatically detect the environment and use the appropriate storage backend

### Requirement 5: Blueprint JSON Schema

**User Story:** As an API developer, I want a well-defined blueprint schema, so that I can generate valid blueprints that the job container can process.

#### Acceptance Criteria

1. THE Blueprint SHALL include a "task_id" field identifying the choreography task
2. THE Blueprint SHALL include a "song" object with path, title, artist, duration, and bpm
3. THE Blueprint SHALL include a "clips" array with video clip specifications
4. EACH Clip Specification SHALL include video_path, start_time, duration, and transition_type
5. THE Blueprint SHALL include a "metadata" object with difficulty, energy_level, style, and created_at

### Requirement 6: API Blueprint Generation for Both User Paths

**User Story:** As an API, I want to generate blueprints with vector search for both "Select Song" and "Describe Choreo" paths, so that I can select the best dance moves for each request.

#### Acceptance Criteria

1. WHEN a "Select Song" request is received via `/api/choreography/generate-from-song`, THE API SHALL retrieve the song from the database and analyze the audio file
2. WHEN a "Describe Choreo" request is received via `/api/choreography/generate-with-ai`, THE API SHALL parse the natural language query with Gemini AI to extract parameters, then analyze the audio file
3. THE API SHALL perform in-memory vector search to find matching dance moves for BOTH paths
4. THE API SHALL use cosine similarity for vector comparisons
5. THE API SHALL generate a choreography sequence based on music features using Gemini AI for BOTH paths
6. THE API SHALL create a complete blueprint JSON document with the same schema for BOTH paths
7. THE API SHALL store the blueprint in the database linked to the ChoreographyTask

### Requirement 7: Job Container Video Assembly

**User Story:** As a job container, I want to assemble videos from blueprints, so that I can generate the final choreography video.

#### Acceptance Criteria

1. WHEN the job starts, THE Job Container SHALL parse the blueprint JSON
2. THE Job Container SHALL fetch the song audio file from storage
3. THE Job Container SHALL fetch all video clip files from storage
4. THE Job Container SHALL use FFmpeg to concatenate clips with the audio track
5. THE Job Container SHALL apply transitions between clips as specified in the blueprint

### Requirement 8: Database Integration

**User Story:** As a job container, I want to update task status in the database, so that the API can track job progress.

#### Acceptance Criteria

1. THE Job Container SHALL connect to PostgreSQL database
2. THE Job Container SHALL update task status to "running" when starting
3. THE Job Container SHALL update task progress percentage during video assembly
4. THE Job Container SHALL update task status to "completed" with result metadata when successful
5. THE Job Container SHALL update task status to "failed" with error message when unsuccessful

### Requirement 9: Error Handling

**User Story:** As a system, I want comprehensive error handling, so that failures are logged and reported correctly.

#### Acceptance Criteria

1. WHEN a blueprint is invalid, THE Job Container SHALL log the validation error and fail gracefully
2. WHEN a video clip is missing, THE Job Container SHALL log the missing file and fail gracefully
3. WHEN FFmpeg fails, THE Job Container SHALL log the FFmpeg error and fail gracefully
4. WHEN storage access fails, THE Job Container SHALL retry up to 3 times before failing
5. ALL errors SHALL be logged to stdout and recorded in the database

### Requirement 10: Performance Requirements

**User Story:** As a user, I want fast video generation, so that I can see my choreography quickly.

#### Acceptance Criteria

1. THE Job Container SHALL start processing within 5 seconds of receiving the blueprint
2. THE Job Container SHALL assemble a 3-minute video in under 30 seconds
3. THE Job Container SHALL use less than 512MB of memory during video assembly
4. THE API SHALL generate a blueprint in under 10 seconds for a 3-minute song
5. THE complete flow (API + Job) SHALL complete in under 60 seconds for a 3-minute song

### Requirement 11: Testing Requirements

**User Story:** As a developer, I want comprehensive tests, so that I can verify the system works correctly.

#### Acceptance Criteria

1. THE System SHALL include unit tests for blueprint generation
2. THE System SHALL include unit tests for video assembly
3. THE System SHALL include integration tests for the complete flow
4. THE System SHALL include tests for both local and GCS storage modes
5. THE Test suite SHALL achieve at least 80% code coverage

### Requirement 12: Documentation Requirements

**User Story:** As a developer, I want clear documentation, so that I can understand and maintain the system.

#### Acceptance Criteria

1. THE System SHALL include a blueprint schema documentation file
2. THE System SHALL include API endpoint documentation for blueprint generation
3. THE System SHALL include job container usage documentation
4. THE System SHALL include examples of valid blueprints
5. THE System SHALL include troubleshooting guide for common issues
