"""
Tests for the collection service functionality.
"""

import pytest
from app.models.collection_models import SaveChoreographyRequest, CollectionListRequest


@pytest.mark.service
class TestCollectionService:
    """Test cases for the collection service."""
    
    @pytest.mark.asyncio
    async def test_save_choreography_success(self, collection_service, test_db, test_user, temp_video_file):
        """Test successful choreography saving."""
        request = SaveChoreographyRequest(
            title="Test Choreography",
            video_path=test_video_file,
            difficulty="intermediate",
            duration=120.5,
            music_info={"title": "Test Song", "artist": "Test Artist"},
            generation_parameters={"tempo": 120, "energy": "medium"}
        )
        
        result = await collection_service.save_choreography(
            db=test_db,
            user_id=test_user.id,
            request=request
        )
        
        assert result.title == "Test Choreography"
        assert result.user_id == test_user.id
        assert result.difficulty == "intermediate"
        assert result.duration == 120.5
        assert result.music_info["title"] == "Test Song"
        
        # Verify file was copied to user storage
        user_storage = Path(collection_service.storage_base_path) / "user_collections" / test_user.id
        assert user_storage.exists()
        
        # Check that choreography was saved to database
        saved_choreo = test_db.query(SavedChoreography).filter(
            SavedChoreography.id == result.id
        ).first()
        assert saved_choreo is not None
        assert saved_choreo.title == "Test Choreography"
    
    @pytest.mark.asyncio
    async def test_save_choreography_invalid_difficulty(self, collection_service, test_db, test_user, test_video_file):
        """Test saving choreography with invalid difficulty."""
        request = SaveChoreographyRequest(
            title="Test Choreography",
            video_path=test_video_file,
            difficulty="expert",  # Invalid difficulty
            duration=120.5
        )
        
        with pytest.raises(ValueError, match="Invalid difficulty level"):
            await collection_service.save_choreography(
                db=test_db,
                user_id=test_user.id,
                request=request
            )
    
    @pytest.mark.asyncio
    async def test_save_choreography_file_not_found(self, collection_service, test_db, test_user):
        """Test saving choreography with non-existent file."""
        request = SaveChoreographyRequest(
            title="Test Choreography",
            video_path="/nonexistent/file.mp4",
            difficulty="beginner",
            duration=120.5
        )
        
        with pytest.raises(FileNotFoundError):
            await collection_service.save_choreography(
                db=test_db,
                user_id=test_user.id,
                request=request
            )
    
    @pytest.mark.asyncio
    async def test_get_user_collection_empty(self, collection_service, test_db, test_user):
        """Test getting empty user collection."""
        request = CollectionListRequest(page=1, limit=20)
        
        result = await collection_service.get_user_collection(
            db=test_db,
            user_id=test_user.id,
            request=request
        )
        
        assert result.total_count == 0
        assert len(result.choreographies) == 0
        assert result.page == 1
        assert result.total_pages == 0
        assert not result.has_next
        assert not result.has_previous
    
    @pytest.mark.asyncio
    async def test_get_user_collection_with_data(self, collection_service, test_db, test_user, test_video_file):
        """Test getting user collection with saved choreographies."""
        # Save a choreography first
        request = SaveChoreographyRequest(
            title="Test Choreography",
            video_path=test_video_file,
            difficulty="intermediate",
            duration=120.5
        )
        
        await collection_service.save_choreography(
            db=test_db,
            user_id=test_user.id,
            request=request
        )
        
        # Get collection
        list_request = CollectionListRequest(page=1, limit=20)
        result = await collection_service.get_user_collection(
            db=test_db,
            user_id=test_user.id,
            request=list_request
        )
        
        assert result.total_count == 1
        assert len(result.choreographies) == 1
        assert result.choreographies[0].title == "Test Choreography"
    
    @pytest.mark.asyncio
    async def test_delete_choreography_success(self, collection_service, test_db, test_user, test_video_file):
        """Test successful choreography deletion."""
        # Save a choreography first
        request = SaveChoreographyRequest(
            title="Test Choreography",
            video_path=test_video_file,
            difficulty="intermediate",
            duration=120.5
        )
        
        saved_choreo = await collection_service.save_choreography(
            db=test_db,
            user_id=test_user.id,
            request=request
        )
        
        # Delete the choreography
        success = await collection_service.delete_choreography(
            db=test_db,
            user_id=test_user.id,
            choreography_id=saved_choreo.id
        )
        
        assert success is True
        
        # Verify it's deleted from database
        deleted_choreo = test_db.query(SavedChoreography).filter(
            SavedChoreography.id == saved_choreo.id
        ).first()
        assert deleted_choreo is None
    
    @pytest.mark.asyncio
    async def test_delete_choreography_not_found(self, collection_service, test_db, test_user):
        """Test deleting non-existent choreography."""
        success = await collection_service.delete_choreography(
            db=test_db,
            user_id=test_user.id,
            choreography_id="nonexistent-id"
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_get_collection_stats(self, collection_service, test_db, test_user, test_video_file):
        """Test getting collection statistics."""
        # Save some choreographies
        for i in range(3):
            request = SaveChoreographyRequest(
                title=f"Test Choreography {i+1}",
                video_path=test_video_file,
                difficulty="beginner" if i == 0 else "intermediate",
                duration=60.0 + i * 30
            )
            
            await collection_service.save_choreography(
                db=test_db,
                user_id=test_user.id,
                request=request
            )
        
        # Get stats
        stats = await collection_service.get_collection_stats(
            db=test_db,
            user_id=test_user.id
        )
        
        assert stats.total_choreographies == 3
        assert stats.total_duration == 60.0 + 90.0 + 120.0  # Sum of durations
        assert stats.difficulty_breakdown["beginner"] == 1
        assert stats.difficulty_breakdown["intermediate"] == 2
        assert len(stats.recent_activity) == 3
    
    @pytest.mark.asyncio
    async def test_get_choreography_by_id(self, collection_service, test_db, test_user, test_video_file):
        """Test getting specific choreography by ID."""
        # Save a choreography first
        request = SaveChoreographyRequest(
            title="Test Choreography",
            video_path=test_video_file,
            difficulty="intermediate",
            duration=120.5
        )
        
        saved_choreo = await collection_service.save_choreography(
            db=test_db,
            user_id=test_user.id,
            request=request
        )
        
        # Get by ID
        result = await collection_service.get_choreography_by_id(
            db=test_db,
            user_id=test_user.id,
            choreography_id=saved_choreo.id
        )
        
        assert result is not None
        assert result.id == saved_choreo.id
        assert result.title == "Test Choreography"
    
    @pytest.mark.asyncio
    async def test_get_choreography_by_id_not_found(self, collection_service, test_db, test_user):
        """Test getting non-existent choreography by ID."""
        result = await collection_service.get_choreography_by_id(
            db=test_db,
            user_id=test_user.id,
            choreography_id="nonexistent-id"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_collection_filtering_by_difficulty(self, collection_service, test_db, test_user, test_video_file):
        """Test filtering collection by difficulty."""
        # Save choreographies with different difficulties
        difficulties = ["beginner", "intermediate", "advanced"]
        for difficulty in difficulties:
            request = SaveChoreographyRequest(
                title=f"Test {difficulty.title()} Choreography",
                video_path=test_video_file,
                difficulty=difficulty,
                duration=120.0
            )
            
            await collection_service.save_choreography(
                db=test_db,
                user_id=test_user.id,
                request=request
            )
        
        # Filter by intermediate
        list_request = CollectionListRequest(page=1, limit=20, difficulty="intermediate")
        result = await collection_service.get_user_collection(
            db=test_db,
            user_id=test_user.id,
            request=list_request
        )
        
        assert result.total_count == 1
        assert result.choreographies[0].difficulty == "intermediate"
        assert "Intermediate" in result.choreographies[0].title