"""
Tests for choreography generation API endpoints.
"""
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import ChoreographyTask, Song

User = get_user_model()


class TaskStatusTests(TestCase):
    """Test suite for task status endpoint"""
    
    def setUp(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create a test task with UUID
        self.task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='running',  # Use valid status from model
            progress=50,
            stage='generating',
            message='Generating choreography...'
        )
    
    def test_get_task_status_success(self):
        """Test getting task status"""
        response = self.client.get(f'/api/choreography/tasks/{self.task.task_id}/')
        
        # Should return 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should return task details
        self.assertEqual(response.data['task_id'], str(self.task.task_id))
        self.assertEqual(response.data['status'], 'running')
        self.assertEqual(response.data['progress'], 50)
        self.assertEqual(response.data['stage'], 'generating')
    
    def test_get_task_status_not_found(self):
        """Test getting non-existent task"""
        fake_id = uuid.uuid4()
        response = self.client.get(f'/api/choreography/tasks/{fake_id}/')
        
        # Should return 404 Not Found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_task_status_other_user(self):
        """Test getting another user's task"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        other_task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=other_user,
            status='completed',
            progress=100
        )
        
        response = self.client.get(f'/api/choreography/tasks/{other_task.task_id}/')
        
        # Should return 404 Not Found (user can't access other user's tasks)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TaskListTests(TestCase):
    """Test suite for task list endpoint"""
    
    def setUp(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create multiple test tasks with UUIDs
        for i in range(5):
            ChoreographyTask.objects.create(
                task_id=str(uuid.uuid4()),
                user=self.user,
                status='completed' if i % 2 == 0 else 'running',  # Use valid statuses
                progress=100 if i % 2 == 0 else 50
            )
    
    def test_list_tasks_success(self):
        """Test listing user's tasks"""
        response = self.client.get('/api/choreography/tasks/')
        
        # Should return 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should return paginated results
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertEqual(len(response.data['results']), 5)
        self.assertEqual(response.data['count'], 5)
    
    def test_list_tasks_filter_by_status(self):
        """Test filtering tasks by status"""
        response = self.client.get('/api/choreography/tasks?status=completed')
        
        # Should return 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should return only completed tasks (3 out of 5 created in setUp)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['count'], 3)
        for task in response.data['results']:
            self.assertEqual(task['status'], 'completed')
    
    def test_list_tasks_filter_by_invalid_status(self):
        """Test filtering tasks by invalid status"""
        response = self.client.get('/api/choreography/tasks?status=invalid_status')
        
        # Should return 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Invalid status', response.data['error'])
    
    def test_list_tasks_pagination(self):
        """Test pagination with multiple pages"""
        # Create 25 tasks (more than default page size of 20)
        for i in range(25):
            ChoreographyTask.objects.create(
                task_id=str(uuid.uuid4()),
                user=self.user,
                status='started',  # Use valid status
                progress=0
            )
        
        # First page
        response = self.client.get('/api/choreography/tasks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 20)
        self.assertEqual(response.data['count'], 30)  # 25 new + 5 from setUp
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        
        # Second page
        response = self.client.get('/api/choreography/tasks?page=2')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNone(response.data['next'])
        self.assertIsNotNone(response.data['previous'])
    
    def test_list_tasks_custom_page_size(self):
        """Test custom page size parameter"""
        # Create 15 tasks
        for i in range(15):
            ChoreographyTask.objects.create(
                task_id=str(uuid.uuid4()),
                user=self.user,
                status='started',  # Use valid status
                progress=0
            )
        
        # Request with page_size=10
        response = self.client.get('/api/choreography/tasks?page_size=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertEqual(response.data['count'], 20)  # 15 new + 5 from setUp
        self.assertIsNotNone(response.data['next'])
    
    def test_list_tasks_max_page_size(self):
        """Test that page size is capped at 100"""
        # Request with page_size=200 (should be capped at 100)
        response = self.client.get('/api/choreography/tasks?page_size=200')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should use max of 100, not 200
        self.assertLessEqual(len(response.data['results']), 100)
    
    def test_list_tasks_ordering(self):
        """Test that tasks are ordered by created_at descending"""
        # Clear existing tasks
        ChoreographyTask.objects.filter(user=self.user).delete()
        
        # Create tasks with specific order
        task1 = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='started',  # Use valid status
            progress=0
        )
        task2 = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='running',  # Use valid status
            progress=50
        )
        task3 = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='completed',
            progress=100
        )
        
        response = self.client.get('/api/choreography/tasks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Most recent task should be first
        results = response.data['results']
        self.assertEqual(results[0]['task_id'], str(task3.task_id))
        self.assertEqual(results[1]['task_id'], str(task2.task_id))
        self.assertEqual(results[2]['task_id'], str(task1.task_id))


class CancelTaskTests(TestCase):
    """Test suite for task cancellation endpoint"""
    
    def setUp(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_cancel_pending_task(self):
        """Test cancelling a pending task"""
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='started',  # Use valid status (started is like pending)
            progress=0,
            stage='initializing',
            message='Task queued'
        )
        
        response = self.client.delete(f'/api/choreography/tasks/{task.task_id}/')
        
        # Should return 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('cancelled', response.data['message'].lower())
        
        # Task should be marked as failed with cancellation message
        task.refresh_from_db()
        self.assertEqual(task.status, 'failed')
        self.assertIn('Cancelled by user', task.error)
        self.assertIn('cancelled', task.message.lower())
    
    def test_cancel_processing_task(self):
        """Test cancelling a processing task"""
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='running',  # Use valid status (running is like processing)
            progress=50,
            stage='generating',
            message='Generating video...',
            job_execution_name='local-dev-execution-test'
        )
        
        response = self.client.delete(f'/api/choreography/tasks/{task.task_id}/')
        
        # Should return 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Task should be marked as failed
        task.refresh_from_db()
        self.assertEqual(task.status, 'failed')
        self.assertIn('Cancelled by user', task.error)
    
    def test_cancel_completed_task(self):
        """Test cancelling a completed task (should fail)"""
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='completed',
            progress=100,
            stage='completed',
            message='Task completed'
        )
        
        response = self.client.delete(f'/api/choreography/tasks/{task.task_id}/')
        
        # Should return 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Cannot cancel', response.data['error'])
    
    def test_cancel_failed_task(self):
        """Test cancelling a failed task (should fail)"""
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=self.user,
            status='failed',
            progress=0,
            error='Previous error'
        )
        
        response = self.client.delete(f'/api/choreography/tasks/{task.task_id}/')
        
        # Should return 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_cancel_other_user_task(self):
        """Test cancelling another user's task (should fail)"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        task = ChoreographyTask.objects.create(
            task_id=str(uuid.uuid4()),
            user=other_user,
            status='started',  # Use valid status
            progress=0
        )
        
        response = self.client.delete(f'/api/choreography/tasks/{task.task_id}/')
        
        # Should return 404 Not Found (user can't access other user's tasks)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_cancel_nonexistent_task(self):
        """Test cancelling a non-existent task"""
        fake_id = uuid.uuid4()
        
        response = self.client.delete(f'/api/choreography/tasks/{fake_id}/')
        
        # Should return 404 Not Found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)



# ============================================================================
# Song Endpoint Tests
# ============================================================================


class SongModelTests(TestCase):
    """Test suite for Song model"""
    
    def test_create_song_with_local_path(self):
        """Test creating a song with local file path"""
        song = Song.objects.create(
            title='Bachata Rosa',
            artist='Juan Luis Guerra',
            duration=245.5,
            bpm=120,
            genre='bachata',
            audio_path='songs/bachata-rosa.mp3'
        )
        
        self.assertEqual(song.title, 'Bachata Rosa')
        self.assertEqual(song.artist, 'Juan Luis Guerra')
        self.assertEqual(song.duration, 245.5)
        self.assertEqual(song.bpm, 120)
        self.assertEqual(song.genre, 'bachata')
        self.assertEqual(song.audio_path, 'songs/bachata-rosa.mp3')
        self.assertIsNotNone(song.created_at)
        self.assertIsNotNone(song.updated_at)
    
    def test_create_song_with_gcs_path(self):
        """Test creating a song with GCS path"""
        song = Song.objects.create(
            title='Obsesión',
            artist='Aventura',
            duration=268.0,
            bpm=125,
            genre='bachata',
            audio_path='gs://bachata-buddy-bucket/songs/obsesion.mp3'
        )
        
        self.assertEqual(song.audio_path, 'gs://bachata-buddy-bucket/songs/obsesion.mp3')
    
    def test_song_str_representation(self):
        """Test song string representation"""
        song = Song.objects.create(
            title='Propuesta Indecente',
            artist='Romeo Santos',
            duration=235.0,
            bpm=118,
            genre='bachata',
            audio_path='songs/propuesta-indecente.mp3'
        )
        
        self.assertEqual(str(song), 'Propuesta Indecente - Romeo Santos')
    
    def test_song_ordering(self):
        """Test songs are ordered by title"""
        Song.objects.create(
            title='Zumba',
            artist='Artist A',
            duration=200.0,
            audio_path='songs/zumba.mp3'
        )
        Song.objects.create(
            title='Amor',
            artist='Artist B',
            duration=210.0,
            audio_path='songs/amor.mp3'
        )
        Song.objects.create(
            title='Bailar',
            artist='Artist C',
            duration=220.0,
            audio_path='songs/bailar.mp3'
        )
        
        songs = list(Song.objects.all())
        self.assertEqual(songs[0].title, 'Amor')
        self.assertEqual(songs[1].title, 'Bailar')
        self.assertEqual(songs[2].title, 'Zumba')


class SongSerializerTests(TestCase):
    """Test suite for song serializers"""
    
    def setUp(self):
        """Set up test data"""
        self.song = Song.objects.create(
            title='Test Song',
            artist='Test Artist',
            duration=180.0,
            bpm=120,
            genre='bachata',
            audio_path='songs/test.mp3'
        )
    
    def test_song_generation_serializer_valid_data(self):
        """Test SongGenerationSerializer with valid data"""
        from .serializers import SongGenerationSerializer
        
        data = {
            'song_id': self.song.id,
            'difficulty': 'intermediate'
        }
        serializer = SongGenerationSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['song_id'], self.song.id)
        self.assertEqual(serializer.validated_data['difficulty'], 'intermediate')
    
    def test_song_generation_serializer_invalid_song_id(self):
        """Test SongGenerationSerializer with non-existent song_id"""
        from .serializers import SongGenerationSerializer
        
        data = {
            'song_id': 99999,
            'difficulty': 'beginner'
        }
        serializer = SongGenerationSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('song_id', serializer.errors)
        self.assertIn('does not exist', str(serializer.errors['song_id'][0]))
    
    def test_song_generation_serializer_invalid_difficulty(self):
        """Test SongGenerationSerializer with invalid difficulty"""
        from .serializers import SongGenerationSerializer
        
        data = {
            'song_id': self.song.id,
            'difficulty': 'expert'
        }
        serializer = SongGenerationSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('difficulty', serializer.errors)
    
    def test_song_generation_serializer_with_optional_fields(self):
        """Test SongGenerationSerializer with optional fields"""
        from .serializers import SongGenerationSerializer
        
        data = {
            'song_id': self.song.id,
            'difficulty': 'advanced',
            'energy_level': 'high',
            'style': 'modern'
        }
        serializer = SongGenerationSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['energy_level'], 'high')
        self.assertEqual(serializer.validated_data['style'], 'modern')


class ListSongsEndpointTests(TestCase):
    """Test suite for list songs endpoint"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test songs
        Song.objects.create(
            title='Bachata Rosa',
            artist='Juan Luis Guerra',
            duration=245.5,
            bpm=120,
            genre='bachata',
            audio_path='songs/bachata-rosa.mp3'
        )
        Song.objects.create(
            title='Obsesión',
            artist='Aventura',
            duration=268.0,
            bpm=125,
            genre='bachata',
            audio_path='songs/obsesion.mp3'
        )
        Song.objects.create(
            title='Vivir Mi Vida',
            artist='Marc Anthony',
            duration=235.0,
            bpm=185,
            genre='salsa',
            audio_path='songs/vivir-mi-vida.mp3'
        )
    
    def test_list_songs_success(self):
        """Test listing all songs"""
        response = self.client.get('/api/choreography/songs/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)
    
    def test_list_songs_authentication_required(self):
        """Test that authentication is required"""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/choreography/songs/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_songs_filter_by_genre(self):
        """Test filtering songs by genre"""
        response = self.client.get('/api/choreography/songs/?genre=bachata')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        for song in response.data['results']:
            self.assertEqual(song['genre'], 'bachata')
    
    def test_list_songs_filter_by_bpm_min(self):
        """Test filtering songs by minimum BPM"""
        response = self.client.get('/api/choreography/songs/?bpm_min=125')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        for song in response.data['results']:
            self.assertGreaterEqual(song['bpm'], 125)
    
    def test_list_songs_filter_by_bpm_max(self):
        """Test filtering songs by maximum BPM"""
        response = self.client.get('/api/choreography/songs/?bpm_max=125')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        for song in response.data['results']:
            self.assertLessEqual(song['bpm'], 125)
    
    def test_list_songs_filter_by_bpm_range(self):
        """Test filtering songs by BPM range"""
        response = self.client.get('/api/choreography/songs/?bpm_min=120&bpm_max=130')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        for song in response.data['results']:
            self.assertGreaterEqual(song['bpm'], 120)
            self.assertLessEqual(song['bpm'], 130)
    
    def test_list_songs_search_by_title(self):
        """Test searching songs by title"""
        response = self.client.get('/api/choreography/songs/?search=rosa')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('Rosa', response.data['results'][0]['title'])
    
    def test_list_songs_search_by_artist(self):
        """Test searching songs by artist"""
        response = self.client.get('/api/choreography/songs/?search=aventura')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('Aventura', response.data['results'][0]['artist'])
    
    def test_list_songs_search_case_insensitive(self):
        """Test search is case-insensitive"""
        response = self.client.get('/api/choreography/songs/?search=BACHATA')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['count'], 0)
    
    def test_list_songs_pagination(self):
        """Test pagination with custom page size"""
        # Create more songs
        for i in range(25):
            Song.objects.create(
                title=f'Song {i}',
                artist=f'Artist {i}',
                duration=200.0,
                bpm=120,
                genre='bachata',
                audio_path=f'songs/song-{i}.mp3'
            )
        
        response = self.client.get('/api/choreography/songs/?page_size=10')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNotNone(response.data['next'])
    
    def test_list_songs_invalid_bpm_min(self):
        """Test invalid bpm_min parameter"""
        response = self.client.get('/api/choreography/songs/?bpm_min=invalid')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_list_songs_negative_bpm(self):
        """Test negative BPM parameter"""
        response = self.client.get('/api/choreography/songs/?bpm_min=-10')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_list_songs_page_size_exceeds_max(self):
        """Test page_size exceeding maximum"""
        response = self.client.get('/api/choreography/songs/?page_size=200')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_list_songs_ordered_by_title(self):
        """Test songs are ordered by title"""
        response = self.client.get('/api/choreography/songs/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [song['title'] for song in response.data['results']]
        self.assertEqual(titles, sorted(titles))


class SongDetailEndpointTests(TestCase):
    """Test suite for song detail endpoint"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.song = Song.objects.create(
            title='Bachata Rosa',
            artist='Juan Luis Guerra',
            duration=245.5,
            bpm=120,
            genre='bachata',
            audio_path='songs/bachata-rosa.mp3'
        )
    
    def test_get_song_detail_success(self):
        """Test getting song details"""
        response = self.client.get(f'/api/choreography/songs/{self.song.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.song.id)
        self.assertEqual(response.data['title'], 'Bachata Rosa')
        self.assertEqual(response.data['artist'], 'Juan Luis Guerra')
        self.assertEqual(response.data['duration'], 245.5)
        self.assertEqual(response.data['bpm'], 120)
        self.assertEqual(response.data['genre'], 'bachata')
        self.assertEqual(response.data['audio_path'], 'songs/bachata-rosa.mp3')
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)
    
    def test_get_song_detail_not_found(self):
        """Test getting non-existent song"""
        response = self.client.get('/api/choreography/songs/99999/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_song_detail_authentication_required(self):
        """Test that authentication is required"""
        self.client.force_authenticate(user=None)
        response = self.client.get(f'/api/choreography/songs/{self.song.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_song_detail_includes_audio_path(self):
        """Test that audio_path is included in detail view"""
        response = self.client.get(f'/api/choreography/songs/{self.song.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('audio_path', response.data)
        self.assertEqual(response.data['audio_path'], self.song.audio_path)


class GenerateFromSongEndpointTests(TestCase):
    """Test suite for generate from song endpoint"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.song = Song.objects.create(
            title='Bachata Rosa',
            artist='Juan Luis Guerra',
            duration=245.5,
            bpm=120,
            genre='bachata',
            audio_path='songs/bachata-rosa.mp3'
        )
    
    def test_generate_from_song_success(self):
        """Test generating choreography from song"""
        data = {
            'song_id': self.song.id,
            'difficulty': 'intermediate'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task_id', response.data)
        self.assertIn('song', response.data)
        self.assertIn('status', response.data)
        self.assertIn('poll_url', response.data)
        
        # Verify song info in response
        self.assertEqual(response.data['song']['id'], self.song.id)
        self.assertEqual(response.data['song']['title'], self.song.title)
        self.assertEqual(response.data['song']['artist'], self.song.artist)
        
        # Verify task was created
        task_id = response.data['task_id']
        task = ChoreographyTask.objects.get(task_id=task_id)
        self.assertEqual(task.user, self.user)
        self.assertIn(task.status, ['pending', 'started'])
    
    def test_generate_from_song_invalid_song_id(self):
        """Test generating with non-existent song_id"""
        data = {
            'song_id': 99999,
            'difficulty': 'beginner'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('song_id', response.data)
    
    def test_generate_from_song_invalid_difficulty(self):
        """Test generating with invalid difficulty"""
        data = {
            'song_id': self.song.id,
            'difficulty': 'expert'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('difficulty', response.data)
    
    def test_generate_from_song_missing_song_id(self):
        """Test generating without song_id"""
        data = {
            'difficulty': 'beginner'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('song_id', response.data)
    
    def test_generate_from_song_with_optional_parameters(self):
        """Test generating with optional parameters"""
        data = {
            'song_id': self.song.id,
            'difficulty': 'advanced',
            'energy_level': 'high',
            'style': 'modern'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task_id', response.data)
    
    def test_generate_from_song_authentication_required(self):
        """Test that authentication is required"""
        self.client.force_authenticate(user=None)
        data = {
            'song_id': self.song.id,
            'difficulty': 'beginner'
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_generate_from_song_default_difficulty(self):
        """Test default difficulty is intermediate"""
        data = {
            'song_id': self.song.id
        }
        response = self.client.post('/api/choreography/generate-from-song/', data, format='json')
        
        # Should succeed with default difficulty
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)


class SongWorkflowIntegrationTests(TestCase):
    """Integration tests for complete song template workflow"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create multiple songs
        self.songs = [
            Song.objects.create(
                title='Bachata Rosa',
                artist='Juan Luis Guerra',
                duration=245.5,
                bpm=120,
                genre='bachata',
                audio_path='songs/bachata-rosa.mp3'
            ),
            Song.objects.create(
                title='Obsesión',
                artist='Aventura',
                duration=268.0,
                bpm=125,
                genre='bachata',
                audio_path='songs/obsesion.mp3'
            ),
            Song.objects.create(
                title='Propuesta Indecente',
                artist='Romeo Santos',
                duration=235.0,
                bpm=118,
                genre='bachata',
                audio_path='songs/propuesta-indecente.mp3'
            )
        ]
    
    def test_complete_workflow_list_select_generate(self):
        """Test complete workflow: list songs → select song → generate choreography"""
        # Step 1: List songs
        list_response = self.client.get('/api/choreography/songs/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['count'], 3)
        
        # Step 2: Select a song (get details)
        selected_song_id = list_response.data['results'][0]['id']
        detail_response = self.client.get(f'/api/choreography/songs/{selected_song_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertIn('audio_path', detail_response.data)
        
        # Step 3: Generate choreography from selected song
        generate_data = {
            'song_id': selected_song_id,
            'difficulty': 'intermediate'
        }
        generate_response = self.client.post(
            '/api/choreography/generate-from-song/',
            generate_data,
            format='json'
        )
        self.assertEqual(generate_response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task_id', generate_response.data)
        
        # Step 4: Poll task status
        task_id = generate_response.data['task_id']
        task_response = self.client.get(f'/api/choreography/tasks/{task_id}/')
        self.assertEqual(task_response.status_code, status.HTTP_200_OK)
        self.assertEqual(task_response.data['task_id'], task_id)
    
    def test_workflow_with_filtering_and_search(self):
        """Test workflow with filtering and search"""
        # Search for specific song
        search_response = self.client.get('/api/choreography/songs/?search=Aventura')
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(search_response.data['count'], 1)
        
        # Get the found song
        song_id = search_response.data['results'][0]['id']
        detail_response = self.client.get(f'/api/choreography/songs/{song_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        
        # Generate from found song
        generate_data = {
            'song_id': song_id,
            'difficulty': 'beginner'
        }
        generate_response = self.client.post(
            '/api/choreography/generate-from-song/',
            generate_data,
            format='json'
        )
        self.assertEqual(generate_response.status_code, status.HTTP_202_ACCEPTED)
    
    def test_workflow_filter_by_bpm_then_generate(self):
        """Test filtering by BPM range then generating"""
        # Filter songs by BPM range
        filter_response = self.client.get('/api/choreography/songs/?bpm_min=118&bpm_max=120')
        self.assertEqual(filter_response.status_code, status.HTTP_200_OK)
        self.assertEqual(filter_response.data['count'], 2)
        
        # Select first filtered song
        song_id = filter_response.data['results'][0]['id']
        
        # Generate choreography
        generate_data = {
            'song_id': song_id,
            'difficulty': 'advanced',
            'energy_level': 'medium'
        }
        generate_response = self.client.post(
            '/api/choreography/generate-from-song/',
            generate_data,
            format='json'
        )
        self.assertEqual(generate_response.status_code, status.HTTP_202_ACCEPTED)
        
        # Verify task was created with correct user
        task_id = generate_response.data['task_id']
        task = ChoreographyTask.objects.get(task_id=task_id)
        self.assertEqual(task.user, self.user)
    
    def test_multiple_generations_from_same_song(self):
        """Test generating multiple choreographies from the same song"""
        song_id = self.songs[0].id
        
        # Generate first choreography
        data1 = {
            'song_id': song_id,
            'difficulty': 'beginner'
        }
        response1 = self.client.post('/api/choreography/generate-from-song/', data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_202_ACCEPTED)
        task_id1 = response1.data['task_id']
        
        # Generate second choreography with different difficulty
        data2 = {
            'song_id': song_id,
            'difficulty': 'advanced'
        }
        response2 = self.client.post('/api/choreography/generate-from-song/', data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_202_ACCEPTED)
        task_id2 = response2.data['task_id']
        
        # Verify both tasks exist and are different
        self.assertNotEqual(task_id1, task_id2)
        task1 = ChoreographyTask.objects.get(task_id=task_id1)
        task2 = ChoreographyTask.objects.get(task_id=task_id2)
        self.assertEqual(task1.user, self.user)
        self.assertEqual(task2.user, self.user)
