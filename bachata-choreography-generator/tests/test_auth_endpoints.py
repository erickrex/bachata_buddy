#!/usr/bin/env python3
"""
Test script to verify authentication endpoints work correctly.
"""

import sys
import asyncio
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from fastapi.testclient import TestClient

# Import the FastAPI app
from main import app


async def test_auth_endpoints():
    """Test all authentication endpoints."""
    print("🧪 Testing Authentication Endpoints\n")
    
    # Create test client
    client = TestClient(app)
    
    try:
        # Test 1: User registration
        print("1. Testing user registration...")
        registration_data = {
            "email": "testuser@example.com",
            "password": "securepassword123",
            "display_name": "Test User",
            "is_instructor": False
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 201:
            registration_result = response.json()
            assert "user" in registration_result
            assert "tokens" in registration_result
            assert registration_result["user"]["email"] == "testuser@example.com"
            assert registration_result["user"]["display_name"] == "Test User"
            
            # Store tokens for later tests
            access_token = registration_result["tokens"]["access_token"]
            print("   ✅ User registration successful")
        else:
            print(f"   ❌ Registration failed: {response.text}")
            return
        
        # Test 2: User login
        print("2. Testing user login...")
        login_data = {
            "email": "testuser@example.com",
            "password": "securepassword123"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            login_result = response.json()
            assert "user" in login_result
            assert "tokens" in login_result
            assert login_result["user"]["email"] == "testuser@example.com"
            
            # Update access token
            access_token = login_result["tokens"]["access_token"]
            print("   ✅ User login successful")
        else:
            print(f"   ❌ Login failed: {response.text}")
            return
        
        # Test 3: Wrong password login
        print("3. Testing wrong password login...")
        wrong_login_data = {
            "email": "testuser@example.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/api/auth/login", json=wrong_login_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 400:
            print("   ✅ Wrong password properly rejected")
        else:
            print(f"   ❌ Wrong password should be rejected: {response.text}")
        
        # Test 4: Get user profile (authenticated)
        print("4. Testing authenticated profile access...")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = client.get("/api/auth/profile", headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            profile_result = response.json()
            assert profile_result["email"] == "testuser@example.com"
            assert profile_result["display_name"] == "Test User"
            print("   ✅ Authenticated profile access successful")
        else:
            print(f"   ❌ Profile access failed: {response.text}")
        
        # Test 5: Get user profile (unauthenticated)
        print("5. Testing unauthenticated profile access...")
        
        response = client.get("/api/auth/profile")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 401:
            print("   ✅ Unauthenticated access properly rejected")
        else:
            print(f"   ❌ Unauthenticated access should be rejected: {response.text}")
        
        # Test 6: Update user profile
        print("6. Testing profile update...")
        update_data = {
            "display_name": "Updated Test User"
        }
        
        response = client.put("/api/auth/profile", json=update_data, headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            updated_profile = response.json()
            assert updated_profile["display_name"] == "Updated Test User"
            print("   ✅ Profile update successful")
        else:
            print(f"   ❌ Profile update failed: {response.text}")
        
        # Test 7: Check authentication status
        print("7. Testing authentication status check...")
        
        response = client.get("/api/auth/status", headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            status_result = response.json()
            assert status_result["authenticated"] == True
            assert "user" in status_result
            print("   ✅ Authentication status check successful")
        else:
            print(f"   ❌ Authentication status check failed: {response.text}")
        
        # Test 8: Logout
        print("8. Testing user logout...")
        
        response = client.post("/api/auth/logout", headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 204:
            print("   ✅ User logout successful")
        else:
            print(f"   ❌ Logout failed: {response.text}")
        
        # Test 9: Duplicate email registration
        print("9. Testing duplicate email registration...")
        duplicate_registration_data = {
            "email": "testuser@example.com",
            "password": "anotherpassword123",
            "display_name": "Another User",
            "is_instructor": True
        }
        
        response = client.post("/api/auth/register", json=duplicate_registration_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 400:
            print("   ✅ Duplicate email registration properly rejected")
        else:
            print(f"   ❌ Duplicate email should be rejected: {response.text}")
        
        # Test 10: Invalid token access
        print("10. Testing invalid token access...")
        invalid_headers = {"Authorization": "Bearer invalid_token_here"}
        
        response = client.get("/api/auth/profile", headers=invalid_headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 401:
            print("   ✅ Invalid token properly rejected")
        else:
            print(f"   ❌ Invalid token should be rejected: {response.text}")
        
        print("\n🎉 All authentication endpoint tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        # Clean up test data
        print("\n🧹 Cleaning up test data...")
        try:
            from app.database import SessionLocal
            from app.models.database_models import User
            
            db = SessionLocal()
            test_user = db.query(User).filter(User.email == "testuser@example.com").first()
            if test_user:
                db.delete(test_user)
                db.commit()
            db.close()
            print("   ✅ Test data cleaned up")
        except Exception as e:
            print(f"   ⚠️ Cleanup warning: {e}")


async def main():
    """Run authentication endpoint tests."""
    await test_auth_endpoints()


if __name__ == "__main__":
    asyncio.run(main())