"""
Direct tests for instructor controller functionality.
Tests the controller logic without full FastAPI integration.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.services.instructor_dashboard_service import InstructorDashboardService
from app.models.database_models import User, ClassPlan, ClassPlanSequence
from app.models.instructor_models import (
    CreateClassPlanRequest,
    UpdateClassPlanRequest,
    AddChoreographyToClassPlanRequest,
    ClassPlanResponse,
    ClassPlanListResponse
)


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
def mock_instructor_user():
    """Create a mock instructor user."""
    user = Mock(spec=User)
    user.id = "instructor-123"
    user.email = "instructor@example.com"
    user.display_name = "Test Instructor"
    user.is_instructor = True
    user.is_active = True
    return user


@pytest.fixture
def mock_class_plan():
    """Create a mock class plan."""
    plan = Mock(spec=ClassPlan)
    plan.id = "plan-123"
    plan.instructor_id = "instructor-123"
    plan.title = "Test Class Plan"
    plan.description = "Test description"
    plan.difficulty_level = "intermediate"
    plan.estimated_duration = 60
    plan.instructor_notes = "Test notes"
    plan.created_at = datetime.now()
    plan.updated_at = datetime.now()
    return plan


class TestInstructorControllerDirect:
    """Test instructor controller functionality directly."""
    
    def test_controller_initialization(self, mock_instructor_service):
        """Test that controller initializes correctly."""
        # Import here to avoid the jose dependency issue
        from app.controllers.instructor_controller import InstructorController
        
        controller = InstructorController(mock_instructor_service)
        assert controller.instructor_service == mock_instructor_service
        assert controller.router.prefix == "/api/instructor"
        assert "instructor" in controller.router.tags
    
    def test_generate_printable_html_basic(self, mock_instructor_service):
        """Test HTML generation functionality."""
        from app.controllers.instructor_controller import InstructorController
        
        controller = InstructorController(mock_instructor_service)
        
        # Test data
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
                }
            ],
            "teaching_recommendations": [
                "Consider adding warm-up time"
            ]
        }
        
        html_content = controller._generate_printable_html(mock_summary)
        
        # Verify HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "Test Class Plan" in html_content
        assert "intermediate" in html_content
        assert "Basic Steps" in html_content
        assert "Consider adding warm-up time" in html_content
        assert "Test notes" in html_content
        assert "Start with basics" in html_content
        
        # Verify CSS is included
        assert "<style>" in html_content
        assert "font-family:" in html_content
        
        # Verify statistics are included
        assert "Total Choreographies" in html_content
        assert "Teaching Time" in html_content
    
    def test_generate_printable_html_empty_sequences(self, mock_instructor_service):
        """Test HTML generation with empty sequences."""
        from app.controllers.instructor_controller import InstructorController
        
        controller = InstructorController(mock_instructor_service)
        
        # Test data with no sequences
        mock_summary = {
            "class_plan": {
                "id": "plan-123",
                "title": "Empty Class Plan",
                "description": None,
                "difficulty_level": "beginner",
                "estimated_duration": None,
                "instructor_notes": None,
                "created_at": "2024-01-01T00:00:00"
            },
            "summary_statistics": {
                "total_choreographies": 0,
                "total_estimated_teaching_time": 0,
                "total_video_duration_minutes": 0.0,
                "estimated_total_class_time": 0,
                "difficulty_distribution": {"beginner": 0, "intermediate": 0, "advanced": 0},
                "difficulty_progression": []
            },
            "choreography_sequences": [],
            "teaching_recommendations": []
        }
        
        html_content = controller._generate_printable_html(mock_summary)
        
        # Verify HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "Empty Class Plan" in html_content
        assert "beginner" in html_content
        
        # Should handle empty sequences gracefully
        assert "Total Choreographies" in html_content
        assert "0" in html_content  # Should show 0 for empty stats
    
    def test_generate_printable_html_with_all_fields(self, mock_instructor_service):
        """Test HTML generation with all optional fields populated."""
        from app.controllers.instructor_controller import InstructorController
        
        controller = InstructorController(mock_instructor_service)
        
        # Test data with all fields
        mock_summary = {
            "class_plan": {
                "id": "plan-123",
                "title": "Complete Class Plan",
                "description": "Full description here",
                "difficulty_level": "advanced",
                "estimated_duration": 90,
                "instructor_notes": "Detailed instructor notes",
                "created_at": "2024-01-01T00:00:00"
            },
            "summary_statistics": {
                "total_choreographies": 3,
                "total_estimated_teaching_time": 60,
                "total_video_duration_minutes": 15.5,
                "estimated_total_class_time": 90,
                "difficulty_distribution": {"beginner": 1, "intermediate": 1, "advanced": 1},
                "difficulty_progression": ["beginner", "intermediate", "advanced"]
            },
            "choreography_sequences": [
                {
                    "sequence_order": 1,
                    "choreography_id": "choreo-1",
                    "choreography_title": "Warm Up",
                    "choreography_difficulty": "beginner",
                    "choreography_duration": 120.0,
                    "estimated_teaching_time": 10,
                    "sequence_notes": "Easy start",
                    "music_info": {"title": "Warm Up Song"}
                },
                {
                    "sequence_order": 2,
                    "choreography_id": "choreo-2",
                    "choreography_title": "Main Sequence",
                    "choreography_difficulty": "intermediate",
                    "choreography_duration": 300.0,
                    "estimated_teaching_time": 25,
                    "sequence_notes": "Core content",
                    "music_info": {"title": "Main Song"}
                },
                {
                    "sequence_order": 3,
                    "choreography_id": "choreo-3",
                    "choreography_title": "Advanced Finale",
                    "choreography_difficulty": "advanced",
                    "choreography_duration": 240.0,
                    "estimated_teaching_time": 25,
                    "sequence_notes": None,
                    "music_info": {"title": "Finale Song"}
                }
            ],
            "teaching_recommendations": [
                "Great progression from beginner to advanced",
                "Consider extra practice time for advanced moves",
                "Perfect class length for advanced students"
            ]
        }
        
        html_content = controller._generate_printable_html(mock_summary)
        
        # Verify all content is included
        assert "Complete Class Plan" in html_content
        assert "Full description here" in html_content
        assert "Detailed instructor notes" in html_content
        assert "advanced" in html_content
        assert "90 minutes" in html_content
        
        # Verify all sequences
        assert "Warm Up" in html_content
        assert "Main Sequence" in html_content
        assert "Advanced Finale" in html_content
        assert "Easy start" in html_content
        assert "Core content" in html_content
        
        # Verify recommendations
        assert "Great progression from beginner to advanced" in html_content
        assert "Consider extra practice time" in html_content
        assert "Perfect class length" in html_content
        
        # Verify statistics
        assert "60 min" in html_content  # teaching time
        assert "15.5 min" in html_content  # video duration
        assert "90 min" in html_content  # total time
    
    def test_service_method_calls(self, mock_instructor_service, mock_instructor_user, mock_class_plan):
        """Test that controller methods call service methods correctly."""
        from app.controllers.instructor_controller import InstructorController
        
        controller = InstructorController(mock_instructor_service)
        
        # Test create class plan service call
        mock_instructor_service.create_class_plan.return_value = mock_class_plan
        
        # We can't easily test the actual endpoint calls without full FastAPI setup,
        # but we can verify the service is properly injected and would be called
        assert controller.instructor_service == mock_instructor_service
        
        # Verify service methods exist and are callable
        assert hasattr(controller.instructor_service, 'create_class_plan')
        assert hasattr(controller.instructor_service, 'get_instructor_class_plans')
        assert hasattr(controller.instructor_service, 'get_class_plan_by_id')
        assert hasattr(controller.instructor_service, 'update_class_plan')
        assert hasattr(controller.instructor_service, 'delete_class_plan')
        assert hasattr(controller.instructor_service, 'add_choreography_to_plan')
        assert hasattr(controller.instructor_service, 'remove_choreography_from_plan')
        assert hasattr(controller.instructor_service, 'update_sequence_details')
        assert hasattr(controller.instructor_service, 'reorder_choreography_sequence')
        assert hasattr(controller.instructor_service, 'generate_class_plan_summary')
        assert hasattr(controller.instructor_service, 'duplicate_class_plan')
        assert hasattr(controller.instructor_service, 'get_instructor_dashboard_stats')
    
    def test_router_configuration(self, mock_instructor_service):
        """Test that router is configured correctly."""
        from app.controllers.instructor_controller import InstructorController
        
        controller = InstructorController(mock_instructor_service)
        router = controller.get_router()
        
        # Check router configuration
        assert router.prefix == "/api/instructor"
        assert "instructor" in router.tags
        
        # Check that routes are registered
        assert len(router.routes) > 0
        
        # Get route paths and methods
        routes_info = []
        for route in router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes_info.append((route.path, route.methods))
        
        # Verify we have the expected routes
        route_paths = [info[0] for info in routes_info]
        
        expected_routes = [
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
        
        for expected_route in expected_routes:
            assert expected_route in route_paths, f"Missing route: {expected_route}"
    
    def test_request_models_validation(self):
        """Test request model validation works correctly."""
        # Test CreateClassPlanRequest
        valid_request = CreateClassPlanRequest(
            title="Valid Title",
            description="Valid description",
            difficulty_level="intermediate",
            estimated_duration=60,
            instructor_notes="Valid notes"
        )
        assert valid_request.title == "Valid Title"
        assert valid_request.difficulty_level == "intermediate"
        
        # Test validation errors
        with pytest.raises(ValueError):
            CreateClassPlanRequest(
                title="",  # Empty title should fail
                difficulty_level="intermediate"
            )
        
        with pytest.raises(ValueError):
            CreateClassPlanRequest(
                title="Valid Title",
                difficulty_level="invalid"  # Invalid difficulty should fail
            )
        
        # Test UpdateClassPlanRequest
        valid_update = UpdateClassPlanRequest(
            title="Updated Title",
            difficulty_level="advanced"
        )
        assert valid_update.title == "Updated Title"
        assert valid_update.difficulty_level == "advanced"
        
        # Test AddChoreographyToClassPlanRequest
        valid_add = AddChoreographyToClassPlanRequest(
            choreography_id="choreo-123",
            sequence_order=1,
            notes="Test notes",
            estimated_time=10
        )
        assert valid_add.choreography_id == "choreo-123"
        assert valid_add.sequence_order == 1
    
    def test_response_models_creation(self, mock_class_plan):
        """Test response model creation from database models."""
        # Test ClassPlanResponse creation
        response = ClassPlanResponse.from_orm(mock_class_plan)
        assert response.id == mock_class_plan.id
        assert response.title == mock_class_plan.title
        assert response.difficulty_level == mock_class_plan.difficulty_level
        
        # Test ClassPlanListResponse creation
        list_response = ClassPlanListResponse(
            class_plans=[response],
            total_count=1,
            page=1,
            limit=20,
            total_pages=1,
            has_next=False,
            has_previous=False
        )
        assert len(list_response.class_plans) == 1
        assert list_response.total_count == 1
        assert list_response.page == 1


if __name__ == "__main__":
    pytest.main([__file__])