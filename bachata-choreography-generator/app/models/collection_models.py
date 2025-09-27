"""
Pydantic models for collection management requests and responses.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SaveChoreographyRequest(BaseModel):
    """Request model for saving a choreography to user's collection."""
    title: str = Field(..., min_length=1, max_length=200, description="Title for the choreography")
    video_path: str = Field(..., description="Path to the generated video file")
    thumbnail_path: Optional[str] = Field(None, description="Path to video thumbnail")
    difficulty: str = Field(..., description="Difficulty level (beginner, intermediate, advanced)")
    duration: float = Field(..., gt=0, description="Video duration in seconds")
    music_info: Optional[Dict[str, Any]] = Field(None, description="Music metadata (title, artist, tempo, etc.)")
    generation_parameters: Optional[Dict[str, Any]] = Field(None, description="Generation settings used")


class SavedChoreographyResponse(BaseModel):
    """Response model for saved choreography information."""
    id: str = Field(..., description="Choreography unique identifier")
    user_id: str = Field(..., description="Owner user ID")
    title: str = Field(..., description="Choreography title")
    video_path: str = Field(..., description="Path to video file")
    thumbnail_path: Optional[str] = Field(None, description="Path to thumbnail")
    difficulty: str = Field(..., description="Difficulty level")
    duration: float = Field(..., description="Duration in seconds")
    music_info: Optional[Dict[str, Any]] = Field(None, description="Music metadata")
    generation_parameters: Optional[Dict[str, Any]] = Field(None, description="Generation parameters")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class CollectionListRequest(BaseModel):
    """Request model for listing user's collection with pagination and filtering."""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")
    difficulty: Optional[str] = Field(None, description="Filter by difficulty level")
    search: Optional[str] = Field(None, min_length=1, description="Search in titles and music info")
    sort_by: str = Field(default="created_at", description="Sort field (created_at, title, difficulty, duration)")
    sort_order: str = Field(default="desc", description="Sort order (asc, desc)")


class CollectionResponse(BaseModel):
    """Response model for user's collection with pagination."""
    choreographies: List[SavedChoreographyResponse] = Field(..., description="List of saved choreographies")
    total_count: int = Field(..., description="Total number of choreographies in collection")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class CollectionStatsResponse(BaseModel):
    """Response model for collection statistics."""
    total_choreographies: int = Field(..., description="Total number of saved choreographies")
    total_duration: float = Field(..., description="Total duration of all choreographies in seconds")
    difficulty_breakdown: Dict[str, int] = Field(..., description="Count by difficulty level")
    recent_activity: List[SavedChoreographyResponse] = Field(..., description="Recently saved choreographies")
    storage_used_mb: float = Field(..., description="Storage space used in MB")


class DeleteChoreographyRequest(BaseModel):
    """Request model for deleting a choreography."""
    choreography_id: str = Field(..., description="ID of choreography to delete")


class DeleteChoreographyResponse(BaseModel):
    """Response model for choreography deletion."""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Success or error message")


class ChoreographyNotFoundError(BaseModel):
    """Error response for choreography not found."""
    detail: str = Field(default="Choreography not found", description="Error message")
    error_code: str = Field(default="CHOREOGRAPHY_NOT_FOUND", description="Error code")


class CollectionError(BaseModel):
    """General error response for collection operations."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")


class UpdateChoreographyRequest(BaseModel):
    """Request model for updating choreography metadata."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="New title")
    difficulty: Optional[str] = Field(None, description="New difficulty level")


class UpdateChoreographyResponse(BaseModel):
    """Response model for choreography update."""
    choreography: SavedChoreographyResponse = Field(..., description="Updated choreography")
    message: str = Field(default="Choreography updated successfully", description="Success message")