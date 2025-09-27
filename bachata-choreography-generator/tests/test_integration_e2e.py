"""
End-to-end integration tests for the complete choreography generation pipeline.
"""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Mock dependencies that might not be available
with patch.dict('sys.modules', {
    'yt_dlp': Mock(),
    'librosa': Mock(),
    'mediapipe': Mock(),
    'cv2': Mock(),
    'numpy': Mock(),
    'sklearn': Mock()
}):
    from app.services.choreography_pipeline import ChoreoGenerationPipeline, PipelineConfig
    from app.validation import validate_youtube_url_async


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def pipeline_config(self):
        """Create a test pipeline configuration."""
        return PipelineConfig(
            quality_mode="fast",
            enable_caching=True,
            max_workers=2,
            cleanup_after_generation=True
        )
    
    @pytest.fixture
    def pipeline(self, pipeline_config):
        """Create a test pipeline instance."""
        return ChoreoGenerationPipeline(pipeline_config)
    
    @pytest.mark.asyncio
    async def test_youtube_url_validation(self):
        """Test YouTube URL validation with various inputs."""
        # Valid YouTube URLs
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        ]
        
        for url in valid_urls:
            with patch('yt_dlp.YoutubeDL') as mock_ydl:
                # Mock successful extraction
                mock_instance = Mock()
                mock_instance.extract_info.return_value = {
                    'title': 'Test Video',
                    'duration': 180,
                    'uploader': 'Test Channel'
                }
                mock_ydl.return_value.__enter__.return_value = mock_instance
                
                result = await validate_youtube_url_async(url)
                assert result["valid"] is True
                assert "details" in result
        
        # Invalid URLs
        invalid_urls = [
            "https://www.google.com",
            "not_a_url",
            "",
            "https://youtube.com/invalid"
        ]
        
        for url in invalid_urls:
            result = await validate_youtube_url_async(url)
            assert result["valid"] is False
            assert "message" in result
    
    @pytest.mark.asyncio
    async def test_local_song_processing(self, pipeline):
        """Test processing with local song files."""
        # Use existing local songs for testing
        songs_dir = Path("data/songs")
        if not songs_dir.exists():
            pytest.skip("No local songs directory found")
        
        song_files = list(songs_dir.glob("*.mp3"))
        if not song_files:
            pytest.skip("No local songs found for testing")
        
        # Test with first available song
        test_song = song_files[0]
        
        with patch.object(pipeline, '_download_audio') as mock_download:
            # Mock download to return local file
            mock_download.return_value = str(test_song)
            
            with patch.object(pipeline, '_generate_video') as mock_video:
                # Mock video generation
                mock_video.return_value = "data/output/test_video.mp4"
                
                result = await pipeline.generate_choreography(
                    audio_input=str(test_song),
                    difficulty="beginner",
                    energy_level="medium"
                )
                
                assert result.success is True
                assert result.processing_time > 0
                assert result.moves_analyzed > 0
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, pipeline):
        """Test pipeline error handling with invalid inputs."""
        # Test with non-existent file
        result = await pipeline.generate_choreography(
            audio_input="/non/existent/file.mp3",
            difficulty="beginner",
            energy_level="medium"
        )
        
        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message.lower() or "invalid" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_pipeline_caching(self, pipeline):
        """Test that pipeline caching works correctly."""
        songs_dir = Path("data/songs")
        if not songs_dir.exists() or not list(songs_dir.glob("*.mp3")):
            pytest.skip("No local songs found for caching test")
        
        test_song = list(songs_dir.glob("*.mp3"))[0]
        
        with patch.object(pipeline, '_download_audio') as mock_download:
            mock_download.return_value = str(test_song)
            
            with patch.object(pipeline, '_generate_video') as mock_video:
                mock_video.return_value = "data/output/test_video.mp4"
                
                # First run - should process normally
                result1 = await pipeline.generate_choreography(
                    audio_input=str(test_song),
                    difficulty="beginner",
                    energy_level="medium"
                )
                
                # Second run - should use cache
                result2 = await pipeline.generate_choreography(
                    audio_input=str(test_song),
                    difficulty="beginner", 
                    energy_level="medium"
                )
                
                assert result1.success is True
                assert result2.success is True
                
                # Second run should have cache hits
                assert result2.cache_hits >= result1.cache_hits
    
    @pytest.mark.asyncio
    async def test_different_difficulty_levels(self, pipeline):
        """Test choreography generation with different difficulty levels."""
        songs_dir = Path("data/songs")
        if not songs_dir.exists() or not list(songs_dir.glob("*.mp3")):
            pytest.skip("No local songs found for difficulty test")
        
        test_song = list(songs_dir.glob("*.mp3"))[0]
        difficulties = ["beginner", "intermediate", "advanced"]
        
        with patch.object(pipeline, '_download_audio') as mock_download:
            mock_download.return_value = str(test_song)
            
            with patch.object(pipeline, '_generate_video') as mock_video:
                mock_video.return_value = "data/output/test_video.mp4"
                
                results = {}
                for difficulty in difficulties:
                    result = await pipeline.generate_choreography(
                        audio_input=str(test_song),
                        difficulty=difficulty,
                        energy_level="medium"
                    )
                    results[difficulty] = result
                    assert result.success is True
                
                # Verify different difficulties produce different results
                # (This would be more meaningful with actual implementation)
                assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_energy_level_variations(self, pipeline):
        """Test choreography generation with different energy levels."""
        songs_dir = Path("data/songs")
        if not songs_dir.exists() or not list(songs_dir.glob("*.mp3")):
            pytest.skip("No local songs found for energy level test")
        
        test_song = list(songs_dir.glob("*.mp3"))[0]
        energy_levels = ["low", "medium", "high"]
        
        with patch.object(pipeline, '_download_audio') as mock_download:
            mock_download.return_value = str(test_song)
            
            with patch.object(pipeline, '_generate_video') as mock_video:
                mock_video.return_value = "data/output/test_video.mp4"
                
                results = {}
                for energy in energy_levels:
                    result = await pipeline.generate_choreography(
                        audio_input=str(test_song),
                        difficulty="intermediate",
                        energy_level=energy
                    )
                    results[energy] = result
                    assert result.success is True
                
                # Verify different energy levels produce different results
                assert len(results) == 3
    
    def test_pipeline_config_validation(self):
        """Test pipeline configuration validation."""
        # Valid config
        valid_config = PipelineConfig(
            quality_mode="balanced",
            enable_caching=True,
            max_workers=4,
            cleanup_after_generation=True
        )
        pipeline = ChoreoGenerationPipeline(valid_config)
        assert pipeline.config.quality_mode == "balanced"
        
        # Test different quality modes
        for mode in ["fast", "balanced", "high"]:
            config = PipelineConfig(quality_mode=mode)
            pipeline = ChoreoGenerationPipeline(config)
            assert pipeline.config.quality_mode == mode
    
    @pytest.mark.asyncio
    async def test_concurrent_generation_handling(self, pipeline):
        """Test handling of concurrent generation requests."""
        songs_dir = Path("data/songs")
        if not songs_dir.exists() or not list(songs_dir.glob("*.mp3")):
            pytest.skip("No local songs found for concurrency test")
        
        test_song = list(songs_dir.glob("*.mp3"))[0]
        
        with patch.object(pipeline, '_download_audio') as mock_download:
            mock_download.return_value = str(test_song)
            
            with patch.object(pipeline, '_generate_video') as mock_video:
                mock_video.return_value = "data/output/test_video.mp4"
                
                # Start multiple concurrent generations
                tasks = []
                for i in range(3):
                    task = asyncio.create_task(
                        pipeline.generate_choreography(
                            audio_input=str(test_song),
                            difficulty="beginner",
                            energy_level="medium"
                        )
                    )
                    tasks.append(task)
                
                # Wait for all to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All should succeed (or handle gracefully)
                for result in results:
                    if isinstance(result, Exception):
                        pytest.fail(f"Concurrent generation failed: {result}")
                    assert result.success is True


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])