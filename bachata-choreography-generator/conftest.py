"""
Pytest configuration and shared fixtures for Bachata Choreography Generator.
This file is automatically loaded by pytest.
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

# Try to import app components, skip if dependencies missing
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from fastapi.testclient import TestClient
    
    from main import app
    from app.database import Base, get_database_session
    from app.models.database_models import User, SavedChoreography, ClassPlan, ClassPlanSequence
    from app.services.authentication_service import AuthenticationService
    from app.services.collection_service import CollectionService
    from app.config import get_settings
    
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    IMPORT_ERROR = str(e)


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_db_engine():
    """
    Create an in-memory SQLite database engine for testing.
    Each test gets a fresh database.
    
    Note: We use poolclass=StaticPool to ensure all connections share the same in-memory database.
    """
    from sqlalchemy import inspect
    from sqlalchemy.pool import StaticPool
    
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool  # This ensures all connections use the same in-memory database
    )
    Base.metadata.create_all(engine)
    

    
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_db(test_db_engine):
    """Create a database session for testing."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def override_get_db(test_db):
    """Override the get_database_session dependency."""
    def _override_get_db():
        try:
            yield test_db
        finally:
            pass
    return _override_get_db


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user(test_db_engine):
    """Create a test user."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    db = TestingSessionLocal()
    try:
        user = User(
            id="test-user-123",
            email="testuser@example.com",
            password_hash="$pbkdf2-sha256$29000$lTKmNMa419p7b.2dEwIgZA$PCdicvWqpKzWETuqEVyrVOQJ9coP5vYKljWM.w7uUw4",  # "testpass123"
            display_name="Test User",
            is_instructor=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture
def test_instructor(test_db_engine):
    """Create a test instructor user."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    db = TestingSessionLocal()
    try:
        instructor = User(
            id="test-instructor-456",
            email="instructor@example.com",
            password_hash="$pbkdf2-sha256$29000$lTKmNMa419p7b.2dEwIgZA$PCdicvWqpKzWETuqEVyrVOQJ9coP5vYKljWM.w7uUw4",  # "testpass123"
            display_name="Test Instructor",
            is_instructor=True
        )
        db.add(instructor)
        db.commit()
        db.refresh(instructor)
        return instructor
    finally:
        db.close()


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def auth_service():
    """Create authentication service instance."""
    settings = get_settings()
    return AuthenticationService(
        jwt_secret=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes
    )


@pytest.fixture
def user_token(auth_service, test_user):
    """Generate JWT token for test user."""
    return auth_service.create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        is_instructor=test_user.is_instructor
    )


@pytest.fixture
def instructor_token(auth_service, test_instructor):
    """Generate JWT token for test instructor."""
    return auth_service.create_access_token(
        user_id=test_instructor.id,
        email=test_instructor.email,
        is_instructor=test_instructor.is_instructor
    )


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def client(test_db_engine):
    """Create FastAPI test client with test database."""
    # Create a new session for each request
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    
    # Override the database dependency to use test database
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_database_session] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client, user_token):
    """Create authenticated test client."""
    client.headers = {"Authorization": f"Bearer {user_token}"}
    return client


@pytest.fixture
def instructor_client(client, instructor_token):
    """Create authenticated instructor test client."""
    client.headers = {"Authorization": f"Bearer {instructor_token}"}
    return client


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
# Service Fixtures
# ============================================================================

@pytest.fixture
def collection_service(temp_dir):
    """Create collection service with temporary storage."""
    return CollectionService(storage_base_path=temp_dir)


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture
def saved_choreography(test_db, test_user, temp_video_file):
    """Create a saved choreography for testing."""
    choreography = SavedChoreography(
        id="test-choreo-789",
        user_id=test_user.id,
        title="Test Choreography",
        video_path=temp_video_file,
        difficulty="intermediate",
        duration=120.5,
        music_info={"title": "Test Song", "artist": "Test Artist"},
        generation_parameters={"tempo": 120, "energy": "medium"}
    )
    test_db.add(choreography)
    test_db.commit()
    test_db.refresh(choreography)
    return choreography


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "service: Service layer tests")
    config.addinivalue_line("markers", "django_db: Mark test as requiring database access")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark API tests
        if "test_auth_endpoints" in item.nodeid or "test_controllers" in item.nodeid:
            item.add_marker(pytest.mark.api)
        
        # Mark service tests
        if "test_service" in item.nodeid or "test_analyzer" in item.nodeid:
            item.add_marker(pytest.mark.service)
        
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
