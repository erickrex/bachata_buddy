"""
Pytest configuration for Django tests.
"""
import pytest
import tempfile
import shutil
import os
from pathlib import Path

# Set environment variables for testing
os.environ["SKIP_DB_INIT"] = "true"
os.environ["SKIP_SYSTEM_VALIDATION"] = "true"
os.environ["DJANGO_SETTINGS_MODULE"] = "bachata_vibes_django.settings"

# Django setup for pytest
import django
try:
    django.setup()
    DJANGO_AVAILABLE = True
except Exception as e:
    DJANGO_AVAILABLE = False
    DJANGO_ERROR = str(e)


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


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "django_db: Mark test as requiring database access")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid or "e2e" in item.nodeid:
            item.add_marker(pytest.mark.integration)


# ============================================================================
# Django Fixtures
# ============================================================================

@pytest.fixture
def django_user_model():
    """Get Django User model."""
    if DJANGO_AVAILABLE:
        from django.contrib.auth import get_user_model
        return get_user_model()
    return None


@pytest.fixture
def create_django_user(django_user_model, db):
    """Factory fixture to create Django users."""
    def _create_user(email="test@example.com", password="testpass123", display_name="Test User", is_instructor=False):
        if django_user_model:
            user = django_user_model.objects.create_user(
                username=email,
                email=email,
                password=password,
            )
            if hasattr(user, 'display_name'):
                user.display_name = display_name
            if hasattr(user, 'is_instructor'):
                user.is_instructor = is_instructor
            user.save()
            return user
        return None
    return _create_user


@pytest.fixture
def django_client():
    """Django test client."""
    if DJANGO_AVAILABLE:
        from django.test import Client
        return Client()
    return None


@pytest.fixture
def authenticated_django_client(django_client, create_django_user):
    """Authenticated Django test client."""
    if django_client and create_django_user:
        user = create_django_user()
        django_client.force_login(user)
        return django_client, user
    return None, None
