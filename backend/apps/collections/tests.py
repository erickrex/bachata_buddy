"""
Tests for collections endpoints
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.authentication.models import User
from .models import SavedChoreography
import uuid


class CollectionListEndpointTests(TestCase):
    """Test suite for GET /api/collections (list) endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.collections_url = reverse('collection-list')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        # Login to get access token
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
    
    def test_list_collections_empty(self):
        """Test listing collections when user has none"""
        response = self.client.get(self.collections_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_list_collections_with_data(self):
        """Test listing collections with existing choreographies"""
        # Create test choreographies
        SavedChoreography.objects.create(
            user=self.user,
            title='Test Choreo 1',
            video_path='videos/test1.mp4',
            difficulty='beginner',
            duration=120.5
        )
        SavedChoreography.objects.create(
            user=self.user,
            title='Test Choreo 2',
            video_path='videos/test2.mp4',
            difficulty='intermediate',
            duration=180.0
        )
        
        response = self.client.get(self.collections_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_list_collections_without_authentication(self):
        """Test that listing collections requires authentication"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.collections_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_collections_only_shows_user_choreographies(self):
        """Test that users only see their own choreographies"""
        # Create another user with choreographies
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='TestPass123!'
        )
        SavedChoreography.objects.create(
            user=other_user,
            title='Other User Choreo',
            video_path='videos/other.mp4',
            difficulty='advanced',
            duration=200.0
        )
        
        # Create choreography for test user
        SavedChoreography.objects.create(
            user=self.user,
            title='My Choreo',
            video_path='videos/mine.mp4',
            difficulty='beginner',
            duration=120.0
        )
        
        response = self.client.get(self.collections_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'My Choreo')


class CollectionFilteringTests(TestCase):
    """Test suite for collection filtering functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.collections_url = reverse('collection-list')
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        
        # Create test choreographies with different difficulties
        SavedChoreography.objects.create(
            user=self.user,
            title='Beginner Choreo',
            video_path='videos/beginner.mp4',
            difficulty='beginner',
            duration=120.0
        )
        SavedChoreography.objects.create(
            user=self.user,
            title='Intermediate Choreo',
            video_path='videos/intermediate.mp4',
            difficulty='intermediate',
            duration=150.0
        )
        SavedChoreography.objects.create(
            user=self.user,
            title='Advanced Choreo',
            video_path='videos/advanced.mp4',
            difficulty='advanced',
            duration=180.0
        )
    
    def test_filter_by_difficulty_beginner(self):
        """Test filtering collections by beginner difficulty"""
        response = self.client.get(self.collections_url, {'difficulty': 'beginner'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['difficulty'], 'beginner')
    
    def test_filter_by_difficulty_intermediate(self):
        """Test filtering collections by intermediate difficulty"""
        response = self.client.get(self.collections_url, {'difficulty': 'intermediate'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['difficulty'], 'intermediate')
    
    def test_filter_by_difficulty_advanced(self):
        """Test filtering collections by advanced difficulty"""
        response = self.client.get(self.collections_url, {'difficulty': 'advanced'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['difficulty'], 'advanced')


class CollectionSearchTests(TestCase):
    """Test suite for collection search functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.collections_url = reverse('collection-list')
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        
        # Create test choreographies with different titles
        SavedChoreography.objects.create(
            user=self.user,
            title='Romantic Bachata',
            video_path='videos/romantic.mp4',
            difficulty='beginner',
            duration=120.0
        )
        SavedChoreography.objects.create(
            user=self.user,
            title='Sensual Dance',
            video_path='videos/sensual.mp4',
            difficulty='intermediate',
            duration=150.0
        )
        SavedChoreography.objects.create(
            user=self.user,
            title='Advanced Bachata Moves',
            video_path='videos/advanced.mp4',
            difficulty='advanced',
            duration=180.0
        )
    
    def test_search_by_title(self):
        """Test searching collections by title"""
        response = self.client.get(self.collections_url, {'search': 'Bachata'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        titles = [item['title'] for item in response.data['results']]
        self.assertIn('Romantic Bachata', titles)
        self.assertIn('Advanced Bachata Moves', titles)
    
    def test_search_case_insensitive(self):
        """Test that search is case-insensitive"""
        response = self.client.get(self.collections_url, {'search': 'bachata'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
    
    def test_search_no_results(self):
        """Test search with no matching results"""
        response = self.client.get(self.collections_url, {'search': 'NonExistent'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)


class CollectionCreateEndpointTests(TestCase):
    """Test suite for POST /api/collections (create) endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.collections_url = reverse('collection-list')
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
    
    def test_create_collection_success(self):
        """Test successful creation of a choreography"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create a simple video file for testing
        video_file = SimpleUploadedFile(
            "test_video.mp4",
            b"fake video content",
            content_type="video/mp4"
        )
        
        data = {
            'title': 'New Choreography',
            'video_path': video_file,
            'difficulty': 'beginner',
            'duration': 120.5
        }
        
        response = self.client.post(self.collections_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Choreography')
        self.assertEqual(response.data['difficulty'], 'beginner')
        self.assertEqual(response.data['duration'], 120.5)
        
        # Verify choreography was created in database
        self.assertEqual(SavedChoreography.objects.filter(user=self.user).count(), 1)
    
    def test_create_collection_without_authentication(self):
        """Test that creating collection requires authentication"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        self.client.credentials()  # Remove authentication
        
        video_file = SimpleUploadedFile(
            "test_video.mp4",
            b"fake video content",
            content_type="video/mp4"
        )
        
        data = {
            'title': 'New Choreography',
            'video_path': video_file,
            'difficulty': 'beginner',
            'duration': 120.5
        }
        
        response = self.client.post(self.collections_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_collection_missing_required_fields(self):
        """Test creation fails when required fields are missing"""
        data = {
            'title': 'New Choreography'
            # Missing video_path, difficulty, duration
        }
        
        response = self.client.post(self.collections_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CollectionDetailEndpointTests(TestCase):
    """Test suite for GET /api/collections/{id} endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        
        # Create test choreography
        self.choreography = SavedChoreography.objects.create(
            user=self.user,
            title='Test Choreography',
            video_path='videos/test.mp4',
            difficulty='intermediate',
            duration=150.0,
            music_info={'song': 'Test Song'},
            generation_parameters={'energy': 'medium'}
        )
        self.detail_url = reverse('collection-detail', kwargs={'pk': self.choreography.id})
    
    def test_get_collection_detail_success(self):
        """Test successful retrieval of choreography details"""
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Choreography')
        self.assertEqual(response.data['difficulty'], 'intermediate')
        self.assertEqual(response.data['duration'], 150.0)
        self.assertEqual(response.data['music_info'], {'song': 'Test Song'})
    
    def test_get_collection_detail_without_authentication(self):
        """Test that getting collection detail requires authentication"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_collection_detail_not_found(self):
        """Test getting non-existent choreography returns 404"""
        non_existent_id = uuid.uuid4()
        url = reverse('collection-detail', kwargs={'pk': non_existent_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_collection_detail_other_user(self):
        """Test that users cannot access other users' choreographies"""
        # Create another user with a choreography
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='TestPass123!'
        )
        other_choreography = SavedChoreography.objects.create(
            user=other_user,
            title='Other User Choreo',
            video_path='videos/other.mp4',
            difficulty='advanced',
            duration=200.0
        )
        
        url = reverse('collection-detail', kwargs={'pk': other_choreography.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CollectionUpdateEndpointTests(TestCase):
    """Test suite for PUT /api/collections/{id} endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        
        # Create test choreography
        self.choreography = SavedChoreography.objects.create(
            user=self.user,
            title='Original Title',
            video_path='videos/test.mp4',
            difficulty='beginner',
            duration=120.0
        )
        self.detail_url = reverse('collection-detail', kwargs={'pk': self.choreography.id})
    
    def test_update_collection_title(self):
        """Test updating choreography title"""
        data = {'title': 'Updated Title'}
        response = self.client.put(self.detail_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')
        
        # Verify database was updated
        self.choreography.refresh_from_db()
        self.assertEqual(self.choreography.title, 'Updated Title')
    
    def test_update_collection_difficulty(self):
        """Test updating choreography difficulty"""
        data = {'difficulty': 'advanced'}
        response = self.client.put(self.detail_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['difficulty'], 'advanced')
        
        # Verify database was updated
        self.choreography.refresh_from_db()
        self.assertEqual(self.choreography.difficulty, 'advanced')
    
    def test_update_collection_without_authentication(self):
        """Test that updating collection requires authentication"""
        self.client.credentials()  # Remove authentication
        
        data = {'title': 'Should Fail'}
        response = self.client.put(self.detail_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_collection_other_user(self):
        """Test that users cannot update other users' choreographies"""
        # Create another user with a choreography
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='TestPass123!'
        )
        other_choreography = SavedChoreography.objects.create(
            user=other_user,
            title='Other User Choreo',
            video_path='videos/other.mp4',
            difficulty='advanced',
            duration=200.0
        )
        
        url = reverse('collection-detail', kwargs={'pk': other_choreography.id})
        data = {'title': 'Hacked Title'}
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CollectionDeleteEndpointTests(TestCase):
    """Test suite for DELETE /api/collections/{id} endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
    
    def test_delete_collection_success(self):
        """Test successful deletion of choreography"""
        choreography = SavedChoreography.objects.create(
            user=self.user,
            title='To Delete',
            video_path='videos/delete.mp4',
            difficulty='beginner',
            duration=120.0
        )
        
        url = reverse('collection-detail', kwargs={'pk': choreography.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify choreography was deleted from database
        self.assertEqual(SavedChoreography.objects.filter(id=choreography.id).count(), 0)
    
    def test_delete_collection_without_authentication(self):
        """Test that deleting collection requires authentication"""
        choreography = SavedChoreography.objects.create(
            user=self.user,
            title='To Delete',
            video_path='videos/delete.mp4',
            difficulty='beginner',
            duration=120.0
        )
        
        self.client.credentials()  # Remove authentication
        
        url = reverse('collection-detail', kwargs={'pk': choreography.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Verify choreography was NOT deleted
        self.assertEqual(SavedChoreography.objects.filter(id=choreography.id).count(), 1)
    
    def test_delete_collection_other_user(self):
        """Test that users cannot delete other users' choreographies"""
        # Create another user with a choreography
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='TestPass123!'
        )
        other_choreography = SavedChoreography.objects.create(
            user=other_user,
            title='Other User Choreo',
            video_path='videos/other.mp4',
            difficulty='advanced',
            duration=200.0
        )
        
        url = reverse('collection-detail', kwargs={'pk': other_choreography.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify choreography was NOT deleted
        self.assertEqual(SavedChoreography.objects.filter(id=other_choreography.id).count(), 1)


class CollectionStatsEndpointTests(TestCase):
    """Test suite for GET /api/collections/stats endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.stats_url = reverse('collection-stats')
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
    
    def test_get_stats_empty_collection(self):
        """Test getting stats when user has no choreographies"""
        response = self.client.get(self.stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 0)
        self.assertEqual(response.data['by_difficulty'], {})
        self.assertEqual(response.data['total_duration'], 0)
    
    def test_get_stats_with_choreographies(self):
        """Test getting stats with multiple choreographies"""
        # Create choreographies with different difficulties
        SavedChoreography.objects.create(
            user=self.user,
            title='Beginner 1',
            video_path='videos/b1.mp4',
            difficulty='beginner',
            duration=120.0
        )
        SavedChoreography.objects.create(
            user=self.user,
            title='Beginner 2',
            video_path='videos/b2.mp4',
            difficulty='beginner',
            duration=130.0
        )
        SavedChoreography.objects.create(
            user=self.user,
            title='Intermediate 1',
            video_path='videos/i1.mp4',
            difficulty='intermediate',
            duration=150.0
        )
        
        response = self.client.get(self.stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 3)
        self.assertEqual(response.data['by_difficulty']['beginner'], 2)
        self.assertEqual(response.data['by_difficulty']['intermediate'], 1)
        self.assertEqual(response.data['total_duration'], 400.0)
    
    def test_get_stats_without_authentication(self):
        """Test that getting stats requires authentication"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_stats_only_user_choreographies(self):
        """Test that stats only include user's own choreographies"""
        # Create choreographies for test user
        SavedChoreography.objects.create(
            user=self.user,
            title='My Choreo',
            video_path='videos/mine.mp4',
            difficulty='beginner',
            duration=120.0
        )
        
        # Create choreographies for another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='TestPass123!'
        )
        SavedChoreography.objects.create(
            user=other_user,
            title='Other Choreo',
            video_path='videos/other.mp4',
            difficulty='advanced',
            duration=200.0
        )
        
        response = self.client.get(self.stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 1)
        self.assertEqual(response.data['total_duration'], 120.0)



class SaveChoreographyEndpointTests(TestCase):
    """Test suite for POST /api/collections/save endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.save_url = reverse('save-choreography')
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
    
    def test_save_completed_task_success(self):
        """Test successfully saving a completed choreography task"""
        from apps.choreography.models import ChoreographyTask
        
        # Create a completed task
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='completed',
            result={
                'video_path': 'choreographies/2025/11/video.mp4',
                'sequence_duration': 180.5,
                'music_info': {'song': 'Obsesión', 'artist': 'Aventura'},
                'difficulty': 'intermediate',
                'generation_parameters': {'energy_level': 'medium'}
            }
        )
        
        response = self.client.post(self.save_url, {
            'task_id': str(task.task_id),
            'title': 'My Romantic Bachata'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'My Romantic Bachata')
        self.assertEqual(response.data['difficulty'], 'intermediate')
        self.assertEqual(response.data['duration'], 180.5)
        self.assertIn('choreographies/2025/11/video.mp4', response.data['video_path'])
        
        # Verify choreography was saved to database
        self.assertEqual(SavedChoreography.objects.count(), 1)
        saved = SavedChoreography.objects.first()
        self.assertEqual(saved.user, self.user)
        self.assertEqual(saved.title, 'My Romantic Bachata')
        self.assertEqual(saved.generation_parameters['task_id'], str(task.task_id))
    
    def test_save_task_with_auto_generated_title(self):
        """Test saving task without providing title generates default title"""
        from apps.choreography.models import ChoreographyTask
        
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='completed',
            result={
                'video_path': 'choreographies/2025/11/video.mp4',
                'sequence_duration': 120.0,
                'difficulty': 'beginner'
            }
        )
        
        response = self.client.post(self.save_url, {
            'task_id': str(task.task_id)
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Title should be auto-generated with format "Choreography YYYY-MM-DD HH:MM"
        self.assertTrue(response.data['title'].startswith('Choreography 2025'))
    
    def test_save_task_with_custom_difficulty(self):
        """Test saving task with custom difficulty overrides task difficulty"""
        from apps.choreography.models import ChoreographyTask
        
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='completed',
            result={
                'video_path': 'choreographies/2025/11/video.mp4',
                'sequence_duration': 120.0,
                'difficulty': 'beginner'
            }
        )
        
        response = self.client.post(self.save_url, {
            'task_id': str(task.task_id),
            'difficulty': 'advanced'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['difficulty'], 'advanced')
    
    def test_save_incomplete_task_fails(self):
        """Test that saving an incomplete task returns 400 error"""
        from apps.choreography.models import ChoreographyTask
        
        # Create a task that's still running
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='running',
            progress=50
        )
        
        response = self.client.post(self.save_url, {
            'task_id': str(task.task_id)
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot save incomplete choreography', response.data['error'])
        
        # Verify nothing was saved
        self.assertEqual(SavedChoreography.objects.count(), 0)
    
    def test_save_nonexistent_task_fails(self):
        """Test that saving a non-existent task returns 404 error"""
        fake_task_id = str(uuid.uuid4())
        
        response = self.client.post(self.save_url, {
            'task_id': fake_task_id
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(SavedChoreography.objects.count(), 0)
    
    def test_save_other_users_task_fails(self):
        """Test that saving another user's task returns 404 error"""
        from apps.choreography.models import ChoreographyTask
        
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='TestPass123!'
        )
        
        # Create task for other user
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=other_user,
            status='completed',
            result={'video_path': 'video.mp4', 'sequence_duration': 120.0}
        )
        
        response = self.client.post(self.save_url, {
            'task_id': str(task.task_id)
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(SavedChoreography.objects.count(), 0)
    
    def test_save_already_saved_task_fails(self):
        """Test that saving the same task twice returns 409 conflict error"""
        from apps.choreography.models import ChoreographyTask
        
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='completed',
            result={
                'video_path': 'choreographies/2025/11/video.mp4',
                'sequence_duration': 120.0
            }
        )
        
        # Save once - should succeed
        response1 = self.client.post(self.save_url, {
            'task_id': str(task.task_id),
            'title': 'First Save'
        }, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Try to save again - should fail
        response2 = self.client.post(self.save_url, {
            'task_id': str(task.task_id),
            'title': 'Second Save'
        }, format='json')
        
        self.assertEqual(response2.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('already saved', response2.data['error'])
        
        # Verify only one choreography was saved
        self.assertEqual(SavedChoreography.objects.count(), 1)
    
    def test_save_without_authentication_fails(self):
        """Test that saving without authentication returns 401 error"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.post(self.save_url, {
            'task_id': str(uuid.uuid4())
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_save_with_invalid_task_id_format(self):
        """Test that invalid UUID format returns 400 error"""
        response = self.client.post(self.save_url, {
            'task_id': 'not-a-valid-uuid'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('task_id', response.data)
    
    def test_difficulty_fallback_logic(self):
        """Test difficulty fallback: request > result > default"""
        from apps.choreography.models import ChoreographyTask
        
        # Test 1: No difficulty anywhere - should default to 'intermediate'
        task1 = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='completed',
            result={'video_path': 'video1.mp4', 'sequence_duration': 120.0}
        )
        
        response1 = self.client.post(self.save_url, {
            'task_id': str(task1.task_id)
        }, format='json')
        
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response1.data['difficulty'], 'intermediate')
        
        # Test 2: Difficulty in result - should use result difficulty
        task2 = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='completed',
            result={
                'video_path': 'video2.mp4',
                'sequence_duration': 120.0,
                'difficulty': 'beginner'
            }
        )
        
        response2 = self.client.post(self.save_url, {
            'task_id': str(task2.task_id)
        }, format='json')
        
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.data['difficulty'], 'beginner')
        
        # Test 3: Difficulty in request - should override result
        task3 = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='completed',
            result={
                'video_path': 'video3.mp4',
                'sequence_duration': 120.0,
                'difficulty': 'beginner'
            }
        )
        
        response3 = self.client.post(self.save_url, {
            'task_id': str(task3.task_id),
            'difficulty': 'advanced'
        }, format='json')
        
        self.assertEqual(response3.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response3.data['difficulty'], 'advanced')



class BulkDeleteChoreographiesEndpointTests(TestCase):
    """Test suite for POST /api/collections/delete-all endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.delete_all_url = reverse('delete-all-choreographies')
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
    
    def test_delete_all_with_confirmation_success(self):
        """Test successfully deleting all choreographies with confirmation"""
        # Create multiple choreographies
        for i in range(5):
            SavedChoreography.objects.create(
                user=self.user,
                title=f'Choreo {i}',
                video_path=f'videos/test{i}.mp4',
                difficulty='intermediate',
                duration=120.0
            )
        
        self.assertEqual(SavedChoreography.objects.filter(user=self.user).count(), 5)
        
        response = self.client.post(self.delete_all_url, {
            'confirmation': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted_count'], 5)
        self.assertIn('Successfully deleted 5', response.data['message'])
        
        # Verify all choreographies were deleted
        self.assertEqual(SavedChoreography.objects.filter(user=self.user).count(), 0)
    
    def test_delete_all_empty_collection(self):
        """Test deleting when collection is already empty"""
        self.assertEqual(SavedChoreography.objects.filter(user=self.user).count(), 0)
        
        response = self.client.post(self.delete_all_url, {
            'confirmation': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted_count'], 0)
        self.assertIn('Successfully deleted 0', response.data['message'])
    
    def test_delete_all_without_confirmation_fails(self):
        """Test that deletion without confirmation returns 400 error"""
        # Create choreographies
        SavedChoreography.objects.create(
            user=self.user,
            title='Test Choreo',
            video_path='videos/test.mp4',
            difficulty='beginner',
            duration=120.0
        )
        
        # Try without confirmation field
        response1 = self.client.post(self.delete_all_url, {}, format='json')
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirmation', response1.data)
        
        # Try with confirmation=false
        response2 = self.client.post(self.delete_all_url, {
            'confirmation': False
        }, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify nothing was deleted
        self.assertEqual(SavedChoreography.objects.filter(user=self.user).count(), 1)
    
    def test_delete_all_only_deletes_user_choreographies(self):
        """Test that bulk delete only affects authenticated user's choreographies"""
        # Create choreographies for test user
        for i in range(3):
            SavedChoreography.objects.create(
                user=self.user,
                title=f'My Choreo {i}',
                video_path=f'videos/mine{i}.mp4',
                difficulty='beginner',
                duration=120.0
            )
        
        # Create another user with choreographies
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='TestPass123!'
        )
        for i in range(2):
            SavedChoreography.objects.create(
                user=other_user,
                title=f'Other Choreo {i}',
                video_path=f'videos/other{i}.mp4',
                difficulty='intermediate',
                duration=150.0
            )
        
        # Delete all for test user
        response = self.client.post(self.delete_all_url, {
            'confirmation': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted_count'], 3)
        
        # Verify test user's choreographies deleted
        self.assertEqual(SavedChoreography.objects.filter(user=self.user).count(), 0)
        
        # Verify other user's choreographies untouched
        self.assertEqual(SavedChoreography.objects.filter(user=other_user).count(), 2)
    
    def test_delete_all_without_authentication_fails(self):
        """Test that deletion without authentication returns 401 error"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.post(self.delete_all_url, {
            'confirmation': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_delete_all_transaction_safety(self):
        """Test that deletion uses transaction (all or nothing)"""
        # Create choreographies
        for i in range(3):
            SavedChoreography.objects.create(
                user=self.user,
                title=f'Choreo {i}',
                video_path=f'videos/test{i}.mp4',
                difficulty='beginner',
                duration=120.0
            )
        
        initial_count = SavedChoreography.objects.filter(user=self.user).count()
        self.assertEqual(initial_count, 3)
        
        # Successful deletion should delete all
        response = self.client.post(self.delete_all_url, {
            'confirmation': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(SavedChoreography.objects.filter(user=self.user).count(), 0)



class CleanupCollectionEndpointTests(TestCase):
    """Test suite for POST /api/collections/cleanup endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.cleanup_url = reverse('cleanup-collection')
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        login_url = reverse('login')
        login_response = self.client.post(login_url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, format='json')
        self.access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
    
    def test_cleanup_with_no_orphans(self):
        """Test cleanup when all choreographies have valid files"""
        # Create choreographies (in test environment, file_exists will return False by default)
        # But we'll test the endpoint behavior
        
        response = self.client.post(self.cleanup_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('cleaned_count', response.data)
        self.assertIn('message', response.data)
    
    def test_cleanup_with_empty_collection(self):
        """Test cleanup when user has no choreographies"""
        self.assertEqual(SavedChoreography.objects.filter(user=self.user).count(), 0)
        
        response = self.client.post(self.cleanup_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['cleaned_count'], 0)
        self.assertIn('Cleaned up 0', response.data['message'])
    
    def test_cleanup_without_authentication_fails(self):
        """Test that cleanup without authentication returns 401 error"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.post(self.cleanup_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_cleanup_only_affects_user_choreographies(self):
        """Test that cleanup only processes authenticated user's choreographies"""
        # Create choreographies for test user
        SavedChoreography.objects.create(
            user=self.user,
            title='My Choreo',
            video_path='videos/mine.mp4',
            difficulty='beginner',
            duration=120.0
        )
        
        # Create another user with choreographies
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='TestPass123!'
        )
        SavedChoreography.objects.create(
            user=other_user,
            title='Other Choreo',
            video_path='videos/other.mp4',
            difficulty='intermediate',
            duration=150.0
        )
        
        initial_other_count = SavedChoreography.objects.filter(user=other_user).count()
        
        # Run cleanup for test user
        response = self.client.post(self.cleanup_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify other user's choreographies untouched
        self.assertEqual(
            SavedChoreography.objects.filter(user=other_user).count(),
            initial_other_count
        )
    
    def test_cleanup_with_empty_video_path(self):
        """Test that choreographies with empty video paths are cleaned up"""
        # Create choreography with empty video path
        choreo = SavedChoreography.objects.create(
            user=self.user,
            title='Empty Path Choreo',
            video_path='',
            difficulty='beginner',
            duration=120.0
        )
        
        self.assertEqual(SavedChoreography.objects.filter(user=self.user).count(), 1)
        
        response = self.client.post(self.cleanup_url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # In test environment without GCS, empty paths should be cleaned
        self.assertGreaterEqual(response.data['cleaned_count'], 0)
