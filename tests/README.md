# Tests

Unified test suite for the Bachata Choreography Generator.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── README.md                # This file
│
├── unit/                    # Pure unit tests (no external dependencies)
│   ├── config/              # Configuration tests
│   └── validators/          # Validator tests
│
├── services/                # Service layer tests
│   ├── test_elasticsearch_service.py
│   ├── test_mmpose_couple_detector.py
│   ├── test_pose_embedding_generator.py
│   ├── test_quality_metrics.py
│   └── test_recommendation_engine.py
│
├── models/                  # Django model tests
│   ├── test_user_models.py
│   ├── test_choreography_models.py
│   └── test_instructor_models.py
│
├── views/                   # Django view tests
│   ├── test_choreography_views.py
│   ├── test_auth_views.py
│   ├── test_collection_views.py
│   └── test_instructor_views.py
│
├── forms/                   # Django form tests
│   └── test_forms.py
│
└── integration/             # Integration & E2E tests
    ├── test_choreography_flow.py
    ├── test_embedding_pipeline.py
    ├── test_error_handling.py
    └── test_feature_parity.py
```

## Running Tests

### All Tests
```bash
uv run pytest tests/
```

### By Directory
```bash
# Unit tests only (fast, no external dependencies)
uv run pytest tests/unit/

# Service tests
uv run pytest tests/services/

# Django model tests
uv run pytest tests/models/

# Django view tests
uv run pytest tests/views/

# Django form tests
uv run pytest tests/forms/

# Integration tests
uv run pytest tests/integration/
```

### By Marker
```bash
# Unit tests only
uv run pytest -m unit

# Integration tests
uv run pytest -m integration

# Django database tests
uv run pytest -m django_db

# Elasticsearch tests
uv run pytest -m elasticsearch

# Skip slow tests
uv run pytest -m "not slow"

# Specific component
uv run pytest -m models
uv run pytest -m views
uv run pytest -m services
```

### With Coverage
```bash
# All tests with coverage
uv run pytest tests/ --cov=core --cov=choreography --cov=users --cov=instructors

# Specific directory with coverage
uv run pytest tests/services/ --cov=core/services --cov-report=html
```

### Specific Test File
```bash
uv run pytest tests/services/test_elasticsearch_service.py
uv run pytest tests/views/test_choreography_views.py -v
```

## Test Categories

### Unit Tests (`tests/unit/`)
Pure unit tests with no external dependencies. Fast and isolated.

**Characteristics:**
- No database access
- No external services (Elasticsearch, APIs)
- Use mocks for dependencies
- Test individual functions/classes in isolation

**Examples:**
- Configuration validation
- Data structure manipulation
- Utility functions
- Validators

**Run with:**
```bash
uv run pytest tests/unit/ -v
```

### Service Tests (`tests/services/`)
Tests for service layer components. May use mocks or real services.

**Characteristics:**
- Test service classes and their methods
- May require external services (marked with `@pytest.mark.integration`)
- Test business logic and data processing

**Examples:**
- Elasticsearch service
- MMPose couple detector
- Embedding generators
- Quality metrics calculator
- Recommendation engine

**Run with:**
```bash
# All service tests
uv run pytest tests/services/

# Only unit service tests (with mocks)
uv run pytest tests/services/ -m "not integration"

# Only integration service tests (with real services)
uv run pytest tests/services/ -m integration
```

### Django Tests (`tests/models/`, `tests/views/`, `tests/forms/`)
Tests for Django components. Require database access.

**Characteristics:**
- Marked with `@pytest.mark.django_db`
- Use Django test client
- Test Django ORM, views, forms
- Transactions rolled back after each test

**Examples:**
- Model creation and validation
- View responses and permissions
- Form validation and submission

**Run with:**
```bash
# All Django tests
uv run pytest tests/models/ tests/views/ tests/forms/

# Specific component
uv run pytest tests/models/ -v
uv run pytest tests/views/ -v
```

### Integration Tests (`tests/integration/`)
End-to-end tests that verify complete workflows.

**Characteristics:**
- Test multiple components working together
- May require database and external services
- Test user-facing functionality
- Slower than unit tests

**Examples:**
- Complete choreography generation flow
- Embedding pipeline (video → embeddings → Elasticsearch)
- User authentication and authorization flow
- Error handling across components

**Run with:**
```bash
uv run pytest tests/integration/ -v
```

## Test Markers

Tests are automatically marked based on their location:

| Marker | Description | Auto-Applied To |
|--------|-------------|-----------------|
| `@pytest.mark.unit` | Unit tests | `tests/unit/` |
| `@pytest.mark.services` | Service tests | `tests/services/` |
| `@pytest.mark.models` | Model tests | `tests/models/` |
| `@pytest.mark.views` | View tests | `tests/views/` |
| `@pytest.mark.forms` | Form tests | `tests/forms/` |
| `@pytest.mark.integration` | Integration tests | `tests/integration/` |
| `@pytest.mark.django_db` | Requires database | Django tests |
| `@pytest.mark.elasticsearch` | Requires Elasticsearch | Elasticsearch tests |
| `@pytest.mark.slow` | Slow tests | Manual |
| `@pytest.mark.e2e` | End-to-end tests | Manual |

## Fixtures

### Environment Fixtures
- `setup_test_environment` - Sets up test environment variables (autouse)

### File System Fixtures
- `temp_dir` - Temporary directory for test files
- `temp_video_file` - Temporary video file
- `temp_audio_file` - Temporary audio file
- `temp_checkpoint_dir` - Temporary checkpoint directory

### Django User Fixtures
- `test_user` - Regular test user
- `test_instructor` - Instructor test user
- `authenticated_client` - Authenticated test client
- `instructor_client` - Authenticated instructor client

### Django Model Fixtures
- `test_choreography` - Test choreography instance
- `test_class_plan` - Test class plan instance

### Mock Fixtures
- `mock_choreography_pipeline` - Mock choreography pipeline
- `mock_youtube_service` - Mock YouTube service

## External Service Requirements

### Elasticsearch (for integration tests)

**Start Elasticsearch:**
```bash
docker run -d --name elasticsearch -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:9.1.0
```

**Check if running:**
```bash
curl http://localhost:9200
```

**Tests will be skipped** if Elasticsearch is not available.

### PostgreSQL (for Django tests)

Django tests use the PostgreSQL test database configured in settings.
pytest-django creates and destroys the test database automatically.

## Writing Tests

### Test File Naming
- Test files must start with `test_`
- Place in appropriate directory based on what you're testing
- Example: `tests/services/test_elasticsearch_service.py`

### Test Function Naming
- Test functions must start with `test_`
- Use descriptive names
- Example: `test_get_embedding_by_id_returns_correct_embedding`

### Test Class Naming
- Test classes must start with `Test`
- Group related tests in classes
- Example: `class TestElasticsearchService:`

### Example Unit Test
```python
import pytest
from core.services.embedding_validator import EmbeddingValidator

class TestEmbeddingValidator:
    """Unit tests for embedding validator."""
    
    def test_validate_valid_embedding(self):
        """Test validation of valid embedding."""
        validator = EmbeddingValidator()
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        is_valid, errors = validator.validate_embedding(
            embedding, 'lead_embedding', check_normalized=True
        )
        
        assert is_valid
        assert errors is None
```

### Example Django Test
```python
import pytest
from django.urls import reverse

@pytest.mark.django_db
class TestChoreographyViews:
    """Tests for choreography views."""
    
    def test_index_view_requires_authentication(self, client):
        """Test that index view requires authentication."""
        response = client.get(reverse('choreography:index'))
        assert response.status_code == 302  # Redirect to login
    
    def test_index_view_authenticated(self, authenticated_client):
        """Test index view with authenticated user."""
        response = authenticated_client.get(reverse('choreography:index'))
        assert response.status_code == 200
```

### Example Integration Test
```python
import pytest

@pytest.mark.integration
@pytest.mark.django_db
class TestChoreographyFlow:
    """Integration tests for choreography generation flow."""
    
    def test_complete_choreography_generation(
        self, authenticated_client, mock_choreography_pipeline
    ):
        """Test complete choreography generation flow."""
        # Submit generation request
        response = authenticated_client.post(
            reverse('choreography:create'),
            data={'difficulty': 'intermediate', 'song': 'test_song'}
        )
        
        # Check task was created
        assert response.status_code == 200
        
        # Verify choreography was saved
        from choreography.models import SavedChoreography
        assert SavedChoreography.objects.filter(
            user=authenticated_client.user
        ).exists()
```

## Continuous Integration

Tests run automatically in CI/CD pipelines:
- Unit tests: Always run
- Service tests: Run with mocks
- Integration tests: Run if services available
- Django tests: Always run (test database created)

## Troubleshooting

### Elasticsearch Tests Failing
**Problem:** Tests skipped with "Elasticsearch not available"

**Solution:**
```bash
# Check if running
curl http://localhost:9200

# Start if not running
docker start elasticsearch

# Create if doesn't exist
docker run -d --name elasticsearch -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:9.1.0
```

### Import Errors
**Problem:** `ModuleNotFoundError`

**Solution:**
- Run tests from project root
- Use `uv run pytest` (not just `pytest`)
- Check `__init__.py` files exist

### Django Database Errors
**Problem:** Database connection errors

**Solution:**
- Check PostgreSQL is running
- Verify database credentials in settings
- pytest-django creates test database automatically

### Fixture Not Found
**Problem:** `fixture 'xyz' not found`

**Solution:**
- Check fixture is defined in `conftest.py`
- Check fixture name spelling
- Ensure `conftest.py` is in correct location

## Best Practices

1. **Isolate tests** - Each test should be independent
2. **Use fixtures** - Share setup code with fixtures
3. **Clean up** - Always clean up resources (use fixtures with yield)
4. **Mark tests** - Use markers to categorize tests
5. **Test edge cases** - Test both success and failure scenarios
6. **Mock external services** - Use mocks for unit tests
7. **Document tests** - Add docstrings explaining what is tested
8. **Keep tests fast** - Unit tests should run in milliseconds
9. **Test one thing** - Each test should verify one behavior
10. **Use descriptive names** - Test names should explain what they test

## Coverage Goals

- **Unit tests**: 100% coverage of testable code
- **Service tests**: >90% coverage
- **Django tests**: >85% coverage
- **Overall**: >80% coverage

Check coverage:
```bash
uv run pytest tests/ --cov=core --cov=choreography --cov-report=html
open htmlcov/index.html
```

## Related Documentation

- [Elasticsearch Service](../core/services/README_ELASTICSEARCH.md)
- [Environment Configuration](../CONFIGURATION_SETUP.md)
- [Quality Metrics](../TASK_9_QUALITY_VALIDATION_SUMMARY.md)
- [Recommendation Engine](../RECOMMENDATION_ENGINE_USAGE.md)
