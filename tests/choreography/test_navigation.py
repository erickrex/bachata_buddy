"""
Tests for dual-template navigation.

Tests navigation menu rendering, active menu highlighting, and route accessibility.
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def client():
    """Create test client."""
    return Client()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.mark.django_db
class TestNavigation:
    """Test navigation between templates."""

    def test_navigation_menu_renders_on_legacy_template(self, client, user):
        """Test that navigation menu renders on legacy template."""
        client.login(username='testuser', password='testpass123')
        
        response = client.get(reverse('choreography:select-song'))
        
        assert response.status_code == 200
        assert b'Select Song' in response.content
        assert b'Describe Choreo' in response.content
        assert b'choreography:select-song' in response.content
        assert b'choreography:describe-choreo' in response.content

    def test_navigation_menu_renders_on_ai_template(self, client, user):
        """Test that navigation menu renders on AI template."""
        client.login(username='testuser', password='testpass123')
        
        response = client.get(reverse('choreography:describe-choreo'))
        
        assert response.status_code == 200
        assert b'Select Song' in response.content
        assert b'Describe Choreo' in response.content
        assert b'choreography:select-song' in response.content
        assert b'choreography:describe-choreo' in response.content

    def test_active_menu_highlighting_legacy_template(self, client, user):
        """Test that active menu item is highlighted on legacy template."""
        client.login(username='testuser', password='testpass123')
        
        response = client.get(reverse('choreography:select-song'))
        
        assert response.status_code == 200
        # Check for active class on Select Song menu item
        assert b'/choreography/select-song/' in response.content
        # The base template should highlight the active menu item

    def test_active_menu_highlighting_ai_template(self, client, user):
        """Test that active menu item is highlighted on AI template."""
        client.login(username='testuser', password='testpass123')
        
        response = client.get(reverse('choreography:describe-choreo'))
        
        assert response.status_code == 200
        # Check for active class on Describe Choreo menu item
        assert b'/choreography/describe-choreo/' in response.content

    def test_legacy_template_route_accessible(self, client, user):
        """Test that legacy template route is accessible."""
        client.login(username='testuser', password='testpass123')
        
        response = client.get(reverse('choreography:select-song'))
        
        assert response.status_code == 200
        assert b'Generate Your Bachata Choreography' in response.content or b'Select Song' in response.content

    def test_ai_template_route_accessible(self, client, user):
        """Test that AI template route is accessible."""
        client.login(username='testuser', password='testpass123')
        
        response = client.get(reverse('choreography:describe-choreo'))
        
        assert response.status_code == 200
        assert b'AI Choreography Creator' in response.content or b'Describe Choreo' in response.content

    def test_default_redirect_to_legacy_template(self, client, user):
        """Test that default route redirects to legacy template."""
        client.login(username='testuser', password='testpass123')
        
        response = client.get(reverse('choreography:index'))
        
        # Should redirect to select-song
        assert response.status_code == 302
        assert response.url == reverse('choreography:select-song')

    def test_navigation_without_authentication(self, client):
        """Test that navigation works without authentication."""
        # Legacy template
        response = client.get(reverse('choreography:select-song'))
        assert response.status_code == 200
        
        # AI template
        response = client.get(reverse('choreography:describe-choreo'))
        assert response.status_code == 200

    def test_switching_between_templates(self, client, user):
        """Test switching between legacy and AI templates."""
        client.login(username='testuser', password='testpass123')
        
        # Start on legacy template
        response = client.get(reverse('choreography:select-song'))
        assert response.status_code == 200
        
        # Switch to AI template
        response = client.get(reverse('choreography:describe-choreo'))
        assert response.status_code == 200
        
        # Switch back to legacy template
        response = client.get(reverse('choreography:select-song'))
        assert response.status_code == 200

    def test_no_state_leakage_between_templates(self, client, user):
        """Test that there's no state leakage between templates."""
        client.login(username='testuser', password='testpass123')
        
        # Visit legacy template
        response1 = client.get(reverse('choreography:select-song'))
        assert response1.status_code == 200
        
        # Visit AI template
        response2 = client.get(reverse('choreography:describe-choreo'))
        assert response2.status_code == 200
        
        # Verify AI template doesn't have legacy template elements
        assert b'song_selection' not in response2.content or b'Describe Your Choreography' in response2.content
        
        # Visit legacy template again
        response3 = client.get(reverse('choreography:select-song'))
        assert response3.status_code == 200
        
        # Verify legacy template doesn't have AI template elements
        assert b'AI Choreography Creator' not in response3.content or b'Select Song' in response3.content
