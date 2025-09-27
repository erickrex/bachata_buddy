"""
Integration tests for the collection system without external dependencies.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.database_models import User, SavedChoreography
from app.services.collection_service import CollectionService
from app.models.collection_models import SaveChoreographyRequest


@pytest.fixture
def temp_storage():
    """Create temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    user = User(
        id="test-user-123",
        email="test@example.com",
        password_hash="hashed_password",
        display_name="Test User",
        is_instructor=False
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_video_file(temp_storage):
    """Create a test video file."""
    video_path = Path(temp_storage) / "test_video.mp4"
    video_path.write_text("fake video content")
    return str(video_path)


@pytest.fixture
def collection_service(temp_storage):
    """Create collection service."""
    return CollectionService(storage_base_path=temp_storage)


class TestCollectionIntegration:
    """Integration tests for the complete collection system."""
    
    @pytest.mark.asyncio
    async def test_complete_collection_workflow(self, collection_service, test_db, test_user, test_video_file):
        """Test complete workflow: save -> list -> get -> update -> delete."""
        service = collection_service
        
        # 1. Save a choreography
        save_request = SaveChoreographyRequest(
            title="Integration Test Choreography",
            video_path=test_video_file,
            difficulty="intermediate",
            duration=150.0,
            music_info={"title": "Test Song", "artist": "Test Artist", "tempo": 120},
            generation_parameters={"energy": "medium", "style": "traditional"}
        )
        
        saved_choreo = await service.save_choreography(
            db=test_db,
            user_id=test_user.id,
            request=save_request
        )
        
        assert saved_choreo.title == "Integration Test Choreography"
        assert saved_choreo.difficulty == "intermediate"
        
        # 2. Verify file was copied to user storage
        user_storage = Path(service.storage_base_path) / "user_collections" / test_user.id
        assert user_storage.exists()
        
        video_files = list(user_storage.glob("*.mp4"))
        assert len(video_files) == 1
        assert video_files[0].read_text() == "fake video content"
        
        # 3. List choreographies
        from app.models.collection_models import CollectionListRequest
        list_request = CollectionListRequest(page=1, limit=20)
        
        collection = await service.get_user_collection(
            db=test_db,
            user_id=test_user.id,
            request=list_request
        )
        
        assert collection.total_count == 1
        assert len(collection.choreographies) == 1
        assert collection.choreographies[0].id == saved_choreo.id
        
        # 4. Get specific choreography
        retrieved_choreo = await service.get_choreography_by_id(
            db=test_db,
            user_id=test_user.id,
            choreography_id=saved_choreo.id
        )
        
        assert retrieved_choreo is not None
        assert retrieved_choreo.title == "Integration Test Choreography"
        assert retrieved_choreo.music_info["tempo"] == 120
        
        # 5. Update choreography
        from app.models.collection_models import UpdateChoreographyRequest
        update_request = UpdateChoreographyRequest(
            title="Updated Integration Test Choreography",
            difficulty="advanced"
        )
        
        updated_choreo = await service.update_choreography(
            db=test_db,
            user_id=test_user.id,
            choreography_id=saved_choreo.id,
            request=update_request
        )
        
        assert updated_choreo is not None
        assert updated_choreo.title == "Updated Integration Test Choreography"
        assert updated_choreo.difficulty == "advanced"
        
        # 6. Get collection stats
        stats = await service.get_collection_stats(
            db=test_db,
            user_id=test_user.id
        )
        
        assert stats.total_choreographies == 1
        assert stats.total_duration == 150.0
        assert stats.difficulty_breakdown["advanced"] == 1
        assert len(stats.recent_activity) == 1
        
        # 7. Delete choreography
        delete_success = await service.delete_choreography(
            db=test_db,
            user_id=test_user.id,
            choreography_id=saved_choreo.id
        )
        
        assert delete_success is True
        
        # 8. Verify deletion
        deleted_choreo = await service.get_choreography_by_id(
            db=test_db,
            user_id=test_user.id,
            choreography_id=saved_choreo.id
        )
        
        assert deleted_choreo is None
        
        # 9. Verify file was deleted
        video_files_after_delete = list(user_storage.glob("*.mp4"))
        assert len(video_files_after_delete) == 0
    
    @pytest.mark.asyncio
    async def test_user_isolation(self, collection_service, test_db, test_video_file):
        """Test that users can only access their own choreographies."""
        service = collection_service
        
        # Create two users
        user1 = User(
            id="user-1",
            email="user1@example.com",
            password_hash="hash1",
            display_name="User 1"
        )
        user2 = User(
            id="user-2",
            email="user2@example.com",
            password_hash="hash2",
            display_name="User 2"
        )
        
        test_db.add(user1)
        test_db.add(user2)
        test_db.commit()
        test_db.refresh(user1)
        test_db.refresh(user2)
        
        # User 1 saves a choreography
        save_request = SaveChoreographyRequest(
            title="User 1 Choreography",
            video_path=test_video_file,
            difficulty="beginner",
            duration=90.0
        )
        
        user1_choreo = await service.save_choreography(
            db=test_db,
            user_id=user1.id,
            request=save_request
        )
        
        # User 2 tries to access User 1's choreography
        user2_access = await service.get_choreography_by_id(
            db=test_db,
            user_id=user2.id,
            choreography_id=user1_choreo.id
        )
        
        assert user2_access is None  # User 2 cannot access User 1's choreography
        
        # User 2 tries to delete User 1's choreography
        delete_success = await service.delete_choreography(
            db=test_db,
            user_id=user2.id,
            choreography_id=user1_choreo.id
        )
        
        assert delete_success is False  # User 2 cannot delete User 1's choreography
        
        # Verify User 1's choreography still exists
        user1_access = await service.get_choreography_by_id(
            db=test_db,
            user_id=user1.id,
            choreography_id=user1_choreo.id
        )
        
        assert user1_access is not None  # User 1 can still access their choreography
    
    @pytest.mark.asyncio
    async def test_storage_organization(self, collection_service, test_db, test_video_file):
        """Test that files are properly organized by user."""
        service = collection_service
        
        # Create two users
        user1 = User(id="user-1", email="user1@example.com", password_hash="hash1", display_name="User 1")
        user2 = User(id="user-2", email="user2@example.com", password_hash="hash2", display_name="User 2")
        
        test_db.add(user1)
        test_db.add(user2)
        test_db.commit()
        test_db.refresh(user1)
        test_db.refresh(user2)
        
        # Both users save choreographies
        for user in [user1, user2]:
            save_request = SaveChoreographyRequest(
                title=f"{user.display_name} Choreography",
                video_path=test_video_file,
                difficulty="intermediate",
                duration=120.0
            )
            
            await service.save_choreography(
                db=test_db,
                user_id=user.id,
                request=save_request
            )
        
        # Verify separate storage directories
        user1_storage = Path(service.storage_base_path) / "user_collections" / user1.id
        user2_storage = Path(service.storage_base_path) / "user_collections" / user2.id
        
        assert user1_storage.exists()
        assert user2_storage.exists()
        assert user1_storage != user2_storage
        
        # Verify each user has their own files
        user1_files = list(user1_storage.glob("*.mp4"))
        user2_files = list(user2_storage.glob("*.mp4"))
        
        assert len(user1_files) == 1
        assert len(user2_files) == 1
        
        # Verify file names are different (based on choreography IDs)
        assert user1_files[0].name != user2_files[0].name