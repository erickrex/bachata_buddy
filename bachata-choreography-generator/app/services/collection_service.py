"""
Collection service for managing user's saved choreographies.

Handles CRUD operations for saved choreographies, file management, and collection analytics.
"""

import uuid
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func

from app.models.database_models import SavedChoreography, User
from app.models.collection_models import (
    SaveChoreographyRequest,
    SavedChoreographyResponse,
    CollectionListRequest,
    CollectionResponse,
    CollectionStatsResponse,
    UpdateChoreographyRequest
)


class CollectionService:
    """
    Service for managing user choreography collections.
    
    Features:
    - Save choreographies with file management
    - Retrieve collections with pagination and filtering
    - Delete choreographies with cleanup
    - Collection statistics and analytics
    - File organization and storage management
    """
    
    def __init__(self, storage_base_path: str):
        """
        Initialize the collection service.
        
        Args:
            storage_base_path: Base path for storing user choreography files
        """
        self.storage_base_path = Path(storage_base_path)
        self.user_collections_path = self.storage_base_path / "user_collections"
        
        # Ensure storage directories exist
        self.user_collections_path.mkdir(parents=True, exist_ok=True)
    
    def _get_user_storage_path(self, user_id: str) -> Path:
        """
        Get the storage path for a specific user.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            Path: User's storage directory path
        """
        user_path = self.user_collections_path / user_id
        user_path.mkdir(parents=True, exist_ok=True)
        return user_path
    
    def _copy_video_to_user_storage(self, source_path: str, user_id: str, choreography_id: str) -> str:
        """
        Copy a video file to user's storage directory.
        
        Args:
            source_path: Path to the source video file
            user_id: User's unique identifier
            choreography_id: Choreography's unique identifier
            
        Returns:
            str: Path to the copied video file
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            OSError: If file copy fails
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source video file not found: {source_path}")
        
        user_storage = self._get_user_storage_path(user_id)
        
        # Create filename with choreography ID and original extension
        file_extension = source.suffix
        destination_filename = f"{choreography_id}{file_extension}"
        destination_path = user_storage / destination_filename
        
        # Copy the file
        shutil.copy2(source, destination_path)
        
        return str(destination_path)
    
    def _copy_thumbnail_to_user_storage(self, source_path: str, user_id: str, choreography_id: str) -> str:
        """
        Copy a thumbnail file to user's storage directory.
        
        Args:
            source_path: Path to the source thumbnail file
            user_id: User's unique identifier
            choreography_id: Choreography's unique identifier
            
        Returns:
            str: Path to the copied thumbnail file
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            OSError: If file copy fails
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source thumbnail file not found: {source_path}")
        
        user_storage = self._get_user_storage_path(user_id)
        
        # Create filename with choreography ID and thumbnail suffix
        file_extension = source.suffix
        destination_filename = f"{choreography_id}_thumb{file_extension}"
        destination_path = user_storage / destination_filename
        
        # Copy the file
        shutil.copy2(source, destination_path)
        
        return str(destination_path)
    
    def _delete_choreography_files(self, choreography: SavedChoreography) -> bool:
        """
        Delete files associated with a choreography.
        
        Args:
            choreography: SavedChoreography instance
            
        Returns:
            bool: True if all files were deleted successfully
        """
        success = True
        
        # Delete video file
        if choreography.video_path:
            try:
                video_path = Path(choreography.video_path)
                if video_path.exists():
                    video_path.unlink()
            except Exception:
                success = False
        
        # Delete thumbnail file
        if choreography.thumbnail_path:
            try:
                thumbnail_path = Path(choreography.thumbnail_path)
                if thumbnail_path.exists():
                    thumbnail_path.unlink()
            except Exception:
                success = False
        
        return success
    
    def _get_file_size_mb(self, file_path: str) -> float:
        """
        Get file size in megabytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            float: File size in MB, 0 if file doesn't exist
        """
        try:
            path = Path(file_path)
            if path.exists():
                return path.stat().st_size / (1024 * 1024)
        except Exception:
            pass
        return 0.0
    
    async def save_choreography(
        self, 
        db: Session, 
        user_id: str, 
        request: SaveChoreographyRequest
    ) -> SavedChoreographyResponse:
        """
        Save a choreography to user's collection.
        
        Args:
            db: Database session
            user_id: User's unique identifier
            request: Save choreography request data
            
        Returns:
            SavedChoreographyResponse: Saved choreography information
            
        Raises:
            ValueError: If user doesn't exist or input validation fails
            FileNotFoundError: If video file doesn't exist
            OSError: If file operations fail
        """
        # Verify user exists
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise ValueError("User not found")
        
        # Validate difficulty level
        valid_difficulties = ["beginner", "intermediate", "advanced"]
        if request.difficulty not in valid_difficulties:
            raise ValueError(f"Invalid difficulty level. Must be one of: {valid_difficulties}")
        
        # Generate unique choreography ID
        choreography_id = str(uuid.uuid4())
        
        try:
            # Copy video file to user storage
            user_video_path = self._copy_video_to_user_storage(
                request.video_path, user_id, choreography_id
            )
            
            # Copy thumbnail if provided
            user_thumbnail_path = None
            if request.thumbnail_path:
                user_thumbnail_path = self._copy_thumbnail_to_user_storage(
                    request.thumbnail_path, user_id, choreography_id
                )
            
            # Create database record
            choreography = SavedChoreography(
                id=choreography_id,
                user_id=user_id,
                title=request.title.strip(),
                video_path=user_video_path,
                thumbnail_path=user_thumbnail_path,
                difficulty=request.difficulty,
                duration=request.duration,
                music_info=request.music_info,
                generation_parameters=request.generation_parameters
            )
            
            db.add(choreography)
            db.commit()
            db.refresh(choreography)
            
            return SavedChoreographyResponse.model_validate(choreography)
            
        except Exception as e:
            db.rollback()
            # Clean up any copied files on error
            try:
                user_storage = self._get_user_storage_path(user_id)
                video_file = user_storage / f"{choreography_id}.mp4"
                if video_file.exists():
                    video_file.unlink()
                thumbnail_file = user_storage / f"{choreography_id}_thumb.jpg"
                if thumbnail_file.exists():
                    thumbnail_file.unlink()
            except Exception:
                pass
            raise e
    
    async def get_user_collection(
        self, 
        db: Session, 
        user_id: str, 
        request: CollectionListRequest
    ) -> CollectionResponse:
        """
        Retrieve user's choreography collection with pagination and filtering.
        
        Args:
            db: Database session
            user_id: User's unique identifier
            request: Collection list request parameters
            
        Returns:
            CollectionResponse: Paginated collection data
            
        Raises:
            ValueError: If user doesn't exist or invalid parameters
        """
        # Verify user exists
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise ValueError("User not found")
        
        # Build base query
        query = db.query(SavedChoreography).filter(SavedChoreography.user_id == user_id)
        
        # Apply difficulty filter
        if request.difficulty:
            query = query.filter(SavedChoreography.difficulty == request.difficulty)
        
        # Apply search filter
        if request.search:
            search_term = f"%{request.search}%"
            query = query.filter(
                or_(
                    SavedChoreography.title.ilike(search_term),
                    SavedChoreography.music_info.op('->>')('title').ilike(search_term),
                    SavedChoreography.music_info.op('->>')('artist').ilike(search_term)
                )
            )
        
        # Apply sorting
        sort_column = getattr(SavedChoreography, request.sort_by, SavedChoreography.created_at)
        if request.sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (request.page - 1) * request.limit
        choreographies = query.offset(offset).limit(request.limit).all()
        
        # Calculate pagination info
        total_pages = (total_count + request.limit - 1) // request.limit
        has_next = request.page < total_pages
        has_previous = request.page > 1
        
        # Convert to response models
        choreography_responses = [
            SavedChoreographyResponse.model_validate(choreo) for choreo in choreographies
        ]
        
        return CollectionResponse(
            choreographies=choreography_responses,
            total_count=total_count,
            page=request.page,
            limit=request.limit,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )
    
    async def get_choreography_by_id(
        self, 
        db: Session, 
        user_id: str, 
        choreography_id: str
    ) -> Optional[SavedChoreographyResponse]:
        """
        Get a specific choreography by ID (user must own it).
        
        Args:
            db: Database session
            user_id: User's unique identifier
            choreography_id: Choreography's unique identifier
            
        Returns:
            Optional[SavedChoreographyResponse]: Choreography if found and owned by user
        """
        choreography = db.query(SavedChoreography).filter(
            and_(
                SavedChoreography.id == choreography_id,
                SavedChoreography.user_id == user_id
            )
        ).first()
        
        if choreography:
            return SavedChoreographyResponse.model_validate(choreography)
        return None
    
    async def update_choreography(
        self, 
        db: Session, 
        user_id: str, 
        choreography_id: str, 
        request: UpdateChoreographyRequest
    ) -> Optional[SavedChoreographyResponse]:
        """
        Update choreography metadata.
        
        Args:
            db: Database session
            user_id: User's unique identifier
            choreography_id: Choreography's unique identifier
            request: Update request data
            
        Returns:
            Optional[SavedChoreographyResponse]: Updated choreography if successful
            
        Raises:
            ValueError: If invalid parameters provided
        """
        choreography = db.query(SavedChoreography).filter(
            and_(
                SavedChoreography.id == choreography_id,
                SavedChoreography.user_id == user_id
            )
        ).first()
        
        if not choreography:
            return None
        
        # Update title if provided
        if request.title is not None:
            choreography.title = request.title.strip()
        
        # Update difficulty if provided
        if request.difficulty is not None:
            valid_difficulties = ["beginner", "intermediate", "advanced"]
            if request.difficulty not in valid_difficulties:
                raise ValueError(f"Invalid difficulty level. Must be one of: {valid_difficulties}")
            choreography.difficulty = request.difficulty
        
        try:
            db.commit()
            db.refresh(choreography)
            return SavedChoreographyResponse.model_validate(choreography)
        except Exception:
            db.rollback()
            raise
    
    async def delete_choreography(
        self, 
        db: Session, 
        user_id: str, 
        choreography_id: str
    ) -> bool:
        """
        Delete a choreography and clean up associated files.
        
        Args:
            db: Database session
            user_id: User's unique identifier
            choreography_id: Choreography's unique identifier
            
        Returns:
            bool: True if deletion was successful, False if choreography not found
        """
        choreography = db.query(SavedChoreography).filter(
            and_(
                SavedChoreography.id == choreography_id,
                SavedChoreography.user_id == user_id
            )
        ).first()
        
        if not choreography:
            return False
        
        try:
            # Delete associated files
            self._delete_choreography_files(choreography)
            
            # Delete database record
            db.delete(choreography)
            db.commit()
            
            return True
            
        except Exception:
            db.rollback()
            raise
    
    async def get_collection_stats(
        self, 
        db: Session, 
        user_id: str
    ) -> CollectionStatsResponse:
        """
        Get collection statistics and analytics.
        
        Args:
            db: Database session
            user_id: User's unique identifier
            
        Returns:
            CollectionStatsResponse: Collection statistics
            
        Raises:
            ValueError: If user doesn't exist
        """
        # Verify user exists
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise ValueError("User not found")
        
        # Get total count and duration
        stats = db.query(
            func.count(SavedChoreography.id).label('total_count'),
            func.sum(SavedChoreography.duration).label('total_duration')
        ).filter(SavedChoreography.user_id == user_id).first()
        
        total_choreographies = stats.total_count or 0
        total_duration = float(stats.total_duration or 0)
        
        # Get difficulty breakdown
        difficulty_stats = db.query(
            SavedChoreography.difficulty,
            func.count(SavedChoreography.id).label('count')
        ).filter(SavedChoreography.user_id == user_id).group_by(SavedChoreography.difficulty).all()
        
        difficulty_breakdown = {stat.difficulty: stat.count for stat in difficulty_stats}
        
        # Get recent activity (last 5 choreographies)
        recent_choreographies = db.query(SavedChoreography).filter(
            SavedChoreography.user_id == user_id
        ).order_by(desc(SavedChoreography.created_at)).limit(5).all()
        
        recent_activity = [
            SavedChoreographyResponse.model_validate(choreo) for choreo in recent_choreographies
        ]
        
        # Calculate storage used
        storage_used_mb = 0.0
        all_choreographies = db.query(SavedChoreography).filter(
            SavedChoreography.user_id == user_id
        ).all()
        
        for choreo in all_choreographies:
            if choreo.video_path:
                storage_used_mb += self._get_file_size_mb(choreo.video_path)
            if choreo.thumbnail_path:
                storage_used_mb += self._get_file_size_mb(choreo.thumbnail_path)
        
        return CollectionStatsResponse(
            total_choreographies=total_choreographies,
            total_duration=total_duration,
            difficulty_breakdown=difficulty_breakdown,
            recent_activity=recent_activity,
            storage_used_mb=round(storage_used_mb, 2)
        )
    
    async def cleanup_orphaned_files(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Clean up orphaned files in user's storage directory.
        
        Args:
            db: Database session
            user_id: User's unique identifier
            
        Returns:
            Dict[str, Any]: Cleanup results
        """
        user_storage = self._get_user_storage_path(user_id)
        
        # Get all choreography IDs for this user
        choreography_ids = set(
            choreo.id for choreo in db.query(SavedChoreography.id).filter(
                SavedChoreography.user_id == user_id
            ).all()
        )
        
        # Find orphaned files
        orphaned_files = []
        total_size_mb = 0.0
        
        if user_storage.exists():
            for file_path in user_storage.iterdir():
                if file_path.is_file():
                    # Extract choreography ID from filename
                    filename = file_path.stem
                    if filename.endswith('_thumb'):
                        choreo_id = filename[:-6]  # Remove '_thumb' suffix
                    else:
                        choreo_id = filename
                    
                    # Check if choreography exists
                    if choreo_id not in choreography_ids:
                        file_size_mb = file_path.stat().st_size / (1024 * 1024)
                        orphaned_files.append({
                            'path': str(file_path),
                            'size_mb': round(file_size_mb, 2)
                        })
                        total_size_mb += file_size_mb
                        
                        # Delete the orphaned file
                        try:
                            file_path.unlink()
                        except Exception:
                            pass
        
        return {
            'orphaned_files_found': len(orphaned_files),
            'total_size_cleaned_mb': round(total_size_mb, 2),
            'files': orphaned_files
        }