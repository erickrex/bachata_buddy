# Requirements Document

## Introduction

This specification defines the integration of video generation functionality from the separate job container into the main Django backend. The goal is to simplify the system architecture by eliminating the need for a separate container, job queues, and asynchronous job orchestration. Video generation will become a synchronous, blocking operation that executes immediately when a user requests choreography generation.

This is a clean-cut migration with no backward compatibility requirements. The job container and related abstractions will be completely removed.

The current architecture uses:
- Django backend for API and blueprint generation
- Separate job container for video assembly (FFmpeg operations)
- Job service abstraction (mock/AWS/Celery modes)
- Asynchronous polling for task status

The new architecture will:
- Move video assembly logic directly into the Django backend
- Execute video generation synchronously within the request
- Maintain blueprint generation as a separate step
- Simplify deployment to a single container

## Glossary

- **Backend**: The Django REST API application that handles choreography requests
- **Blueprint**: A JSON document containing all video assembly instructions (moves, timing, audio path, output configuration)
- **Video Assembly**: The process of concatenating video clips with audio using FFmpeg to produce the final choreography video
- **FFmpeg**: Command-line tool for video/audio processing
- **Blocking Request**: An HTTP request that waits for the complete operation to finish before returning a response
- **Storage Service**: Abstraction layer for file storage (local filesystem or S3)
- **UV**: Fast Python package installer and resolver used for dependency management
- **pyproject.toml**: Standard Python project configuration file for dependencies and build settings

## Requirements

### Requirement 1

**User Story:** As a user, I want my choreography video to be generated immediately when I submit a request, so that I don't have to poll for status updates.

#### Acceptance Criteria

1. WHEN a user submits a choreography generation request THEN the Backend SHALL generate the blueprint and assemble the video within the same HTTP request
2. WHEN video assembly completes successfully THEN the Backend SHALL return the video URL directly in the response
3. WHEN video assembly fails THEN the Backend SHALL return an error response with details about the failure
4. IF the video assembly takes longer than 10 minutes THEN the Backend SHALL timeout and return an error response

### Requirement 2

**User Story:** As a developer, I want the video assembly code integrated into the backend, so that I only need to deploy and maintain a single container.

#### Acceptance Criteria

1. THE Backend SHALL include a VideoAssemblyService that performs FFmpeg-based video concatenation
2. THE Backend SHALL include an FFmpegCommandBuilder that constructs FFmpeg commands for video operations
3. WHEN the VideoAssemblyService is initialized THEN the Backend SHALL verify FFmpeg is available in the system PATH
4. THE Backend SHALL reuse the existing storage service abstraction for downloading source files and uploading results

### Requirement 3

**User Story:** As a developer, I want the video assembly to use the same blueprint format, so that the integration is straightforward and testable.

#### Acceptance Criteria

1. THE Backend SHALL accept blueprints in the existing JSON format containing task_id, audio_path, moves array, and output_config
2. WHEN processing a blueprint THEN the Backend SHALL validate all required fields before starting assembly
3. WHEN a blueprint contains invalid paths THEN the Backend SHALL reject the blueprint with a descriptive error
4. THE Backend SHALL serialize blueprints to JSON and deserialize them back to equivalent objects (round-trip consistency)

### Requirement 4

**User Story:** As a user, I want to see progress updates during video generation, so that I know the system is working.

#### Acceptance Criteria

1. WHEN video assembly is in progress THEN the Backend SHALL update the task record with current stage and progress percentage
2. THE Backend SHALL report progress through stages: fetching (20%), concatenating (50%), adding_audio (70%), uploading (85%), cleanup (95%), completed (100%)
3. WHEN an error occurs during any stage THEN the Backend SHALL update the task record with the error details

### Requirement 5

**User Story:** As a developer, I want to remove the job service abstraction, so that the codebase is simpler.

#### Acceptance Criteria

1. THE Backend SHALL remove the JobsService class and its mock/AWS/Celery modes
2. THE Backend SHALL remove the job_execution_name field usage from ChoreographyTask
3. WHEN a choreography request is received THEN the Backend SHALL call the VideoAssemblyService directly instead of creating a job execution

### Requirement 6

**User Story:** As a developer, I want the video assembly to handle errors gracefully, so that users get meaningful feedback.

#### Acceptance Criteria

1. IF FFmpeg is not available THEN the Backend SHALL return an error indicating FFmpeg is required
2. IF a source video file cannot be downloaded THEN the Backend SHALL return an error with the file path that failed
3. IF FFmpeg concatenation fails THEN the Backend SHALL return the FFmpeg error output
4. IF the output file upload fails THEN the Backend SHALL return an error with upload details
5. WHEN any error occurs THEN the Backend SHALL clean up temporary files before returning

### Requirement 7

**User Story:** As a developer, I want a simplified API that returns the video directly, so that the frontend can be updated to use the new synchronous flow.

#### Acceptance Criteria

1. THE Backend SHALL provide a /api/choreography/generate/ endpoint that accepts song_id and parameters
2. WHEN video generation completes THEN the Backend SHALL return the video_url directly in the response body
3. THE Backend SHALL remove the task polling endpoints as they are no longer needed
4. THE Backend SHALL remove the job_execution_name field from the ChoreographyTask model

### Requirement 8

**User Story:** As a developer, I want the video assembly to work with both local and S3 storage, so that it works in development and production.

#### Acceptance Criteria

1. WHEN STORAGE_BACKEND is set to 'local' THEN the Backend SHALL download and upload files using the local filesystem
2. WHEN STORAGE_BACKEND is set to 's3' THEN the Backend SHALL download and upload files using AWS S3
3. THE Backend SHALL use temporary directories for intermediate files during assembly
4. WHEN assembly completes THEN the Backend SHALL clean up all temporary files

### Requirement 9

**User Story:** As a developer, I want to use UV and pyproject.toml for Python dependency management, so that the project follows modern Python standards.

#### Acceptance Criteria

1. THE Backend SHALL use pyproject.toml as the single source of truth for Python dependencies
2. THE Backend SHALL use UV as the package installer and resolver
3. THE Backend SHALL remove requirements.txt files in favor of pyproject.toml
4. WHEN adding new dependencies THEN the developer SHALL use UV commands to update pyproject.toml

### Requirement 10

**User Story:** As a developer, I want the job container code to be completely removed, so that there is no confusion about which code is active.

#### Acceptance Criteria

1. THE Backend SHALL delete the job/ directory and all its contents
2. THE Backend SHALL delete the jobs_service.py file
3. THE Backend SHALL remove all references to Cloud Run Jobs, ECS tasks, and Celery
4. THE Backend SHALL update docker-compose.yml to remove the job container service
