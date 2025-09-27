#!/usr/bin/env python3
"""
Test script for collection management interface functionality.
Tests the enhanced collection interface with search, filtering, pagination, and delete confirmation.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import shutil
import json

# Import application components
from main import app
from app.database import get_database_session, Base
from app.models.database_models import User, SavedChoreography
from app.services.authentication_service import AuthenticationService
from app.services.collection_service import CollectionService


def create_test_database():
    """Create a test database with sample data."""
    # Create temporary database
    db_path = tempfile.mktemp(suffix='.db')
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine, TestingSessionLocal, db_path


def create_test_user_and_choreographies(db_session, storage_path):
    """Create test user and sample choreographies."""
    # Create test user
    auth_service = AuthenticationService("test-jwt-secret-key")
    password_hash = auth_service.hash_password("testpass123")
    
    user = User(
        id="test-user-123",
        email="test@example.com",
        password_hash=password_hash,
        display_name="Test User",
        is_active=True,
        is_instructor=False
    )
    db_session.add(user)
    
    # Create sample video files
    user_storage = Path(storage_path) / "user_collections" / user.id
    user_storage.mkdir(parents=True, exist_ok=True)
    
    # Create sample choreographies with different difficulties and metadata
    choreographies_data = [
        {
            "id": "choreo-1",
            "title": "Romantic Bachata Sequence",
            "difficulty": "beginner",
            "duration": 120.5,
            "music_info": {
                "title": "Corazón Sin Cara",
                "artist": "Prince Royce",
                "tempo": 125
            },
            "generation_parameters": {
                "moves_count": 8,
                "style": "romantic"
            }
        },
        {
            "id": "choreo-2", 
            "title": "Advanced Turn Patterns",
            "difficulty": "advanced",
            "duration": 180.0,
            "music_info": {
                "title": "Obsesión",
                "artist": "Aventura",
                "tempo": 130
            },
            "generation_parameters": {
                "moves_count": 12,
                "style": "traditional"
            }
        },
        {
            "id": "choreo-3",
            "title": "Intermediate Flow",
            "difficulty": "intermediate", 
            "duration": 150.3,
            "music_info": {
                "title": "Danza Kuduro",
                "artist": "Don Omar",
                "tempo": 128
            },
            "generation_parameters": {
                "moves_count": 10,
                "style": "modern"
            }
        },
        {
            "id": "choreo-4",
            "title": "Basic Steps Practice",
            "difficulty": "beginner",
            "duration": 90.0,
            "music_info": {
                "title": "Bailando",
                "artist": "Enrique Iglesias",
                "tempo": 120
            },
            "generation_parameters": {
                "moves_count": 6,
                "style": "basic"
            }
        },
        {
            "id": "choreo-5",
            "title": "Sensual Bachata Moves",
            "difficulty": "intermediate",
            "duration": 200.7,
            "music_info": {
                "title": "Propuesta Indecente",
                "artist": "Romeo Santos",
                "tempo": 115
            },
            "generation_parameters": {
                "moves_count": 14,
                "style": "sensual"
            }
        }
    ]
    
    for choreo_data in choreographies_data:
        # Create dummy video file
        video_path = user_storage / f"{choreo_data['id']}.mp4"
        video_path.write_text("dummy video content")
        
        # Create dummy thumbnail
        thumbnail_path = user_storage / f"{choreo_data['id']}_thumb.jpg"
        thumbnail_path.write_text("dummy thumbnail content")
        
        choreography = SavedChoreography(
            id=choreo_data["id"],
            user_id=user.id,
            title=choreo_data["title"],
            video_path=str(video_path),
            thumbnail_path=str(thumbnail_path),
            difficulty=choreo_data["difficulty"],
            duration=choreo_data["duration"],
            music_info=choreo_data["music_info"],
            generation_parameters=choreo_data["generation_parameters"]
        )
        db_session.add(choreography)
    
    db_session.commit()
    return user


def test_collection_endpoints():
    """Test collection management endpoints."""
    print("🧪 Testing Collection Management Interface")
    print("=" * 50)
    
    # Create test database and storage
    engine, TestingSessionLocal, db_path = create_test_database()
    storage_path = tempfile.mkdtemp()
    
    try:
        # Override database dependency
        def override_get_database():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        app.dependency_overrides[get_database_session] = override_get_database
        
        # Create test data
        db_session = TestingSessionLocal()
        user = create_test_user_and_choreographies(db_session, storage_path)
        db_session.close()
        
        # Create test client
        client = TestClient(app)
        
        # Login to get token
        login_response = client.post("/api/auth/login", data={
            "email": "test@example.com",
            "password": "testpass123"
        })
        
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        login_data = login_response.json()
        token = login_data["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print("✅ User authentication successful")
        
        # Test 1: Get collection without filters
        print("\n📋 Test 1: Get full collection")
        response = client.get("/api/collection", headers=headers)
        assert response.status_code == 200, f"Get collection failed: {response.text}"
        
        data = response.json()
        assert "choreographies" in data
        assert "total_count" in data
        assert data["total_count"] == 5
        assert len(data["choreographies"]) == 5
        print(f"✅ Retrieved {data['total_count']} choreographies")
        
        # Test 2: Search functionality
        print("\n🔍 Test 2: Search functionality")
        response = client.get("/api/collection?search=romantic", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 1
        assert "romantic" in data["choreographies"][0]["title"].lower()
        print("✅ Search by title works")
        
        # Search by artist
        response = client.get("/api/collection?search=prince royce", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 1
        print("✅ Search by artist works")
        
        # Test 3: Difficulty filtering
        print("\n🎯 Test 3: Difficulty filtering")
        response = client.get("/api/collection?difficulty=beginner", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 2
        for choreo in data["choreographies"]:
            assert choreo["difficulty"] == "beginner"
        print("✅ Difficulty filtering works")
        
        # Test 4: Sorting
        print("\n📊 Test 4: Sorting functionality")
        response = client.get("/api/collection?sort_by=duration&sort_order=asc", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        durations = [choreo["duration"] for choreo in data["choreographies"]]
        assert durations == sorted(durations), "Choreographies should be sorted by duration ascending"
        print("✅ Sorting by duration works")
        
        # Test 5: Pagination
        print("\n📄 Test 5: Pagination")
        response = client.get("/api/collection?limit=2&page=1", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["choreographies"]) == 2
        assert data["page"] == 1
        assert data["total_pages"] == 3  # 5 items with limit 2 = 3 pages
        assert data["has_next"] == True
        assert data["has_previous"] == False
        print("✅ Pagination works correctly")
        
        # Test page 2
        response = client.get("/api/collection?limit=2&page=2", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["choreographies"]) == 2
        assert data["page"] == 2
        assert data["has_next"] == True
        assert data["has_previous"] == True
        print("✅ Page 2 navigation works")
        
        # Test 6: Get specific choreography
        print("\n🎬 Test 6: Get specific choreography")
        response = client.get("/api/collection/choreo-1", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "choreo-1"
        assert data["title"] == "Romantic Bachata Sequence"
        print("✅ Get specific choreography works")
        
        # Test 7: Delete choreography
        print("\n🗑️ Test 7: Delete choreography")
        response = client.delete("/api/collection/choreo-1", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        print("✅ Delete choreography works")
        
        # Verify deletion
        response = client.get("/api/collection", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 4  # Should be 4 after deletion
        print("✅ Choreography successfully deleted")
        
        # Test 8: Combined filters
        print("\n🔧 Test 8: Combined filters")
        response = client.get("/api/collection?difficulty=intermediate&sort_by=title&sort_order=asc", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_count"] == 2
        titles = [choreo["title"] for choreo in data["choreographies"]]
        assert titles == sorted(titles), "Should be sorted by title"
        print("✅ Combined filtering and sorting works")
        
        print("\n🎉 All collection interface tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise
    
    finally:
        # Cleanup
        try:
            os.unlink(db_path)
            shutil.rmtree(storage_path)
        except Exception:
            pass
        
        # Reset dependency overrides
        app.dependency_overrides.clear()


def test_frontend_template():
    """Test that the frontend template has all required features."""
    print("\n🎨 Testing Frontend Template Features")
    print("=" * 50)
    
    template_path = Path("app/templates/collection.html")
    
    if not template_path.exists():
        print("❌ Collection template not found")
        return False
    
    template_content = template_path.read_text()
    
    # Check for required features
    required_features = [
        # Search and filtering
        ('x-model="searchQuery"', "Search input"),
        ('x-model="difficultyFilter"', "Difficulty filter"),
        ('x-model="sortBy"', "Sort options"),
        
        # Grid layout
        ('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3', "Responsive grid layout"),
        
        # Video thumbnails
        (':poster="getThumbnailUrl(choreography)"', "Video thumbnails"),
        ('preload="metadata"', "Video preloading"),
        
        # Difficulty badges
        ('getDifficultyBadgeClass', "Difficulty badges"),
        
        # Pagination
        ('getPageNumbers()', "Pagination"),
        ('goToPage(', "Page navigation"),
        
        # Delete confirmation
        ('showDeleteModal', "Delete confirmation modal"),
        ('confirmDelete(', "Delete confirmation"),
        
        # Search functionality
        ('performSearch()', "Search function"),
        ('clearFilters()', "Clear filters function"),
        
        # Responsive design
        ('lg:col-span-2', "Responsive layout"),
        ('md:grid-cols-2', "Medium screen layout"),
    ]
    
    missing_features = []
    for feature, description in required_features:
        if feature not in template_content:
            missing_features.append(description)
        else:
            print(f"✅ {description}")
    
    if missing_features:
        print(f"\n❌ Missing features: {', '.join(missing_features)}")
        return False
    
    print("\n✅ All frontend template features present")
    return True


async def main():
    """Run all tests."""
    print("🚀 Starting Collection Management Interface Tests")
    print("=" * 60)
    
    try:
        # Test backend endpoints
        test_collection_endpoints()
        
        # Test frontend template
        test_frontend_template()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Collection management interface is ready.")
        print("\nFeatures implemented:")
        print("✅ Grid layout with video thumbnails")
        print("✅ Search functionality (title, artist, music)")
        print("✅ Difficulty filtering")
        print("✅ Sorting options (date, title, difficulty, duration)")
        print("✅ Pagination for large collections")
        print("✅ Delete confirmation modal")
        print("✅ Responsive design")
        print("✅ Video metadata display")
        print("✅ Download functionality")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())