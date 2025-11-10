"""
Unit tests for VectorSearchService

Tests cover:
- Embedding loading from database
- FAISS index building and normalization
- FAISS similarity search with various query embeddings
- Move filtering by difficulty, energy, style
- Caching mechanism for FAISS index
- Fallback to NumPy when FAISS fails

Run with:
    cd backend && python manage.py test services.test_vector_search_service
"""
from django.test import TestCase
from apps.choreography.models import MoveEmbedding
from services.vector_search_service import VectorSearchService, get_vector_search_service, FAISS_AVAILABLE
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class VectorSearchServiceTestCase(TestCase):
    """Test cases for VectorSearchService"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample move embeddings with distinct patterns
        self.move1 = MoveEmbedding.objects.create(
            move_id='move_001',
            move_name='Basic Step',
            video_path='data/Bachata_steps/basic_steps/basic_1.mp4',
            pose_embedding=[0.1] * 512,  # 512D pose embedding
            audio_embedding=[0.2] * 128,  # 128D audio embedding
            text_embedding=[0.3] * 384,   # 384D text embedding
            difficulty='beginner',
            energy_level='low',
            style='romantic',
            duration=8.0
        )
        
        self.move2 = MoveEmbedding.objects.create(
            move_id='move_002',
            move_name='Body Roll',
            video_path='data/Bachata_steps/body_roll/body_roll_1.mp4',
            pose_embedding=[0.5] * 512,
            audio_embedding=[0.6] * 128,
            text_embedding=[0.7] * 384,
            difficulty='intermediate',
            energy_level='high',
            style='sensual',
            duration=8.0
        )
        
        self.move3 = MoveEmbedding.objects.create(
            move_id='move_003',
            move_name='Turn',
            video_path='data/Bachata_steps/lady_right_turn/turn_1.mp4',
            pose_embedding=[0.9] * 512,
            audio_embedding=[0.8] * 128,
            text_embedding=[0.7] * 384,
            difficulty='intermediate',
            energy_level='medium',
            style='energetic',
            duration=8.0
        )
        
        self.move4 = MoveEmbedding.objects.create(
            move_id='move_004',
            move_name='Advanced Spin',
            video_path='data/Bachata_steps/spins/spin_1.mp4',
            pose_embedding=[0.2] * 512,
            audio_embedding=[0.3] * 128,
            text_embedding=[0.4] * 384,
            difficulty='advanced',
            energy_level='high',
            style='energetic',
            duration=8.0
        )
        
        # Create service instance
        self.service = VectorSearchService(cache_ttl_seconds=60)
    
    def tearDown(self):
        """Clean up after tests"""
        # Clear the global singleton
        import services.vector_search_service as vss_module
        vss_module._vector_search_service = None
    
    # Test: Embedding loading from database
    def test_load_embeddings_from_db(self):
        """Test loading embeddings from database"""
        self.service.load_embeddings_from_db()
        
        # Check that embeddings were loaded
        self.assertIsNotNone(self.service.embeddings)
        self.assertEqual(len(self.service.move_metadata), 4)
        self.assertEqual(self.service.embedding_dimension, 512 + 128 + 384)  # 1024
        
        # Check metadata
        move_ids = [m['move_id'] for m in self.service.move_metadata]
        self.assertIn('move_001', move_ids)
        self.assertIn('move_002', move_ids)
        self.assertIn('move_003', move_ids)
        self.assertIn('move_004', move_ids)
        
        # Verify embeddings are numpy arrays
        self.assertIsInstance(self.service.embeddings, np.ndarray)
        self.assertEqual(self.service.embeddings.dtype, np.float32)
    
    def test_load_embeddings_combines_all_types(self):
        """Test that pose, audio, and text embeddings are combined"""
        self.service.load_embeddings_from_db()
        
        # Check that combined embedding has correct dimension
        expected_dim = 512 + 128 + 384  # pose + audio + text
        self.assertEqual(self.service.embeddings.shape[1], expected_dim)
        
        # Note: Embeddings are normalized by FAISS, so we can't check exact values
        # Just verify the structure is correct
        self.assertEqual(self.service.embeddings.shape[0], 4)  # 4 moves
        self.assertIsInstance(self.service.embeddings, np.ndarray)
    
    def test_load_embeddings_no_data(self):
        """Test loading embeddings when database is empty"""
        MoveEmbedding.objects.all().delete()
        
        with self.assertRaises(ValueError) as context:
            self.service.load_embeddings_from_db()
        
        self.assertIn("No move embeddings found", str(context.exception))
    
    # Test: FAISS index building and normalization
    def test_build_faiss_index(self):
        """Test FAISS index building"""
        if not FAISS_AVAILABLE:
            self.skipTest("FAISS not available")
        
        self.service.load_embeddings_from_db()
        
        # Check that FAISS index was built
        self.assertIsNotNone(self.service.faiss_index)
        self.assertEqual(self.service.faiss_index.ntotal, 4)
        self.assertEqual(self.service.faiss_index.d, 1024)
    
    def test_faiss_index_normalization(self):
        """Test that embeddings are normalized for cosine similarity"""
        if not FAISS_AVAILABLE:
            self.skipTest("FAISS not available")
        
        self.service.load_embeddings_from_db()
        
        # After normalization, embeddings should have unit length
        # Note: FAISS normalizes in-place, so we check the stored embeddings
        norms = np.linalg.norm(self.service.embeddings, axis=1)
        np.testing.assert_array_almost_equal(norms, np.ones(4), decimal=5)
    
    def test_build_faiss_index_without_faiss(self):
        """Test that building index without FAISS raises error"""
        if not FAISS_AVAILABLE:
            self.skipTest("FAISS not available - cannot test error case")
        
        # Mock FAISS as unavailable by patching the module-level check
        with patch('services.vector_search_service.FAISS_AVAILABLE', False):
            service = VectorSearchService(cache_ttl_seconds=60)
            embeddings = np.random.randn(10, 128).astype(np.float32)
            
            with self.assertRaises(ValueError) as context:
                service.build_faiss_index(embeddings)
            
            self.assertIn("FAISS is not available", str(context.exception))
    
    # Test: FAISS similarity search with various query embeddings
    def test_search_similar_moves_no_filters(self):
        """Test searching for similar moves without filters"""
        query_emb = np.random.randn(1024).astype(np.float32)
        
        results = self.service.search_similar_moves(query_emb, filters=None, top_k=3)
        
        # Check results
        self.assertEqual(len(results), 3)
        self.assertTrue(all(hasattr(r, 'move_id') for r in results))
        self.assertTrue(all(hasattr(r, 'similarity_score') for r in results))
        
        # Results should be sorted by similarity score (descending)
        scores = [r.similarity_score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_search_similar_moves_with_specific_query(self):
        """Test search with query similar to a specific move"""
        # Create query similar to move1 (all 0.1-0.3 values)
        query_emb = np.concatenate([
            np.full(512, 0.1),
            np.full(128, 0.2),
            np.full(384, 0.3)
        ]).astype(np.float32)
        
        results = self.service.search_similar_moves(query_emb, filters=None, top_k=4)
        
        # First result should be move1 (most similar)
        self.assertEqual(results[0].move_id, 'move_001')
        self.assertGreater(results[0].similarity_score, results[1].similarity_score)
    
    def test_search_similar_moves_different_query_embeddings(self):
        """Test search with various query embedding patterns"""
        # Test with different query patterns
        queries = [
            np.random.randn(1024).astype(np.float32),
            np.ones(1024, dtype=np.float32),
            np.zeros(1024, dtype=np.float32),
            np.full(1024, 0.5, dtype=np.float32),
        ]
        
        for query in queries:
            results = self.service.search_similar_moves(query, filters=None, top_k=2)
            self.assertEqual(len(results), 2)
            self.assertTrue(all(isinstance(r.similarity_score, float) for r in results))
    
    def test_search_with_1d_query_embedding(self):
        """Test that 1D query embeddings are reshaped correctly"""
        query_emb = np.random.randn(1024).astype(np.float32)  # 1D array
        
        results = self.service.search_similar_moves(query_emb, filters=None, top_k=2)
        
        self.assertEqual(len(results), 2)
    
    def test_search_with_wrong_dimension(self):
        """Test that wrong dimension query raises error"""
        query_emb = np.random.randn(512).astype(np.float32)  # Wrong dimension
        
        with self.assertRaises(ValueError) as context:
            self.service.search_similar_moves(query_emb, filters=None, top_k=2)
        
        self.assertIn("dimension", str(context.exception).lower())
    
    # Test: Move filtering by difficulty, energy, style
    def test_filter_by_difficulty(self):
        """Test filtering moves by difficulty"""
        query_emb = np.random.randn(1024).astype(np.float32)
        
        # Filter for intermediate difficulty
        results = self.service.search_similar_moves(
            query_emb,
            filters={'difficulty': 'intermediate'},
            top_k=5
        )
        
        # Should only return intermediate moves (move2 and move3)
        self.assertLessEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.difficulty, 'intermediate')
    
    def test_filter_by_energy_level(self):
        """Test filtering moves by energy level"""
        query_emb = np.random.randn(1024).astype(np.float32)
        
        # Filter for high energy
        results = self.service.search_similar_moves(
            query_emb,
            filters={'energy_level': 'high'},
            top_k=5
        )
        
        # Should only return high energy moves (move2 and move4)
        self.assertLessEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.energy_level, 'high')
    
    def test_filter_by_style(self):
        """Test filtering moves by style"""
        query_emb = np.random.randn(1024).astype(np.float32)
        
        # Filter for energetic style
        results = self.service.search_similar_moves(
            query_emb,
            filters={'style': 'energetic'},
            top_k=5
        )
        
        # Should only return energetic moves (move3 and move4)
        self.assertLessEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.style, 'energetic')
    
    def test_filter_multiple_criteria(self):
        """Test filtering with multiple criteria"""
        query_emb = np.random.randn(1024).astype(np.float32)
        
        # Filter for intermediate + high energy
        results = self.service.search_similar_moves(
            query_emb,
            filters={'difficulty': 'intermediate', 'energy_level': 'high'},
            top_k=5
        )
        
        # Should only return move2
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].move_id, 'move_002')
        self.assertEqual(results[0].difficulty, 'intermediate')
        self.assertEqual(results[0].energy_level, 'high')
    
    def test_filter_no_matches(self):
        """Test filtering with criteria that match no moves"""
        query_emb = np.random.randn(1024).astype(np.float32)
        
        # Filter for combination that doesn't exist
        results = self.service.search_similar_moves(
            query_emb,
            filters={'difficulty': 'beginner', 'energy_level': 'high'},
            top_k=5
        )
        
        # Should return empty list
        self.assertEqual(len(results), 0)
    
    # Test: Caching mechanism for FAISS index
    def test_cache_validity_after_load(self):
        """Test that cache is valid after loading"""
        self.service.load_embeddings_from_db()
        
        # Cache should be valid
        self.assertTrue(self.service._is_cache_valid())
        
        # Get cache info
        cache_info = self.service.get_cache_info()
        self.assertTrue(cache_info['cached'])
        self.assertEqual(cache_info['num_moves'], 4)
        self.assertTrue(cache_info['cache_valid'])
        self.assertIsNotNone(cache_info['cache_age_seconds'])
        self.assertLess(cache_info['cache_age_seconds'], 5)
    
    def test_cache_reuse(self):
        """Test that cache is reused on subsequent loads"""
        # First load
        self.service.load_embeddings_from_db()
        first_timestamp = self.service.cache_timestamp
        first_embeddings = self.service.embeddings
        
        # Second load (should use cache)
        self.service.load_embeddings_from_db()
        second_timestamp = self.service.cache_timestamp
        
        # Timestamp should be the same (cache was reused)
        self.assertEqual(first_timestamp, second_timestamp)
        self.assertIs(self.service.embeddings, first_embeddings)
    
    def test_cache_expiration(self):
        """Test that cache expires after TTL"""
        # Create service with short TTL
        service = VectorSearchService(cache_ttl_seconds=1)
        service.load_embeddings_from_db()
        
        # Cache should be valid initially
        self.assertTrue(service._is_cache_valid())
        
        # Manually set cache timestamp to past
        service.cache_timestamp = datetime.now() - timedelta(seconds=2)
        
        # Cache should now be invalid
        self.assertFalse(service._is_cache_valid())
    
    def test_cache_info_when_empty(self):
        """Test cache info when cache is empty"""
        cache_info = self.service.get_cache_info()
        
        self.assertFalse(cache_info['cached'])
        self.assertEqual(cache_info['num_moves'], 0)
        self.assertIsNone(cache_info['embedding_dimension'])
        self.assertIsNone(cache_info['cache_age_seconds'])
        self.assertFalse(cache_info['cache_valid'])
    
    def test_clear_cache(self):
        """Test clearing the cache"""
        self.service.load_embeddings_from_db()
        self.assertTrue(self.service._is_cache_valid())
        
        # Clear cache
        self.service.clear_cache()
        
        # Cache should be invalid
        self.assertFalse(self.service._is_cache_valid())
        self.assertIsNone(self.service.embeddings)
        self.assertEqual(len(self.service.move_metadata), 0)
        self.assertIsNone(self.service.cache_timestamp)
    
    def test_cache_reload_after_clear(self):
        """Test that embeddings can be reloaded after cache clear"""
        self.service.load_embeddings_from_db()
        self.service.clear_cache()
        
        # Should be able to load again
        self.service.load_embeddings_from_db()
        self.assertTrue(self.service._is_cache_valid())
        self.assertEqual(len(self.service.move_metadata), 4)
    
    # Test: Fallback to NumPy when FAISS fails
    def test_numpy_fallback_when_disabled(self):
        """Test NumPy fallback when FAISS is disabled"""
        service = VectorSearchService(cache_ttl_seconds=60)
        service.use_faiss = False
        
        # Load embeddings (should not build FAISS index)
        service.load_embeddings_from_db()
        self.assertIsNone(service.faiss_index)
        
        # Search should still work with NumPy
        query_emb = np.random.randn(1024).astype(np.float32)
        results = service.search_similar_moves(query_emb, filters=None, top_k=3)
        
        self.assertEqual(len(results), 3)
        self.assertTrue(all(isinstance(r.similarity_score, float) for r in results))
    
    def test_numpy_fallback_on_faiss_error(self):
        """Test that NumPy fallback is used when FAISS search fails"""
        if not FAISS_AVAILABLE:
            self.skipTest("FAISS not available")
        
        self.service.load_embeddings_from_db()
        
        # Mock FAISS search to raise an error
        with patch.object(self.service.faiss_index, 'search', side_effect=Exception("FAISS error")):
            query_emb = np.random.randn(1024).astype(np.float32)
            results = self.service.search_similar_moves(query_emb, filters=None, top_k=3)
            
            # Should still get results via NumPy fallback
            self.assertEqual(len(results), 3)
    
    def test_numpy_search_correctness(self):
        """Test that NumPy search produces correct similarity scores"""
        service = VectorSearchService(cache_ttl_seconds=60)
        service.use_faiss = False
        service.load_embeddings_from_db()
        
        # Create query identical to move1
        query_emb = np.concatenate([
            np.full(512, 0.1),
            np.full(128, 0.2),
            np.full(384, 0.3)
        ]).astype(np.float32)
        
        results = service.search_similar_moves(query_emb, filters=None, top_k=4)
        
        # First result should be move1 with high similarity
        self.assertEqual(results[0].move_id, 'move_001')
        self.assertGreater(results[0].similarity_score, 0.99)  # Should be very close to 1.0
    
    def test_numpy_search_with_filters(self):
        """Test that NumPy search works with filters"""
        service = VectorSearchService(cache_ttl_seconds=60)
        service.use_faiss = False
        service.load_embeddings_from_db()
        
        query_emb = np.random.randn(1024).astype(np.float32)
        results = service.search_similar_moves(
            query_emb,
            filters={'difficulty': 'intermediate'},
            top_k=5
        )
        
        # Should only return intermediate moves
        self.assertLessEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.difficulty, 'intermediate')
    
    # Test: Singleton pattern
    def test_get_vector_search_service_singleton(self):
        """Test that get_vector_search_service returns singleton"""
        service1 = get_vector_search_service()
        service2 = get_vector_search_service()
        
        # Should be the same instance
        self.assertIs(service1, service2)
    
    def test_singleton_preserves_cache(self):
        """Test that singleton preserves cache across calls"""
        service1 = get_vector_search_service()
        service1.load_embeddings_from_db()
        
        service2 = get_vector_search_service()
        
        # Should have the same cache
        self.assertTrue(service2._is_cache_valid())
        self.assertEqual(len(service2.move_metadata), 4)
    
    # Test: MoveResult dataclass
    def test_move_result_to_dict(self):
        """Test MoveResult to_dict conversion"""
        from services.vector_search_service import MoveResult
        
        result = MoveResult(
            move_id='test_001',
            move_name='Test Move',
            video_path='path/to/video.mp4',
            similarity_score=0.95,
            difficulty='intermediate',
            energy_level='high',
            style='energetic',
            duration=8.0
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict['move_id'], 'test_001')
        self.assertEqual(result_dict['move_name'], 'Test Move')
        self.assertEqual(result_dict['similarity_score'], 0.95)
        self.assertEqual(result_dict['difficulty'], 'intermediate')
        self.assertIsInstance(result_dict['similarity_score'], float)
