"""
Tests for user authentication views.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestRegistrationView:
    """Tests for user registration view"""
    
    def test_registration_page_loads(self):
        """Test that registration page loads successfully"""
        client = Client()
        url = reverse('users:register')
        response = client.get(url)
        assert response.status_code == 200
        assert 'form' in response.context
    
    def test_registration_creates_user(self):
        """Test that registration creates a new user"""
        client = Client()
        url = reverse('users:register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'display_name': 'New User',
            'password1': 'testpass123!@#',
            'password2': 'testpass123!@#',
        }
        response = client.post(url, data)
        
        # Should redirect to login
        assert response.status_code == 302
        assert response.url == reverse('users:login')
        
        # User should be created
        assert User.objects.filter(username='newuser').exists()
        user = User.objects.get(username='newuser')
        assert user.email == 'newuser@example.com'
        assert user.display_name == 'New User'
        assert user.check_password('testpass123!@#')
    
    def test_registration_with_invalid_data(self):
        """Test registration with invalid data"""
        client = Client()
        url = reverse('users:register')
        data = {
            'username': 'newuser',
            'email': 'invalid-email',
            'display_name': 'New User',
            'password1': 'testpass123',
            'password2': 'different',
        }
        response = client.post(url, data)
        
        # Should not redirect
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors


@pytest.mark.django_db
class TestLoginView:
    """Tests for login view"""
    
    def test_login_page_loads(self):
        """Test that login page loads successfully"""
        client = Client()
        url = reverse('users:login')
        response = client.get(url)
        assert response.status_code == 200
    
    def test_login_with_valid_credentials(self, test_user):
        """Test login with valid credentials"""
        client = Client()
        url = reverse('users:login')
        data = {
            'username': test_user.username,
            'password': 'testpass123',
        }
        response = client.post(url, data)
        
        # Should redirect to index
        assert response.status_code == 302
        assert response.url == reverse('choreography:index')
    
    def test_login_with_invalid_credentials(self, test_user):
        """Test login with invalid credentials"""
        client = Client()
        url = reverse('users:login')
        data = {
            'username': test_user.username,
            'password': 'wrongpassword',
        }
        response = client.post(url, data)
        
        # Should not redirect
        assert response.status_code == 200


@pytest.mark.django_db
class TestLogoutView:
    """Tests for logout view"""
    
    def test_logout_redirects(self, test_user):
        """Test that logout redirects to index"""
        client = Client()
        client.force_login(test_user)
        url = reverse('users:logout')
        response = client.post(url)
        
        # Should redirect to index
        assert response.status_code == 302
        assert response.url == reverse('choreography:index')


@pytest.mark.django_db
class TestProfileView:
    """Tests for profile view"""
    
    def test_profile_requires_authentication(self):
        """Test that profile view requires authentication"""
        client = Client()
        url = reverse('users:profile')
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
        assert reverse('users:login') in response.url
    
    def test_profile_page_loads_for_authenticated_user(self, test_user):
        """Test that profile page loads for authenticated user"""
        client = Client()
        client.force_login(test_user)
        url = reverse('users:profile')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
    
    def test_profile_update(self, test_user):
        """Test updating user profile"""
        client = Client()
        client.force_login(test_user)
        url = reverse('users:profile')
        data = {
            'display_name': 'Updated Name',
            'preferences': '{"theme": "dark"}',
        }
        response = client.post(url, data)
        
        # Should redirect back to profile
        assert response.status_code == 302
        assert response.url == reverse('users:profile')
        
        # User should be updated
        test_user.refresh_from_db()
        assert test_user.display_name == 'Updated Name'
