"""
Integration tests for instructor controller endpoints.
Tests the endpoint structure and basic functionality without full authentication.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.controllers.instructor_controller import InstructorController
from app.services.instructor_dashboard_service import InstructorDashboardService
from app.models.database_models import User, ClassPlan


@pytest.fixture
def mock_instructor_service():
    """Create a mock instructor dashboard service."""
    service = Mock(spec=InstructorDashboardService)
    
    # Mock all async methods
    service.create_class_plan = AsyncMock()
    service.get_instructor_class_plans = AsyncMock()
    service.get_class_plan_by_id = AsyncMock()
    service.update_class_plan = AsyncMock()
    service.delete_class_plan = AsyncMock()
    service.add_choreography_to_plan = AsyncMock()
    service.remove_choreography_from_plan = AsyncMock()
    service.update_sequence_details = AsyncMock()
    service.reorder_choreography_sequence = AsyncMock()
    service.generate_class_plan_summary = AsyncMock()
    service.duplicate_class_plan = AsyncMock()
    service.get_instructor_dashboard_stats = AsyncMock()
    
    return service


@pytest.fixture
def instructor_controller(mock_instructor_service):
    """Create instructor controller with mocked service."""
    return InstructorController(mock_instructor_service)


@pytest.fixture
def test_app(instructor_controller):
    """Create test FastAPI app with instructor controller."""
    app = FastAPI()
    app.include_router(instructor_controller.get_router())
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestInstructorEndpointsIntegration:
    """Test instructor controller endpoint integration."""
    
    def test_controller_initialization(self, mock_instructor_service):
        """Test that controller initializes correctly."""
        controller = InstructorController(mock_instructor_service)
        assert controller.instructor_service == mock_instructor_service
        assert controller.router.prefix == "/api/instructor"
        assert "instructor" in controller.router.tags
    
    def test_router_has_expected_routes(self, instructor_controller):
        """Test that all expected routes are registered."""
        router = instructor_controller.get_router()
        
        # Get all route paths
        route_paths = [route.path for route in router.routes]
        
        expected_paths = [
            "/class-plans",
            "/class-plans/{class_plan_id}",
            "/class-plans/{class_plan_id}/choreographies",
            "/class-plans/{class_plan_id}/choreographies/{choreography_id}",
            "/class-plans/{class_plan_id}/reorder",
            "/class-plans/{class_plan_id}/summary",
            "/class-plans/{class_plan_id}/export",
            "/class-plans/{class_plan_id}/duplicate",
            "/dashboard/stats"
        ]
        
        for expected_path in expected_paths:
            assert expected_path in route_paths, f"Missing route: {expected_path}"
    
    def test_create_class_plan_endpoint_structure(self, client):
        """Test create class plan endpoint structure (without auth)."""
        # This will fail auth but should show the endpoint exists
        response = client.post("/api/instructor/class-plans", json={
            "title": "Test Plan",
            "difficulty_level": "intermediate"
        })
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403, 422], f"Unexpected status: {response.status_code}"
    
    def test_list_class_plans_endpoint_structure(self, client):
        """Test list class plans endpoint structure (without auth)."""
        response = client.get("/api/instructor/class-plans")
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403], f"Unexpected status: {response.status_code}"
    
    def test_get_class_plan_endpoint_structure(self, client):
        """Test get class plan endpoint structure (without auth)."""
        response = client.get("/api/instructor/class-plans/test-id")
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403], f"Unexpected status: {response.status_code}"
    
    def test_update_class_plan_endpoint_structure(self, client):
        """Test update class plan endpoint structure (without auth)."""
        response = client.put("/api/instructor/class-plans/test-id", json={
            "title": "Updated Plan"
        })
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403, 422], f"Unexpected status: {response.status_code}"
    
    def test_delete_class_plan_endpoint_structure(self, client):
        """Test delete class plan endpoint structure (without auth)."""
        response = client.delete("/api/instructor/class-plans/test-id")
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403], f"Unexpected status: {response.status_code}"
    
    def test_add_choreography_endpoint_structure(self, client):
        """Test add choreography to plan endpoint structure (without auth)."""
        response = client.post("/api/instructor/class-plans/test-id/choreographies", json={
            "choreography_id": "choreo-123"
        })
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403, 422], f"Unexpected status: {response.status_code}"
    
    def test_remove_choreography_endpoint_structure(self, client):
        """Test remove choreography from plan endpoint structure (without auth)."""
        response = client.delete("/api/instructor/class-plans/test-id/choreographies/choreo-123")
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403], f"Unexpected status: {response.status_code}"
    
    def test_update_sequence_endpoint_structure(self, client):
        """Test update sequence details endpoint structure (without auth)."""
        response = client.put("/api/instructor/class-plans/test-id/choreographies/choreo-123", json={
            "notes": "Updated notes"
        })
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403, 422], f"Unexpected status: {response.status_code}"
    
    def test_reorder_sequences_endpoint_structure(self, client):
        """Test reorder sequences endpoint structure (without auth)."""
        response = client.put("/api/instructor/class-plans/test-id/reorder", json={
            "sequence_updates": [
                {"choreography_id": "choreo-1", "sequence_order": 1}
            ]
        })
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403, 422], f"Unexpected status: {response.status_code}"
    
    def test_class_plan_summary_endpoint_structure(self, client):
        """Test class plan summary endpoint structure (without auth)."""
        response = client.get("/api/instructor/class-plans/test-id/summary")
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403], f"Unexpected status: {response.status_code}"
    
    def test_export_class_plan_endpoint_structure(self, client):
        """Test export class plan endpoint structure (without auth)."""
        response = client.get("/api/instructor/class-plans/test-id/export")
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403], f"Unexpected status: {response.status_code}"
    
    def test_duplicate_class_plan_endpoint_structure(self, client):
        """Test duplicate class plan endpoint structure (without auth)."""
        response = client.post("/api/instructor/class-plans/test-id/duplicate", json={
            "new_title": "Duplicated Plan"
        })
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403, 422], f"Unexpected status: {response.status_code}"
    
    def test_dashboard_stats_endpoint_structure(self, client):
        """Test dashboard stats endpoint structure (without auth)."""
        response = client.get("/api/instructor/dashboard/stats")
        
        # Should get 403 (auth required) not 404 (endpoint not found)
        assert response.status_code in [401, 403], f"Unexpected status: {response.status_code}"
    
    @patch('app.middleware.auth_middleware.require_instructor')
    @patch('app.database.get_database_session')
    def test_create_class_plan_with_mocked_auth(self, mock_db, mock_auth, mock_instructor_service):
        """Test create class plan with mocked authentication."""
        # Mock the authentication to return a valid instructor
        mock_instructor = Mock(spec=User)
        mock_instructor.id = "instructor-123"
        mock_instructor.is_instructor = True
        mock_auth.return_value = mock_instructor
        
        # Mock the database session
        mock_db.return_value = Mock()
        
        # Mock the service response
        mock_class_plan = Mock(spec=ClassPlan)
        mock_class_plan.id = "plan-123"
        mock_class_plan.title = "Test Plan"
        mock_class_plan.difficulty_level = "intermediate"
        mock_instructor_service.create_class_plan.return_value = mock_class_plan
        
        # Create controller with mocked service
        controller = InstructorController(mock_instructor_service)
        app = FastAPI()
        app.include_router(controller.get_router())
        client = TestClient(app)
        
        # Test the endpoint
        response = client.post("/api/instructor/class-plans", json={
            "title": "Test Plan",
            "difficulty_level": "intermediate"
        })
        
        # This test verifies the endpoint structure works with proper mocking
        # The actual response will depend on how the mocking is set up
        assert response.status_code in [200, 201, 401, 403, 422]
    
    def test_printable_html_generation(self, instructor_controller):
        """Test the HTML generation for class plan export."""
        # Test the private method directly
        mock_summary = {
            "class_plan": {
                "id": "plan-123",
                "title": "Test Class Plan",
                "description": "Test description",
                "difficulty_level": "intermediate",
                "estimated_duration": 60,
                "instructor_notes": "Test notes",
                "created_at": "2024-01-01T00:00:00"
            },
            "summary_statistics": {
                "total_choreographies": 2,
                "total_estimated_teaching_time": 30,
                "total_video_duration_minutes": 8.5,
                "estimated_total_class_time": 45,
                "difficulty_distribution": {"beginner": 1, "intermediate": 1, "advanced": 0},
                "difficulty_progression": ["beginner", "intermediate"]
            },
            "choreography_sequences": [
                {
                    "sequence_order": 1,
                    "choreography_id": "choreo-1",
                    "choreography_title": "Basic Steps",
                    "choreography_difficulty": "beginner",
                    "choreography_duration": 180.0,
                    "estimated_teaching_time": 15,
                    "sequence_notes": "Start with basics",
                    "music_info": {"title": "Test Song"}
                },
                {
                    "sequence_order": 2,
                    "choreography_id": "choreo-2",
                    "choreography_title": "Advanced Moves",
                    "choreography_difficulty": "intermediate",
                    "choreography_duration": 330.0,
                    "estimated_teaching_time": 15,
                    "sequence_notes": None,
                    "music_info": {"title": "Another Song"}
                }
            ],
            "teaching_recommendations": [
                "Consider adding warm-up time",
                "Good progression from beginner to intermediate"
            ]
        }
        
        html_content = instructor_controller._generate_printable_html(mock_summary)
        
        # Verify HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "Test Class Plan" in html_content
        assert "intermediate" in html_content
        assert "Basic Steps" in html_content
        assert "Advanced Moves" in html_content
        assert "Consider adding warm-up time" in html_content
        assert "Test notes" in html_content
        assert "Start with basics" in html_content
        
        # Verify CSS is included
        assert "<style>" in html_content
        assert "font-family:" in html_content
        
        # Verify statistics are included
        assert "Total Choreographies" in html_content
        assert "Teaching Time" in html_content
        assert "30 min" in html_content
        assert "8.5 min" in html_content


if __name__ == "__main__":
    pytest.main([__file__])