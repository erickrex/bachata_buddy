"""
Instructor dashboard service for managing class plans and choreography sequences.

Handles CRUD operations for class plans, choreography sequencing, and lesson management.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func

from app.models.database_models import ClassPlan, ClassPlanSequence, SavedChoreography, User


class InstructorDashboardService:
    """
    Service for managing instructor class plans and choreography sequences.
    
    Features:
    - Create and manage class plans with choreography sequences
    - Organize saved choreographies into structured lesson plans
    - Provide class timing and difficulty progression tools
    - Generate printable class plans and instructor notes
    - Track class history and duplicate/template functionality
    """
    
    def __init__(self):
        """Initialize the instructor dashboard service."""
        pass
    
    async def create_class_plan(
        self, 
        db: Session, 
        instructor_id: str, 
        title: str,
        description: Optional[str] = None,
        difficulty_level: str = "intermediate",
        estimated_duration: Optional[int] = None,
        instructor_notes: Optional[str] = None
    ) -> ClassPlan:
        """
        Create a new class plan for an instructor.
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            title: Class plan title
            description: Detailed description of the class
            difficulty_level: Overall difficulty (beginner, intermediate, advanced)
            estimated_duration: Estimated class duration in minutes
            instructor_notes: Rich text notes for teaching tips and objectives
            
        Returns:
            ClassPlan: Created class plan
            
        Raises:
            ValueError: If instructor doesn't exist or invalid parameters
        """
        # Verify instructor exists and has instructor privileges
        instructor = db.query(User).filter(
            and_(
                User.id == instructor_id,
                User.is_instructor == True,
                User.is_active == True
            )
        ).first()
        
        if not instructor:
            raise ValueError("Instructor not found or user does not have instructor privileges")
        
        # Validate difficulty level
        valid_difficulties = ["beginner", "intermediate", "advanced"]
        if difficulty_level not in valid_difficulties:
            raise ValueError(f"Invalid difficulty level. Must be one of: {valid_difficulties}")
        
        # Generate unique class plan ID
        class_plan_id = str(uuid.uuid4())
        
        try:
            # Create class plan record
            class_plan = ClassPlan(
                id=class_plan_id,
                instructor_id=instructor_id,
                title=title.strip(),
                description=description.strip() if description else None,
                difficulty_level=difficulty_level,
                estimated_duration=estimated_duration,
                instructor_notes=instructor_notes.strip() if instructor_notes else None
            )
            
            db.add(class_plan)
            db.commit()
            db.refresh(class_plan)
            
            return class_plan
            
        except Exception as e:
            db.rollback()
            raise e
    
    async def get_instructor_class_plans(
        self, 
        db: Session, 
        instructor_id: str,
        difficulty_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieve class plans for an instructor with filtering and sorting.
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            difficulty_filter: Filter by difficulty level (optional)
            sort_by: Sort field (created_at, title, difficulty_level, estimated_duration)
            sort_order: Sort order (asc, desc)
            page: Page number for pagination
            limit: Number of items per page
            
        Returns:
            Dict containing class plans and pagination info
            
        Raises:
            ValueError: If instructor doesn't exist
        """
        # Verify instructor exists
        instructor = db.query(User).filter(
            and_(
                User.id == instructor_id,
                User.is_instructor == True,
                User.is_active == True
            )
        ).first()
        
        if not instructor:
            raise ValueError("Instructor not found or user does not have instructor privileges")
        
        # Build base query
        query = db.query(ClassPlan).filter(ClassPlan.instructor_id == instructor_id)
        
        # Apply difficulty filter
        if difficulty_filter:
            valid_difficulties = ["beginner", "intermediate", "advanced"]
            if difficulty_filter in valid_difficulties:
                query = query.filter(ClassPlan.difficulty_level == difficulty_filter)
        
        # Apply sorting
        valid_sort_fields = ["created_at", "title", "difficulty_level", "estimated_duration", "updated_at"]
        if sort_by in valid_sort_fields:
            sort_column = getattr(ClassPlan, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            # Default sorting
            query = query.order_by(desc(ClassPlan.created_at))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        class_plans = query.offset(offset).limit(limit).all()
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_previous = page > 1
        
        return {
            "class_plans": class_plans,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_previous": has_previous
        }
    
    async def get_class_plan_by_id(
        self, 
        db: Session, 
        instructor_id: str, 
        class_plan_id: str
    ) -> Optional[ClassPlan]:
        """
        Get a specific class plan by ID (instructor must own it).
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            class_plan_id: Class plan's unique identifier
            
        Returns:
            Optional[ClassPlan]: Class plan if found and owned by instructor
        """
        class_plan = db.query(ClassPlan).filter(
            and_(
                ClassPlan.id == class_plan_id,
                ClassPlan.instructor_id == instructor_id
            )
        ).first()
        
        return class_plan
    
    async def update_class_plan(
        self, 
        db: Session, 
        instructor_id: str, 
        class_plan_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        estimated_duration: Optional[int] = None,
        instructor_notes: Optional[str] = None
    ) -> Optional[ClassPlan]:
        """
        Update class plan metadata.
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            class_plan_id: Class plan's unique identifier
            title: Updated title (optional)
            description: Updated description (optional)
            difficulty_level: Updated difficulty level (optional)
            estimated_duration: Updated duration (optional)
            instructor_notes: Updated notes (optional)
            
        Returns:
            Optional[ClassPlan]: Updated class plan if successful
            
        Raises:
            ValueError: If invalid parameters provided
        """
        class_plan = db.query(ClassPlan).filter(
            and_(
                ClassPlan.id == class_plan_id,
                ClassPlan.instructor_id == instructor_id
            )
        ).first()
        
        if not class_plan:
            return None
        
        # Update fields if provided
        if title is not None:
            class_plan.title = title.strip()
        
        if description is not None:
            class_plan.description = description.strip() if description else None
        
        if difficulty_level is not None:
            valid_difficulties = ["beginner", "intermediate", "advanced"]
            if difficulty_level not in valid_difficulties:
                raise ValueError(f"Invalid difficulty level. Must be one of: {valid_difficulties}")
            class_plan.difficulty_level = difficulty_level
        
        if estimated_duration is not None:
            class_plan.estimated_duration = estimated_duration
        
        if instructor_notes is not None:
            class_plan.instructor_notes = instructor_notes.strip() if instructor_notes else None
        
        # Update timestamp
        class_plan.updated_at = datetime.utcnow()
        
        try:
            db.commit()
            db.refresh(class_plan)
            return class_plan
        except Exception:
            db.rollback()
            raise
    
    async def delete_class_plan(
        self, 
        db: Session, 
        instructor_id: str, 
        class_plan_id: str
    ) -> bool:
        """
        Delete a class plan and all associated sequences.
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            class_plan_id: Class plan's unique identifier
            
        Returns:
            bool: True if deletion was successful, False if class plan not found
        """
        class_plan = db.query(ClassPlan).filter(
            and_(
                ClassPlan.id == class_plan_id,
                ClassPlan.instructor_id == instructor_id
            )
        ).first()
        
        if not class_plan:
            return False
        
        try:
            # Delete associated sequences (cascade should handle this, but explicit for clarity)
            db.query(ClassPlanSequence).filter(
                ClassPlanSequence.class_plan_id == class_plan_id
            ).delete()
            
            # Delete class plan
            db.delete(class_plan)
            db.commit()
            
            return True
            
        except Exception:
            db.rollback()
            raise
    
    async def add_choreography_to_plan(
        self, 
        db: Session, 
        instructor_id: str, 
        class_plan_id: str,
        choreography_id: str,
        sequence_order: Optional[int] = None,
        notes: Optional[str] = None,
        estimated_time: Optional[int] = None
    ) -> Optional[ClassPlanSequence]:
        """
        Add a choreography to a class plan with sequencing information.
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            class_plan_id: Class plan's unique identifier
            choreography_id: Choreography's unique identifier
            sequence_order: Order in the class plan (auto-assigned if None)
            notes: Specific notes for this choreography in the class context
            estimated_time: Estimated time to teach this choreography (minutes)
            
        Returns:
            Optional[ClassPlanSequence]: Created sequence if successful
            
        Raises:
            ValueError: If class plan or choreography not found/accessible
        """
        # Verify class plan exists and belongs to instructor
        class_plan = db.query(ClassPlan).filter(
            and_(
                ClassPlan.id == class_plan_id,
                ClassPlan.instructor_id == instructor_id
            )
        ).first()
        
        if not class_plan:
            raise ValueError("Class plan not found or not accessible")
        
        # Verify choreography exists and belongs to instructor
        choreography = db.query(SavedChoreography).filter(
            and_(
                SavedChoreography.id == choreography_id,
                SavedChoreography.user_id == instructor_id
            )
        ).first()
        
        if not choreography:
            raise ValueError("Choreography not found or not accessible")
        
        # Check if choreography is already in this class plan
        existing_sequence = db.query(ClassPlanSequence).filter(
            and_(
                ClassPlanSequence.class_plan_id == class_plan_id,
                ClassPlanSequence.choreography_id == choreography_id
            )
        ).first()
        
        if existing_sequence:
            raise ValueError("Choreography is already in this class plan")
        
        # Auto-assign sequence order if not provided
        if sequence_order is None:
            max_order = db.query(func.max(ClassPlanSequence.sequence_order)).filter(
                ClassPlanSequence.class_plan_id == class_plan_id
            ).scalar()
            sequence_order = (max_order or 0) + 1
        
        # Generate unique sequence ID
        sequence_id = str(uuid.uuid4())
        
        try:
            # Create sequence record
            sequence = ClassPlanSequence(
                id=sequence_id,
                class_plan_id=class_plan_id,
                choreography_id=choreography_id,
                sequence_order=sequence_order,
                notes=notes.strip() if notes else None,
                estimated_time=estimated_time
            )
            
            db.add(sequence)
            
            # Update class plan timestamp
            class_plan.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(sequence)
            
            return sequence
            
        except Exception as e:
            db.rollback()
            raise e
    
    async def remove_choreography_from_plan(
        self, 
        db: Session, 
        instructor_id: str, 
        class_plan_id: str,
        choreography_id: str
    ) -> bool:
        """
        Remove a choreography from a class plan.
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            class_plan_id: Class plan's unique identifier
            choreography_id: Choreography's unique identifier
            
        Returns:
            bool: True if removal was successful, False if sequence not found
        """
        # Verify class plan belongs to instructor
        class_plan = db.query(ClassPlan).filter(
            and_(
                ClassPlan.id == class_plan_id,
                ClassPlan.instructor_id == instructor_id
            )
        ).first()
        
        if not class_plan:
            return False
        
        # Find and delete the sequence
        sequence = db.query(ClassPlanSequence).filter(
            and_(
                ClassPlanSequence.class_plan_id == class_plan_id,
                ClassPlanSequence.choreography_id == choreography_id
            )
        ).first()
        
        if not sequence:
            return False
        
        try:
            db.delete(sequence)
            
            # Update class plan timestamp
            class_plan.updated_at = datetime.utcnow()
            
            db.commit()
            return True
            
        except Exception:
            db.rollback()
            raise
    
    async def reorder_choreography_sequence(
        self, 
        db: Session, 
        instructor_id: str, 
        class_plan_id: str,
        choreography_sequence_updates: List[Dict[str, Any]]
    ) -> bool:
        """
        Reorder choreographies in a class plan.
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            class_plan_id: Class plan's unique identifier
            choreography_sequence_updates: List of dicts with choreography_id and new sequence_order
            
        Returns:
            bool: True if reordering was successful
            
        Raises:
            ValueError: If class plan not found or invalid sequence data
        """
        # Verify class plan belongs to instructor
        class_plan = db.query(ClassPlan).filter(
            and_(
                ClassPlan.id == class_plan_id,
                ClassPlan.instructor_id == instructor_id
            )
        ).first()
        
        if not class_plan:
            raise ValueError("Class plan not found or not accessible")
        
        try:
            # Update sequence orders
            for update in choreography_sequence_updates:
                choreography_id = update.get("choreography_id")
                new_order = update.get("sequence_order")
                
                if not choreography_id or new_order is None:
                    continue
                
                sequence = db.query(ClassPlanSequence).filter(
                    and_(
                        ClassPlanSequence.class_plan_id == class_plan_id,
                        ClassPlanSequence.choreography_id == choreography_id
                    )
                ).first()
                
                if sequence:
                    sequence.sequence_order = new_order
            
            # Update class plan timestamp
            class_plan.updated_at = datetime.utcnow()
            
            db.commit()
            return True
            
        except Exception:
            db.rollback()
            raise
    
    async def update_sequence_details(
        self, 
        db: Session, 
        instructor_id: str, 
        class_plan_id: str,
        choreography_id: str,
        notes: Optional[str] = None,
        estimated_time: Optional[int] = None
    ) -> Optional[ClassPlanSequence]:
        """
        Update sequence-specific details (notes and estimated time).
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            class_plan_id: Class plan's unique identifier
            choreography_id: Choreography's unique identifier
            notes: Updated notes (optional)
            estimated_time: Updated estimated time (optional)
            
        Returns:
            Optional[ClassPlanSequence]: Updated sequence if successful
        """
        # Verify class plan belongs to instructor
        class_plan = db.query(ClassPlan).filter(
            and_(
                ClassPlan.id == class_plan_id,
                ClassPlan.instructor_id == instructor_id
            )
        ).first()
        
        if not class_plan:
            return None
        
        # Find the sequence
        sequence = db.query(ClassPlanSequence).filter(
            and_(
                ClassPlanSequence.class_plan_id == class_plan_id,
                ClassPlanSequence.choreography_id == choreography_id
            )
        ).first()
        
        if not sequence:
            return None
        
        # Update fields if provided
        if notes is not None:
            sequence.notes = notes.strip() if notes else None
        
        if estimated_time is not None:
            sequence.estimated_time = estimated_time
        
        try:
            # Update class plan timestamp
            class_plan.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(sequence)
            return sequence
            
        except Exception:
            db.rollback()
            raise
    
    async def generate_class_plan_summary(
        self, 
        db: Session, 
        instructor_id: str, 
        class_plan_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a structured summary of a class plan with timing and progression.
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            class_plan_id: Class plan's unique identifier
            
        Returns:
            Optional[Dict]: Structured class plan summary if found
        """
        # Get class plan with sequences
        class_plan = db.query(ClassPlan).filter(
            and_(
                ClassPlan.id == class_plan_id,
                ClassPlan.instructor_id == instructor_id
            )
        ).first()
        
        if not class_plan:
            return None
        
        # Get sequences with choreography details, ordered by sequence_order
        sequences = db.query(ClassPlanSequence, SavedChoreography).join(
            SavedChoreography, ClassPlanSequence.choreography_id == SavedChoreography.id
        ).filter(
            ClassPlanSequence.class_plan_id == class_plan_id
        ).order_by(ClassPlanSequence.sequence_order).all()
        
        # Calculate summary statistics
        total_choreographies = len(sequences)
        total_estimated_time = sum(
            seq.estimated_time or 0 for seq, _ in sequences
        )
        
        # Calculate difficulty distribution
        difficulty_counts = {"beginner": 0, "intermediate": 0, "advanced": 0}
        total_video_duration = 0.0
        
        sequence_details = []
        for sequence, choreography in sequences:
            difficulty_counts[choreography.difficulty] += 1
            total_video_duration += choreography.duration
            
            sequence_details.append({
                "sequence_order": sequence.sequence_order,
                "choreography_id": choreography.id,
                "choreography_title": choreography.title,
                "choreography_difficulty": choreography.difficulty,
                "choreography_duration": choreography.duration,
                "estimated_teaching_time": sequence.estimated_time,
                "sequence_notes": sequence.notes,
                "music_info": choreography.music_info
            })
        
        # Calculate progression analysis
        difficulty_progression = [
            choreo.difficulty for _, choreo in sequences
        ]
        
        # Estimate total class time (teaching time + video duration + transitions)
        estimated_total_time = total_estimated_time + (total_video_duration / 60) + (total_choreographies * 2)  # 2 min transition buffer per choreography
        
        return {
            "class_plan": {
                "id": class_plan.id,
                "title": class_plan.title,
                "description": class_plan.description,
                "difficulty_level": class_plan.difficulty_level,
                "estimated_duration": class_plan.estimated_duration,
                "instructor_notes": class_plan.instructor_notes,
                "created_at": class_plan.created_at,
                "updated_at": class_plan.updated_at
            },
            "summary_statistics": {
                "total_choreographies": total_choreographies,
                "total_estimated_teaching_time": total_estimated_time,
                "total_video_duration_minutes": round(total_video_duration / 60, 1),
                "estimated_total_class_time": round(estimated_total_time, 0),
                "difficulty_distribution": difficulty_counts,
                "difficulty_progression": difficulty_progression
            },
            "choreography_sequences": sequence_details,
            "teaching_recommendations": self._generate_teaching_recommendations(
                difficulty_progression, total_estimated_time, class_plan.difficulty_level
            )
        }
    
    def _generate_teaching_recommendations(
        self, 
        difficulty_progression: List[str], 
        total_time: int, 
        class_difficulty: str
    ) -> List[str]:
        """
        Generate teaching recommendations based on class plan analysis.
        
        Args:
            difficulty_progression: List of difficulty levels in sequence order
            total_time: Total estimated teaching time
            class_difficulty: Overall class difficulty level
            
        Returns:
            List[str]: Teaching recommendations
        """
        recommendations = []
        
        # Time-based recommendations
        if total_time > 90:
            recommendations.append("Consider breaking this into multiple sessions - over 90 minutes may be too long for most students")
        elif total_time < 30:
            recommendations.append("Class may be too short - consider adding warm-up time or additional practice")
        
        # Difficulty progression recommendations
        if len(difficulty_progression) > 1:
            # Check for difficulty jumps
            difficulty_levels = {"beginner": 1, "intermediate": 2, "advanced": 3}
            for i in range(1, len(difficulty_progression)):
                current_level = difficulty_levels[difficulty_progression[i]]
                previous_level = difficulty_levels[difficulty_progression[i-1]]
                
                if current_level - previous_level > 1:
                    recommendations.append(f"Consider adding intermediate steps between choreography {i} and {i+1} - difficulty jump may be too large")
        
        # Class structure recommendations
        if difficulty_progression and difficulty_progression[0] != "beginner":
            recommendations.append("Consider starting with a beginner-level choreography as warm-up")
        
        if difficulty_progression and difficulty_progression[-1] == "advanced":
            recommendations.append("Ending with advanced choreography - ensure students are ready and consider cool-down time")
        
        # Class difficulty alignment
        beginner_count = difficulty_progression.count("beginner")
        advanced_count = difficulty_progression.count("advanced")
        
        if class_difficulty == "beginner" and advanced_count > 0:
            recommendations.append("Class marked as beginner but contains advanced choreographies - consider adjusting class level or choreography selection")
        
        if class_difficulty == "advanced" and beginner_count > len(difficulty_progression) / 2:
            recommendations.append("Class marked as advanced but contains many beginner choreographies - consider adjusting class level")
        
        return recommendations
    
    async def duplicate_class_plan(
        self, 
        db: Session, 
        instructor_id: str, 
        source_class_plan_id: str,
        new_title: str,
        copy_sequences: bool = True
    ) -> Optional[ClassPlan]:
        """
        Duplicate an existing class plan with optional sequence copying.
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            source_class_plan_id: ID of class plan to duplicate
            new_title: Title for the new class plan
            copy_sequences: Whether to copy choreography sequences
            
        Returns:
            Optional[ClassPlan]: Duplicated class plan if successful
            
        Raises:
            ValueError: If source class plan not found
        """
        # Get source class plan
        source_plan = db.query(ClassPlan).filter(
            and_(
                ClassPlan.id == source_class_plan_id,
                ClassPlan.instructor_id == instructor_id
            )
        ).first()
        
        if not source_plan:
            raise ValueError("Source class plan not found or not accessible")
        
        try:
            # Create new class plan
            new_plan = await self.create_class_plan(
                db=db,
                instructor_id=instructor_id,
                title=new_title,
                description=source_plan.description,
                difficulty_level=source_plan.difficulty_level,
                estimated_duration=source_plan.estimated_duration,
                instructor_notes=source_plan.instructor_notes
            )
            
            # Copy sequences if requested
            if copy_sequences:
                source_sequences = db.query(ClassPlanSequence).filter(
                    ClassPlanSequence.class_plan_id == source_class_plan_id
                ).order_by(ClassPlanSequence.sequence_order).all()
                
                for source_sequence in source_sequences:
                    await self.add_choreography_to_plan(
                        db=db,
                        instructor_id=instructor_id,
                        class_plan_id=new_plan.id,
                        choreography_id=source_sequence.choreography_id,
                        sequence_order=source_sequence.sequence_order,
                        notes=source_sequence.notes,
                        estimated_time=source_sequence.estimated_time
                    )
            
            return new_plan
            
        except Exception as e:
            db.rollback()
            raise e
    
    async def get_instructor_dashboard_stats(
        self, 
        db: Session, 
        instructor_id: str
    ) -> Dict[str, Any]:
        """
        Get dashboard statistics for an instructor.
        
        Args:
            db: Database session
            instructor_id: Instructor's unique identifier
            
        Returns:
            Dict: Dashboard statistics
            
        Raises:
            ValueError: If instructor not found
        """
        # Verify instructor exists
        instructor = db.query(User).filter(
            and_(
                User.id == instructor_id,
                User.is_instructor == True,
                User.is_active == True
            )
        ).first()
        
        if not instructor:
            raise ValueError("Instructor not found or user does not have instructor privileges")
        
        # Get class plan statistics
        total_class_plans = db.query(func.count(ClassPlan.id)).filter(
            ClassPlan.instructor_id == instructor_id
        ).scalar() or 0
        
        # Get difficulty breakdown for class plans
        difficulty_stats = db.query(
            ClassPlan.difficulty_level,
            func.count(ClassPlan.id).label('count')
        ).filter(
            ClassPlan.instructor_id == instructor_id
        ).group_by(ClassPlan.difficulty_level).all()
        
        class_plan_difficulty_breakdown = {stat.difficulty_level: stat.count for stat in difficulty_stats}
        
        # Get recent class plans
        recent_class_plans = db.query(ClassPlan).filter(
            ClassPlan.instructor_id == instructor_id
        ).order_by(desc(ClassPlan.updated_at)).limit(5).all()
        
        # Get choreography usage statistics
        choreography_usage = db.query(
            SavedChoreography.id,
            SavedChoreography.title,
            func.count(ClassPlanSequence.id).label('usage_count')
        ).join(
            ClassPlanSequence, SavedChoreography.id == ClassPlanSequence.choreography_id
        ).join(
            ClassPlan, ClassPlanSequence.class_plan_id == ClassPlan.id
        ).filter(
            and_(
                SavedChoreography.user_id == instructor_id,
                ClassPlan.instructor_id == instructor_id
            )
        ).group_by(SavedChoreography.id, SavedChoreography.title).order_by(
            desc(func.count(ClassPlanSequence.id))
        ).limit(10).all()
        
        return {
            "instructor_info": {
                "id": instructor.id,
                "display_name": instructor.display_name,
                "email": instructor.email
            },
            "class_plan_statistics": {
                "total_class_plans": total_class_plans,
                "difficulty_breakdown": class_plan_difficulty_breakdown,
                "recent_activity": [
                    {
                        "id": plan.id,
                        "title": plan.title,
                        "difficulty_level": plan.difficulty_level,
                        "updated_at": plan.updated_at
                    } for plan in recent_class_plans
                ]
            },
            "choreography_usage": [
                {
                    "choreography_id": usage.id,
                    "choreography_title": usage.title,
                    "usage_count": usage.usage_count
                } for usage in choreography_usage
            ]
        }