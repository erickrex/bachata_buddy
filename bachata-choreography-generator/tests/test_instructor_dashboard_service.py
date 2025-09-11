"""
Tests for the instructor dashboard service.

Tests class plan CRUD operations, choreography sequencing, and summary generation.
"""

import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.database_models import User, SavedChoreography, ClassPlan, ClassPlanSequence
from app.services.instructor_dashboard_service import InstructorDashboardService


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def instructor_service():
    """Create instructor dashboard service instance."""
    return InstructorDashboardService()


@pytest.fixture
def test_instructor(db_session):
    """Create a test instructor user."""
    instructor = User(
        id=str(uuid.uuid4()),
        email="instructor@test.com",
        password_hash="hashed_password",
        display_name="Test Instructor",
        is_instructor=True,
        is_active=True
    )
    db_session.add(instructor)
    db_session.commit()
    db_session.refresh(instructor)
    return instructor


@pytest.fixture
def test_regular_user(db_session):
    """Create a test regular user (non-instructor)."""
    user = User(
        id=str(uuid.uuid4()),
        email="user@test.com",
        password_hash="hashed_password",
        display_name="Test User",
        is_instructor=False,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_choreographies(db_session, test_instructor):
    """Create test choreographies for the instructor."""
    choreographies = []
    for i in range(3):
        choreo = SavedChoreography(
            id=str(uuid.uuid4()),
            user_id=test_instructor.id,
            title=f"Test Choreography {i+1}",
            video_path=f"/path/to/video{i+1}.mp4",
            difficulty=["beginner", "intermediate", "advanced"][i],
            duration=60.0 + i * 30,
            music_info={"title": f"Song {i+1}", "artist": f"Artist {i+1}"},
            generation_parameters={"tempo": 120 + i * 10}
        )
        choreographies.append(choreo)
        db_session.add(choreo)
    
    db_session.commit()
    for choreo in choreographies:
        db_session.refresh(choreo)
    return choreographies


class TestInstructorDashboardService:
    """Test cases for instructor dashboard service."""
    
    @pytest.mark.asyncio
    async def test_create_class_plan_success(self, db_session, instructor_service, test_instructor):
        """Test successful class plan creation."""
        class_plan = await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Beginner Bachata Class",
            description="Introduction to basic Bachata steps",
            difficulty_level="beginner",
            estimated_duration=60,
            instructor_notes="Focus on basic timing and posture"
        )
        
        assert class_plan is not None
        assert class_plan.title == "Beginner Bachata Class"
        assert class_plan.difficulty_level == "beginner"
        assert class_plan.estimated_duration == 60
        assert class_plan.instructor_id == test_instructor.id
    
    @pytest.mark.asyncio
    async def test_create_class_plan_non_instructor_fails(self, db_session, instructor_service, test_regular_user):
        """Test that non-instructors cannot create class plans."""
        with pytest.raises(ValueError, match="Instructor not found or user does not have instructor privileges"):
            await instructor_service.create_class_plan(
                db=db_session,
                instructor_id=test_regular_user.id,
                title="Test Class"
            )
    
    @pytest.mark.asyncio
    async def test_create_class_plan_invalid_difficulty(self, db_session, instructor_service, test_instructor):
        """Test class plan creation with invalid difficulty level."""
        with pytest.raises(ValueError, match="Invalid difficulty level"):
            await instructor_service.create_class_plan(
                db=db_session,
                instructor_id=test_instructor.id,
                title="Test Class",
                difficulty_level="expert"
            )
    
    @pytest.mark.asyncio
    async def test_get_instructor_class_plans(self, db_session, instructor_service, test_instructor):
        """Test retrieving instructor's class plans."""
        # Create test class plans
        for i in range(3):
            await instructor_service.create_class_plan(
                db=db_session,
                instructor_id=test_instructor.id,
                title=f"Class Plan {i+1}",
                difficulty_level=["beginner", "intermediate", "advanced"][i]
            )
        
        # Get class plans
        result = await instructor_service.get_instructor_class_plans(
            db=db_session,
            instructor_id=test_instructor.id
        )
        
        assert result["total_count"] == 3
        assert len(result["class_plans"]) == 3
        assert result["page"] == 1
        assert result["total_pages"] == 1
    
    @pytest.mark.asyncio
    async def test_get_instructor_class_plans_with_filtering(self, db_session, instructor_service, test_instructor):
        """Test retrieving class plans with difficulty filtering."""
        # Create test class plans
        await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Beginner Class",
            difficulty_level="beginner"
        )
        await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Advanced Class",
            difficulty_level="advanced"
        )
        
        # Filter by beginner difficulty
        result = await instructor_service.get_instructor_class_plans(
            db=db_session,
            instructor_id=test_instructor.id,
            difficulty_filter="beginner"
        )
        
        assert result["total_count"] == 1
        assert result["class_plans"][0].title == "Beginner Class"
    
    @pytest.mark.asyncio
    async def test_update_class_plan(self, db_session, instructor_service, test_instructor):
        """Test updating class plan metadata."""
        # Create class plan
        class_plan = await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Original Title"
        )
        
        # Update class plan
        updated_plan = await instructor_service.update_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id,
            title="Updated Title",
            difficulty_level="advanced"
        )
        
        assert updated_plan is not None
        assert updated_plan.title == "Updated Title"
        assert updated_plan.difficulty_level == "advanced"
    
    @pytest.mark.asyncio
    async def test_delete_class_plan(self, db_session, instructor_service, test_instructor):
        """Test deleting a class plan."""
        # Create class plan
        class_plan = await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="To Delete"
        )
        
        # Delete class plan
        success = await instructor_service.delete_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id
        )
        
        assert success is True
        
        # Verify deletion
        deleted_plan = await instructor_service.get_class_plan_by_id(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id
        )
        assert deleted_plan is None
    
    @pytest.mark.asyncio
    async def test_add_choreography_to_plan(self, db_session, instructor_service, test_instructor, test_choreographies):
        """Test adding choreography to a class plan."""
        # Create class plan
        class_plan = await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Test Class"
        )
        
        # Add choreography to plan
        sequence = await instructor_service.add_choreography_to_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id,
            choreography_id=test_choreographies[0].id,
            notes="Start with this basic move",
            estimated_time=15
        )
        
        assert sequence is not None
        assert sequence.choreography_id == test_choreographies[0].id
        assert sequence.sequence_order == 1
        assert sequence.notes == "Start with this basic move"
        assert sequence.estimated_time == 15
    
    @pytest.mark.asyncio
    async def test_add_choreography_duplicate_fails(self, db_session, instructor_service, test_instructor, test_choreographies):
        """Test that adding the same choreography twice fails."""
        # Create class plan
        class_plan = await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Test Class"
        )
        
        # Add choreography first time
        await instructor_service.add_choreography_to_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id,
            choreography_id=test_choreographies[0].id
        )
        
        # Try to add same choreography again
        with pytest.raises(ValueError, match="Choreography is already in this class plan"):
            await instructor_service.add_choreography_to_plan(
                db=db_session,
                instructor_id=test_instructor.id,
                class_plan_id=class_plan.id,
                choreography_id=test_choreographies[0].id
            )
    
    @pytest.mark.asyncio
    async def test_remove_choreography_from_plan(self, db_session, instructor_service, test_instructor, test_choreographies):
        """Test removing choreography from a class plan."""
        # Create class plan and add choreography
        class_plan = await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Test Class"
        )
        
        await instructor_service.add_choreography_to_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id,
            choreography_id=test_choreographies[0].id
        )
        
        # Remove choreography
        success = await instructor_service.remove_choreography_from_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id,
            choreography_id=test_choreographies[0].id
        )
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_reorder_choreography_sequence(self, db_session, instructor_service, test_instructor, test_choreographies):
        """Test reordering choreographies in a class plan."""
        # Create class plan and add multiple choreographies
        class_plan = await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Test Class"
        )
        
        for i, choreo in enumerate(test_choreographies):
            await instructor_service.add_choreography_to_plan(
                db=db_session,
                instructor_id=test_instructor.id,
                class_plan_id=class_plan.id,
                choreography_id=choreo.id,
                sequence_order=i + 1
            )
        
        # Reorder sequences
        sequence_updates = [
            {"choreography_id": test_choreographies[0].id, "sequence_order": 3},
            {"choreography_id": test_choreographies[2].id, "sequence_order": 1}
        ]
        
        success = await instructor_service.reorder_choreography_sequence(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id,
            choreography_sequence_updates=sequence_updates
        )
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_generate_class_plan_summary(self, db_session, instructor_service, test_instructor, test_choreographies):
        """Test generating a comprehensive class plan summary."""
        # Create class plan and add choreographies
        class_plan = await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Complete Class",
            description="Full class with multiple choreographies",
            difficulty_level="intermediate",
            estimated_duration=90
        )
        
        for i, choreo in enumerate(test_choreographies):
            await instructor_service.add_choreography_to_plan(
                db=db_session,
                instructor_id=test_instructor.id,
                class_plan_id=class_plan.id,
                choreography_id=choreo.id,
                estimated_time=20 + i * 5,
                notes=f"Notes for choreography {i+1}"
            )
        
        # Generate summary
        summary = await instructor_service.generate_class_plan_summary(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id
        )
        
        assert summary is not None
        assert summary["class_plan"]["title"] == "Complete Class"
        assert summary["summary_statistics"]["total_choreographies"] == 3
        assert len(summary["choreography_sequences"]) == 3
        assert len(summary["teaching_recommendations"]) >= 0
        
        # Check difficulty distribution
        difficulty_dist = summary["summary_statistics"]["difficulty_distribution"]
        assert difficulty_dist["beginner"] == 1
        assert difficulty_dist["intermediate"] == 1
        assert difficulty_dist["advanced"] == 1
    
    @pytest.mark.asyncio
    async def test_duplicate_class_plan(self, db_session, instructor_service, test_instructor, test_choreographies):
        """Test duplicating a class plan with sequences."""
        # Create original class plan
        original_plan = await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Original Class",
            description="Original description",
            difficulty_level="intermediate"
        )
        
        # Add choreography to original plan
        await instructor_service.add_choreography_to_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=original_plan.id,
            choreography_id=test_choreographies[0].id,
            notes="Original notes"
        )
        
        # Duplicate class plan
        duplicated_plan = await instructor_service.duplicate_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            source_class_plan_id=original_plan.id,
            new_title="Duplicated Class",
            copy_sequences=True
        )
        
        assert duplicated_plan is not None
        assert duplicated_plan.title == "Duplicated Class"
        assert duplicated_plan.description == "Original description"
        assert duplicated_plan.difficulty_level == "intermediate"
        assert duplicated_plan.id != original_plan.id
        
        # Verify sequences were copied
        summary = await instructor_service.generate_class_plan_summary(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=duplicated_plan.id
        )
        assert summary["summary_statistics"]["total_choreographies"] == 1
    
    @pytest.mark.asyncio
    async def test_get_instructor_dashboard_stats(self, db_session, instructor_service, test_instructor, test_choreographies):
        """Test getting instructor dashboard statistics."""
        # Create some class plans
        for i in range(2):
            class_plan = await instructor_service.create_class_plan(
                db=db_session,
                instructor_id=test_instructor.id,
                title=f"Class {i+1}",
                difficulty_level=["beginner", "intermediate"][i]
            )
            
            # Add choreography to each plan
            await instructor_service.add_choreography_to_plan(
                db=db_session,
                instructor_id=test_instructor.id,
                class_plan_id=class_plan.id,
                choreography_id=test_choreographies[0].id
            )
        
        # Get dashboard stats
        stats = await instructor_service.get_instructor_dashboard_stats(
            db=db_session,
            instructor_id=test_instructor.id
        )
        
        assert stats["instructor_info"]["display_name"] == "Test Instructor"
        assert stats["class_plan_statistics"]["total_class_plans"] == 2
        assert len(stats["choreography_usage"]) >= 1
        assert stats["choreography_usage"][0]["usage_count"] == 2  # Used in both class plans
    
    @pytest.mark.asyncio
    async def test_update_sequence_details(self, db_session, instructor_service, test_instructor, test_choreographies):
        """Test updating sequence-specific details."""
        # Create class plan and add choreography
        class_plan = await instructor_service.create_class_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            title="Test Class"
        )
        
        await instructor_service.add_choreography_to_plan(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id,
            choreography_id=test_choreographies[0].id,
            notes="Original notes",
            estimated_time=15
        )
        
        # Update sequence details
        updated_sequence = await instructor_service.update_sequence_details(
            db=db_session,
            instructor_id=test_instructor.id,
            class_plan_id=class_plan.id,
            choreography_id=test_choreographies[0].id,
            notes="Updated notes",
            estimated_time=25
        )
        
        assert updated_sequence is not None
        assert updated_sequence.notes == "Updated notes"
        assert updated_sequence.estimated_time == 25