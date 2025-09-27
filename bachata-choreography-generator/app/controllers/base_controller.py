"""
Base controller class for common functionality.
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter

logger = logging.getLogger(__name__)

class BaseController:
    """Base controller class with common functionality."""
    
    def __init__(self, prefix: str = "", tags: list = None):
        """Initialize the base controller with router configuration."""
        self.router = APIRouter(prefix=prefix, tags=tags or [])
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_router(self) -> APIRouter:
        """Get the FastAPI router for this controller."""
        return self.router
    
    def log_request(self, endpoint: str, params: Dict[str, Any] = None):
        """Log incoming requests for debugging."""
        if params:
            self.logger.info(f"{endpoint} called with params: {params}")
        else:
            self.logger.info(f"{endpoint} called")
    
    def log_error(self, endpoint: str, error: Exception):
        """Log errors with context."""
        self.logger.error(f"Error in {endpoint}: {error}", exc_info=True)