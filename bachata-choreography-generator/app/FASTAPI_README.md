# Bachata Choreography Generator - FastAPI Web Application

This document describes the FastAPI web application for the Bachata Choreography Generator, which provides a complete web interface for generating dance choreographies from YouTube videos with user authentication, collection management, and instructor features.

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- All dependencies installed via `uv` (see main README)
- Move clips and annotations data in place
- Database initialized (run `python init_database.py`)

### Starting the Server

```bash
# Option 1: Direct uvicorn command (recommended)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Option 2: Python module
python main.py
```

The server will be available at:
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Instructor Dashboard**: http://localhost:8000/instructor

## 📋 API Endpoints

### Authentication Endpoints

#### `POST /api/auth/register`
- **Description**: Register a new user account
- **Request Body** (Form data):
  ```
  email: user@example.com
  password: securepassword
  display_name: John Doe
  is_instructor: false
  ```
- **Response**:
  ```json
  {
    "user": {
      "id": "uuid-string",
      "email": "user@example.com",
      "display_name": "John Doe",
      "is_instructor": false,
      "created_at": "2024-01-01T00:00:00Z"
    },
    "tokens": {
      "access_token": "jwt-token",
      "refresh_token": "refresh-token",
      "expires_in": 3600
    }
  }
  ```

#### `POST /api/auth/login`
- **Description**: Authenticate user and create session
- **Request Body** (Form data):
  ```
  email: user@example.com
  password: securepassword
  ```
- **Response**: Same as register response
- **Features**: Rate limiting protection

#### `POST /api/auth/logout`
- **Description**: Log out current user (client-side token removal)
- **Authentication**: Required

#### `GET /api/auth/profile`
- **Description**: Get current user profile information
- **Authentication**: Required
- **Response**:
  ```json
  {
    "id": "uuid-string",
    "email": "user@example.com",
    "display_name": "John Doe",
    "is_instructor": false,
    "created_at": "2024-01-01T00:00:00Z"
  }
  ```

#### `PUT /api/auth/profile`
- **Description**: Update user profile (display name and/or password)
- **Authentication**: Required
- **Request Body** (JSON):
  ```json
  {
    "display_name": "New Name",
    "new_password": "newpassword"
  }
  ```

#### `GET /api/auth/me`
- **Description**: Alternative endpoint to get current user info
- **Authentication**: Required

#### `GET /api/auth/status`
- **Description**: Check authentication status
- **Response**:
  ```json
  {
    "authenticated": true,
    "user": { /* user object */ }
  }
  ```

#### `GET /api/auth/preferences`
- **Description**: Get user preferences (auto-save settings)
- **Authentication**: Required
- **Response**:
  ```json
  {
    "preferences": {
      "auto_save_choreographies": true
    }
  }
  ```

#### `PUT /api/auth/preferences`
- **Description**: Update user preferences
- **Authentication**: Required
- **Request Body** (JSON):
  ```json
  {
    "auto_save_choreographies": false
  }
  ```

### Choreography Generation Endpoints

#### `POST /api/choreography`
- **Description**: Start choreography generation from YouTube URL
- **Authentication**: Required
- **Request Body** (Form data):
  ```
  youtube_url: https://www.youtube.com/watch?v=...
  difficulty: intermediate
  quality_mode: balanced
  energy_level: medium
  auto_save: true
  ```
- **Response**:
  ```json
  {
    "task_id": "uuid-string",
    "status": "started",
    "message": "Choreography generation started. Use the task ID to track progress."
  }
  ```

#### `GET /api/task/{task_id}`
- **Description**: Get task status and progress
- **Response**:
  ```json
  {
    "task_id": "uuid-string",
    "status": "running",
    "progress": 45,
    "stage": "analyzing",
    "message": "Analyzing musical structure and tempo...",
    "result": null,
    "error": null
  }
  ```

#### `GET /api/task/progress`
- **Description**: Get progress for most recent active task (HTMX polling)
- **Returns**: HTML with JavaScript for real-time updates

#### `GET /api/tasks`
- **Description**: List all active tasks with automatic cleanup
- **Response**:
  ```json
  {
    "total_tasks": 3,
    "running_tasks": 1,
    "completed_tasks": 1,
    "failed_tasks": 1,
    "tasks": { /* task details */ }
  }
  ```

#### `DELETE /api/task/{task_id}`
- **Description**: Remove task from tracking
- **Response**:
  ```json
  {
    "message": "Task removed from tracking",
    "task_id": "uuid-string",
    "previous_status": "completed"
  }
  ```

#### `POST /api/validate/youtube`
- **Description**: Validate YouTube URL without starting generation
- **Request Body** (JSON):
  ```json
  {
    "url": "https://www.youtube.com/watch?v=..."
  }
  ```
- **Response**:
  ```json
  {
    "valid": true,
    "message": "URL is valid",
    "details": {
      "title": "Song Title",
      "duration": 180,
      "thumbnail": "https://..."
    }
  }
  ```

#### `GET /api/video/{filename}`
- **Description**: Serve generated choreography videos
- **Features**: User-specific file serving, security validation, streaming headers
- **Returns**: MP4 video file

### Collection Management Endpoints

#### `POST /api/collection/save`
- **Description**: Save a generated choreography to user's collection
- **Authentication**: Required
- **Request Body** (JSON):
  ```json
  {
    "title": "My Bachata Choreography",
    "video_path": "/path/to/video.mp4",
    "thumbnail_path": "/path/to/thumbnail.jpg",
    "difficulty": "intermediate",
    "duration": 120,
    "music_info": {
      "youtube_url": "https://www.youtube.com/watch?v=...",
      "title": "Song Title",
      "duration": 180,
      "tempo": 120,
      "energy_level": "medium"
    },
    "generation_parameters": {
      "quality_mode": "balanced",
      "processing_time": 45.2,
      "moves_analyzed": 150
    }
  }
  ```
- **Response**:
  ```json
  {
    "id": "uuid-string",
    "title": "My Bachata Choreography",
    "created_at": "2024-01-01T00:00:00Z",
    "message": "Choreography saved successfully"
  }
  ```

#### `GET /api/collection`
- **Description**: Get user's choreography collection with pagination and filtering
- **Authentication**: Required
- **Query Parameters**:
  - `page`: Page number (default: 1)
  - `limit`: Items per page (default: 20, max: 100)
  - `difficulty`: Filter by difficulty level
  - `search`: Search in titles and music info
  - `sort_by`: Sort field (default: created_at)
  - `sort_order`: Sort order (asc/desc, default: desc)
- **Response**:
  ```json
  {
    "choreographies": [
      {
        "id": "uuid-string",
        "title": "My Bachata Choreography",
        "difficulty": "intermediate",
        "duration": 120,
        "created_at": "2024-01-01T00:00:00Z",
        "thumbnail_path": "/path/to/thumbnail.jpg",
        "music_info": { /* music details */ }
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 5,
      "pages": 1
    }
  }
  ```

#### `GET /api/collection/list`
- **Description**: Alternative endpoint for listing choreographies
- **Authentication**: Required
- **Parameters**: Same as `/api/collection`

#### `GET /api/collection/{choreography_id}`
- **Description**: Get specific choreography details
- **Authentication**: Required
- **Response**: Full choreography object with metadata

#### `PUT /api/collection/{choreography_id}`
- **Description**: Update choreography metadata
- **Authentication**: Required
- **Request Body** (JSON):
  ```json
  {
    "title": "Updated Title",
    "difficulty": "advanced"
  }
  ```

#### `DELETE /api/collection/{choreography_id}`
- **Description**: Delete choreography from collection
- **Authentication**: Required
- **Response**:
  ```json
  {
    "message": "Choreography deleted successfully",
    "id": "uuid-string"
  }
  ```

### Instructor Dashboard Endpoints

#### `POST /api/instructor/class-plans`
- **Description**: Create a new class plan
- **Authentication**: Required (instructor privileges)
- **Request Body** (JSON):
  ```json
  {
    "title": "Beginner Bachata Class",
    "description": "Introduction to basic bachata steps",
    "duration_minutes": 60,
    "difficulty_level": "beginner",
    "choreography_ids": ["uuid1", "uuid2"]
  }
  ```
- **Response**:
  ```json
  {
    "id": "uuid-string",
    "title": "Beginner Bachata Class",
    "created_at": "2024-01-01T00:00:00Z",
    "message": "Class plan created successfully"
  }
  ```

#### `GET /api/instructor/class-plans`
- **Description**: List instructor's class plans
- **Authentication**: Required (instructor privileges)

#### `GET /api/instructor/dashboard`
- **Description**: Get instructor dashboard data and statistics
- **Authentication**: Required (instructor privileges)

### Utility Endpoints

#### `GET /health`
- **Description**: Comprehensive health check
- **Returns**: System status, resource usage, service availability
- **Response**:
  ```json
  {
    "status": "healthy",
    "version": "0.1.0",
    "timestamp": "1234567890.123",
    "system": {
      "memory_percent": 45.2,
      "memory_available_gb": 8.5,
      "disk_percent": 23.1,
      "disk_free_gb": 156.7
    },
    "services": {
      "youtube_service": true,
      "active_tasks": 2,
      "pipeline_cache_enabled": true
    },
    "system_validation": {
      "valid": true,
      "issues_count": 0,
      "warnings_count": 1
    }
  }
  ```

#### `GET /api/system/status`
- **Description**: Detailed system diagnostics
- **Response**: Extended system information including pipeline status

#### `GET /api/videos`
- **Description**: List available video files
- **Response**:
  ```json
  {
    "videos": [
      {
        "filename": "choreography_001.mp4",
        "size": 15728640,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
  ```

#### `GET /api/songs`
- **Description**: List available song files
- **Response**:
  ```json
  {
    "songs": [
      {
        "filename": "song_001.mp3",
        "size": 5242880,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
  ```

## 🎛️ Configuration Options

### Request Parameters

#### `difficulty`
- **Options**: `"beginner"`, `"intermediate"`, `"advanced"`
- **Default**: `"intermediate"`
- **Description**: Target difficulty level for selected moves

#### `quality_mode`
- **Options**: `"fast"`, `"balanced"`, `"high_quality"`
- **Default**: `"balanced"`
- **Description**: Processing quality vs speed trade-off
  - `fast`: 8 moves, 720p, faster processing
  - `balanced`: 12 moves, 720p, good quality
  - `high_quality`: 20 moves, 1080p, best quality

#### `energy_level`
- **Options**: `"low"`, `"medium"`, `"high"`
- **Default**: `"medium"`
- **Description**: Target energy level for choreography

#### `auto_save`
- **Options**: `true`, `false`
- **Default**: `true`
- **Description**: Automatically save generated choreography to user's collection

## 🔒 Security Features

### Authentication & Authorization
- JWT-based authentication with access and refresh tokens
- Role-based access control (user vs instructor privileges)
- Rate limiting on authentication endpoints
- Password hashing with bcrypt
- Session management and token expiration

### Input Validation
- YouTube URL format validation
- Parameter type and range checking
- File path sanitization
- SQL injection prevention via SQLAlchemy ORM

### File Serving Security
- Path traversal prevention
- File type restrictions (video files only)
- Size limitations
- User-specific directory access controls
- Authentication-based file access

### Rate Limiting
- Maximum 3 concurrent choreography generations
- Login attempt rate limiting
- Automatic task cleanup
- Resource monitoring and protection

## 📊 Monitoring & Diagnostics

### Health Monitoring
The `/health` endpoint provides:
- System resource usage (memory, disk)
- Service availability status
- Active task counts
- Pipeline configuration
- System validation results

### Logging
- Structured logging with timestamps
- Error tracking with stack traces
- Performance metrics
- User action auditing
- Request/response logging

### Task Management
- Automatic cleanup of old tasks (1 hour)
- Progress tracking with detailed stages
- Error categorization and user-friendly messages
- Background task processing with comprehensive error handling

## 🎨 Web Interface Features

### User Experience
- Responsive design for mobile/desktop
- Real-time progress updates via HTMX
- Drag-and-drop URL input
- Video player with controls
- User authentication and session management

### Progress Tracking
- Visual progress bar
- Stage-specific messages
- Estimated completion time
- Error recovery options
- Real-time updates without page refresh

### Video Playback
- HTML5 video player
- Streaming support
- Quality adaptation
- Download options
- User-specific video serving

### Collection Management
- Save generated choreographies
- Browse personal collection
- Search and filter capabilities
- Thumbnail previews
- Metadata management

## 🔧 Development

### Testing
```bash
# Test specific components
python -c "from main import app; print('App loaded successfully')"

# Test authentication endpoints
python -m pytest tests/test_auth_endpoints.py

# Test choreography generation
python -m pytest tests/test_choreography_controller.py

# Run all tests
python -m pytest tests/
```

### Adding New Endpoints
1. Add route handler to appropriate controller (`app/controllers/`)
2. Include appropriate error handling
3. Add validation if needed
4. Update this documentation
5. Add tests for new functionality

### Custom Error Types
1. Define in `app/exceptions.py`
2. Add user-friendly messages
3. Include in exception handlers
4. Test error scenarios

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Initialize database
python init_database.py
```

## 📁 File Structure

```
bachata-choreography-generator/
├── main.py                     # FastAPI application entry point
├── init_database.py           # Database initialization
├── app/
│   ├── __init__.py
│   ├── config.py              # Application configuration
│   ├── database.py             # Database connection and session management
│   ├── exceptions.py           # Custom exception classes and handlers
│   ├── validation.py           # Input validation utilities
│   ├── controllers/            # API endpoint controllers
│   │   ├── __init__.py
│   │   ├── base_controller.py  # Base controller class
│   │   ├── auth_controller.py  # Authentication endpoints
│   │   ├── choreography_controller.py  # Choreography generation
│   │   ├── collection_controller.py    # Collection management
│   │   ├── instructor_controller.py   # Instructor dashboard
│   │   └── media_controller.py        # Media serving and utilities
│   ├── middleware/             # Custom middleware
│   │   ├── __init__.py
│   │   └── auth_middleware.py  # JWT authentication middleware
│   ├── models/                 # Data models
│   │   ├── __init__.py
│   │   ├── auth_models.py      # Authentication models
│   │   ├── collection_models.py # Collection models
│   │   ├── database_models.py  # SQLAlchemy database models
│   │   ├── instructor_models.py # Instructor models
│   │   └── video_models.py     # Video processing models
│   ├── services/               # Business logic services
│   │   ├── authentication_service.py
│   │   ├── collection_service.py
│   │   ├── instructor_dashboard_service.py
│   │   ├── choreography_pipeline.py
│   │   ├── music_analyzer.py
│   │   ├── move_analyzer.py
│   │   ├── recommendation_engine.py
│   │   ├── resource_manager.py
│   │   └── [20+ other service files]
│   ├── static/                 # Static assets
│   │   └── logo.png
│   └── templates/              # Jinja2 HTML templates
│       ├── base.html
│       ├── index.html
│       ├── collection.html
│       └── instructor.html
├── data/                       # Data storage
│   ├── temp/                   # Temporary files
│   ├── output/                 # Generated videos
│   ├── cache/                  # Service cache
│   ├── user_collections/       # User-specific collections
│   └── database.db             # SQLite database
├── alembic/                    # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/                       # Test suite
│   ├── test_auth_endpoints.py
│   ├── test_choreography_controller.py
│   ├── test_collection_service.py
│   ├── test_instructor_controller.py
│   └── [30+ other test files]
└── pyproject.toml              # Project dependencies
```

## 🤝 Contributing

When adding new features:
1. Follow existing error handling patterns
2. Add comprehensive validation
3. Include user-friendly error messages
4. Update documentation
5. Add tests for new functionality
6. Ensure authentication requirements are properly implemented
7. Follow the controller-service-model architecture pattern

## 📞 Support

For issues or questions:
1. Check the logs for detailed error information
2. Verify system requirements
3. Test with the health check endpoint
4. Review this documentation
5. Check authentication status with `/api/auth/status`
6. Verify database connectivity

The FastAPI application provides a robust, user-friendly interface for the Bachata Choreography Generator with comprehensive authentication, collection management, instructor features, error handling, security features, and monitoring capabilities.