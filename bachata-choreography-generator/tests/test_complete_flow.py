#!/usr/bin/env python3
"""
Test the complete choreography generation flow including authentication.
"""

import sys
import asyncio
import json
import uuid
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from main import app


def test_complete_flow():
    """Test the complete application flow."""
    print("🧪 Testing Complete Application Flow")
    print("=" * 50)
    
    # Create test client
    client = TestClient(app)
    
    # Generate unique email for this test
    test_email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    
    try:
        # Test 1: User Registration
        print("\n1. Testing user registration...")
        registration_data = {
            "email": test_email,
            "password": "securepassword123",
            "display_name": "Test User",
            "is_instructor": False
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        print(f"   Registration status: {response.status_code}")
        
        if response.status_code == 201:
            registration_result = response.json()
            access_token = registration_result["tokens"]["access_token"]
            print("   ✅ User registration successful")
        else:
            print(f"   ❌ Registration failed: {response.text}")
            return False
        
        # Test 2: Choreography Generation
        print("\n2. Testing choreography generation...")
        choreography_data = {
            "youtube_url": "data/songs/Amor.mp3",
            "difficulty": "intermediate",
            "quality_mode": "balanced"
        }
        
        response = client.post("/api/choreography", json=choreography_data)
        print(f"   Generation request status: {response.status_code}")
        
        if response.status_code == 200:
            generation_result = response.json()
            task_id = generation_result["task_id"]
            print(f"   ✅ Generation started, task ID: {task_id}")
            
            # Poll for completion (simplified for test)
            max_polls = 120  # 2 minutes max
            for i in range(max_polls):
                response = client.get(f"/api/task/{task_id}")
                if response.status_code == 200:
                    status = response.json()
                    print(f"   Progress: {status['progress']}% - {status['message']}")
                    
                    if status["status"] == "completed":
                        print("   ✅ Generation completed successfully!")
                        video_filename = status["result"]["video_filename"]
                        break
                    elif status["status"] == "failed":
                        print(f"   ❌ Generation failed: {status['error']}")
                        return False
                else:
                    print(f"   ❌ Error checking status: {response.text}")
                    return False
                
                # Wait 1 second between polls
                import time
                time.sleep(1)
            else:
                print("   ❌ Generation timed out")
                return False
        else:
            print(f"   ❌ Generation request failed: {response.text}")
            return False
        
        # Test 3: Video Access
        print("\n3. Testing video file access...")
        response = client.get(f"/api/video/{video_filename}")
        print(f"   Video access status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Video file accessible, size: {len(response.content)} bytes")
        else:
            print(f"   ❌ Video access failed: {response.text}")
            return False
        
        # Test 4: Save to Collection (authenticated)
        print("\n4. Testing save to collection...")
        headers = {"Authorization": f"Bearer {access_token}"}
        collection_data = {
            "title": f"Test Choreography - {video_filename}",
            "video_filename": video_filename,
            "metadata": {
                "song": "data/songs/Amor.mp3",
                "difficulty": "intermediate",
                "quality_mode": "balanced"
            }
        }
        
        response = client.post("/api/collection/save", json=collection_data, headers=headers)
        print(f"   Save to collection status: {response.status_code}")
        
        if response.status_code == 201:
            print("   ✅ Choreography saved to collection successfully")
        else:
            print(f"   ❌ Save to collection failed: {response.text}")
            return False
        
        # Test 5: List User's Collection
        print("\n5. Testing collection listing...")
        response = client.get("/api/collection", headers=headers)
        print(f"   Collection listing status: {response.status_code}")
        
        if response.status_code == 200:
            collection_result = response.json()
            print(f"   ✅ Collection listed, {len(collection_result['choreographies'])} items")
        else:
            print(f"   ❌ Collection listing failed: {response.text}")
            return False
        
        # Test 6: Frontend Pages
        print("\n6. Testing frontend pages...")
        
        # Main page
        response = client.get("/")
        print(f"   Main page status: {response.status_code}")
        if response.status_code != 200:
            print(f"   ❌ Main page failed: {response.text}")
            return False
        
        # Collection page
        response = client.get("/collection")
        print(f"   Collection page status: {response.status_code}")
        if response.status_code != 200:
            print(f"   ❌ Collection page failed: {response.text}")
            return False
        
        print("   ✅ All frontend pages accessible")
        
        print("\n🎉 Complete Application Flow Test PASSED!")
        print("\n📋 Summary:")
        print("✅ User registration and authentication")
        print("✅ Choreography generation from local song")
        print("✅ Video file serving")
        print("✅ Save choreography to user collection")
        print("✅ Collection management")
        print("✅ Frontend page serving")
        print("\n🚀 The application is working correctly!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    
    finally:
        # Clean up test data
        print("\n🧹 Cleaning up test data...")
        try:
            from app.database import SessionLocal
            from app.models.database_models import User
            
            db = SessionLocal()
            test_user = db.query(User).filter(User.email == test_email).first()
            if test_user:
                db.delete(test_user)
                db.commit()
            db.close()
            print("   ✅ Test data cleaned up")
        except Exception as e:
            print(f"   ⚠️ Cleanup warning: {e}")


if __name__ == "__main__":
    success = test_complete_flow()
    if not success:
        sys.exit(1)