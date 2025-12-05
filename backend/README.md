# Bachata Buddy Backend

Django REST API for AI-powered Bachata choreography generation.

## Technology Stack

- **Django 5.2** + Django REST Framework
- **PostgreSQL 15+** - Database
- **OpenAI GPT-4** - AI orchestration
- **Librosa** - Audio analysis
- **FFmpeg** - Video processing
- **UV** - Python package manager
- **Gunicorn** - Production server

## Quick Start

### Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec backend uv run python manage.py migrate

# Create superuser
docker-compose exec backend uv run python manage.py createsuperuser

# View logs
docker-compose logs -f backend

# Access API
# http://localhost:8000
# http://localhost:8000/api/schema/swagger-ui/
```

### Native Development

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
cd backend
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
uv run python manage.py migrate

# Start server
uv run python manage.py runserver
```

## ⚠️ Important: Always Use UV

This project uses **UV** for all Python operations:

```bash
# ✅ Correct
uv sync                              # Install dependencies
uv add django-cors-headers           # Add package
uv run python manage.py migrate      # Run Django commands
uv run pytest                        # Run tests

# ❌ Wrong
pip install                          # Don't use pip
python manage.py migrate             # Don't use python directly
pytest                               # Don't run pytest directly
```

## Project Structure

```
backend/
├── api/                    # Django settings & URLs
├── apps/                   # Django apps
│   ├── authentication/     # User auth
│   ├── choreography/       # Choreography generation
│   ├── collections/        # User collections
│   └── instructors/        # Instructor features
├── services/               # Business logic
│   ├── agent_service.py              # OpenAI orchestration
│   ├── blueprint_generator.py        # Choreography planning
│   ├── parameter_extractor.py        # NLP extraction
│   ├── vector_search_service.py      # Move search
│   ├── video_assembly_service.py     # Video processing
│   ├── ffmpeg_builder.py             # FFmpeg commands
│   └── storage_service.py            # File storage
├── data/                   # Media files
│   ├── Bachata_steps/      # Video clips
│   └── songs/              # Audio files
├── pyproject.toml          # Dependencies
└── manage.py               # Django management
```

## Environment Variables

### Required Variables

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
ENVIRONMENT=local

# Database
DB_NAME=bachata_buddy
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# OpenAI
OPENAI_API_KEY=sk-proj-your-key-here

# Agent Configuration
AGENT_ENABLED=True
AGENT_TIMEOUT=300

# Storage
STORAGE_BACKEND=local  # or 's3' for production

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

See `.env.example` for all available variables.

## API Endpoints

### Authentication

```
POST /api/auth/register/     - Register user
POST /api/auth/login/        - Login (get JWT)
POST /api/auth/refresh/      - Refresh token
GET  /api/auth/profile/      - Get profile
```

### Choreography Generation

**Path 1: Song Selection**
```
GET  /api/choreography/songs/                    - List songs
GET  /api/choreography/songs/{id}/               - Song details
POST /api/choreography/generate-from-song/       - Generate
```

**Path 2: AI Description**
```
POST /api/choreography/describe/                 - AI generation
POST /api/choreography/parse-query/              - Parse NL query
```

**Task Management**
```
GET  /api/choreography/tasks/                    - List tasks
GET  /api/choreography/tasks/{id}/               - Task status
POST /api/choreography/tasks/{id}/cancel/        - Cancel task
```

### Collections

```
GET    /api/collections/                - List collections
POST   /api/collections/save/           - Save choreography
GET    /api/collections/{id}/           - Get details
DELETE /api/collections/{id}/           - Delete
GET    /api/collections/stats/          - Statistics
```

### Interactive Docs

- **Swagger UI:** http://localhost:8000/api/schema/swagger-ui/
- **OpenAPI Schema:** http://localhost:8000/api/schema/

## OpenAI Agent Orchestration

### Overview

The system uses OpenAI function calling for intelligent workflow orchestration:

1. User describes choreography in natural language
2. OpenAI extracts parameters (difficulty, style, energy)
3. Agent orchestrates workflow autonomously
4. Functions called: analyze_music → search_moves → generate_blueprint → assemble_video

### Configuration

```bash
# .env
OPENAI_API_KEY=sk-proj-your-key-here
AGENT_ENABLED=True
AGENT_TIMEOUT=300
```

### Usage

```bash
curl -X POST http://localhost:8000/api/choreography/describe/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Create a romantic beginner choreography"
  }'
```

### Testing

```bash
# Test parameter extraction
uv run pytest services/test_parameter_extractor_properties.py

# Test agent service
uv run pytest services/test_agent_service_properties.py

# Full integration test
uv run pytest apps/choreography/test_e2e_integration.py
```

## Video Generation

### Synchronous Processing

Video generation happens synchronously within HTTP requests:

1. **Blueprint Generation** - AI selects moves and creates plan
2. **Video Assembly** - FFmpeg concatenates clips
3. **Audio Sync** - Add audio track
4. **Upload** - Save to storage
5. **Cleanup** - Remove temp files

### Progress Stages

```
pending (0%) → fetching (20%) → concatenating (50%) → 
adding_audio (70%) → uploading (85%) → cleanup (95%) → 
completed (100%)
```

### API Response

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "video_url": "https://storage.example.com/output/video.mp4",
  "duration_seconds": 45.2,
  "progress": 100
}
```

## Database

### PostgreSQL Configuration

**Local Development:**
```bash
DB_HOST=db              # Docker Compose
DB_HOST=localhost       # Native development
DB_PORT=5432
```

**Production (AWS RDS):**
```bash
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_PORT=5432
DB_SSLMODE=require
```

### Migrations

```bash
# Create migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Show migration status
uv run python manage.py showmigrations
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=apps --cov=services --cov-report=html

# Run specific tests
uv run pytest apps/choreography/tests/

# Run property-based tests
uv run pytest services/test_*_properties.py
```

## Storage

### Local Storage (Development)

```bash
# Audio files
backend/data/songs/

# Video clips
backend/data/Bachata_steps/

# Generated videos
backend/data/output/
```

### S3 Storage (Production)

```bash
# Environment variables
STORAGE_BACKEND=s3
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_REGION=us-east-1
```

## Deployment

### Docker Build

```bash
# Build production image
docker build -t bachata-backend .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e DB_HOST=your-db-host \
  bachata-backend
```

### AWS App Runner

```bash
# Push to ECR
docker tag bachata-backend:latest \
  123456789.dkr.ecr.us-east-1.amazonaws.com/bachata-backend:latest

docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/bachata-backend:latest

# Deploy via AWS Console or CDK
```

See `DEPLOYMENT.md` for detailed instructions.

## Common Issues

### OpenAI API Errors

```bash
# Verify API key
docker-compose exec backend env | grep OPENAI_API_KEY

# Test connection
docker-compose exec backend uv run python -c "
import openai
import os
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
response = client.chat.completions.create(
    model='gpt-4o-mini',
    messages=[{'role': 'user', 'content': 'Hello'}]
)
print(response.choices[0].message.content)
"
```

### Database Connection

```bash
# Check database
docker-compose exec postgres psql -U postgres -d bachata_buddy

# Verify connection
docker-compose exec backend uv run python manage.py dbshell
```

### FFmpeg Issues

```bash
# Verify FFmpeg
docker-compose exec backend ffmpeg -version

# Test video processing
docker-compose exec backend uv run python -c "
import subprocess
result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
print(result.stdout.decode())
"
```

## Development Tips

### Adding Dependencies

```bash
# Add package
uv add package-name

# Add dev dependency
uv add --dev pytest-django

# Update all dependencies
uv sync --upgrade
```

### Database Reset

```bash
# Drop and recreate database
docker-compose down -v
docker-compose up -d
docker-compose exec backend uv run python manage.py migrate
```

### Load Sample Data

```bash
# Load songs
docker-compose exec backend uv run python manage.py loaddata songs

# Create test user
docker-compose exec backend uv run python manage.py createsuperuser
```

## Architecture

```
User Request
    ↓
Django REST API
    ↓
OpenAI Agent (orchestrates)
    ↓
Services (music analysis, move selection, video assembly)
    ↓
PostgreSQL (store results)
    ↓
Response (video URL)
```

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Parameter Extraction | 1-2s | OpenAI API |
| Music Analysis | 2-3s | Librosa |
| Move Selection | <1s | Database query |
| Blueprint Generation | <1s | JSON creation |
| Video Assembly | 30-60s | FFmpeg processing |
| **Total** | **35-70s** | End-to-end |

## Contributing

1. Use UV for all Python operations
2. Follow Django best practices
3. Write tests for new features
4. Update API documentation
5. Keep services focused and small

## License

[Your License]
