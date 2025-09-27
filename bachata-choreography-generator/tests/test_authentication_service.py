#!/usr/bin/env python3
"""
Test script to verify the authentication service works correctly.
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.services.authentication_service import AuthenticationService
from app.models.database_models import User


async def test_authentication_service():
    """Test the authentication service functionality."""
    print("🧪 Testing Authentication Service\n")
    
    # Initialize authentication service
    jwt_secret = "test_secret_key_for_testing_only"
    auth_service = AuthenticationService(jwt_secret=jwt_secret)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Test 1: Password hashing and verification
        print("1. Testing password hashing and verification...")
        password = "testpass123"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password(password, hashed), "Password verification failed"
        assert not auth_service.verify_password("wrong_password", hashed), "Wrong password should not verify"
        print("   ✅ Password hashing and verification work correctly")
        
        # Test 2: User registration
        print("2. Testing user registration...")
        user = await auth_service.register_user(
            db=db,
            email="test@example.com",
            password="secure_password_123",
            display_name="Test User",
            is_instructor=False
        )
        
        assert user is not None, "User registration failed"
        assert user.email == "test@example.com", "Email not set correctly"
        assert user.display_name == "Test User", "Display name not set correctly"
        assert not user.is_instructor, "Instructor flag not set correctly"
        print("   ✅ User registration works correctly")
        
        # Test 3: Duplicate email registration
        print("3. Testing duplicate email registration...")
        duplicate_user = await auth_service.register_user(
            db=db,
            email="test@example.com",
            password="another_password",
            display_name="Another User"
        )
        
        assert duplicate_user is None, "Duplicate email registration should fail"
        print("   ✅ Duplicate email registration properly rejected")
        
        # Test 4: User authentication
        print("4. Testing user authentication...")
        authenticated_user = await auth_service.authenticate_user(
            db=db,
            email="test@example.com",
            password="secure_password_123"
        )
        
        assert authenticated_user is not None, "User authentication failed"
        assert authenticated_user.id == user.id, "Authenticated user ID mismatch"
        print("   ✅ User authentication works correctly")
        
        # Test 5: Wrong password authentication
        print("5. Testing wrong password authentication...")
        wrong_auth = await auth_service.authenticate_user(
            db=db,
            email="test@example.com",
            password="wrong_password"
        )
        
        assert wrong_auth is None, "Wrong password should not authenticate"
        print("   ✅ Wrong password properly rejected")
        
        # Test 6: JWT token creation and verification
        print("6. Testing JWT token creation and verification...")
        access_token = auth_service.create_access_token(
            user_id=user.id,
            email=user.email,
            is_instructor=user.is_instructor
        )
        
        refresh_token = auth_service.create_refresh_token(user_id=user.id)
        
        # Verify access token
        access_payload = auth_service.verify_token(access_token)
        assert access_payload is not None, "Access token verification failed"
        assert access_payload["sub"] == user.id, "Access token user ID mismatch"
        assert access_payload["email"] == user.email, "Access token email mismatch"
        assert access_payload["type"] == "access", "Access token type mismatch"
        
        # Verify refresh token
        refresh_payload = auth_service.verify_token(refresh_token)
        assert refresh_payload is not None, "Refresh token verification failed"
        assert refresh_payload["sub"] == user.id, "Refresh token user ID mismatch"
        assert refresh_payload["type"] == "refresh", "Refresh token type mismatch"
        
        print("   ✅ JWT token creation and verification work correctly")
        
        # Test 7: Get user by ID
        print("7. Testing get user by ID...")
        retrieved_user = await auth_service.get_user_by_id(db, user.id)
        
        assert retrieved_user is not None, "Get user by ID failed"
        assert retrieved_user.id == user.id, "Retrieved user ID mismatch"
        assert retrieved_user.email == user.email, "Retrieved user email mismatch"
        print("   ✅ Get user by ID works correctly")
        
        # Test 8: Update user profile
        print("8. Testing user profile update...")
        updated_user = await auth_service.update_user_profile(
            db=db,
            user_id=user.id,
            display_name="Updated Test User",
            new_password="new_secure_password_456"
        )
        
        assert updated_user is not None, "User profile update failed"
        assert updated_user.display_name == "Updated Test User", "Display name not updated"
        
        # Verify new password works
        auth_with_new_password = await auth_service.authenticate_user(
            db=db,
            email="test@example.com",
            password="new_secure_password_456"
        )
        assert auth_with_new_password is not None, "New password authentication failed"
        
        # Verify old password doesn't work
        auth_with_old_password = await auth_service.authenticate_user(
            db=db,
            email="test@example.com",
            password="secure_password_123"
        )
        assert auth_with_old_password is None, "Old password should not work after update"
        
        print("   ✅ User profile update works correctly")
        
        # Test 9: Rate limiting
        print("9. Testing rate limiting...")
        
        # Make multiple failed login attempts
        for i in range(6):  # Exceed the limit of 5
            await auth_service.authenticate_user(
                db=db,
                email="nonexistent@example.com",
                password="wrong_password"
            )
        
        # Check if rate limited
        is_limited = auth_service.is_rate_limited("nonexistent@example.com")
        assert is_limited, "Rate limiting should be active after multiple failed attempts"
        print("   ✅ Rate limiting works correctly")
        
        # Test 10: User deactivation
        print("10. Testing user deactivation...")
        deactivated = await auth_service.deactivate_user(db, user.id)
        assert deactivated, "User deactivation failed"
        
        # Try to authenticate deactivated user
        deactivated_auth = await auth_service.authenticate_user(
            db=db,
            email="test@example.com",
            password="new_secure_password_456"
        )
        assert deactivated_auth is None, "Deactivated user should not authenticate"
        print("   ✅ User deactivation works correctly")
        
        print("\n🎉 All authentication service tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        # Clean up test data
        print("\n🧹 Cleaning up test data...")
        try:
            test_user = db.query(User).filter(User.email == "test@example.com").first()
            if test_user:
                db.delete(test_user)
                db.commit()
            print("   ✅ Test data cleaned up")
        except Exception as e:
            print(f"   ⚠️ Cleanup warning: {e}")
        finally:
            db.close()


async def main():
    """Run authentication service tests."""
    await test_authentication_service()


if __name__ == "__main__":
    asyncio.run(main())