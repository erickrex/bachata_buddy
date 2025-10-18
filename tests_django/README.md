# Django Tests

This folder contains tests for the Django version of the Bachata Choreography Generator.

## Structure

```
tests_django/
├── conftest.py              # Django pytest configuration
├── test_models.py           # Model tests
├── test_views.py            # View tests (FBV)
├── test_forms.py            # Form tests
├── test_integration.py      # Integration tests
└── README.md                # This file
```

## Running Tests

```bash
# Run all Django tests
uv run pytest tests_django/

# Run specific test file
uv run pytest tests_django/test_models.py

# Run with coverage
uv run pytest tests_django/ --cov=choreography --cov=users --cov=user_collections --cov=instructors

# Run only Django tests (exclude FastAPI tests)
uv run pytest tests_django/ -v
```

## Test Strategy

### Parallel Test Structure
- `tests/` - Original FastAPI tests (kept as reference)
- `tests_django/` - New Django tests (gradual migration)

### Migration Approach
1. Keep FastAPI tests as reference for functionality
2. Create equivalent Django tests incrementally
3. Each Django test should cover the same functionality as FastAPI counterpart
4. Use pytest-django for Django-specific testing features

### Test Coverage Goals
- Models: 100% coverage
- Views: >90% coverage
- Forms: >90% coverage
- Integration: Key user flows covered
- Overall: >80% coverage

## Django Test Features

### pytest-django Features Used
- `@pytest.mark.django_db` - Enable database access
- `client` fixture - Django test client
- `admin_client` fixture - Authenticated admin client
- `django_user_model` fixture - User model
- `settings` fixture - Modify settings in tests

### Test Database
- Uses PostgreSQL test database (created/destroyed automatically)
- Transactions rolled back after each test
- Fast and isolated

## Test Organization

### test_models.py
Tests for Django models:
- User model (custom user with display_name, is_instructor)
- SavedChoreography model
- ClassPlan and ClassPlanSequence models

### test_views.py
Tests for Function-Based Views:
- Choreography views (index, create, task_status, serve_video)
- Collection views (list, detail, edit, delete, save, stats)
- Authentication views (login, logout, register, profile)
- Instructor views (dashboard, class plan CRUD)

### test_forms.py
Tests for Django forms:
- ChoreographyGenerationForm
- SaveChoreographyForm
- User registration/profile forms

### test_integration.py
End-to-end tests:
- Complete choreography generation flow
- Video player with loop controls
- Collection management
- User authentication flow

## Comparison with FastAPI Tests

| FastAPI Test | Django Equivalent | Status |
|--------------|-------------------|--------|
| test_auth_endpoints.py | test_views.py (auth section) | TODO |
| test_choreography_*.py | test_views.py (choreography section) | TODO |
| test_models.py | test_models.py | TODO |
| test_forms.py | test_forms.py | TODO |

## Notes

- FastAPI tests use TestClient from fastapi.testclient
- Django tests use Client from django.test
- FastAPI tests use SQLAlchemy models
- Django tests use Django ORM models
- Both test suites should verify the same functionality
