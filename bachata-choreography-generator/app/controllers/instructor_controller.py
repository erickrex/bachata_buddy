"""
Instructor dashboard controller for class plan management and choreography sequencing.
"""

from typing import Annotated, List, Dict, Any
from fastapi import HTTPException, status, Depends, Query, Response
from sqlalchemy.orm import Session

from .base_controller import BaseController
from app.database import get_database_session
from app.services.instructor_dashboard_service import InstructorDashboardService
from app.middleware.auth_middleware import InstructorUser
from app.models.instructor_models import (
    CreateClassPlanRequest,
    UpdateClassPlanRequest,
    AddChoreographyToClassPlanRequest,
    UpdateSequenceDetailsRequest,
    ReorderSequencesRequest,
    DuplicateClassPlanRequest,
    ClassPlanListRequest,
    ClassPlanResponse,
    ClassPlanListResponse,
    ClassPlanSummaryResponse,
    InstructorDashboardStatsResponse,
    ClassPlanSequenceResponse
)
from app.models.auth_models import ErrorResponse


class InstructorController(BaseController):
    """Controller for instructor dashboard endpoints."""
    
    def __init__(self, instructor_service: InstructorDashboardService):
        """
        Initialize the instructor controller.
        
        Args:
            instructor_service: Instructor dashboard service instance
        """
        super().__init__(prefix="/api/instructor", tags=["instructor"])
        self.instructor_service = instructor_service
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up instructor dashboard routes."""
        
        @self.router.post(
            "/class-plans",
            response_model=ClassPlanResponse,
            status_code=status.HTTP_201_CREATED,
            responses={
                400: {"model": ErrorResponse, "description": "Invalid input"},
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                422: {"model": ErrorResponse, "description": "Validation error"}
            }
        )
        async def create_class_plan(
            request: CreateClassPlanRequest,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Create a new class plan.
            
            Creates a new class plan with the provided metadata.
            Only accessible to users with instructor privileges.
            """
            try:
                self.log_request("create_class_plan", {
                    "instructor_id": instructor.id,
                    "title": request.title,
                    "difficulty_level": request.difficulty_level
                })
                
                class_plan = await self.instructor_service.create_class_plan(
                    db=db,
                    instructor_id=instructor.id,
                    title=request.title,
                    description=request.description,
                    difficulty_level=request.difficulty_level,
                    estimated_duration=request.estimated_duration,
                    instructor_notes=request.instructor_notes
                )
                
                return ClassPlanResponse.from_orm(class_plan)
                
            except ValueError as e:
                self.log_error("create_class_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                self.log_error("create_class_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create class plan"
                )
        
        @self.router.get(
            "/class-plans",
            response_model=ClassPlanListResponse,
            responses={
                403: {"model": ErrorResponse, "description": "Instructor privileges required"}
            }
        )
        async def list_class_plans(
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)],
            difficulty_filter: str = Query(None, description="Filter by difficulty level"),
            sort_by: str = Query("created_at", description="Sort field"),
            sort_order: str = Query("desc", description="Sort order (asc/desc)"),
            page: int = Query(1, ge=1, description="Page number"),
            limit: int = Query(20, ge=1, le=100, description="Items per page")
        ):
            """
            List class plans for the authenticated instructor.
            
            Returns paginated list of class plans with filtering and sorting options.
            """
            try:
                self.log_request("list_class_plans", {
                    "instructor_id": instructor.id,
                    "difficulty_filter": difficulty_filter,
                    "page": page,
                    "limit": limit
                })
                
                result = await self.instructor_service.get_instructor_class_plans(
                    db=db,
                    instructor_id=instructor.id,
                    difficulty_filter=difficulty_filter,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    page=page,
                    limit=limit
                )
                
                return ClassPlanListResponse(
                    class_plans=[ClassPlanResponse.from_orm(cp) for cp in result["class_plans"]],
                    total_count=result["total_count"],
                    page=result["page"],
                    limit=result["limit"],
                    total_pages=result["total_pages"],
                    has_next=result["has_next"],
                    has_previous=result["has_previous"]
                )
                
            except ValueError as e:
                self.log_error("list_class_plans", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                self.log_error("list_class_plans", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve class plans"
                )
        
        @self.router.get(
            "/class-plans/{class_plan_id}",
            response_model=ClassPlanResponse,
            responses={
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                404: {"model": ErrorResponse, "description": "Class plan not found"}
            }
        )
        async def get_class_plan(
            class_plan_id: str,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Get a specific class plan by ID.
            
            Returns detailed information about a class plan owned by the instructor.
            """
            try:
                self.log_request("get_class_plan", {
                    "instructor_id": instructor.id,
                    "class_plan_id": class_plan_id
                })
                
                class_plan = await self.instructor_service.get_class_plan_by_id(
                    db=db,
                    instructor_id=instructor.id,
                    class_plan_id=class_plan_id
                )
                
                if not class_plan:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Class plan not found"
                    )
                
                return ClassPlanResponse.from_orm(class_plan)
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("get_class_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve class plan"
                )
        
        @self.router.put(
            "/class-plans/{class_plan_id}",
            response_model=ClassPlanResponse,
            responses={
                400: {"model": ErrorResponse, "description": "Invalid input"},
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                404: {"model": ErrorResponse, "description": "Class plan not found"},
                422: {"model": ErrorResponse, "description": "Validation error"}
            }
        )
        async def update_class_plan(
            class_plan_id: str,
            request: UpdateClassPlanRequest,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Update class plan metadata.
            
            Updates the specified class plan with new metadata.
            Only the instructor who owns the class plan can update it.
            """
            try:
                self.log_request("update_class_plan", {
                    "instructor_id": instructor.id,
                    "class_plan_id": class_plan_id
                })
                
                updated_class_plan = await self.instructor_service.update_class_plan(
                    db=db,
                    instructor_id=instructor.id,
                    class_plan_id=class_plan_id,
                    title=request.title,
                    description=request.description,
                    difficulty_level=request.difficulty_level,
                    estimated_duration=request.estimated_duration,
                    instructor_notes=request.instructor_notes
                )
                
                if not updated_class_plan:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Class plan not found"
                    )
                
                return ClassPlanResponse.from_orm(updated_class_plan)
                
            except HTTPException:
                raise
            except ValueError as e:
                self.log_error("update_class_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                self.log_error("update_class_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update class plan"
                )
        
        @self.router.delete(
            "/class-plans/{class_plan_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                404: {"model": ErrorResponse, "description": "Class plan not found"}
            }
        )
        async def delete_class_plan(
            class_plan_id: str,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Delete a class plan and all associated sequences.
            
            Permanently deletes the specified class plan and all its choreography sequences.
            Only the instructor who owns the class plan can delete it.
            """
            try:
                self.log_request("delete_class_plan", {
                    "instructor_id": instructor.id,
                    "class_plan_id": class_plan_id
                })
                
                success = await self.instructor_service.delete_class_plan(
                    db=db,
                    instructor_id=instructor.id,
                    class_plan_id=class_plan_id
                )
                
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Class plan not found"
                    )
                
                return None
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("delete_class_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete class plan"
                )
        
        @self.router.post(
            "/class-plans/{class_plan_id}/choreographies",
            response_model=ClassPlanSequenceResponse,
            status_code=status.HTTP_201_CREATED,
            responses={
                400: {"model": ErrorResponse, "description": "Invalid input or choreography already in plan"},
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                404: {"model": ErrorResponse, "description": "Class plan or choreography not found"},
                422: {"model": ErrorResponse, "description": "Validation error"}
            }
        )
        async def add_choreography_to_plan(
            class_plan_id: str,
            request: AddChoreographyToClassPlanRequest,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Add a choreography to a class plan.
            
            Adds the specified choreography to the class plan with sequencing information.
            The choreography must be owned by the instructor.
            """
            try:
                self.log_request("add_choreography_to_plan", {
                    "instructor_id": instructor.id,
                    "class_plan_id": class_plan_id,
                    "choreography_id": request.choreography_id
                })
                
                sequence = await self.instructor_service.add_choreography_to_plan(
                    db=db,
                    instructor_id=instructor.id,
                    class_plan_id=class_plan_id,
                    choreography_id=request.choreography_id,
                    sequence_order=request.sequence_order,
                    notes=request.notes,
                    estimated_time=request.estimated_time
                )
                
                return ClassPlanSequenceResponse.from_orm(sequence)
                
            except ValueError as e:
                self.log_error("add_choreography_to_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                self.log_error("add_choreography_to_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to add choreography to class plan"
                )
        
        @self.router.delete(
            "/class-plans/{class_plan_id}/choreographies/{choreography_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                404: {"model": ErrorResponse, "description": "Class plan or choreography sequence not found"}
            }
        )
        async def remove_choreography_from_plan(
            class_plan_id: str,
            choreography_id: str,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Remove a choreography from a class plan.
            
            Removes the specified choreography from the class plan sequence.
            """
            try:
                self.log_request("remove_choreography_from_plan", {
                    "instructor_id": instructor.id,
                    "class_plan_id": class_plan_id,
                    "choreography_id": choreography_id
                })
                
                success = await self.instructor_service.remove_choreography_from_plan(
                    db=db,
                    instructor_id=instructor.id,
                    class_plan_id=class_plan_id,
                    choreography_id=choreography_id
                )
                
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Class plan or choreography sequence not found"
                    )
                
                return None
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("remove_choreography_from_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to remove choreography from class plan"
                )
        
        @self.router.put(
            "/class-plans/{class_plan_id}/choreographies/{choreography_id}",
            response_model=ClassPlanSequenceResponse,
            responses={
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                404: {"model": ErrorResponse, "description": "Class plan or choreography sequence not found"},
                422: {"model": ErrorResponse, "description": "Validation error"}
            }
        )
        async def update_sequence_details(
            class_plan_id: str,
            choreography_id: str,
            request: UpdateSequenceDetailsRequest,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Update sequence-specific details (notes and estimated time).
            
            Updates the notes and/or estimated teaching time for a choreography in a class plan.
            """
            try:
                self.log_request("update_sequence_details", {
                    "instructor_id": instructor.id,
                    "class_plan_id": class_plan_id,
                    "choreography_id": choreography_id
                })
                
                updated_sequence = await self.instructor_service.update_sequence_details(
                    db=db,
                    instructor_id=instructor.id,
                    class_plan_id=class_plan_id,
                    choreography_id=choreography_id,
                    notes=request.notes,
                    estimated_time=request.estimated_time
                )
                
                if not updated_sequence:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Class plan or choreography sequence not found"
                    )
                
                return ClassPlanSequenceResponse.from_orm(updated_sequence)
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("update_sequence_details", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update sequence details"
                )
        
        @self.router.put(
            "/class-plans/{class_plan_id}/reorder",
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                400: {"model": ErrorResponse, "description": "Invalid sequence data"},
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                404: {"model": ErrorResponse, "description": "Class plan not found"},
                422: {"model": ErrorResponse, "description": "Validation error"}
            }
        )
        async def reorder_choreography_sequences(
            class_plan_id: str,
            request: ReorderSequencesRequest,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Reorder choreographies in a class plan.
            
            Updates the sequence order of choreographies in the specified class plan.
            """
            try:
                self.log_request("reorder_choreography_sequences", {
                    "instructor_id": instructor.id,
                    "class_plan_id": class_plan_id,
                    "sequence_count": len(request.sequence_updates)
                })
                
                # Convert Pydantic models to dicts for service layer
                sequence_updates = [
                    {
                        "choreography_id": update.choreography_id,
                        "sequence_order": update.sequence_order
                    }
                    for update in request.sequence_updates
                ]
                
                success = await self.instructor_service.reorder_choreography_sequence(
                    db=db,
                    instructor_id=instructor.id,
                    class_plan_id=class_plan_id,
                    choreography_sequence_updates=sequence_updates
                )
                
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Class plan not found"
                    )
                
                return None
                
            except HTTPException:
                raise
            except ValueError as e:
                self.log_error("reorder_choreography_sequences", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                self.log_error("reorder_choreography_sequences", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to reorder choreography sequences"
                )
        
        @self.router.get(
            "/class-plans/{class_plan_id}/summary",
            response_model=ClassPlanSummaryResponse,
            responses={
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                404: {"model": ErrorResponse, "description": "Class plan not found"}
            }
        )
        async def get_class_plan_summary(
            class_plan_id: str,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Generate a structured summary of a class plan.
            
            Returns detailed summary with timing, progression analysis, and teaching recommendations.
            """
            try:
                self.log_request("get_class_plan_summary", {
                    "instructor_id": instructor.id,
                    "class_plan_id": class_plan_id
                })
                
                summary = await self.instructor_service.generate_class_plan_summary(
                    db=db,
                    instructor_id=instructor.id,
                    class_plan_id=class_plan_id
                )
                
                if not summary:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Class plan not found"
                    )
                
                return ClassPlanSummaryResponse(**summary)
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("get_class_plan_summary", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate class plan summary"
                )
        
        @self.router.get(
            "/class-plans/{class_plan_id}/export",
            responses={
                200: {"description": "Printable class plan HTML"},
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                404: {"model": ErrorResponse, "description": "Class plan not found"}
            }
        )
        async def export_class_plan(
            class_plan_id: str,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Export class plan as printable HTML.
            
            Generates a formatted HTML document suitable for printing or saving as PDF.
            """
            try:
                self.log_request("export_class_plan", {
                    "instructor_id": instructor.id,
                    "class_plan_id": class_plan_id
                })
                
                summary = await self.instructor_service.generate_class_plan_summary(
                    db=db,
                    instructor_id=instructor.id,
                    class_plan_id=class_plan_id
                )
                
                if not summary:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Class plan not found"
                    )
                
                # Generate HTML content for printing
                html_content = self._generate_printable_html(summary)
                
                return Response(
                    content=html_content,
                    media_type="text/html",
                    headers={
                        "Content-Disposition": f"inline; filename=class_plan_{class_plan_id}.html"
                    }
                )
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("export_class_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to export class plan"
                )
        
        @self.router.post(
            "/class-plans/{class_plan_id}/duplicate",
            response_model=ClassPlanResponse,
            status_code=status.HTTP_201_CREATED,
            responses={
                400: {"model": ErrorResponse, "description": "Invalid input"},
                403: {"model": ErrorResponse, "description": "Instructor privileges required"},
                404: {"model": ErrorResponse, "description": "Source class plan not found"},
                422: {"model": ErrorResponse, "description": "Validation error"}
            }
        )
        async def duplicate_class_plan(
            class_plan_id: str,
            request: DuplicateClassPlanRequest,
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Duplicate an existing class plan.
            
            Creates a copy of the specified class plan with optional sequence copying.
            """
            try:
                self.log_request("duplicate_class_plan", {
                    "instructor_id": instructor.id,
                    "source_class_plan_id": class_plan_id,
                    "new_title": request.new_title,
                    "copy_sequences": request.copy_sequences
                })
                
                duplicated_plan = await self.instructor_service.duplicate_class_plan(
                    db=db,
                    instructor_id=instructor.id,
                    source_class_plan_id=class_plan_id,
                    new_title=request.new_title,
                    copy_sequences=request.copy_sequences
                )
                
                return ClassPlanResponse.from_orm(duplicated_plan)
                
            except ValueError as e:
                self.log_error("duplicate_class_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                self.log_error("duplicate_class_plan", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to duplicate class plan"
                )
        
        @self.router.get(
            "/dashboard/stats",
            response_model=InstructorDashboardStatsResponse,
            responses={
                403: {"model": ErrorResponse, "description": "Instructor privileges required"}
            }
        )
        async def get_dashboard_stats(
            instructor: InstructorUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Get instructor dashboard statistics.
            
            Returns comprehensive statistics for the instructor dashboard including
            class plan counts, choreography usage, and recent activity.
            """
            try:
                self.log_request("get_dashboard_stats", {
                    "instructor_id": instructor.id
                })
                
                stats = await self.instructor_service.get_instructor_dashboard_stats(
                    db=db,
                    instructor_id=instructor.id
                )
                
                return InstructorDashboardStatsResponse(**stats)
                
            except Exception as e:
                self.log_error("get_dashboard_stats", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve dashboard statistics"
                )
    
    def _generate_printable_html(self, summary: Dict[str, Any]) -> str:
        """
        Generate printable HTML content for a class plan.
        
        Args:
            summary: Class plan summary data
            
        Returns:
            str: HTML content for printing
        """
        class_plan = summary["class_plan"]
        stats = summary["summary_statistics"]
        sequences = summary["choreography_sequences"]
        recommendations = summary["teaching_recommendations"]
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Class Plan: {class_plan['title']}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            line-height: 1.6;
        }}
        .header {{
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .class-title {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .class-meta {{
            color: #666;
            font-size: 14px;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: bold;
            border-bottom: 1px solid #ccc;
            padding-bottom: 5px;
            margin-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-item {{
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
        }}
        .stat-label {{
            font-weight: bold;
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .stat-value {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }}
        .sequence-list {{
            list-style: none;
            padding: 0;
        }}
        .sequence-item {{
            background: #f9f9f9;
            margin-bottom: 10px;
            padding: 15px;
            border-left: 4px solid #007bff;
            border-radius: 0 5px 5px 0;
        }}
        .sequence-title {{
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 5px;
        }}
        .sequence-meta {{
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
        }}
        .sequence-notes {{
            font-style: italic;
            color: #555;
        }}
        .recommendations {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
        }}
        .recommendation {{
            margin-bottom: 8px;
            padding-left: 15px;
            position: relative;
        }}
        .recommendation:before {{
            content: "•";
            position: absolute;
            left: 0;
            color: #856404;
            font-weight: bold;
        }}
        @media print {{
            body {{ margin: 0; }}
            .section {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="class-title">{class_plan['title']}</div>
        <div class="class-meta">
            Difficulty: {class_plan['difficulty_level'].title()} | 
            Created: {class_plan['created_at'][:10]} | 
            Duration: {class_plan.get('estimated_duration', 'Not specified')} minutes
        </div>
    </div>
    
    {f'<div class="section"><div class="section-title">Description</div><p>{class_plan["description"]}</p></div>' if class_plan.get('description') else ''}
    
    <div class="section">
        <div class="section-title">Class Statistics</div>
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">Total Choreographies</div>
                <div class="stat-value">{stats['total_choreographies']}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Teaching Time</div>
                <div class="stat-value">{stats['total_estimated_teaching_time']} min</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Video Duration</div>
                <div class="stat-value">{stats['total_video_duration_minutes']} min</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Estimated Total</div>
                <div class="stat-value">{stats['estimated_total_class_time']} min</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-title">Choreography Sequence</div>
        <ol class="sequence-list">
"""
        
        for seq in sequences:
            html_content += f"""
            <li class="sequence-item">
                <div class="sequence-title">{seq['choreography_title']}</div>
                <div class="sequence-meta">
                    Difficulty: {seq['choreography_difficulty'].title()} | 
                    Duration: {seq['choreography_duration']:.1f}s | 
                    Teaching Time: {seq.get('estimated_teaching_time', 'Not specified')} min
                </div>
                {f'<div class="sequence-notes">Notes: {seq["sequence_notes"]}</div>' if seq.get('sequence_notes') else ''}
            </li>
"""
        
        html_content += """
        </ol>
    </div>
"""
        
        if recommendations:
            html_content += f"""
    <div class="section">
        <div class="section-title">Teaching Recommendations</div>
        <div class="recommendations">
"""
            for rec in recommendations:
                html_content += f'<div class="recommendation">{rec}</div>'
            
            html_content += """
        </div>
    </div>
"""
        
        if class_plan.get('instructor_notes'):
            html_content += f"""
    <div class="section">
        <div class="section-title">Instructor Notes</div>
        <p>{class_plan['instructor_notes']}</p>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        return html_content