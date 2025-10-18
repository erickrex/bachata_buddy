"""
Tests for collection views (Task 6)
"""
import pytest
import json
from django.urls import reverse
from django.contrib.auth import get_user_model
from choreography.models import SavedChoreography

User = get_user_model()


@pytest.mark.django_db
class TestCollectionListView:
    """Tests for collection_list view"""
    
    def test_requires_authentication(self, client):
        """Test that collection_list requires login"""
        url = reverse('collections:list')
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login
        assert '/login/' in response.url
    
    def test_empty_collection(self, client, django_user):
        """Test collection_list with no choreographies"""
        client.force_login(django_user)
        url = reverse('collections:list')
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.context['choreographies']) == 0
    
    def test_displays_user_choreographies(self, client, django_user, saved_choreography):
        """Test collection_list displays user's choreographies"""
        client.force_login(django_user)
        url = reverse('collections:list')
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.context['choreographies']) == 1
        assert response.context['choreographies'][0] == saved_choreography
    
    def test_difficulty_filter(self, client, django_user):
        """Test filtering by difficulty"""
        client.force_login(django_user)
        
        # Create choreographies with different difficulties
        SavedChoreography.objects.create(
            user=django_user,
            title='Beginner Dance',
            difficulty='beginner',
            duration=120.0,
            video_path='test1.mp4'
        )
        SavedChoreography.objects.create(
            user=django_user,
            title='Advanced Dance',
            difficulty='advanced',
            duration=180.0,
            video_path='test2.mp4'
        )
        
        url = reverse('collections:list') + '?difficulty=beginner'
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.context['choreographies']) == 1
        assert response.context['choreographies'][0].difficulty == 'beginner'
    
    def test_search_filter(self, client, django_user):
        """Test search functionality"""
        client.force_login(django_user)
        
        SavedChoreography.objects.create(
            user=django_user,
            title='Salsa Dance',
            difficulty='beginner',
            duration=120.0,
            video_path='test1.mp4'
        )
        SavedChoreography.objects.create(
            user=django_user,
            title='Bachata Dance',
            difficulty='intermediate',
            duration=150.0,
            video_path='test2.mp4'
        )
        
        url = reverse('collections:list') + '?search=Salsa'
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.context['choreographies']) == 1
        assert 'Salsa' in response.context['choreographies'][0].title
    
    def test_pagination(self, client, django_user):
        """Test pagination with 20 items per page"""
        client.force_login(django_user)
        
        # Create 25 choreographies
        for i in range(25):
            SavedChoreography.objects.create(
                user=django_user,
                title=f'Dance {i}',
                difficulty='beginner',
                duration=120.0,
                video_path=f'test{i}.mp4'
            )
        
        url = reverse('collections:list')
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.context['choreographies']) == 20
        assert response.context['page_obj'].has_next()
        
        # Test page 2
        url = reverse('collections:list') + '?page=2'
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.context['choreographies']) == 5


@pytest.mark.django_db
class TestChoreographyDetailView:
    """Tests for choreography_detail view"""
    
    def test_requires_authentication(self, client, saved_choreography):
        """Test that choreography_detail requires login"""
        url = reverse('collections:detail', kwargs={'pk': saved_choreography.pk})
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login
    
    def test_displays_choreography(self, client, django_user, saved_choreography):
        """Test choreography_detail displays the choreography"""
        client.force_login(django_user)
        url = reverse('collections:detail', kwargs={'pk': saved_choreography.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['choreography'] == saved_choreography
    
    def test_returns_404_for_other_user(self, client, saved_choreography):
        """Test that users can't access other users' choreographies"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        client.force_login(other_user)
        url = reverse('collections:detail', kwargs={'pk': saved_choreography.pk})
        response = client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestChoreographyEditView:
    """Tests for choreography_edit view"""
    
    def test_requires_authentication(self, client, saved_choreography):
        """Test that choreography_edit requires login"""
        url = reverse('collections:edit', kwargs={'pk': saved_choreography.pk})
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login
    
    def test_displays_edit_form(self, client, django_user, saved_choreography):
        """Test choreography_edit displays the form"""
        client.force_login(django_user)
        url = reverse('collections:edit', kwargs={'pk': saved_choreography.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['choreography'] == saved_choreography
    
    def test_updates_choreography(self, client, django_user, saved_choreography):
        """Test choreography_edit updates the choreography"""
        client.force_login(django_user)
        url = reverse('collections:edit', kwargs={'pk': saved_choreography.pk})
        response = client.post(url, {
            'title': 'Updated Title',
            'difficulty': 'advanced'
        })
        assert response.status_code == 302  # Redirect to detail
        
        saved_choreography.refresh_from_db()
        assert saved_choreography.title == 'Updated Title'
        assert saved_choreography.difficulty == 'advanced'


@pytest.mark.django_db
class TestChoreographyDeleteView:
    """Tests for choreography_delete view"""
    
    def test_requires_authentication(self, client, saved_choreography):
        """Test that choreography_delete requires login"""
        url = reverse('collections:delete', kwargs={'pk': saved_choreography.pk})
        response = client.post(url)
        assert response.status_code == 302  # Redirect to login
    
    def test_deletes_choreography(self, client, django_user, saved_choreography):
        """Test choreography_delete removes the choreography"""
        client.force_login(django_user)
        url = reverse('collections:delete', kwargs={'pk': saved_choreography.pk})
        response = client.post(url)
        assert response.status_code == 302  # Redirect to list
        assert not SavedChoreography.objects.filter(pk=saved_choreography.pk).exists()
    
    def test_returns_json_for_htmx(self, client, django_user, saved_choreography):
        """Test choreography_delete returns JSON for HTMX requests"""
        client.force_login(django_user)
        url = reverse('collections:delete', kwargs={'pk': saved_choreography.pk})
        response = client.post(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert not SavedChoreography.objects.filter(pk=saved_choreography.pk).exists()


@pytest.mark.django_db
class TestSaveChoreographyView:
    """Tests for save_choreography view"""
    
    def test_requires_authentication(self, client):
        """Test that save_choreography requires login"""
        url = reverse('collections:save')
        response = client.post(url)
        assert response.status_code == 302  # Redirect to login
    
    def test_saves_choreography(self, client, django_user):
        """Test save_choreography creates a new choreography"""
        client.force_login(django_user)
        url = reverse('collections:save')
        response = client.post(url, {
            'title': 'New Dance',
            'difficulty': 'intermediate',
            'video_path': 'test.mp4',
            'duration': '150.5',
            'music_info': json.dumps({'song': 'Test Song'}),
            'generation_parameters': json.dumps({'param': 'value'})
        })
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'choreography_id' in data
        
        # Verify choreography was created
        choreography = SavedChoreography.objects.get(pk=data['choreography_id'])
        assert choreography.title == 'New Dance'
        assert choreography.user == django_user
        assert choreography.duration == 150.5
    
    def test_returns_error_for_invalid_data(self, client, django_user):
        """Test save_choreography returns error for invalid data"""
        client.force_login(django_user)
        url = reverse('collections:save')
        response = client.post(url, {
            'title': '',  # Invalid: empty title
            'difficulty': 'intermediate'
        })
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['success'] is False
        assert 'errors' in data


@pytest.mark.django_db
class TestCollectionStatsView:
    """Tests for collection_stats view"""
    
    def test_requires_authentication(self, client):
        """Test that collection_stats requires login"""
        url = reverse('collections:stats')
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login
    
    def test_returns_empty_stats(self, client, django_user):
        """Test collection_stats with no choreographies"""
        client.force_login(django_user)
        url = reverse('collections:stats')
        response = client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['total_count'] == 0
        assert data['total_duration'] == 0
        assert data['avg_duration'] == 0
    
    def test_calculates_stats(self, client, django_user):
        """Test collection_stats calculates correct statistics"""
        client.force_login(django_user)
        
        # Create choreographies
        SavedChoreography.objects.create(
            user=django_user,
            title='Dance 1',
            difficulty='beginner',
            duration=120.0,
            video_path='test1.mp4'
        )
        SavedChoreography.objects.create(
            user=django_user,
            title='Dance 2',
            difficulty='beginner',
            duration=180.0,
            video_path='test2.mp4'
        )
        SavedChoreography.objects.create(
            user=django_user,
            title='Dance 3',
            difficulty='advanced',
            duration=150.0,
            video_path='test3.mp4'
        )
        
        url = reverse('collections:stats')
        response = client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert data['total_count'] == 3
        assert data['total_duration'] == 450.0
        assert data['avg_duration'] == 150.0
        assert data['by_difficulty']['beginner'] == 2
        assert data['by_difficulty']['intermediate'] == 0
        assert data['by_difficulty']['advanced'] == 1
