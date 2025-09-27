"""
Database models for the Bachata Choreography Generator application.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """
    User model for authentication and user management.
    
    Attributes:
        id: Unique user identifier (UUID string)
        email: User's email address (unique)
        password_hash: Bcrypt hashed password
        display_name: User's display name
        is_instructor: Whether the user has instructor privileges
        created_at: Account creation timestamp
        updated_at: Last account update timestamp
        is_active: Whether the account is active (for soft deletion)
    """
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    is_instructor = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    preferences = Column(JSON, default=lambda: {"auto_save_choreographies": True}, nullable=True)
    
    # Relationships
    choreographies = relationship("SavedChoreography", back_populates="user", cascade="all, delete-orphan")
    class_plans = relationship("ClassPlan", back_populates="instructor", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}', display_name='{self.display_name}')>"


class SavedChoreography(Base):
    """
    Model for user's saved choreographies.
    
    Attributes:
        id: Unique choreography identifier
        user_id: Foreign key to User
        title: User-defined title for the choreography
        video_path: Path to the generated video file
        thumbnail_path: Path to video thumbnail (optional)
        difficulty: Difficulty level (beginner, intermediate, advanced)
        duration: Video duration in seconds
        music_info: JSON containing music metadata (title, artist, tempo, etc.)
        generation_parameters: JSON containing generation settings used
        created_at: Creation timestamp
    """
    __tablename__ = "saved_choreographies"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    video_path = Column(String, nullable=False)
    thumbnail_path = Column(String)
    difficulty = Column(String, nullable=False)  # beginner, intermediate, advanced
    duration = Column(Float, nullable=False)
    music_info = Column(JSON)  # Store music metadata as JSON
    generation_parameters = Column(JSON)  # Store generation settings as JSON
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="choreographies")
    class_plan_sequences = relationship("ClassPlanSequence", back_populates="choreography")
    
    def __repr__(self):
        return f"<SavedChoreography(id='{self.id}', title='{self.title}', user_id='{self.user_id}')>"


class ClassPlan(Base):
    """
    Model for instructor class plans.
    
    Attributes:
        id: Unique class plan identifier
        instructor_id: Foreign key to User (must be instructor)
        title: Class plan title
        description: Detailed description of the class
        difficulty_level: Overall difficulty (beginner, intermediate, advanced)
        estimated_duration: Estimated class duration in minutes
        instructor_notes: Rich text notes for teaching tips and objectives
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "class_plans"
    
    id = Column(String, primary_key=True)
    instructor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    difficulty_level = Column(String, nullable=False)  # beginner, intermediate, advanced
    estimated_duration = Column(Integer)  # Duration in minutes
    instructor_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    instructor = relationship("User", back_populates="class_plans")
    choreography_sequences = relationship("ClassPlanSequence", back_populates="class_plan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ClassPlan(id='{self.id}', title='{self.title}', instructor_id='{self.instructor_id}')>"


class ClassPlanSequence(Base):
    """
    Model for choreography sequences within class plans.
    
    Attributes:
        id: Unique sequence identifier
        class_plan_id: Foreign key to ClassPlan
        choreography_id: Foreign key to SavedChoreography
        sequence_order: Order of this choreography in the class plan
        notes: Specific notes for this choreography in the class context
        estimated_time: Estimated time to teach this choreography (minutes)
    """
    __tablename__ = "class_plan_sequences"
    
    id = Column(String, primary_key=True)
    class_plan_id = Column(String, ForeignKey("class_plans.id"), nullable=False, index=True)
    choreography_id = Column(String, ForeignKey("saved_choreographies.id"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    notes = Column(Text)
    estimated_time = Column(Integer)  # Time in minutes
    
    # Relationships
    class_plan = relationship("ClassPlan", back_populates="choreography_sequences")
    choreography = relationship("SavedChoreography", back_populates="class_plan_sequences")
    
    def __repr__(self):
        return f"<ClassPlanSequence(id='{self.id}', class_plan_id='{self.class_plan_id}', sequence_order={self.sequence_order})>"