"""
Pydantic models for instructor dashboard functionality.

Request and response models for class plan management and choreography sequencing.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class CreateClassPlanRequest(BaseModel):
    """Request model for creating a new class plan."""
    title: str = Field(..., min_length=1, max_length=200, description="Class plan title")
    description: Optional[str] = Field(None, max_length=1000, description="Detailed description of the class")
    difficulty_level: str = Field("intermediate", description="Overall difficulty level")
    estimated_duration: Optional[int] = Field(None, ge=1, le=480, description="Estimated class duration in minutes")
    instructor_notes: Optional[str] = Field(None, max_length=2000, description="Rich text notes for teaching tips")
    
    @validator('difficulty_level')
    def validate_difficulty_level(cls, v):
        valid_levels = ["beginner", "intermediate", "advanced"]
        if v not in valid_levels:
            raise ValueError(f"Difficulty level must be one of: {valid_levels}")
        return v


class UpdateClassPlanRequest(BaseModel):
    """Request model for updating class plan metadata."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Updated title")
    description: Optional[str] = Field(None, max_length=1000, description="Updated description")
    difficulty_level: Optional[str] = Field(None, description="Updated difficulty level")
    estimated_duration: Optional[int] = Field(None, ge=1, le=480, description="Updated duration in minutes")
    instructor_notes: Optional[str] = Field(None, max_length=2000, description="Updated instructor notes")
    
    @validator('difficulty_level')
    def validate_difficulty_level(cls, v):
        if v is not None:
            valid_levels = ["beginner", "intermediate", "advanced"]
            if v not in valid_levels:
                raise ValueError(f"Difficulty level must be one of: {valid_levels}")
        return v


class AddChoreographyToClassPlanRequest(BaseModel):
    """Request model for adding choreography to a class plan."""
    choreography_id: str = Field(..., description="ID of choreography to add")
    sequence_order: Optional[int] = Field(None, ge=1, description="Order in the class plan")
    notes: Optional[str] = Field(None, max_length=500, description="Sequence-specific notes")
    estimated_time: Optional[int] = Field(None, ge=1, le=120, description="Estimated teaching time in minutes")


class UpdateSequenceDetailsRequest(BaseModel):
    """Request model for updating sequence-specific details."""
    notes: Optional[str] = Field(None, max_length=500, description="Updated sequence notes")
    estimated_time: Optional[int] = Field(None, ge=1, le=120, description="Updated estimated time")


class ReorderSequenceRequest(BaseModel):
    """Request model for reordering choreography sequences."""
    choreography_id: str = Field(..., description="ID of choreography to reorder")
    sequence_order: int = Field(..., ge=1, description="New sequence order")


class ReorderSequencesRequest(BaseModel):
    """Request model for reordering multiple choreography sequences."""
    sequence_updates: List[ReorderSequenceRequest] = Field(..., description="List of sequence reorder updates")


class DuplicateClassPlanRequest(BaseModel):
    """Request model for duplicating a class plan."""
    new_title: str = Field(..., min_length=1, max_length=200, description="Title for the duplicated class plan")
    copy_sequences: bool = Field(True, description="Whether to copy choreography sequences")


class ClassPlanListRequest(BaseModel):
    """Request model for listing class plans with filtering and pagination."""
    difficulty_filter: Optional[str] = Field(None, description="Filter by difficulty level")
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    
    @validator('difficulty_filter')
    def validate_difficulty_filter(cls, v):
        if v is not None:
            valid_levels = ["beginner", "intermediate", "advanced"]
            if v not in valid_levels:
                raise ValueError(f"Difficulty filter must be one of: {valid_levels}")
        return v
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        valid_fields = ["created_at", "title", "difficulty_level", "estimated_duration", "updated_at"]
        if v not in valid_fields:
            raise ValueError(f"Sort field must be one of: {valid_fields}")
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v.lower() not in ["asc", "desc"]:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v.lower()


class ClassPlanSequenceResponse(BaseModel):
    """Response model for class plan sequence information."""
    id: str
    class_plan_id: str
    choreography_id: str
    sequence_order: int
    notes: Optional[str]
    estimated_time: Optional[int]
    
    # Choreography details (populated via join)
    choreography_title: Optional[str] = None
    choreography_difficulty: Optional[str] = None
    choreography_duration: Optional[float] = None
    music_info: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class ClassPlanResponse(BaseModel):
    """Response model for class plan information."""
    id: str
    instructor_id: str
    title: str
    description: Optional[str]
    difficulty_level: str
    estimated_duration: Optional[int]
    instructor_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Optional sequences (populated when requested)
    choreography_sequences: Optional[List[ClassPlanSequenceResponse]] = None
    
    class Config:
        from_attributes = True


class ClassPlanListResponse(BaseModel):
    """Response model for paginated class plan list."""
    class_plans: List[ClassPlanResponse]
    total_count: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ClassPlanSummaryStatistics(BaseModel):
    """Summary statistics for a class plan."""
    total_choreographies: int
    total_estimated_teaching_time: int
    total_video_duration_minutes: float
    estimated_total_class_time: float
    difficulty_distribution: Dict[str, int]
    difficulty_progression: List[str]


class ClassPlanSequenceDetail(BaseModel):
    """Detailed sequence information for class plan summary."""
    sequence_order: int
    choreography_id: str
    choreography_title: str
    choreography_difficulty: str
    choreography_duration: float
    estimated_teaching_time: Optional[int]
    sequence_notes: Optional[str]
    music_info: Optional[Dict[str, Any]]


class ClassPlanSummaryResponse(BaseModel):
    """Response model for detailed class plan summary."""
    class_plan: ClassPlanResponse
    summary_statistics: ClassPlanSummaryStatistics
    choreography_sequences: List[ClassPlanSequenceDetail]
    teaching_recommendations: List[str]


class InstructorDashboardStats(BaseModel):
    """Response model for instructor dashboard statistics."""
    instructor_info: Dict[str, Any]
    class_plan_statistics: Dict[str, Any]
    choreography_usage: List[Dict[str, Any]]


class ChoreographyUsageInfo(BaseModel):
    """Information about choreography usage in class plans."""
    choreography_id: str
    choreography_title: str
    usage_count: int


class InstructorInfo(BaseModel):
    """Basic instructor information."""
    id: str
    display_name: str
    email: str


class ClassPlanStatistics(BaseModel):
    """Statistics about instructor's class plans."""
    total_class_plans: int
    difficulty_breakdown: Dict[str, int]
    recent_activity: List[Dict[str, Any]]


class InstructorDashboardStatsResponse(BaseModel):
    """Comprehensive response model for instructor dashboard statistics."""
    instructor_info: InstructorInfo
    class_plan_statistics: ClassPlanStatistics
    choreography_usage: List[ChoreographyUsageInfo]