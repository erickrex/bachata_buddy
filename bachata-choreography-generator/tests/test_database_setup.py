#!/usr/bin/env python3
"""
Test script to verify database setup and models work correctly.
"""

import sys
import uuid
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal, get_database_info
from app.models.database_models import User, SavedChoreography, ClassPlan, ClassPlanSequence


def test_database_models():
    """Test that all database models work correctly."""
    print("Testing database models...")
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Test User model
        print("1. Testing User model...")
        test_user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            password_hash="hashed_password_here",
            display_name="Test User",
            is_instructor=True
        )
        db.add(test_user)
        db.commit()
        print("   ✅ User created successfully")
        
        # Test SavedChoreography model
        print("2. Testing SavedChoreography model...")
        test_choreography = SavedChoreography(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            title="Test Choreography",
            video_path="/path/to/video.mp4",
            difficulty="intermediate",
            duration=120.5,
            music_info={"title": "Test Song", "artist": "Test Artist", "tempo": 125},
            generation_parameters={"difficulty": "intermediate", "energy": "medium"}
        )
        db.add(test_choreography)
        db.commit()
        print("   ✅ SavedChoreography created successfully")
        
        # Test ClassPlan model
        print("3. Testing ClassPlan model...")
        test_class_plan = ClassPlan(
            id=str(uuid.uuid4()),
            instructor_id=test_user.id,
            title="Beginner Bachata Class",
            description="Introduction to basic Bachata steps",
            difficulty_level="beginner",
            estimated_duration=60,
            instructor_notes="Focus on basic timing and connection"
        )
        db.add(test_class_plan)
        db.commit()
        print("   ✅ ClassPlan created successfully")
        
        # Test ClassPlanSequence model
        print("4. Testing ClassPlanSequence model...")
        test_sequence = ClassPlanSequence(
            id=str(uuid.uuid4()),
            class_plan_id=test_class_plan.id,
            choreography_id=test_choreography.id,
            sequence_order=1,
            notes="Start with this choreography to warm up",
            estimated_time=15
        )
        db.add(test_sequence)
        db.commit()
        print("   ✅ ClassPlanSequence created successfully")
        
        # Test relationships
        print("5. Testing model relationships...")
        
        # Query user and check relationships
        user_from_db = db.query(User).filter(User.email == "test@example.com").first()
        assert user_from_db is not None
        assert len(user_from_db.choreographies) == 1
        assert len(user_from_db.class_plans) == 1
        print("   ✅ User relationships work correctly")
        
        # Query choreography and check relationship
        choreography_from_db = db.query(SavedChoreography).filter(SavedChoreography.title == "Test Choreography").first()
        assert choreography_from_db is not None
        assert choreography_from_db.user.email == "test@example.com"
        print("   ✅ SavedChoreography relationships work correctly")
        
        # Query class plan and check relationships
        class_plan_from_db = db.query(ClassPlan).filter(ClassPlan.title == "Beginner Bachata Class").first()
        assert class_plan_from_db is not None
        assert class_plan_from_db.instructor.email == "test@example.com"
        assert len(class_plan_from_db.choreography_sequences) == 1
        print("   ✅ ClassPlan relationships work correctly")
        
        print("\n🎉 All database models and relationships work correctly!")
        
        # Clean up test data
        print("\n6. Cleaning up test data...")
        db.delete(test_sequence)
        db.delete(test_class_plan)
        db.delete(test_choreography)
        db.delete(test_user)
        db.commit()
        print("   ✅ Test data cleaned up")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Run database tests."""
    print("🧪 Testing Bachata Choreography Generator Database Setup\n")
    
    # Display database info
    db_info = get_database_info()
    print(f"Database: {db_info['database_path']}")
    print(f"Size: {db_info['database_size_mb']} MB\n")
    
    # Run tests
    test_database_models()
    
    print("\n✅ All tests passed! Database setup is working correctly.")


if __name__ == "__main__":
    main()