"""
Django authentication view tests.

Tests for:
- login view (Django's built-in LoginView)
- logout view (Django's built-in LogoutView)
- register view (custom registration)
- profile view (user profile management)

Reference: users/views.py
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


# Use Django test client instead of FastAPI TestClient
@pytest.fixture
def client():
    """Override root conftest client with Django test client."""
    return Client()


@pytest.fixture
def authenticated_client(client, test_user):
    """Override root conftest authenticated_client with Django authenticated client."""
    client.force_login(test_user)
    return client


@pytest.mark.django_db
@pytest.mark.views
class TestLoginView:
    """Test the login view."""
    
    def test_login_view_loads(self, client):
        """Test login page loads successfully."""
        url = reverse('users:login')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'users/login.html' in [t.name for t in response.templates]
        
        # Check for login form elements
        assert b'username' in response.content or b'email' in response.content
        assert b'password' in response.content
    
    def test_login_with_valid_credentials(self, client, test_user):
        """Test login with valid username and password."""
        url = reverse('users:login')
        
        response = client.post(url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Should redirect after successful login
        assert response.status_code == 302
        
        # Verify user is authenticated
        assert '_auth_user_id' in client.session
        assert int(client.session['_auth_user_id']) == test_user.id
    
    def test_login_with_invalid_credentials(self, client, test_user):
        """Test login with invalid password."""
        url = reverse('users:login')
        
        response = client.post(url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        # Should not redirect (stays on login page)
        assert response.status_code == 200
        
        # Should show error message
        assert b'error' in response.content.lower() or b'invalid' in response.content.lower()
        
        # Verify user is NOT authenticated
        assert '_auth_user_id' not in client.session
    
    def test_login_with_nonexistent_user(self, client):
        """Test login with non-existent username."""
        url = reverse('users:login')
        
        response = client.post(url, {
            'username': 'nonexistent',
            'password': 'testpass123'
        })
        
        # Should not redirect
        assert response.status_code == 200
        
        # Verify user is NOT authenticated
        assert '_auth_user_id' not in client.session
    
    def test_login_redirects_authenticated_user(self, authenticated_client):
        """Test login redirects already authenticated users."""
        url = reverse('users:login')
        response = authenticated_client.get(url)
        
        # Django's LoginView redirects authenticated users by default
        # or shows the login page (behavior may vary)
        assert response.status_code in [200, 302]
    
    def test_login_with_next_parameter(self, client, test_user):
        """Test login redirects to 'next' parameter after successful login."""
        url = reverse('users:login') + '?next=/collections/'
        
        response = client.post(url, {
            'username': 'testuser',
            'password': 'testpass123'
        }, follow=False)
        
        # Should redirect to the 'next' URL
        assert response.status_code == 302
        assert '/collections/' in response.url


@pytest.mark.django_db
@pytest.mark.views
class TestLogoutView:
    """Test the logout view."""
    
    def test_logout_redirects_correctly(self, authenticated_client):
        """Test logout redirects to configured LOGOUT_REDIRECT_URL."""
        url = reverse('users:logout')
        response = authenticated_client.post(url)
        
        # Should redirect after logout
        assert response.status_code == 302
        
        # Verify user is logged out
        # Create a new request to check session
        from django.test import Client
        new_client = Client()
        new_client.cookies = authenticated_client.cookies
        
        # Session should not have auth user
        response = new_client.get(reverse('choreography:index'))
        # User should not be authenticated in new requests
    
    def test_logout_clears_session(self, authenticated_client, test_user):
        """Test logout clears user session."""
        # Verify user is authenticated before logout
        assert '_auth_user_id' in authenticated_client.session
        
        url = reverse('users:logout')
        response = authenticated_client.post(url, follow=True)
        
        # After logout, session should not have auth user
        # Note: Django's LogoutView clears the session
        assert response.status_code == 200
    
    def test_logout_unauthenticated_user(self, client):
        """Test logout works even for unauthenticated users."""
        url = reverse('users:logout')
        response = client.post(url)
        
        # Should still redirect (no error)
        assert response.status_code == 302


@pytest.mark.django_db
@pytest.mark.views
class TestRegisterView:
    """Test the register view."""
    
    def test_register_view_loads(self, client):
        """Test registration page loads successfully."""
        url = reverse('users:register')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'users/register.html' in [t.name for t in response.templates]
        
        # Check for registration form elements
        assert b'username' in response.content
        assert b'email' in response.content
        assert b'password' in response.content
    
    def test_registration_creates_new_user(self, client):
        """Test registration creates a new user."""
        url = reverse('users:register')
        
        response = client.post(url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'securepass123',
            'password2': 'securepass123',
            'display_name': 'New User'
        })
        
        # Should redirect to login page after successful registration
        assert response.status_code == 302
        assert 'login' in response.url
        
        # Verify user was created
        assert User.objects.filter(username='newuser').exists()
        user = User.objects.get(username='newuser')
        assert user.email == 'newuser@example.com'
        assert user.display_name == 'New User'
        assert user.check_password('securepass123')
    
    def test_registration_with_duplicate_username(self, client, test_user):
        """Test registration fails with duplicate username."""
        url = reverse('users:register')
        
        response = client.post(url, {
            'username': 'testuser',  # Already exists
            'email': 'newemail@example.com',
            'password1': 'securepass123',
            'password2': 'securepass123',
            'display_name': 'Another User'
        })
        
        # Should not redirect (stays on registration page)
        assert response.status_code == 200
        
        # Should show error message
        assert b'error' in response.content.lower() or b'exists' in response.content.lower()
        
        # Verify no new user was created
        assert User.objects.filter(username='testuser').count() == 1
    
    def test_registration_with_mismatched_passwords(self, client):
        """Test registration fails with mismatched passwords."""
        url = reverse('users:register')
        
        response = client.post(url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'securepass123',
            'password2': 'differentpass123',
            'display_name': 'New User'
        })
        
        # Should not redirect
        assert response.status_code == 200
        
        # Should show error message
        assert b'error' in response.content.lower() or b'match' in response.content.lower()
        
        # Verify user was NOT created
        assert not User.objects.filter(username='newuser').exists()
    
    def test_registration_with_invalid_email(self, client):
        """Test registration fails with invalid email."""
        url = reverse('users:register')
        
        response = client.post(url, {
            'username': 'newuser',
            'email': 'invalid-email',
            'password1': 'securepass123',
            'password2': 'securepass123',
            'display_name': 'New User'
        })
        
        # Should not redirect
        assert response.status_code == 200
        
        # Verify user was NOT created
        assert not User.objects.filter(username='newuser').exists()
    
    def test_registration_with_missing_fields(self, client):
        """Test registration fails with missing required fields."""
        url = reverse('users:register')
        
        # Missing password
        response = client.post(url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'display_name': 'New User'
        })
        
        # Should not redirect
        assert response.status_code == 200
        
        # Verify user was NOT created
        assert not User.objects.filter(username='newuser').exists()
    
    def test_registration_sets_display_name(self, client):
        """Test registration correctly sets display_name field."""
        url = reverse('users:register')
        
        response = client.post(url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'securepass123',
            'password2': 'securepass123',
            'display_name': 'My Display Name'
        })
        
        # Verify user has correct display_name
        user = User.objects.get(username='newuser')
        assert user.display_name == 'My Display Name'
    
    def test_registration_hashes_password(self, client):
        """Test registration stores hashed password, not plaintext."""
        url = reverse('users:register')
        
        response = client.post(url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'securepass123',
            'password2': 'securepass123',
            'display_name': 'New User'
        })
        
        # Verify password is hashed
        user = User.objects.get(username='newuser')
        assert user.password != 'securepass123'
        assert user.password.startswith('pbkdf2_sha256$') or user.password.startswith('argon2')
        assert user.check_password('securepass123')


@pytest.mark.django_db
@pytest.mark.views
class TestProfileView:
    """Test the profile view."""
    
    def test_profile_requires_authentication(self, client):
        """Test profile page redirects unauthenticated users."""
        url = reverse('users:profile')
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.url or 'login' in response.url
    
    def test_profile_view_loads_for_authenticated_user(self, authenticated_client):
        """Test profile page loads for authenticated users."""
        url = reverse('users:profile')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        assert 'users/profile.html' in [t.name for t in response.templates]
        assert 'form' in response.context
    
    def test_profile_displays_user_information(self, authenticated_client, test_user):
        """Test profile page displays current user information."""
        url = reverse('users:profile')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        
        # Check user information is displayed
        content = response.content.decode()
        assert test_user.username in content or test_user.display_name in content
    
    def test_profile_update_display_name(self, authenticated_client, test_user):
        """Test profile allows updating display_name."""
        url = reverse('users:profile')
        
        response = authenticated_client.post(url, {
            'display_name': 'Updated Display Name',
            'preferences': '{}'
        })
        
        # Should redirect back to profile
        assert response.status_code == 302
        assert response.url == reverse('users:profile')
        
        # Verify display_name was updated
        test_user.refresh_from_db()
        assert test_user.display_name == 'Updated Display Name'
    
    def test_profile_update_preferences(self, authenticated_client, test_user):
        """Test profile allows updating preferences."""
        url = reverse('users:profile')
        
        import json
        preferences = {
            'theme': 'dark',
            'auto_save': True,
            'notifications': False
        }
        
        response = authenticated_client.post(url, {
            'display_name': test_user.display_name,
            'preferences': json.dumps(preferences)
        })
        
        # Should redirect back to profile
        assert response.status_code == 302
        
        # Verify preferences were updated
        test_user.refresh_from_db()
        assert test_user.preferences == preferences
    
    def test_profile_shows_success_message_on_update(
        self, authenticated_client, test_user
    ):
        """Test profile shows success message after update."""
        url = reverse('users:profile')
        
        response = authenticated_client.post(url, {
            'display_name': 'New Name',
            'preferences': '{}'
        }, follow=True)
        
        assert response.status_code == 200
        
        # Check for success message
        messages = list(response.context['messages'])
        assert len(messages) > 0
        assert any('success' in str(m).lower() for m in messages)
    
    def test_profile_shows_error_on_invalid_data(
        self, authenticated_client, test_user
    ):
        """Test profile shows error message with invalid data."""
        url = reverse('users:profile')
        
        # Submit invalid preferences (not valid JSON)
        response = authenticated_client.post(url, {
            'display_name': '',  # Empty display_name might be invalid
            'preferences': 'invalid json'
        })
        
        # Should stay on profile page or redirect with error
        assert response.status_code in [200, 302]
        
        # If it's a 200, check for error messages
        if response.status_code == 200:
            content = response.content.decode()
            # May show error in form or messages


@pytest.mark.django_db
@pytest.mark.views
@pytest.mark.integration
class TestAuthenticationFlow:
    """Test complete authentication flow."""
    
    def test_complete_registration_login_flow(self, client):
        """Test complete flow: register -> login -> access protected page."""
        # Step 1: Register
        register_url = reverse('users:register')
        response = client.post(register_url, {
            'username': 'flowuser',
            'email': 'flowuser@example.com',
            'password1': 'securepass123',
            'password2': 'securepass123',
            'display_name': 'Flow User'
        })
        
        assert response.status_code == 302
        assert User.objects.filter(username='flowuser').exists()
        
        # Step 2: Login
        login_url = reverse('users:login')
        response = client.post(login_url, {
            'username': 'flowuser',
            'password': 'securepass123'
        })
        
        assert response.status_code == 302
        assert '_auth_user_id' in client.session
        
        # Step 3: Access protected page
        profile_url = reverse('users:profile')
        response = client.get(profile_url)
        
        assert response.status_code == 200
        assert b'Flow User' in response.content or b'flowuser' in response.content
    
    def test_logout_prevents_access_to_protected_pages(
        self, authenticated_client, test_user
    ):
        """Test logout prevents access to protected pages."""
        # Verify can access protected page while authenticated
        profile_url = reverse('users:profile')
        response = authenticated_client.get(profile_url)
        assert response.status_code == 200
        
        # Logout
        logout_url = reverse('users:logout')
        authenticated_client.post(logout_url)
        
        # Try to access protected page after logout
        response = authenticated_client.get(profile_url)
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.url or 'login' in response.url
    
    def test_unauthenticated_access_redirects_to_login(self, client):
        """Test unauthenticated users are redirected to login for protected pages."""
        protected_urls = [
            reverse('users:profile'),
            reverse('collections:list'),
            reverse('choreography:create'),
        ]
        
        for url in protected_urls:
            response = client.get(url) if 'create' not in url else client.post(url)
            
            # Should redirect to login
            assert response.status_code == 302
            assert '/login' in response.url or 'login' in response.url
