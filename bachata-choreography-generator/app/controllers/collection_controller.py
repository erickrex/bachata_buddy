"""
Collection controller for managing user's saved choreographies.
"""

from typing import Annotated
from fastapi import HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

from .base_controller import BaseController
from app.database import get_database_session
from app.services.collection_service import CollectionService
from app.middleware.auth_middleware import AuthenticatedUser
from app.models.collection_models import (
    SaveChoreographyRequest,
    SavedChoreographyResponse,
    CollectionListRequest,
    CollectionResponse,
    CollectionStatsResponse,
    UpdateChoreographyRequest,
    UpdateChoreographyResponse,
    DeleteChoreographyResponse,
    ChoreographyNotFoundError,
    CollectionError
)


class CollectionController(BaseController):
    """Controller for collection management endpoints."""
    
    def __init__(self, collection_service: CollectionService):
        """
        Initialize the collection controller.
        
        Args:
            collection_service: Collection service instance
        """
        super().__init__(prefix="/api/collection", tags=["collection"])
        self.collection_service = collection_service
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up collection management routes."""
        
        @self.router.post(
            "/save",
            response_model=SavedChoreographyResponse,
            status_code=status.HTTP_201_CREATED,
            responses={
                400: {"model": CollectionError, "description": "Invalid input or file not found"},
                401: {"model": CollectionError, "description": "Authentication required"},
                422: {"model": CollectionError, "description": "Validation error"}
            }
        )
        async def save_choreography(
            request: SaveChoreographyRequest,
            current_user: AuthenticatedUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Save a choreography to user's collection.
            
            Saves the choreography video and metadata to the user's personal collection.
            The video file is copied to user-specific storage for organization.
            """
            try:
                self.log_request("save_choreography", {"user_id": current_user.id, "title": request.title})
                
                choreography = await self.collection_service.save_choreography(
                    db=db,
                    user_id=current_user.id,
                    request=request
                )
                
                return choreography
                
            except ValueError as e:
                self.log_error("save_choreography", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except FileNotFoundError as e:
                self.log_error("save_choreography", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Video file not found"
                )
            except Exception as e:
                self.log_error("save_choreography", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save choreography"
                )
        
        @self.router.get(
            "",
            response_model=CollectionResponse,
            responses={
                400: {"model": CollectionError, "description": "Invalid parameters"},
                401: {"model": CollectionError, "description": "Authentication required"}
            }
        )
        async def get_collection(
            current_user: AuthenticatedUser,
            db: Annotated[Session, Depends(get_database_session)],
            page: int = Query(default=1, ge=1, description="Page number (1-based)"),
            limit: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
            difficulty: str = Query(default=None, description="Filter by difficulty level"),
            search: str = Query(default=None, description="Search in titles and music info"),
            sort_by: str = Query(default="created_at", description="Sort field"),
            sort_order: str = Query(default="desc", description="Sort order (asc, desc)")
        ):
            """
            Get user's saved choreographies with pagination and filtering.
            
            Supports filtering by difficulty, searching in titles and music metadata,
            and sorting by various fields. Returns paginated results.
            """
            try:
                self.log_request("get_collection", {
                    "user_id": current_user.id,
                    "page": page,
                    "limit": limit,
                    "difficulty": difficulty,
                    "search": search
                })
                
                request = CollectionListRequest(
                    page=page,
                    limit=limit,
                    difficulty=difficulty,
                    search=search,
                    sort_by=sort_by,
                    sort_order=sort_order
                )
                
                collection = await self.collection_service.get_user_collection(
                    db=db,
                    user_id=current_user.id,
                    request=request
                )
                
                return collection
                
            except ValueError as e:
                self.log_error("get_collection", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                self.log_error("get_collection", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve collection"
                )
        
        @self.router.get(
            "/list",
            response_model=CollectionResponse,
            responses={
                400: {"model": CollectionError, "description": "Invalid parameters"},
                401: {"model": CollectionError, "description": "Authentication required"}
            }
        )
        async def list_choreographies(
            current_user: AuthenticatedUser,
            db: Annotated[Session, Depends(get_database_session)],
            page: int = Query(default=1, ge=1, description="Page number (1-based)"),
            limit: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
            difficulty: str = Query(default=None, description="Filter by difficulty level"),
            search: str = Query(default=None, description="Search in titles and music info"),
            sort_by: str = Query(default="created_at", description="Sort field"),
            sort_order: str = Query(default="desc", description="Sort order (asc, desc)")
        ):
            """
            List user's saved choreographies with pagination and filtering.
            
            Supports filtering by difficulty, searching in titles and music metadata,
            and sorting by various fields. Returns paginated results.
            """
            try:
                self.log_request("list_choreographies", {
                    "user_id": current_user.id,
                    "page": page,
                    "limit": limit,
                    "difficulty": difficulty,
                    "search": search
                })
                
                request = CollectionListRequest(
                    page=page,
                    limit=limit,
                    difficulty=difficulty,
                    search=search,
                    sort_by=sort_by,
                    sort_order=sort_order
                )
                
                collection = await self.collection_service.get_user_collection(
                    db=db,
                    user_id=current_user.id,
                    request=request
                )
                
                return collection
                
            except ValueError as e:
                self.log_error("list_choreographies", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                self.log_error("list_choreographies", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve collection"
                )
        
        @self.router.get(
            "/{choreography_id}",
            response_model=SavedChoreographyResponse,
            responses={
                404: {"model": ChoreographyNotFoundError, "description": "Choreography not found"},
                401: {"model": CollectionError, "description": "Authentication required"}
            }
        )
        async def get_choreography(
            choreography_id: str,
            current_user: AuthenticatedUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Get a specific choreography by ID.
            
            Returns choreography details if it exists and belongs to the current user.
            """
            try:
                self.log_request("get_choreography", {
                    "user_id": current_user.id,
                    "choreography_id": choreography_id
                })
                
                choreography = await self.collection_service.get_choreography_by_id(
                    db=db,
                    user_id=current_user.id,
                    choreography_id=choreography_id
                )
                
                if not choreography:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Choreography not found"
                    )
                
                return choreography
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("get_choreography", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve choreography"
                )
        
        @self.router.put(
            "/{choreography_id}",
            response_model=UpdateChoreographyResponse,
            responses={
                400: {"model": CollectionError, "description": "Invalid input"},
                404: {"model": ChoreographyNotFoundError, "description": "Choreography not found"},
                401: {"model": CollectionError, "description": "Authentication required"}
            }
        )
        async def update_choreography(
            choreography_id: str,
            request: UpdateChoreographyRequest,
            current_user: AuthenticatedUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Update choreography metadata.
            
            Allows updating the title and difficulty level of a saved choreography.
            """
            try:
                self.log_request("update_choreography", {
                    "user_id": current_user.id,
                    "choreography_id": choreography_id,
                    "updates": request.dict(exclude_unset=True)
                })
                
                choreography = await self.collection_service.update_choreography(
                    db=db,
                    user_id=current_user.id,
                    choreography_id=choreography_id,
                    request=request
                )
                
                if not choreography:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Choreography not found"
                    )
                
                return UpdateChoreographyResponse(choreography=choreography)
                
            except HTTPException:
                raise
            except ValueError as e:
                self.log_error("update_choreography", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                self.log_error("update_choreography", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update choreography"
                )
        
        @self.router.delete(
            "/{choreography_id}",
            response_model=DeleteChoreographyResponse,
            responses={
                404: {"model": ChoreographyNotFoundError, "description": "Choreography not found"},
                401: {"model": CollectionError, "description": "Authentication required"}
            }
        )
        async def delete_choreography(
            choreography_id: str,
            current_user: AuthenticatedUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Delete a choreography from user's collection.
            
            Removes the choreography from the database and deletes associated files.
            This action cannot be undone.
            """
            try:
                self.log_request("delete_choreography", {
                    "user_id": current_user.id,
                    "choreography_id": choreography_id
                })
                
                success = await self.collection_service.delete_choreography(
                    db=db,
                    user_id=current_user.id,
                    choreography_id=choreography_id
                )
                
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Choreography not found"
                    )
                
                return DeleteChoreographyResponse(
                    success=True,
                    message="Choreography deleted successfully"
                )
                
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("delete_choreography", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete choreography"
                )
        
        @self.router.get(
            "/stats/overview",
            response_model=CollectionStatsResponse,
            responses={
                401: {"model": CollectionError, "description": "Authentication required"}
            }
        )
        async def get_collection_stats(
            current_user: AuthenticatedUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Get collection statistics and analytics.
            
            Returns overview statistics including total choreographies, duration,
            difficulty breakdown, recent activity, and storage usage.
            """
            try:
                self.log_request("get_collection_stats", {"user_id": current_user.id})
                
                stats = await self.collection_service.get_collection_stats(
                    db=db,
                    user_id=current_user.id
                )
                
                return stats
                
            except ValueError as e:
                self.log_error("get_collection_stats", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                self.log_error("get_collection_stats", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve collection statistics"
                )
        
        @self.router.post(
            "/cleanup",
            responses={
                200: {"description": "Cleanup completed successfully"},
                401: {"model": CollectionError, "description": "Authentication required"}
            }
        )
        async def cleanup_orphaned_files(
            current_user: AuthenticatedUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Clean up orphaned files in user's storage directory.
            
            Removes files that are no longer associated with any choreography
            in the user's collection. This helps free up storage space.
            """
            try:
                self.log_request("cleanup_orphaned_files", {"user_id": current_user.id})
                
                cleanup_result = await self.collection_service.cleanup_orphaned_files(
                    db=db,
                    user_id=current_user.id
                )
                
                return {
                    "success": True,
                    "message": f"Cleanup completed. Removed {cleanup_result['orphaned_files_found']} orphaned files.",
                    "details": cleanup_result
                }
                
            except Exception as e:
                self.log_error("cleanup_orphaned_files", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to cleanup orphaned files"
                )