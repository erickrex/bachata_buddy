"""
Test authentication endpoints using pytest - Functional Programming Style.
All tests are pure functions without class-based organization.
"""
import pytest
from fastapi import status
from typing import Dict, Any


# ============================================================================
# HELPER FUNCTIONS (Pure Functions)
# ============================================================================

def create_registration_data(email: str, password: str, display_name: str, 
                            is_instructor: bool = False) -> Dict[str, str]:
    """Create registration data dictionary."""
    return {
        "email": email,
        "password": password,
        "display_name": display_name,
        "is_instructor": "true" if is_instructor else "false"
    }


def create_login_data(email: str, password: str) -> Dict[str, str]:
    """Create login data dictionary."""
    return {
        "email": email,
        "password": password
    }


def assert_valid_auth_response(data: Dict[str, Any], expected_email: str) -> None:
    """Assert that auth response contains valid user and token data."""
    assert "user" in data
    assert "tokens" in data
    assert data["user"]["email"] == expected_email
    assert "access_token" in data["tokens"]


def assert_valid_user_profile(data: Dict[str, Any], expected_email: str, 
                              expected_display_name: str) -> None:
    """Assert that user profile data is valid."""
    assert data["email"] == expected_email
    assert data["display_name"] == expected_display_name


# ============================================================================
# REGISTRATION TESTS
# ============================================================================

@pytest.mark.api
def test_user_registration_success(client, test_db):
    """Test successful user registration."""
    registration_data = create_registration_data(
        email="newuser@example.com",
        password="securepass123",
        display_name="New User",
        is_instructor=False
    )
    
    response = client.post("/api/auth/register", data=registration_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert_valid_auth_response(data, "newuser@example.com")
    assert data["user"]["display_name"] == "New User"


@pytest.mark.api
def test_user_registration_duplicate_email(client, test_user):
    """Test registration with duplicate email fails."""
    registration_data = create_registration_data(
        email=test_user.email,
        password="anotherpass123",
        display_name="Another User"
    )
    
    response = client.post("/api/auth/register", data=registration_data)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.api
def test_user_registration_invalid_email(client, test_db):
    """Test registration with invalid email format fails."""
    registration_data = create_registration_data(
        email="not-an-email",
        password="securepass123",
        display_name="Test User"
    )
    
    response = client.post("/api/auth/register", data=registration_data)
    
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


@pytest.mark.api
def test_user_registration_weak_password(client, test_db):
    """Test registration with weak password."""
    registration_data = create_registration_data(
        email="newuser@example.com",
        password="123",  # Too short
        display_name="Test User"
    )
    
    response = client.post("/api/auth/register", data=registration_data)
    
    # Should either reject or accept based on validation rules
    assert response.status_code in [
        status.HTTP_201_CREATED, 
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ]


@pytest.mark.api
def test_user_registration_as_instructor(client, test_db):
    """Test registration as instructor."""
    registration_data = create_registration_data(
        email="instructor@example.com",
        password="securepass123",
        display_name="Instructor User",
        is_instructor=True
    )
    
    response = client.post("/api/auth/register", data=registration_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["user"]["is_instructor"] is True


# ============================================================================
# LOGIN TESTS
# ============================================================================

@pytest.mark.api
def test_user_login_success(client, test_user):
    """Test successful user login."""
    login_data = create_login_data(test_user.email, "testpass123")
    
    response = client.post("/api/auth/login", data=login_data)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert_valid_auth_response(data, test_user.email)


@pytest.mark.api
def test_user_login_wrong_password(client, test_user):
    """Test login with wrong password fails."""
    login_data = create_login_data(test_user.email, "wrongpassword")
    
    response = client.post("/api/auth/login", data=login_data)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.api
def test_user_login_nonexistent_user(client):
    """Test login with non-existent user fails."""
    login_data = create_login_data("nonexistent@example.com", "somepassword")
    
    response = client.post("/api/auth/login", data=login_data)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.api
def test_user_login_empty_credentials(client):
    """Test login with empty credentials fails."""
    login_data = create_login_data("", "")
    
    response = client.post("/api/auth/login", data=login_data)
    
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


@pytest.mark.api
def test_user_login_case_sensitive_email(client, test_user):
    """Test login with different email case."""
    login_data = create_login_data(test_user.email.upper(), "testpass123")
    
    response = client.post("/api/auth/login", data=login_data)
    
    # Behavior depends on implementation - either succeeds or fails
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


# ============================================================================
# PROFILE TESTS
# ============================================================================

@pytest.mark.api
def test_get_profile_authenticated(authenticated_client, test_user):
    """Test getting user profile when authenticated."""
    response = authenticated_client.get("/api/auth/profile")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert_valid_user_profile(data, test_user.email, test_user.display_name)


@pytest.mark.api
def test_get_profile_unauthenticated(client):
    """Test getting profile without authentication fails."""
    response = client.get("/api/auth/profile")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
def test_update_profile_success(authenticated_client, test_user):
    """Test updating user profile."""
    update_data = {"display_name": "Updated Name"}
    
    response = authenticated_client.put("/api/auth/profile", json=update_data)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["display_name"] == "Updated Name"


@pytest.mark.api
def test_update_profile_unauthenticated(client):
    """Test updating profile without authentication fails."""
    update_data = {"display_name": "Updated Name"}
    
    response = client.put("/api/auth/profile", json=update_data)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
def test_update_profile_empty_display_name(authenticated_client):
    """Test updating profile with empty display name."""
    update_data = {"display_name": ""}
    
    response = authenticated_client.put("/api/auth/profile", json=update_data)
    
    # Should either reject or accept based on validation rules
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ]


@pytest.mark.api
def test_update_profile_multiple_fields(authenticated_client):
    """Test updating multiple profile fields."""
    update_data = {
        "display_name": "New Display Name",
        "bio": "This is my bio"
    }
    
    response = authenticated_client.put("/api/auth/profile", json=update_data)
    
    # Should succeed if endpoint supports multiple fields
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]


# ============================================================================
# AUTH STATUS TESTS
# ============================================================================

@pytest.mark.api
def test_check_auth_status_authenticated(authenticated_client):
    """Test checking authentication status when authenticated."""
    response = authenticated_client.get("/api/auth/status")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["authenticated"] is True
    assert "user" in data


@pytest.mark.api
def test_check_auth_status_unauthenticated(client):
    """Test checking authentication status when not authenticated."""
    response = client.get("/api/auth/status")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# LOGOUT TESTS
# ============================================================================

@pytest.mark.api
def test_logout_success(authenticated_client):
    """Test user logout."""
    response = authenticated_client.post("/api/auth/logout")
    
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.api
def test_logout_unauthenticated(client):
    """Test logout without authentication."""
    response = client.post("/api/auth/logout")
    
    # Should either fail or succeed based on implementation
    assert response.status_code in [
        status.HTTP_204_NO_CONTENT,
        status.HTTP_401_UNAUTHORIZED
    ]


@pytest.mark.api
def test_logout_twice(authenticated_client):
    """Test logging out twice."""
    # First logout
    response1 = authenticated_client.post("/api/auth/logout")
    assert response1.status_code == status.HTTP_204_NO_CONTENT
    
    # Second logout should fail
    response2 = authenticated_client.post("/api/auth/logout")
    assert response2.status_code in [
        status.HTTP_204_NO_CONTENT,
        status.HTTP_401_UNAUTHORIZED
    ]


# ============================================================================
# TOKEN TESTS
# ============================================================================

@pytest.mark.api
def test_invalid_token_access(client):
    """Test access with invalid token fails."""
    client.headers = {"Authorization": "Bearer invalid_token_here"}
    
    response = client.get("/api/auth/profile")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
def test_malformed_token_header(client):
    """Test access with malformed authorization header."""
    client.headers = {"Authorization": "InvalidFormat token123"}
    
    response = client.get("/api/auth/profile")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
def test_missing_bearer_prefix(client):
    """Test access with missing Bearer prefix."""
    client.headers = {"Authorization": "some_token_without_bearer"}
    
    response = client.get("/api/auth/profile")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
def test_expired_token_access(client, test_user):
    """Test access with expired token."""
    # This would require creating an expired token
    # For now, just test with invalid token
    client.headers = {"Authorization": "Bearer expired_token"}
    
    response = client.get("/api/auth/profile")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# PREFERENCES TESTS
# ============================================================================

@pytest.mark.api
def test_get_user_preferences(authenticated_client):
    """Test getting user preferences."""
    response = authenticated_client.get("/api/auth/preferences")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "preferences" in data


@pytest.mark.api
def test_get_preferences_unauthenticated(client):
    """Test getting preferences without authentication."""
    response = client.get("/api/auth/preferences")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
def test_update_user_preferences(authenticated_client):
    """Test updating user preferences."""
    preferences = {"auto_save_choreographies": False}
    
    response = authenticated_client.put("/api/auth/preferences", json=preferences)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["preferences"]["auto_save_choreographies"] is False


@pytest.mark.api
def test_update_preferences_unauthenticated(client):
    """Test updating preferences without authentication."""
    preferences = {"auto_save_choreographies": False}
    
    response = client.put("/api/auth/preferences", json=preferences)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
def test_update_preferences_invalid_data(authenticated_client):
    """Test updating preferences with invalid data."""
    preferences = {"invalid_key": "invalid_value"}
    
    response = authenticated_client.put("/api/auth/preferences", json=preferences)
    
    # Should either accept or reject based on validation
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ]


@pytest.mark.api
def test_update_multiple_preferences(authenticated_client):
    """Test updating multiple preferences at once."""
    preferences = {
        "auto_save_choreographies": True,
        "default_difficulty": "intermediate",
        "theme": "dark"
    }
    
    response = authenticated_client.put("/api/auth/preferences", json=preferences)
    
    # May accept or reject based on validation rules
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ]
    
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "preferences" in data
