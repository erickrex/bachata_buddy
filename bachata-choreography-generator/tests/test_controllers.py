"""
Unit tests for API controllers.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Mock the dependencies that might not be available
with patch.dict('sys.modules', {
    'yt_dlp': Mock(),
    'librosa': Mock(),
    'mediapipe': Mock(),
    'cv2': Mock(),
    'numpy': Mock(),
    'sklearn': Mock()
}):
    from app.controllers.choreography_controller import ChoreographyController
    from app.controllers.media_controller import MediaController
    from app.controllers.auth_controller import AuthController
    from app.controllers.collection_controller import CollectionController
    from app.controllers.instructor_controller import InstructorController


class TestChoreographyController:
    """Test cases for ChoreographyController."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with choreography controller."""
        app = FastAPI()
        controller = ChoreographyController()
        app.include_router(controller.get_router())
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    def test_create_choreography_endpoint_exists(self, client):
        """Test that the choreography creation endpoint exists."""
        # Test with invalid data to check endpoint exists
        response = client.post("/api/choreography", json={})
        # Should return 422 (validation error) not 404 (not found)
        assert response.status_code == 422
    
    def test_task_status_endpoint(self, client):
        """Test task status endpoint."""
        # Test with non-existent task ID
        response = client.get("/api/task/non-existent-id")
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]
    
    def test_list_tasks_endpoint(self, client):
        """Test list tasks endpoint."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_tasks" in data
        assert "running_tasks" in data
        assert "completed_tasks" in data
        assert "failed_tasks" in data
        assert "tasks" in data
    
    def test_youtube_validation_endpoint(self, client):
        """Test YouTube URL validation endpoint."""
        # Test with empty URL
        response = client.post("/api/validate/youtube", json={"url": ""})
        assert response.status_code == 400
        
        # Test with valid URL format
        with patch('app.validation.validate_youtube_url_async') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "message": "Valid URL",
                "details": {"title": "Test Video"}
            }
            
            response = client.post("/api/validate/youtube", json={
                "url": "https://www.youtube.com/watch?v=test"
            })
            assert response.status_code == 200
            
            data = response.json()
            assert data["valid"] is True
            assert "details" in data
    
    @patch('app.controllers.choreography_controller.validate_system_requirements')
    @patch('app.controllers.choreography_controller.validate_youtube_url_async')
    def test_create_choreography_validation(self, mock_url_validate, mock_system_validate, client):
        """Test choreography creation with validation."""
        # Mock system validation to pass
        mock_system_validate.return_value = {"valid": True, "issues": [], "warnings": []}
        
        # Mock URL validation to pass
        mock_url_validate.return_value = {
            "valid": True,
            "message": "Valid URL",
            "details": {"title": "Test Video", "duration": 180}
        }
        
        response = client.post("/api/choreography", json={
            "youtube_url": "https://www.youtube.com/watch?v=test",
            "difficulty": "beginner",
            "energy_level": "medium",
            "quality_mode": "balanced"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "started"


class TestMediaController:
    """Test cases for MediaController."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with media controller."""
        app = FastAPI()
        controller = MediaController()
        app.include_router(controller.get_router())
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
    
    def test_list_videos_endpoint(self, client):
        """Test video listing endpoint."""
        response = client.get("/api/videos")
        assert response.status_code == 200
        
        data = response.json()
        assert "videos" in data
        assert isinstance(data["videos"], list)
    
    def test_list_songs_endpoint(self, client):
        """Test song listing endpoint."""
        response = client.get("/api/songs")
        assert response.status_code == 200
        
        data = response.json()
        assert "songs" in data
        assert isinstance(data["songs"], list)
    
    def test_system_status_endpoint(self, client):
        """Test system status endpoint."""
        response = client.get("/api/system/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "system_validation" in data
        assert "pipeline_status" in data
    
    def test_serve_video_security(self, client):
        """Test video serving security measures."""
        # Test path traversal attempt
        response = client.get("/api/video/../../../etc/passwd")
        assert response.status_code == 400
        
        # Test invalid file extension
        response = client.get("/api/video/test.txt")
        assert response.status_code == 400
        
        # Test non-existent file
        response = client.get("/api/video/nonexistent.mp4")
        assert response.status_code == 404
    
    @patch('app.services.resource_manager.resource_manager')
    def test_manual_cleanup_endpoint(self, mock_resource_manager, client):
        """Test manual cleanup endpoint."""
        # Mock cleanup results
        mock_resource_manager.cleanup_temporary_files.return_value = {
            "files_removed": 5,
            "bytes_freed": 1024000
        }
        mock_resource_manager.cleanup_cache_directory.return_value = {
            "files_removed": 2,
            "bytes_freed": 512000
        }
        
        response = client.post("/api/system/cleanup")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "temporary_files" in data
        assert "cache_cleanup" in data
        assert data["total_files_removed"] == 7
        assert data["total_bytes_freed"] == 1536000


class TestAuthController:
    """Test cases for AuthController."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with auth controller."""
        app = FastAPI()
        controller = AuthController()
        app.include_router(controller.get_router())
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    def test_register_endpoint_not_implemented(self, client):
        """Test that register endpoint returns not implemented."""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "display_name": "Test User"
        })
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]
    
    def test_login_endpoint_not_implemented(self, client):
        """Test that login endpoint returns not implemented."""
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]
    
    def test_logout_endpoint_not_implemented(self, client):
        """Test that logout endpoint returns not implemented."""
        response = client.post("/api/auth/logout")
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]
    
    def test_profile_endpoint_not_implemented(self, client):
        """Test that profile endpoint returns not implemented."""
        response = client.get("/api/auth/profile")
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]


class TestCollectionController:
    """Test cases for CollectionController."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with collection controller."""
        app = FastAPI()
        controller = CollectionController()
        app.include_router(controller.get_router())
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    def test_save_choreography_not_implemented(self, client):
        """Test that save choreography endpoint returns not implemented."""
        response = client.post("/api/collection/save", json={
            "video_id": "test-id",
            "title": "Test Choreography"
        })
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]
    
    def test_get_collection_not_implemented(self, client):
        """Test that get collection endpoint returns not implemented."""
        response = client.get("/api/collection/")
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]
    
    def test_delete_choreography_not_implemented(self, client):
        """Test that delete choreography endpoint returns not implemented."""
        response = client.delete("/api/collection/test-id")
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]


class TestInstructorController:
    """Test cases for InstructorController."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with instructor controller."""
        app = FastAPI()
        controller = InstructorController()
        app.include_router(controller.get_router())
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    def test_create_class_plan_not_implemented(self, client):
        """Test that create class plan endpoint returns not implemented."""
        response = client.post("/api/instructor/class-plans", json={
            "title": "Test Class",
            "description": "Test Description",
            "difficulty_level": "beginner",
            "estimated_duration": 60
        })
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]
    
    def test_get_class_plans_not_implemented(self, client):
        """Test that get class plans endpoint returns not implemented."""
        response = client.get("/api/instructor/class-plans")
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]
    
    def test_instructor_analytics_not_implemented(self, client):
        """Test that instructor analytics endpoint returns not implemented."""
        response = client.get("/api/instructor/dashboard/analytics")
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]


class TestControllerIntegration:
    """Integration tests for controller interactions."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with all controllers."""
        app = FastAPI()
        
        # Add all controllers
        controllers = [
            ChoreographyController(),
            MediaController(),
            AuthController(),
            CollectionController(),
            InstructorController()
        ]
        
        for controller in controllers:
            app.include_router(controller.get_router())
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    def test_all_endpoints_accessible(self, client):
        """Test that all main endpoints are accessible."""
        endpoints_to_test = [
            ("/health", "GET", 200),
            ("/api/videos", "GET", 200),
            ("/api/songs", "GET", 200),
            ("/api/system/status", "GET", 200),
            ("/api/tasks", "GET", 200),
            ("/api/task/nonexistent", "GET", 404),
            ("/api/auth/profile", "GET", 501),
            ("/api/collection/", "GET", 501),
            ("/api/instructor/class-plans", "GET", 501)
        ]
        
        for endpoint, method, expected_status in endpoints_to_test:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            
            assert response.status_code == expected_status, f"Endpoint {endpoint} failed"
    
    def test_error_handling_consistency(self, client):
        """Test that error handling is consistent across controllers."""
        # Test 404 errors
        not_found_endpoints = [
            "/api/task/nonexistent",
            "/api/video/nonexistent.mp4"
        ]
        
        for endpoint in not_found_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 404
            assert "detail" in response.json()
    
    def test_cors_and_middleware(self, client):
        """Test that CORS and middleware are properly configured."""
        # Test OPTIONS request (CORS preflight)
        response = client.options("/health")
        # Should not return 405 Method Not Allowed if CORS is configured
        assert response.status_code != 405


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])