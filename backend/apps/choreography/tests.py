"""
Tests for choreography generation API endpoints.
"""
import os
import uuid
import unittest
import unittest.mock
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import ChoreographyTask, Song

User = get_user_model()


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


class GenerateEndpointTests(TestCase):
    """Test suite for synchronous generate endpoint"""
    
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
    
    def test_generate_invalid_song_id(self):
        """Test generating with non-existent song_id"""
        data = {
            'song_id': 99999,
            'difficulty': 'beginner'
        }
        response = self.client.post('/api/choreography/generate/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('song_id', response.data)
    
    def test_generate_invalid_difficulty(self):
        """Test generating with invalid difficulty"""
        data = {
            'song_id': self.song.id,
            'difficulty': 'expert'
        }
        response = self.client.post('/api/choreography/generate/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('difficulty', response.data)
    
    def test_generate_missing_song_id(self):
        """Test generating without song_id"""
        data = {
            'difficulty': 'beginner'
        }
        response = self.client.post('/api/choreography/generate/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('song_id', response.data)
    
    def test_generate_authentication_required(self):
        """Test that authentication is required"""
        self.client.force_authenticate(user=None)
        data = {
            'song_id': self.song.id,
            'difficulty': 'beginner'
        }
        response = self.client.post('/api/choreography/generate/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)



