"""
Additional tests to increase coverage of views.py
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.choreography.models import Song, ChoreographyTask

User = get_user_model()


class SongViewsCoverageTests(TestCase):
    """Tests for song-related views to increase coverage"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test songs
        self.song1 = Song.objects.create(
            title='Test Song 1',
            artist='Test Artist',
            genre='bachata',
            bpm=120,
            duration=180.0,
            audio_path='songs/test1.mp3'
        )
        
        self.song2 = Song.objects.create(
            title='Test Song 2',
            artist='Another Artist',
            genre='salsa',
            bpm=140,
            duration=200.0,
            audio_path='songs/test2.mp3'
        )
    
    def test_list_songs(self):
        """Test listing all songs"""
        response = self.client.get('/api/choreography/songs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_list_songs_with_genre_filter(self):
        """Test filtering songs by genre"""
        response = self.client.get('/api/choreography/songs/?genre=bachata')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['genre'], 'bachata')
    
    def test_list_songs_with_bpm_filter(self):
        """Test filtering songs by BPM range"""
        response = self.client.get('/api/choreography/songs/?bpm_min=115&bpm_max=125')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_list_songs_with_search(self):
        """Test searching songs by title or artist"""
        response = self.client.get('/api/choreography/songs/?search=Test Song 1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_list_songs_pagination(self):
        """Test pagination of songs"""
        # Create more songs
        for i in range(25):
            Song.objects.create(
                title=f'Song {i}',
                artist='Artist',
                genre='bachata',
                bpm=120,
                duration=180.0,
                audio_path=f'songs/song{i}.mp3'
            )
        
        response = self.client.get('/api/choreography/songs/?page=1&page_size=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
    
    def test_song_detail(self):
        """Test retrieving a single song"""
        response = self.client.get(f'/api/choreography/songs/{self.song1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Song 1')
    
    def test_song_detail_not_found(self):
        """Test retrieving a non-existent song"""
        response = self.client.get('/api/choreography/songs/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TaskViewsCoverageTests(TestCase):
    """Tests for task-related views to increase coverage"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test task
        self.task = ChoreographyTask.objects.create(
            user=self.user,
            status='completed',
            stage='completed',
            message='Task completed'
        )
    
    def test_list_tasks(self):
        """Test listing user's tasks"""
        response = self.client.get('/api/choreography/tasks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_list_tasks_with_status_filter(self):
        """Test filtering tasks by status"""
        response = self.client.get('/api/choreography/tasks/?status=completed')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_task_detail(self):
        """Test retrieving a single task"""
        response = self.client.get(f'/api/choreography/tasks/{self.task.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
    
    def test_task_detail_not_found(self):
        """Test retrieving a non-existent task"""
        response = self.client.get('/api/choreography/tasks/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_task_detail_other_user(self):
        """Test that users can't access other users' tasks"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        other_task = ChoreographyTask.objects.create(
            user=other_user,
            status='pending'
        )
        
        response = self.client.get(f'/api/choreography/tasks/{other_task.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
