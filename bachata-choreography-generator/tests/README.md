# Test Suite Documentation

This directory contains the comprehensive test suite for the Bachata Choreography Generator application, written in **functional programming style** using pytest.

## 🎯 Testing Philosophy

All new tests follow **functional programming principles**:
- ✅ Pure functions without class-based organization
- ✅ No mutable shared state
- ✅ Independent, self-contained tests
- ✅ Reusable helper functions
- ✅ Clear, descriptive naming

## 📊 Test Coverage Summary

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| **Video Generator** | 48 | 90% | ✅ ⭐ |
| **Music Analyzer** | 36 | 87% | ✅ ⭐ |
| **Authentication** | 31 | 81% | ✅ ⭐ |
| **Auth Service** | - | 77% | ✅ |
| **Overall** | 284+ | 33% | 🔄 |

⭐ = Exemplary (90%+ coverage, functional style)

## 🚀 Quick Start

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_video_generator.py -v

# Run multiple test files
uv run pytest tests/test_video_generator.py tests/test_auth_endpoints.py -v

# Skip slow tests (audio/video processing)
uv run pytest -m "not slow"

# Run only API tests
uv run pytest -m api

# Stop on first failure
uv run pytest -x

# Show print statements
uv run pytest -s
```

## 📁 Test Organization

### ⭐ Core Service Tests (Functional Style - Exemplary)
- `test_video_generator.py` - Video generation service (48 tests, 90% coverage)
- `test_music_analyzer_pytest.py` - Music analysis service (36 tests, 87% coverage)
- `test_auth_endpoints.py` - Authentication API endpoints (31 tests, 81% coverage)

### 🔄 Legacy Tests (Being Migrated to Functional Style)
- `test_basic_functionality.py` - Basic infrastructure tests
- `test_basic_pytest.py` - Pytest infrastructure validation
- `test_authentication_service.py` - Authentication service tests
- `test_collection_service.py` - Collection management tests
- `test_collection_integration.py` - Collection integration tests
- `test_collection_interface.py` - Collection UI tests
- `test_instructor_dashboard_service.py` - Instructor dashboard tests
- `test_instructor_controller.py` - Instructor controller tests
- `test_instructor_endpoints_integration.py` - Instructor API integration
- `test_complete_flow.py` - End-to-end workflow tests
- `test_feature_fusion.py` - Feature fusion system tests
- `test_hyperparameter_optimizer.py` - Hyperparameter optimization tests
- `test_move_analyzer.py` - Move analysis tests
- `test_recommendation_engine.py` - Recommendation engine tests

### 📚 Test Documentation
- `VIDEO_GENERATOR_TEST_SUMMARY.md` - Detailed video generator test documentation
- `FUNCTIONAL_TESTS_SUMMARY.md` - Functional programming test patterns
- `README.md` - This file

## 🧪 Test Fixtures

Common fixtures are defined in `conftest.py`:

### API Testing
- `client` - FastAPI test client
- `authenticated_client` - Client with authentication headers
- `instructor_client` - Client with instructor authentication

### Database
- `test_db` - Test database session
- `test_user` - Test user instance
- `test_instructor` - Test instructor user

### Media Files
- `temp_video` - Temporary video file for testing
- `temp_audio` - Temporary audio file for testing
- `temp_video_file` - Path to temporary video
- `temp_audio_file` - Path to temporary audio
- `sample_video_path` - Path to sample video file
- `sample_audio_path` - Path to sample audio file

### Services
- `auth_service` - Authentication service instance
- `collection_service` - Collection service with temp storage

### Tokens
- `user_token` - JWT token for test user
- `instructor_token` - JWT token for test instructor

## 🏷️ Test Markers

Tests use custom markers for categorization:

```python
@pytest.mark.api          # API endpoint tests
@pytest.mark.service      # Service layer tests
@pytest.mark.slow         # Tests requiring audio/video processing
@pytest.mark.integration  # Integration tests
@pytest.mark.unit         # Unit tests
@pytest.mark.e2e          # End-to-end tests
```

### Using Markers
```bash
# Run only API tests
uv run pytest -m api

# Run service tests but skip slow ones
uv run pytest -m "service and not slow"

# Run integration tests
uv run pytest -m integration

# Run fast tests only
uv run pytest -m "not slow"
```

## ✍️ Writing New Tests (Functional Style)

### Template for New Tests

```python
"""
Test module for [Feature] - Functional Programming Style.
All tests are pure functions without class-based organization.
"""
import pytest
from typing import Optional


# ============================================================================
# HELPER FUNCTIONS (Pure Functions)
# ============================================================================

def create_test_data(param: str) -> dict:
    """Create test data - pure function with no side effects."""
    return {"key": param}


def assert_valid_result(result: dict) -> None:
    """Assert result is valid - pure validation function."""
    assert "key" in result
    assert result["key"] is not None


# ============================================================================
# TESTS
# ============================================================================

@pytest.mark.service
def test_feature_success():
    """Test successful feature operation."""
    # Arrange
    test_data = create_test_data("value")
    
    # Act
    result = some_function(test_data)
    
    # Assert
    assert_valid_result(result)


@pytest.mark.service
def test_feature_error_handling():
    """Test feature handles errors gracefully."""
    with pytest.raises(ValueError):
        some_function(None)
```

### Best Practices

1. **Use Pure Functions**
   - No class-based tests
   - No setup/teardown methods
   - No shared mutable state

2. **Descriptive Names**
   ```python
   # Good
   def test_user_registration_with_duplicate_email_fails():
   
   # Bad
   def test_registration():
   ```

3. **Helper Functions**
   ```python
   # Create reusable pure helper functions
   def create_test_user(email: str, password: str) -> dict:
       return {"email": email, "password": password}
   ```

4. **Clear Assertions**
   ```python
   # Use helper functions for complex assertions
   def assert_valid_auth_response(data: dict) -> None:
       assert "user" in data
       assert "tokens" in data
       assert "access_token" in data["tokens"]
   ```

5. **Proper Cleanup**
   ```python
   # Use try/finally for resource cleanup
   temp_dir = tempfile.mkdtemp()
   try:
       # Test code
       pass
   finally:
       shutil.rmtree(temp_dir, ignore_errors=True)
   ```

## 📦 Test Data

Test data files are located in:
- `data/songs/` - Sample audio files (MP3) for music analysis
- `data/Bachata_steps/` - Sample video files (MP4) for choreography
- `data/annotations/` - Sample annotation files (JSON/CSV)

### Using Test Data
```python
from pathlib import Path

def get_test_audio_path() -> Optional[str]:
    """Get path to test audio file."""
    audio_path = Path("data/songs/Amor.mp3")
    if audio_path.exists():
        return str(audio_path)
    return None
```

## 🎯 Coverage Goals

| Component | Target | Current | Status |
|-----------|--------|---------|--------|
| Critical Services | 90%+ | 87-90% | ✅ |
| API Endpoints | 80%+ | 81% | ✅ |
| Business Logic | 80%+ | 77% | 🔄 |
| UI/Presentation | 60%+ | - | 📝 |
| Overall | 60%+ | 33% | 🔄 |

## 📈 Running Tests with Coverage

```bash
# Generate HTML coverage report
uv run pytest --cov=app --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Show missing lines
uv run pytest --cov=app --cov-report=term-missing

# Focus on specific module
uv run pytest tests/test_video_generator.py --cov=app/services/video_generator --cov-report=term-missing

# Coverage with branch analysis
uv run pytest --cov=app --cov-branch --cov-report=html
```

## 🔧 Troubleshooting

### Missing Dependencies
```bash
# Install all dependencies
uv sync

# Or with pip
pip install -r requirements.txt
```

### FFmpeg Not Found
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### Database Issues
```bash
# Reset test database
rm -f test.db
uv run pytest --create-db
```

### Audio/Video Processing Errors
```bash
# Skip slow tests that require media processing
uv run pytest -m "not slow"
```

### Import Errors
```bash
# Ensure you're in the project root
cd bachata_vibes/bachata-choreography-generator

# Run tests with uv
uv run pytest
```

## 🔍 Debugging Tests

```bash
# Verbose output
uv run pytest -v

# Show print statements
uv run pytest -s

# Stop on first failure
uv run pytest -x

# Show local variables on failure
uv run pytest -l

# Drop into debugger on failure
uv run pytest --pdb

# Run specific test
uv run pytest tests/test_video_generator.py::test_video_generator_initialization_success -v

# Show slowest tests
uv run pytest --durations=10
```

## 🚦 Continuous Integration

Tests run automatically on:
- ✅ Every commit to main branch
- ✅ Every pull request
- ✅ Scheduled daily runs
- ✅ Pre-deployment checks

### CI Configuration
- Minimum coverage: 60%
- All tests must pass
- No security vulnerabilities
- Code style checks (black, flake8)

## 📊 Test Analysis

### View Coverage Report
```bash
# Generate HTML report
uv run pytest --cov=app --cov-report=html

# Open in browser
open htmlcov/index.html
```

### Identify Untested Code
```bash
# Show missing lines
uv run pytest --cov=app --cov-report=term-missing

# Focus on specific module
uv run pytest --cov=app/services/video_generator --cov-report=term-missing
```

### Performance Analysis
```bash
# Show slowest tests
uv run pytest --durations=10

# Profile test execution
uv run pytest --profile
```

## 🎓 Learning Resources

### Functional Programming in Tests
- Pure functions for test helpers
- Immutable test data
- No shared state between tests
- Composition over inheritance

### Example: Functional vs OOP

**OOP Style (Old)**:
```python
class TestVideoGenerator:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def test_something(self):
        generator = VideoGenerator(self.temp_dir)
        # test code
```

**Functional Style (New)**:
```python
def test_video_generator_initialization():
    """Pure function test - no class, no state."""
    temp_dir = tempfile.mkdtemp()
    try:
        generator = VideoGenerator(temp_dir)
        assert generator is not None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
```

## 📚 Additional Resources

### Documentation
- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)

### Project-Specific
- [VIDEO_GENERATOR_TEST_SUMMARY.md](./VIDEO_GENERATOR_TEST_SUMMARY.md) - Video generator test details
- [FUNCTIONAL_TESTS_SUMMARY.md](./FUNCTIONAL_TESTS_SUMMARY.md) - Functional programming patterns
- [TEST_ANALYSIS.md](../TEST_ANALYSIS.md) - Overall test analysis

## 🚦 Test Status Legend

- ✅ Complete and passing
- 🔄 In progress / needs improvement
- 📝 Planned / not started
- ⚠️ Failing / needs attention
- ⭐ Exemplary (90%+ coverage, functional style)

## 📋 Common Test Patterns

### Testing API Endpoints
```python
@pytest.mark.api
def test_endpoint_success(authenticated_client):
    response = authenticated_client.get("/api/endpoint")
    assert response.status_code == 200
    data = response.json()
    assert "key" in data
```

### Testing Services
```python
@pytest.mark.service
def test_service_method():
    service = MyService()
    result = service.do_something("input")
    assert result is not None
```

### Testing with Fixtures
```python
def test_with_fixtures(test_user, temp_video_file, test_db):
    # Fixtures are automatically provided
    assert test_user.email == "testuser@example.com"
    assert Path(temp_video_file).exists()
```

### Testing Error Handling
```python
def test_error_handling():
    with pytest.raises(ValueError, match="Invalid input"):
        function_that_raises("bad_input")
```

---

**Last Updated**: December 2024  
**Test Framework**: pytest 8.4.2  
**Python Version**: 3.12.6  
**Total Tests**: 284+  
**Overall Coverage**: 33% (Target: 60%)  
**Functional Style Tests**: 115 (48 + 36 + 31)
