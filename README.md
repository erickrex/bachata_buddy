# 🎵 Bachata Buddy

An AI-powered Django application that generates personalized Bachata choreographies by analyzing music characteristics and matching them with appropriate dance moves from a curated video library using advanced machine learning techniques.

## 🤖 Machine Learning Architecture

### Model Overview
The system employs a **multi-modal machine learning pipeline** that combines audio analysis, computer vision, and recommendation algorithms to generate contextually appropriate dance choreographies.

**Core ML Components:**
- **Audio Feature Extraction**: Librosa-based spectral analysis with 128-dimensional embeddings
- **Pose Estimation**: MediaPipe-based movement analysis with 384-dimensional pose features  
- **Multi-Modal Fusion**: Feature fusion network combining audio and visual embeddings
- **Similarity Matching**: Cosine similarity-based recommendation engine with pre-computed matrices
- **Sequence Generation**: Temporal alignment algorithm for smooth choreography transitions

## 🏗️ System Architecture & Data Flow

### Architecture Diagram
```mermaid
graph TB
    A[Audio Input] --> B[Music Analyzer]
    V[Video Library] --> C[Move Analyzer]
    B --> D[Audio Features]
    C --> E[Movement Features]
    D --> F[Multi-Modal Fusion]
    E --> F
    F --> G[Recommendation Engine]
    G --> H[Choreography Generator]
    H --> I[Output Video]
```

### Project Structure
```
bachata_buddy/
├── bachata_buddy/          # Django project settings
├── core/                   # Shared services & utilities
│   ├── services/           # 22 ML/business logic services
│   ├── models/             # Pydantic data models
│   └── exceptions.py       # Custom exceptions
├── choreography/           # Choreography generation app
├── users/                  # User management app
├── instructors/            # Instructor features app
├── user_collections/       # Collection management app
├── data/                   # Data files
│   ├── Bachata_steps/      # Video library (38 moves)
│   ├── songs/              # Audio files
│   ├── output/             # Generated choreographies
│   └── cache/              # ML model cache
├── static/                 # Static files (CSS, JS)
├── templates/              # Global templates
└── tests/                  # Unified test suite
    ├── unit/               # Unit tests (no dependencies)
    ├── services/           # Service layer tests
    ├── models/             # Django model tests
    ├── views/              # Django view tests
    ├── forms/              # Django form tests
    └── integration/        # Integration & E2E tests
```

## 🚀 Technical Implementation Highlights

### 🔧 Core Technical Components

#### 1. **Advanced Audio Analysis Engine** 🎼
```python
# Real-time spectral analysis with Bachata-specific optimizations
class MusicAnalyzer:
    - Librosa-based feature extraction (22.05kHz sampling)
    - Multi-scale tempo detection (80-160 BPM Bachata range)
    - Enhanced rhythm pattern recognition for Latin music
    - Musical structure segmentation (intro/verse/chorus/outro)
    - 128D audio embeddings with timbral + harmonic features
```

**Key Innovations:**
- **Bachata-Specific Rhythm Detection**: Custom algorithms for syncopation and guitar patterns
- **Multi-Feature Fusion**: MFCC + Chroma + Spectral + Rhythm features
- **Temporal Segmentation**: Automatic detection of musical sections for choreography mapping
- **Performance**: 2-3 seconds analysis time for full songs

#### 2. **MMPose Couple Detection System** 👯
```python
# Research-grade multi-person pose estimation for partner dancing
class MMPoseCoupleDetector:
    - Detects both lead and follow dancers simultaneously
    - 17 COCO body keypoints + 21 hand keypoints per person
    - IoU-based tracking for consistent person IDs across frames
    - Couple detection rate: >70% of frames with both dancers
    - 512D lead + 512D follow + 256D interaction embeddings
```

**Key Innovations:**
- **Multi-Person Detection**: Simultaneous tracking of both dance partners
- **Couple Interaction Analysis**: Hand connections, proximity, synchronization
- **Quality Metrics**: Automatic quality scoring and validation
- **Performance**: 75-80% mAP accuracy (vs MediaPipe's 60-65%)
- **Embedding Validation**: NaN/Inf detection, dimensionality verification

#### 3. **Text Semantic Understanding** 📝
```python
# Semantic analysis of move annotations for intelligent matching
class TextEmbeddingService:
    - Sentence-transformers 'all-MiniLM-L6-v2' model
    - 384D semantic embeddings from move metadata
    - Natural language descriptions from annotations
    - Difficulty-aware and role-specific matching
```

**Key Innovations:**
- **Semantic Grouping**: Clusters similar move types (e.g., all "cross_body_lead" variations)
- **Difficulty Matching**: Ensures consistent difficulty progression
- **Role-Specific Filtering**: Lead-focus vs follow-focus moves
- **Performance**: <5 seconds for all 38 clips

#### 4. **Trimodal Feature Fusion** 🔗
```python
# Intelligent fusion of audio, visual, and semantic features
class MultimodalEmbedding:
    - Audio: 128D (music characteristics)
    - Lead: 512D (lead dancer movements)
    - Follow: 512D (follow dancer movements)
    - Interaction: 256D (couple dynamics)
    - Text: 384D (semantic understanding)
    - Total: 1792D stored individually in Elasticsearch
```

**Key Innovations:**
- **Trimodal Learning**: Audio (35%) + Pose (30%) + Text (35%) weighted fusion
- **No Compression**: All embeddings stored at full dimensionality for maximum quality
- **Query-Time Weighting**: Flexible similarity computation with adjustable weights
- **Elasticsearch Storage**: Fast kNN search (<50ms) across all modalities

#### 5. **Elasticsearch-Powered Recommendation Engine** 🎯
```python
# High-performance similarity matching with vector search
class RecommendationEngine:
    - Elasticsearch 9.1 for vector similarity search
    - Retrieves all 38 embeddings in <10ms
    - Computes weighted similarities across all modalities
    - Metadata filtering (difficulty, energy, role)
    - Detailed score breakdowns per component
```

**Key Innovations:**
- **Fast Retrieval**: <10ms embedding lookup, <50ms total recommendation time
- **Flexible Weighting**: Adjustable weights for audio, pose, and text components
- **Semantic Grouping**: Text embeddings enable intelligent move clustering
- **Quality Validation**: Automatic NaN/Inf detection and dimensionality verification

#### 6. **Intelligent Sequence Generation** 🎬
```python
# Temporal choreography assembly with smooth transitions
class ChoreographyPipeline:
    - Musical structure mapping to dance move categories
    - Transition optimization for movement flow
    - Energy curve matching throughout choreography
    - Full-song duration with adaptive pacing
```

**Key Innovations:**
- **Structure-Aware Mapping**: Matches musical sections to appropriate move types
- **Transition Optimization**: Ensures smooth flow between different moves
- **Energy Management**: Maintains appropriate energy levels throughout choreography
- **Adaptive Timing**: Adjusts move duration based on musical phrasing

### 📊 Production-Ready Performance Metrics

| Component | Metric | Performance | Optimization |
|-----------|--------|-------------|--------------|
| **Audio Analysis** | Processing Speed | 2-3 sec/song | Vectorized operations, caching |
| **MMPose Detection** | Accuracy Rate | 75-80% mAP | Research-grade multi-person detection |
| **Couple Detection** | Frame Coverage | >70% both dancers | IoU-based tracking, quality filtering |
| **Text Embeddings** | Processing Speed | <5 sec/38 clips | Sentence-transformers, batch processing |
| **Elasticsearch** | Retrieval Time | <10ms lookup | Vector similarity search, kNN optimization |
| **Recommendation** | Response Time | <50ms total | Elasticsearch + weighted similarity |
| **Embedding Validation** | Accuracy | 100% valid | NaN/Inf detection, dimension verification |
| **Memory Usage** | Peak Consumption | <500MB | Lazy loading, automatic cleanup |
| **Video Generation** | Rendering Speed | 1-2x realtime | FFmpeg optimization, quality modes |
| **Overall Pipeline** | End-to-End | 25-30 seconds | Full pipeline optimization |

## 🆕 Recent Improvements

### Test Infrastructure Unification ✅
- **Unified Test Directory**: Consolidated `tests/` and `tests_django/` into single organized structure
- **Clear Organization**: Tests organized by type (unit, services, models, views, forms, integration)
- **Improved Maintainability**: Single conftest.py, unified documentation, consistent patterns
- **Better Developer Experience**: Clear where to find/add tests, automatic test marking

### Enhanced ML Pipeline ✅
- **MMPose Integration**: Upgraded from MediaPipe to research-grade multi-person pose detection
- **Trimodal Embeddings**: Audio (128D) + Pose (1280D) + Text (384D) = 1792D total
- **Elasticsearch Storage**: Fast vector similarity search with kNN optimization
- **Quality Validation**: Comprehensive embedding validation with NaN/Inf detection
- **Semantic Understanding**: Text embeddings enable intelligent move grouping and filtering

### Production Readiness ✅
- **Embedding Validation**: Automatic quality checks and dimensionality verification
- **Quality Metrics**: Comprehensive quality scoring and reporting
- **Error Handling**: Graceful degradation and clear error messages
- **Documentation**: Extensive documentation for all components
- **Test Coverage**: 67%+ coverage with unified test structure

## 🌟 Features Overview

### ✅ Implemented Features

#### 1. **Choreography Generation** 🎬
- **AI-Powered Generation**: Automatic choreography creation from music
- **Multiple Difficulty Levels**: Beginner, Intermediate, Advanced
- **Song Selection**: Pre-loaded songs or YouTube URL input
- **Real-Time Progress**: Live progress tracking with stage indicators
- **Video Preview**: Built-in video player with loop controls
- **Auto-Save**: Automatic saving to user collection

#### 2. **User Management** 👤
- **Authentication**: Secure login/logout with session management
- **User Profiles**: Customizable user profiles with preferences
- **Role-Based Access**: Regular users and instructors
- **Rate Limiting**: Protection against abuse

#### 3. **Collection Management** 📚
- **Save Choreographies**: Save generated videos to personal collection
- **Search & Filter**: Find choreographies by title, difficulty, date
- **Sorting**: Multiple sorting options (newest, title, difficulty, duration)
- **Pagination**: Efficient browsing of large collections
- **Edit Metadata**: Update titles and difficulty levels
- **Delete Videos**: Individual or bulk deletion with confirmation
- **Statistics**: View collection stats and insights

#### 4. **Instructor Dashboard** 🎓
- **Class Planning**: Create and manage class plans
- **Choreography Selection**: Add choreographies to class sequences
- **Student Management**: Track student progress (planned)
- **Analytics**: View teaching statistics (planned)

#### 5. **Video Player** 🎥
- **Advanced Controls**: Play, pause, seek, loop
- **Loop Segments**: Select and loop specific sections
- **Adjustable Loop Points**: Fine-tune loop start/end times
- **Progress Bar**: Visual progress with click-to-seek
- **Responsive Design**: Works on desktop and mobile

#### 6. **Music Analysis Engine** 🎼
- **Tempo Detection**: Accurate BPM analysis using librosa
- **Energy Level Analysis**: Classifies songs as low, medium, or high energy
- **Musical Structure Detection**: Identifies verses, choruses, and bridges
- **Beat Tracking**: Precise beat detection for move synchronization
- **Comprehensive Reporting**: Detailed analysis results

#### 7. **Video Library** 📹
- **38 Annotated Moves**: Curated library of Bachata moves
- **12 Move Categories**: Organized by move type
- **Quality Validated**: All moves analyzed and validated
- **Difficulty Levels**: Beginner (26%), Intermediate (21%), Advanced (53%)
- **Energy Distribution**: Low (5%), Medium (42%), High (53%)
- **Tempo Range**: 102-150 BPM

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- UV (Python package manager)
- PostgreSQL 14+ (or SQLite for development)
- FFmpeg

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd bachata_buddy
```

2. **Install UV Package Manager**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

3. **Install FFmpeg**
```bash
# macOS
brew install ffmpeg portaudio libsndfile

# Ubuntu/Debian
sudo apt-get install ffmpeg portaudio19-dev libsndfile1-dev

# Windows
# Download from https://ffmpeg.org/download.html
```

4. **Install Python dependencies**
```bash
# Install core dependencies via UV
uv sync

# Install MMPose stack via mim (handles chumpy dependency correctly)
uv pip install openmim
mim install mmengine mmcv mmdet mmpose

# Download MMPose model checkpoints
uv run python scripts/download_mmpose_models.py
```

**Note:** MMPose dependencies are installed separately via `mim` due to a build issue with the `chumpy` package. See **[UV_SETUP.md](UV_SETUP.md)** for detailed UV configuration and **[CHUMPY_PRODUCTION_SOLUTION.md](CHUMPY_PRODUCTION_SOLUTION.md)** for production deployment.

5. **Set up environment variables**
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
# For development, SQLite is fine (default)
# For production, configure PostgreSQL
```

6. **Run Django migrations**
```bash
uv run python manage.py migrate
```

7. **Create superuser**
```bash
uv run python manage.py createsuperuser
```

8. **Run the development server**
```bash
uv run python manage.py runserver
```

9. **Access the application**
- **Home**: http://localhost:8000/
- **Admin**: http://localhost:8000/admin/
- **Collections**: http://localhost:8000/collections/
- **Generate**: http://localhost:8000/ (main page)

**Enjoy! 💃🕺**

### 📚 Detailed Setup Guide

For comprehensive setup instructions, see **[DJANGO_SETUP_GUIDE.md](DJANGO_SETUP_GUIDE.md)**

## 🏗️ Technology Stack

### Backend
- **Framework**: Django 5.2 LTS
- **Database**: PostgreSQL 14+ (SQLite for development)
- **ORM**: Django ORM
- **Authentication**: Django session-based auth
- **Package Manager**: UV (fast Python package manager)

### Frontend
- **Templates**: Django Template Language
- **Interactivity**: HTMX + Alpine.js
- **Styling**: Tailwind CSS
- **Icons**: Emoji-based (no icon library needed)

### Machine Learning & AI
- **Audio Analysis**: librosa, numpy, scipy
- **Computer Vision**: MMPose, MMDetection, MMCV, OpenCV
- **Text Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector Search**: Elasticsearch 9.1 with kNN
- **Video Processing**: FFmpeg, moviepy
- **Feature Extraction**: Custom trimodal ML pipeline

### Testing
- **Framework**: pytest + pytest-django
- **Structure**: Unified test directory organized by type
- **Coverage**: 67%+ test coverage
- **Types**: Unit, service, model, view, form, and integration tests

## 📊 Data Management

### Video Library Statistics
- **38 annotated move clips** across 12 categories
- **Quality validated** with comprehensive metadata
- **Organized by difficulty**: Beginner (26%), Intermediate (21%), Advanced (53%)
- **Energy distribution**: Low (5%), Medium (42%), High (53%)
- **Tempo range**: 102-150 BPM

### Move Categories
1. Basic Steps
2. Partner Work (Cross Body Leads)
3. Turns & Spins
4. Styling & Body Rolls
5. Footwork Variations
6. Dips & Drops
7. Hammerlock Variations
8. Shadow Position
9. Hand Styling
10. Advanced Combinations
11. Musicality Accents
12. Social Dancing Moves

### User Data Storage
- **Generated Videos**: `data/output/user_{id}/`
- **Temporary Files**: `data/temp/user_{id}/`
- **Database**: PostgreSQL (user accounts, choreographies, collections)

## 🔧 Configuration

### Django Settings
```python
# In bachata_buddy/settings.py
INSTALLED_APPS = [
    'core',              # Shared services
    'users',             # User management
    'choreography',      # Choreography generation
    'user_collections',  # Collection management
    'instructors',       # Instructor features
]

MEDIA_ROOT = BASE_DIR / 'data'
MEDIA_URL = '/media/'
```

### Music Analysis Settings
```python
# In core/services/music_analyzer.py
TEMPO_RANGE = (80, 160)  # BPM range for Bachata
ENERGY_THRESHOLDS = {
    "low": 0.3,
    "medium": 0.7,
    "high": 1.0
}
```

### Video Generation Settings
```python
# In core/services/video_generator.py
QUALITY_MODES = {
    "fast": {"fps": 15, "bitrate": "1M"},
    "balanced": {"fps": 15, "bitrate": "1.5M"},
    "high_quality": {"fps": 20, "bitrate": "2M"}
}
```

## 🧪 Testing

### Unified Test Structure

The project uses a **unified test directory** organized by test type for clarity and maintainability:

```
tests/
├── unit/          # Pure unit tests (no external dependencies)
├── services/      # Service layer tests (ML, Elasticsearch, etc.)
├── models/        # Django model tests
├── views/         # Django view tests
├── forms/         # Django form tests
└── integration/   # Integration & E2E tests
```

### Run Tests

```bash
# Run all tests
uv run pytest tests/

# Run by directory (test type)
uv run pytest tests/unit/          # Fast unit tests only
uv run pytest tests/services/      # Service layer tests
uv run pytest tests/models/        # Django model tests
uv run pytest tests/views/         # Django view tests
uv run pytest tests/integration/   # Integration tests

# Run by marker
uv run pytest -m unit              # Unit tests only
uv run pytest -m integration       # Integration tests
uv run pytest -m django_db         # Django DB tests
uv run pytest -m "not slow"        # Skip slow tests

# Run with coverage
uv run pytest tests/ --cov=core --cov=choreography --cov=users --cov-report=html

# Run specific test file
uv run pytest tests/views/test_choreography_views.py -v

# Run verification scripts
uv run python verify_frame_processing.py
uv run python verify_pose_detection.py
uv run python verify_embedding_validation.py
```

### Test Coverage
- **Overall**: 67%+ coverage
- **Views**: 85%+ coverage
- **Models**: 90%+ coverage
- **Services**: 60%+ coverage (ML components)
- **Unit Tests**: 12/14 passing (2 expected failures for Google Cloud dependencies)

### Test Documentation
See **[tests/README.md](tests/README.md)** for comprehensive testing documentation including:
- Test structure and organization
- Running tests by type and marker
- Writing new tests
- Fixtures and utilities
- Troubleshooting guide

## 🚀 Deployment

### Production Deployment Options

#### Option 1: Google Cloud Run (Recommended)
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT/bachata-buddy
gcloud run deploy bachata-buddy \
    --image gcr.io/YOUR_PROJECT/bachata-buddy \
    --region us-central1 \
    --cpu 4 \
    --memory 16Gi
```

#### Option 2: Docker Compose (Local/Staging)
```bash
docker-compose up --build
```

#### Option 3: Kubernetes (Advanced)
See `PRODUCTION_DEPLOYMENT.md` for detailed instructions.

### Production Checklist
- [ ] Set `DEBUG = False` in settings
- [ ] Configure PostgreSQL database
- [ ] Set up static file serving (WhiteNoise or CDN)
- [ ] Configure media file storage (S3 or similar)
- [ ] Set up HTTPS/SSL
- [ ] Configure environment variables
- [ ] Set up logging and monitoring
- [ ] Configure backup strategy
- [ ] Set up CI/CD pipeline
- [ ] **CRITICAL:** Use production-ready Dockerfile (handles chumpy dependency)

### Environment Variables
```bash
# Required
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
ENVIRONMENT=cloud  # or 'local'

# Database
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Elasticsearch
ELASTICSEARCH_HOST=your-es-host
ELASTICSEARCH_PORT=9200

# Optional
MEDIA_ROOT=/path/to/media
STATIC_ROOT=/path/to/static
GCP_PROJECT_ID=your-project-id  # For Google Cloud
```

### ⚠️ Critical Production Note

**The `uv run --no-sync` workaround only works in local development** with an existing `.venv/`. 

For production deployment:
- Use the provided `Dockerfile` which handles MMPose installation via `mim`
- See `CHUMPY_PRODUCTION_SOLUTION.md` for detailed explanation
- See `PRODUCTION_DEPLOYMENT.md` for deployment guides

**Why this matters:** Docker builds start with a clean slate and must install all dependencies from scratch. The hybrid UV + mim approach in the Dockerfile ensures reliable builds.

## 📖 Documentation

### Setup & Configuration
- **[DJANGO_SETUP_GUIDE.md](DJANGO_SETUP_GUIDE.md)** - Comprehensive setup guide
- **[QUICK_START.md](QUICK_START.md)** - Quick reference for common commands
- **[UV_MMPOSE_SETUP.md](UV_MMPOSE_SETUP.md)** - UV and MMPose setup guide
- **[CONFIGURATION_SETUP.md](CONFIGURATION_SETUP.md)** - Environment configuration

### Production Deployment
- **[PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)** - Complete deployment guide
- **[CHUMPY_PRODUCTION_SOLUTION.md](CHUMPY_PRODUCTION_SOLUTION.md)** - Critical: chumpy dependency solution
- **[Dockerfile](Dockerfile)** - Production-ready Docker configuration

### Feature Documentation
- **[DELETE_FUNCTIONALITY.md](DELETE_FUNCTIONALITY.md)** - Delete feature documentation
- **[MMPOSE_SETUP.md](MMPOSE_SETUP.md)** - MMPose integration guide
- **[ELASTICSEARCH_IMPLEMENTATION.md](ELASTICSEARCH_IMPLEMENTATION.md)** - Elasticsearch setup
- **[RECOMMENDATION_ENGINE_USAGE.md](RECOMMENDATION_ENGINE_USAGE.md)** - Recommendation engine guide
- **[VALIDATION_QUICK_REFERENCE.md](VALIDATION_QUICK_REFERENCE.md)** - Embedding validation reference

### Testing
- **[tests/README.md](tests/README.md)** - Comprehensive testing guide
- **[TEST_UNIFICATION_COMPLETE.md](TEST_UNIFICATION_COMPLETE.md)** - Test structure unification

### Architecture & Migration
- **[CORE_APP_MIGRATION.md](CORE_APP_MIGRATION.md)** - Core app restructuring
- **[PROJECT_RESTRUCTURE.md](PROJECT_RESTRUCTURE.md)** - Project rename and flattening
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Complete documentation index

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Write tests for new features
- Update documentation
- Use type hints where appropriate
- Keep functions focused and small

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Django** for the excellent web framework
- **librosa** for music analysis capabilities
- **MediaPipe** for pose estimation
- **FFmpeg** for video processing
- **yt-dlp** for YouTube integration
- **Tailwind CSS** for styling
- **HTMX** for seamless interactivity
- **Alpine.js** for reactive components

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review closed issues for solutions

---

**Built with ❤️ for the Bachata dance community**

**Happy Dancing! 💃🕺**
