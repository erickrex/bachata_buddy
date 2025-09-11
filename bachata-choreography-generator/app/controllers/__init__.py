"""
Controllers package for the Bachata Choreography Generator.

This package contains all the FastAPI route controllers organized by functionality.
"""

from .base_controller import BaseController
from .auth_controller import AuthController
from .choreography_controller import ChoreographyController
from .collection_controller import CollectionController
from .instructor_controller import InstructorController
from .media_controller import MediaController

__all__ = [
    "BaseController",
    "AuthController",
    "ChoreographyController", 
    "CollectionController",
    "InstructorController",
    "MediaController"
]