"""
Tests for authentication endpoints
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import User


class RegistrationEndpointTests(TestCase):
    """Test suite for user registration endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
    
    def test_register_user_success(self):
        """Test successful user registration"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'display_name': 'Test User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
        self.assertEqual(response.data['user']['email'], 'test@example.com')
        self.assertEqual(response.data['user']['display_name'], 'Test User')
        
        # Verify user was created in database
        user = User.objects.get(username='testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('TestPass123!'))
    
    def test_register_user_password_mismatch(self):
        """Test registration fails when passwords don't match"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'password2': 'DifferentPass123!',
            'display_name': 'Test User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_register_user_weak_password(self):
        """Test registration fails with weak password"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123',
            'password2': '123',
            'display_name': 'Test User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_register_user_password_too_short(self):
        """Test registration fails when password is too short (less than 8 characters)"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Short1!',  # Only 7 characters
            'password2': 'Short1!',
            'display_name': 'Test User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_register_user_password_too_common(self):
        """Test registration fails with common password"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',  # Common password
            'password2': 'password123',
            'display_name': 'Test User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_register_user_password_entirely_numeric(self):
        """Test registration fails when password is entirely numeric"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '12345678',  # All numbers
            'password2': '12345678',
            'display_name': 'Test User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_register_user_duplicate_username(self):
        """Test registration fails with duplicate username"""
        # Create first user
        User.objects.create_user(
            username='testuser',
            email='first@example.com',
            password='TestPass123!'
        )
        
        # Try to create second user with same username
        data = {
            'username': 'testuser',
            'email': 'second@example.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'display_name': 'Test User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
    
    def test_register_user_missing_required_fields(self):
        """Test registration fails when required fields are missing"""
        data = {
            'username': 'testuser',
            # Missing email, password, password2
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_register_user_returns_jwt_tokens(self):
        """Test that registration returns valid JWT tokens"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'display_name': 'Test User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify tokens are strings and not empty
        self.assertIsInstance(response.data['access'], str)
        self.assertIsInstance(response.data['refresh'], str)
        self.assertGreater(len(response.data['access']), 0)
        self.assertGreater(len(response.data['refresh']), 0)
        
        # Verify we can use the access token to access protected endpoints
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile_url = reverse('profile')
        profile_response = self.client.get(profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)


class LoginEndpointTests(TestCase):
    """Test suite for user login endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('login')
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            display_name='Test User'
        )
    
    def test_login_success(self):
        """Test successful login with valid credentials"""
        data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
        self.assertEqual(response.data['user']['email'], 'test@example.com')
        self.assertEqual(response.data['user']['display_name'], 'Test User')
    
    def test_login_invalid_username(self):
        """Test login fails with invalid username"""
        data = {
            'username': 'wronguser',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Invalid username or password')
    
    def test_login_invalid_password(self):
        """Test login fails with invalid password"""
        data = {
            'username': 'testuser',
            'password': 'WrongPassword123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Invalid username or password')
    
    def test_login_missing_username(self):
        """Test login fails when username is missing"""
        data = {
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
    
    def test_login_missing_password(self):
        """Test login fails when password is missing"""
        data = {
            'username': 'testuser'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_login_inactive_user(self):
        """Test login fails for inactive user"""
        # Create inactive user
        inactive_user = User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='TestPass123!',
            is_active=False
        )
        
        data = {
            'username': 'inactiveuser',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'User account is disabled')
    
    def test_login_returns_valid_jwt_tokens(self):
        """Test that login returns valid JWT tokens"""
        data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify tokens are strings and not empty
        self.assertIsInstance(response.data['access'], str)
        self.assertIsInstance(response.data['refresh'], str)
        self.assertGreater(len(response.data['access']), 0)
        self.assertGreater(len(response.data['refresh']), 0)
        
        # Verify we can use the access token to access protected endpoints
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile_url = reverse('profile')
        profile_response = self.client.get(profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['username'], 'testuser')
    
    def test_login_case_sensitive_username(self):
        """Test that username is case-sensitive"""
        data = {
            'username': 'TESTUSER',  # Different case
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)


class UserProfileEndpointTests(TestCase):
    """Test suite for user profile endpoint GET /api/auth/me"""
    
    def setUp(self):
        self.client = APIClient()
        self.profile_url = reverse('profile')
        self.login_url = reverse('login')
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            display_name='Test User'
        )
    
    def test_get_profile_success(self):
        """Test successful retrieval of user profile with valid token"""
        # Login to get access token
        login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        access_token = login_response.data['access']
        
        # Get profile with access token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['display_name'], 'Test User')
        self.assertIn('id', response.data)
        self.assertIn('is_instructor', response.data)
        self.assertIn('preferences', response.data)
    
    def test_get_profile_without_authentication(self):
        """Test that profile endpoint requires authentication"""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_profile_with_invalid_token(self):
        """Test profile endpoint fails with invalid token"""
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_profile_returns_correct_fields(self):
        """Test that profile endpoint returns all expected fields"""
        # Login to get access token
        login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        access_token = login_response.data['access']
        
        # Get profile
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all expected fields are present
        expected_fields = ['id', 'username', 'email', 'display_name', 'is_instructor', 'preferences']
        for field in expected_fields:
            self.assertIn(field, response.data)
        
        # Verify password is not included
        self.assertNotIn('password', response.data)
    
    def test_get_profile_with_instructor_user(self):
        """Test profile endpoint for instructor user"""
        # Create instructor user
        instructor = User.objects.create_user(
            username='instructor',
            email='instructor@example.com',
            password='TestPass123!',
            display_name='Instructor User',
            is_instructor=True
        )
        
        # Login as instructor
        login_data = {
            'username': 'instructor',
            'password': 'TestPass123!'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        access_token = login_response.data['access']
        
        # Get profile
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_instructor'], True)
    
    def test_get_profile_with_preferences(self):
        """Test profile endpoint returns user preferences"""
        # Update user with preferences
        self.user.preferences = {'theme': 'dark', 'language': 'en'}
        self.user.save()
        
        # Login to get access token
        login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        access_token = login_response.data['access']
        
        # Get profile
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['preferences'], {'theme': 'dark', 'language': 'en'})


class UpdateProfileEndpointTests(TestCase):
    """Test suite for user profile update endpoint PUT /api/auth/me"""
    
    def setUp(self):
        self.client = APIClient()
        self.profile_url = reverse('profile')
        self.login_url = reverse('login')
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            display_name='Test User'
        )
        
        # Login to get access token
        login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
    
    def test_update_profile_display_name(self):
        """Test updating user display name"""
        update_data = {
            'display_name': 'Updated Name'
        }
        
        response = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Name')
        
        # Verify database was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, 'Updated Name')
    
    def test_update_profile_email(self):
        """Test updating user email"""
        update_data = {
            'email': 'newemail@example.com'
        }
        
        response = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'newemail@example.com')
        
        # Verify database was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')
    
    def test_update_profile_preferences(self):
        """Test updating user preferences"""
        update_data = {
            'preferences': {'theme': 'dark', 'language': 'es'}
        }
        
        response = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['preferences'], {'theme': 'dark', 'language': 'es'})
        
        # Verify database was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferences, {'theme': 'dark', 'language': 'es'})
    
    def test_update_profile_multiple_fields(self):
        """Test updating multiple profile fields at once"""
        update_data = {
            'display_name': 'New Display Name',
            'email': 'updated@example.com',
            'preferences': {'theme': 'light'}
        }
        
        response = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'New Display Name')
        self.assertEqual(response.data['email'], 'updated@example.com')
        self.assertEqual(response.data['preferences'], {'theme': 'light'})
        
        # Verify database was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, 'New Display Name')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.preferences, {'theme': 'light'})
    
    def test_update_profile_partial_update(self):
        """Test partial update (only some fields)"""
        # Set initial preferences
        self.user.preferences = {'theme': 'dark', 'language': 'en'}
        self.user.save()
        
        # Update only display_name
        update_data = {
            'display_name': 'Partial Update'
        }
        
        response = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Partial Update')
        # Other fields should remain unchanged
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['username'], 'testuser')
    
    def test_update_profile_without_authentication(self):
        """Test that update profile requires authentication"""
        self.client.credentials()  # Remove authentication
        
        update_data = {
            'display_name': 'Should Fail'
        }
        
        response = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_profile_with_invalid_token(self):
        """Test update profile fails with invalid token"""
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")
        
        update_data = {
            'display_name': 'Should Fail'
        }
        
        response = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_profile_cannot_change_username(self):
        """Test that username cannot be changed (read-only)"""
        update_data = {
            'username': 'newusername'
        }
        
        response = self.client.put(self.profile_url, update_data, format='json')
        
        # Should succeed but username should not change
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        
        # Verify database was not updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'testuser')
    
    def test_update_profile_invalid_email_format(self):
        """Test update fails with invalid email format"""
        update_data = {
            'email': 'not-a-valid-email'
        }
        
        response = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_update_profile_empty_data(self):
        """Test update with empty data returns current profile"""
        update_data = {}
        
        response = self.client.put(self.profile_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['display_name'], 'Test User')


class TokenRefreshEndpointTests(TestCase):
    """Test suite for JWT token refresh endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.refresh_url = reverse('refresh')
        self.login_url = reverse('login')
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            display_name='Test User'
        )
    
    def test_refresh_token_success(self):
        """Test successful token refresh with valid refresh token"""
        # First login to get tokens
        login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']
        old_access_token = login_response.data['access']
        
        # Use refresh token to get new access token
        refresh_data = {
            'refresh': refresh_token
        }
        response = self.client.post(self.refresh_url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verify new tokens are different from old ones
        self.assertNotEqual(response.data['access'], old_access_token)
        self.assertNotEqual(response.data['refresh'], refresh_token)
        
        # Verify new access token works
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile_url = reverse('profile')
        profile_response = self.client.get(profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
    
    def test_refresh_token_invalid(self):
        """Test token refresh fails with invalid refresh token"""
        refresh_data = {
            'refresh': 'invalid.token.here'
        }
        
        response = self.client.post(self.refresh_url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_refresh_token_missing(self):
        """Test token refresh fails when refresh token is missing"""
        refresh_data = {}
        
        response = self.client.post(self.refresh_url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('refresh', response.data)
    
    def test_refresh_token_blacklisted(self):
        """Test that old refresh token is blacklisted after rotation"""
        # First login to get tokens
        login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']
        
        # Use refresh token to get new tokens
        refresh_data = {
            'refresh': refresh_token
        }
        first_refresh_response = self.client.post(self.refresh_url, refresh_data, format='json')
        self.assertEqual(first_refresh_response.status_code, status.HTTP_200_OK)
        
        # Try to use the old refresh token again (should fail because it's blacklisted)
        second_refresh_response = self.client.post(self.refresh_url, refresh_data, format='json')
        self.assertEqual(second_refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_refresh_token_returns_new_tokens(self):
        """Test that refresh returns both new access and refresh tokens"""
        # First login to get tokens
        login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']
        
        # Use refresh token
        refresh_data = {
            'refresh': refresh_token
        }
        response = self.client.post(self.refresh_url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify both tokens are returned
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verify tokens are strings and not empty
        self.assertIsInstance(response.data['access'], str)
        self.assertIsInstance(response.data['refresh'], str)
        self.assertGreater(len(response.data['access']), 0)
        self.assertGreater(len(response.data['refresh']), 0)
    
    def test_refresh_token_multiple_times(self):
        """Test that we can refresh tokens multiple times in sequence"""
        # First login to get tokens
        login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']
        
        # Refresh multiple times
        for i in range(3):
            refresh_data = {
                'refresh': refresh_token
            }
            response = self.client.post(self.refresh_url, refresh_data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('access', response.data)
            self.assertIn('refresh', response.data)
            
            # Use the new refresh token for next iteration
            refresh_token = response.data['refresh']
            
            # Verify new access token works
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
            profile_url = reverse('profile')
            profile_response = self.client.get(profile_url)
            self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
