"""
Unified Pytest Configuration

This file provides fixtures and configuration for all tests:
- Unit tests (config, validators, utils)
- Service tests (Elasticsearch, MMPose, embeddings)
- Django tests (models, views, forms)
- Integration tests (end-to-end flows)
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

# Set up Django before importing Django modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bachata_buddy.settings")
os.environ.setdefault("SKIP_DB_INIT", "true")
os.environ.setdefault("SKIP_SYSTEM_VALIDATION", "true")

# Try to import and setup Django
try:
    import django
    django.setup()
    from django.conf import settings
    from django.contrib.auth import get_user_model
    User = get_user_model()
    DJANGO_AVAILABLE = True
except Exception as e:
    settings = None
    User = None
    DJANGO_AVAILABLE = False
    print(f"Warning: Django not available: {e}")


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables (auto-applied to all tests)."""
    # Set to local environment by default
    monkeypatch.setenv("ENVIRONMENT", "local")
    
    # Set default Elasticsearch config
    monkeypatch.setenv("ELASTICSEARCH_HOST", "localhost")
    monkeypatch.setenv("ELASTICSEARCH_PORT", "9200")
    monkeypatch.setenv("ELASTICSEARCH_INDEX", "test_bachata_embeddings")
    
    # Set default MMPose config
    monkeypatch.setenv("MMPOSE_CHECKPOINT_PATH", "./test_checkpoints")
    monkeypatch.setenv("MMPOSE_CONFIDENCE", "0.3")


# ============================================================================
# Django Database Setup
# ============================================================================

@pytest.fixture(scope='session')
def django_db_setup():
    """
    Configure the test database.
    pytest-django will create/destroy the test database automatically.
    """
    if not DJANGO_AVAILABLE:
        pytest.skip("Django not available")
    
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_bachata_vibes',
        'USER': settings.DATABASES['default']['USER'],
        'PASSWORD': settings.DATABASES['default']['PASSWORD'],
        'HOST': settings.DATABASES['default']['HOST'],
        'PORT': settings.DATABASES['default']['PORT'],
        'ATOMIC_REQUESTS': False,
        'TEST': {
            'NAME': 'test_bachata_vibes',
        }
    }


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_video_file(temp_dir):
    """Create a temporary test video file."""
    video_path = Path(temp_dir) / "test_video.mp4"
    video_path.write_bytes(b"fake video content for testing")
    return str(video_path)


@pytest.fixture
def temp_audio_file(temp_dir):
    """Create a temporary test audio file."""
    audio_path = Path(temp_dir) / "test_audio.mp3"
    audio_path.write_bytes(b"fake audio content for testing")
    return str(audio_path)


@pytest.fixture
def temp_checkpoint_dir(temp_dir):
    """Create a temporary checkpoint directory."""
    checkpoint_path = Path(temp_dir) / "checkpoints"
    checkpoint_path.mkdir(exist_ok=True)
    return str(checkpoint_path)


# ============================================================================
# User Fixtures (Django)
# ============================================================================

@pytest.fixture
@pytest.mark.django_db
def test_user(db):
    """Create a regular test user."""
    if not DJANGO_AVAILABLE:
        pytest.skip("Django not available")
    
    user = User.objects.create_user(
        username='testuser',
        email='testuser@example.com',
        password='testpass123',
        display_name='Test User',
        is_instructor=False
    )
    return user


@pytest.fixture
@pytest.mark.django_db
def test_instructor(db):
    """Create a test instructor user."""
    user = User.objects.create_user(
        username='instructor',
        email='instructor@example.com',
        password='testpass123',
        display_name='Test Instructor',
        is_instructor=True
    )
    return user


@pytest.fixture
def authenticated_client(client, test_user):
    """Create an authenticated test client."""
    from django.test import Client
    django_client = Client()
    django_client.force_login(test_user)
    return django_client


@pytest.fixture
def instructor_client(client, test_instructor):
    """Create an authenticated instructor test client."""
    from django.test import Client
    django_client = Client()
    django_client.force_login(test_instructor)
    return django_client


# Aliases for compatibility
@pytest.fixture
@pytest.mark.django_db
def django_user(test_user):
    """Alias for test_user (for compatibility)."""
    return test_user


# ============================================================================
# Choreography Fixtures (Django)
# ============================================================================

@pytest.fixture
@pytest.mark.django_db
def test_choreography(test_user):
    """Create a test choreography."""
    from choreography.models import SavedChoreography
    
    choreography = SavedChoreography.objects.create(
        user=test_user,
        title='Test Choreography',
        video_path='data/output/test_video.mp4',
        difficulty='intermediate',
        duration=180.5,
        music_info={
            'title': 'Test Song',
            'artist': 'Test Artist',
            'tempo': 120
        },
        generation_parameters={
            'difficulty': 'intermediate',
            'song_selection': 'test_song'
        }
    )
    return choreography


@pytest.fixture
@pytest.mark.django_db
def saved_choreography(test_choreography):
    """Alias for test_choreography (for compatibility)."""
    return test_choreography


@pytest.fixture
@pytest.mark.django_db
def test_class_plan(test_instructor):
    """Create a test class plan."""
    from instructors.models import ClassPlan
    
    class_plan = ClassPlan.objects.create(
        instructor=test_instructor,
        title='Test Class Plan',
        description='A test class plan',
        difficulty_level='intermediate',
        estimated_duration=60,
        instructor_notes='Test notes'
    )
    return class_plan


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_choreography_pipeline(mocker):
    """Mock the choreography pipeline for testing."""
    mock = mocker.patch('choreography.views.choreography_pipeline')
    mock.return_value = {
        'video_path': 'data/output/test_video.mp4',
        'thumbnail_path': 'data/output/test_thumbnail.jpg',
        'duration': 180.5,
        'music_info': {
            'title': 'Test Song',
            'artist': 'Test Artist',
            'tempo': 120
        }
    }
    return mock


@pytest.fixture
def mock_youtube_service(mocker):
    """Mock the YouTube service for testing."""
    mock = mocker.patch('choreography.views.YouTubeService')
    mock.return_value.download_audio.return_value = 'data/songs/test_song.mp3'
    return mock


# ============================================================================
# Settings Fixtures
# ============================================================================

@pytest.fixture
def disable_task_cleanup(settings):
    """Disable task cleanup for testing."""
    settings.TASK_CLEANUP_ENABLED = False
    return settings


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    # Test type markers
    config.addinivalue_line(
        "markers",
        "unit: Unit tests (no external dependencies)"
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests (require external services)"
    )
    config.addinivalue_line(
        "markers",
        "e2e: End-to-end tests"
    )
    
    # Component markers
    config.addinivalue_line(
        "markers",
        "models: Django model tests"
    )
    config.addinivalue_line(
        "markers",
        "views: Django view tests"
    )
    config.addinivalue_line(
        "markers",
        "forms: Django form tests"
    )
    config.addinivalue_line(
        "markers",
        "services: Service layer tests"
    )
    
    # Service-specific markers
    config.addinivalue_line(
        "markers",
        "elasticsearch: Tests that require Elasticsearch"
    )
    config.addinivalue_line(
        "markers",
        "slow: Slow running tests (deselect with '-m \"not slow\"')"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location and name."""
    for item in items:
        # Mark by directory
        if "/unit/" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "/services/" in item.nodeid:
            item.add_marker(pytest.mark.services)
        elif "/models/" in item.nodeid:
            item.add_marker(pytest.mark.models)
            item.add_marker(pytest.mark.django_db)
        elif "/views/" in item.nodeid:
            item.add_marker(pytest.mark.views)
            item.add_marker(pytest.mark.django_db)
        elif "/forms/" in item.nodeid:
            item.add_marker(pytest.mark.forms)
            item.add_marker(pytest.mark.django_db)
        elif "/integration/" in item.nodeid:
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.django_db)
        
        # Mark integration tests
        if "integration" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)
        
        # Mark Elasticsearch tests
        if "elasticsearch" in item.nodeid.lower():
            item.add_marker(pytest.mark.elasticsearch)
            item.add_marker(pytest.mark.integration)


# ============================================================================
# Skip Conditions
# ============================================================================

def pytest_runtest_setup(item):
    """Skip tests based on markers and environment."""
    # Skip integration tests if Elasticsearch is not available
    if "elasticsearch" in [marker.name for marker in item.iter_markers()]:
        try:
            import requests
            response = requests.get("http://localhost:9200", timeout=1)
            if response.status_code != 200:
                pytest.skip("Elasticsearch not available at localhost:9200")
        except Exception:
            pytest.skip("Elasticsearch not available at localhost:9200")
