"""
Pytest configuration for Django tests.
This file is automatically loaded by pytest when running tests in tests_django/.
"""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


# ============================================================================
# Pytest Django Configuration
# ============================================================================

@pytest.fixture(scope='session')
def django_db_setup():
    """
    Configure the test database.
    pytest-django will create/destroy the test database automatically.
    """
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
# User Fixtures
# ============================================================================

@pytest.fixture
@pytest.mark.django_db
def test_user(db):
    """Create a regular test user."""
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


# ============================================================================
# Choreography Fixtures
# ============================================================================

@pytest.fixture
@pytest.mark.django_db
def django_user(db):
    """Create a regular test user (alias for test_user)."""
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
def saved_choreography(django_user):
    """Create a saved choreography (alias for test_choreography)."""
    from choreography.models import SavedChoreography
    
    choreography = SavedChoreography.objects.create(
        user=django_user,
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
# File Fixtures
# ============================================================================

@pytest.fixture
def temp_video_file(tmp_path):
    """Create a temporary video file for testing."""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"fake video content")
    return video_file


@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary audio file for testing."""
    audio_file = tmp_path / "test_audio.mp3"
    audio_file.write_bytes(b"fake audio content")
    return audio_file


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
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "views: marks tests for views"
    )
    config.addinivalue_line(
        "markers", "models: marks tests for models"
    )
    config.addinivalue_line(
        "markers", "forms: marks tests for forms"
    )
