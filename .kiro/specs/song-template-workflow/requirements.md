# Requirements Document

## Introduction

This specification defines the requirements for implementing the "Select Song Template" workflow in the REST API. This workflow allows users to select from pre-existing songs stored in the system and generate choreography videos based on those songs with a selected difficulty level. This is a migration of Workflow #1 from the legacy Django monolith application.

## Glossary

- **Song Template**: A pre-existing audio file stored locally or in Google Cloud Storage (GCS) with associated metadata (title, artist, duration, BPM, etc.)
- **REST API**: The Django REST Framework API service (backend application) that handles HTTP requests
- **Choreography Generation**: The process of creating a dance video by selecting moves and stitching video clips
- **Cloud Run Job**: The asynchronous video processing service that generates choreography videos
- **GCS**: Google Cloud Storage, where audio files and generated videos are stored in production
- **Local Storage**: File system storage used for development and testing before GCS deployment
- **Backend Application**: The Django REST API service located in the `/backend` directory

## Scope

**In Scope:**
- All work is limited to the `/backend` application directory
- Local development environment with file system storage
- Production environment with Google Cloud Storage
- REST API endpoints and database models

**Out of Scope:**
- Frontend application changes
- Legacy monolith application
- Job processing service (except parameter passing)
- Deployment configuration

## Requirements

### Requirement 1: List Available Songs

**User Story:** As a user, I want to view a list of available songs, so that I can select one to generate a choreography video.

#### Acceptance Criteria

1. WHEN a user requests the songs list, THE REST API SHALL return a paginated list of available songs
2. THE REST API SHALL include song metadata (title, artist, duration, BPM, genre) in the response
3. THE REST API SHALL support filtering songs by genre, BPM range, and duration
4. THE REST API SHALL support searching songs by title or artist name
5. THE REST API SHALL order songs by title ascending by default

### Requirement 2: Get Song Details

**User Story:** As a user, I want to view detailed information about a specific song, so that I can make an informed decision before generating choreography.

#### Acceptance Criteria

1. WHEN a user requests a specific song by ID, THE REST API SHALL return complete song metadata
2. THE REST API SHALL include the GCS path to the audio file in the response
3. IF the song does not exist, THEN THE REST API SHALL return a 404 error
4. THE REST API SHALL validate that the user is authenticated before returning song details

### Requirement 3: Generate Choreography from Song Template

**User Story:** As a user, I want to generate a choreography video from a selected song template with my chosen difficulty level, so that I can create personalized dance content.

#### Acceptance Criteria

1. WHEN a user submits a generation request with song ID and difficulty, THE REST API SHALL create a choreography task
2. THE REST API SHALL validate that the song ID exists before creating the task
3. THE REST API SHALL validate that the difficulty is one of: beginner, intermediate, advanced
4. THE REST API SHALL trigger a Cloud Run Job with the song's GCS path and difficulty level
5. THE REST API SHALL return the task ID and polling URL immediately (202 Accepted)

### Requirement 4: Remove YouTube URL Support

**User Story:** As a developer, I want to remove the incomplete YouTube URL download functionality, so that the API only supports fully implemented features.

#### Acceptance Criteria

1. THE REST API SHALL remove the `/api/choreography/generate/` endpoint that accepts arbitrary audio URLs
2. THE REST API SHALL remove the `ChoreographyGenerationSerializer` that validates YouTube URLs
3. THE REST API SHALL remove any YouTube-related validation logic from the codebase
4. THE REST API SHALL remove any unused dependencies related to YouTube downloading from pyproject.toml
5. THE REST API SHALL update API documentation to reflect the removed endpoint

### Requirement 5: Song Data Model with Dual Storage Support

**User Story:** As a developer, I want a database model to store song metadata with support for both local and GCS storage, so that songs can be tested locally before production deployment.

#### Acceptance Criteria

1. THE REST API SHALL define a Song model with fields: id, title, artist, duration, bpm, genre, audio_path, created_at, updated_at
2. THE REST API SHALL support local file paths (e.g., "songs/bachata-song.mp3") for development
3. THE REST API SHALL support GCS paths (e.g., "gs://bucket/songs/bachata-song.mp3") for production
4. THE REST API SHALL create database migrations for the Song model
5. THE REST API SHALL add database indexes on title and artist fields for search performance

### Requirement 6: Maintain AI Workflow

**User Story:** As a user, I want to continue using the natural language "Describe Choreo" workflow, so that I can generate choreography using text descriptions.

#### Acceptance Criteria

1. THE REST API SHALL maintain the `/api/choreography/parse-query/` endpoint without changes
2. THE REST API SHALL maintain the `/api/choreography/generate-with-ai/` endpoint without changes
3. THE REST API SHALL ensure the AI workflow continues to function after removing the YouTube endpoint
4. THE REST API SHALL keep the `QueryParseSerializer` and `AIGenerationSerializer` unchanged
5. THE REST API SHALL preserve all Gemini AI integration code

### Requirement 7: Task Management Compatibility

**User Story:** As a user, I want to track the status of choreography generation tasks regardless of which workflow I used, so that I have a consistent experience.

#### Acceptance Criteria

1. THE REST API SHALL use the existing ChoreographyTask model for song template workflow
2. THE REST API SHALL maintain the `/api/choreography/tasks/` list endpoint without changes
3. THE REST API SHALL maintain the `/api/choreography/tasks/{id}/` detail endpoint without changes
4. THE REST API SHALL ensure task status updates work identically for both workflows
5. THE REST API SHALL store the song ID reference in the task for song template workflow

### Requirement 8: API Documentation and OpenAPI Fix

**User Story:** As an API consumer, I want clear and functional documentation for the song template endpoints, so that I can integrate them into my application.

#### Acceptance Criteria

1. THE REST API SHALL provide OpenAPI/Swagger documentation for all song endpoints
2. THE REST API SHALL include request/response examples for each endpoint
3. THE REST API SHALL document all query parameters for filtering and pagination
4. THE REST API SHALL update the API README with song template workflow examples
5. THE REST API SHALL remove documentation for the deleted `/api/choreography/generate/` endpoint

### Requirement 9: Fix OpenAPI/Swagger UI

**User Story:** As a developer, I want the Swagger UI to work correctly with the right server URLs, so that I can test API endpoints interactively.

#### Acceptance Criteria

1. THE REST API SHALL configure Swagger UI to use the correct server URL (http://localhost:8001 for local development)
2. THE REST API SHALL ensure all API endpoints are accessible and testable through Swagger UI
3. THE REST API SHALL fix any CORS issues preventing Swagger UI from making requests
4. THE REST API SHALL validate that the OpenAPI schema generation uses the correct port mapping
5. THE REST API SHALL test that authentication works correctly in Swagger UI

### Requirement 10: Local Development Priority

**User Story:** As a developer, I want to develop and test all functionality locally first, so that I can iterate quickly without cloud dependencies.

#### Acceptance Criteria

1. THE REST API SHALL store song audio files in the local file system during development
2. THE REST API SHALL provide sample song data for local testing
3. THE REST API SHALL include comprehensive unit and integration tests that run locally
4. THE REST API SHALL document the local development setup in the README
5. WHEN deploying to production, THEN THE REST API SHALL seamlessly switch to GCS storage
