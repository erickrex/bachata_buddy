"""
Authentication middleware for the Bachata Choreography Generator.

Provides middleware and dependencies for protecting FastAPI routes.
"""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.services.authentication_service import AuthenticationService
from app.models.database_models import User


# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """
    Authentication middleware for FastAPI.
    """
    
    def __init__(self, auth_service: AuthenticationService):
        """
        Initialize the authentication middleware.
        
        Args:
            auth_service: Authentication service instance
        """
        self.auth_service = auth_service
    
    async def get_current_user(
        self,
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
        db: Annotated[Session, Depends(get_database_session)]
    ) -> Optional[User]:
        """
        Get the current authenticated user from the request.
        
        Args:
            credentials: HTTP Bearer credentials
            db: Database session
            
        Returns:
            Optional[User]: Current user if authenticated, None otherwise
        """
        if not credentials:
            return None
        
        # Verify the token
        token_payload = self.auth_service.verify_token(credentials.credentials)
        if not token_payload:
            return None
        
        # Check token type
        if token_payload.get("type") != "access":
            return None
        
        # Get user from database
        user_id = token_payload.get("sub")
        if not user_id:
            return None
        
        user = await self.auth_service.get_user_by_id(db, user_id)
        return user
    
    async def require_authentication(
        self,
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
        db: Annotated[Session, Depends(get_database_session)]
    ) -> User:
        """
        Require authentication for a route.
        
        Args:
            credentials: HTTP Bearer credentials
            db: Database session
            
        Returns:
            User: Current authenticated user
            
        Raises:
            HTTPException: If authentication fails
        """
        user = await self.get_current_user(credentials, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    
    async def require_instructor(
        self,
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
        db: Annotated[Session, Depends(get_database_session)]
    ) -> User:
        """
        Require instructor privileges for a route.
        
        Args:
            credentials: HTTP Bearer credentials
            db: Database session
            
        Returns:
            User: Current authenticated instructor user
            
        Raises:
            HTTPException: If authentication fails or user is not an instructor
        """
        user = await self.require_authentication(credentials, db)
        
        if not user.is_instructor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Instructor privileges required"
            )
        
        return user


# Global authentication middleware instance
# This will be initialized in main.py with the proper JWT secret
_auth_middleware: Optional[AuthMiddleware] = None


def set_auth_middleware(middleware: AuthMiddleware):
    """
    Set the global authentication middleware instance.
    
    Args:
        middleware: Authentication middleware instance
    """
    global _auth_middleware
    _auth_middleware = middleware


def get_auth_middleware() -> AuthMiddleware:
    """
    Get the global authentication middleware instance.
    
    Returns:
        AuthMiddleware: Global auth middleware instance
        
    Raises:
        RuntimeError: If middleware is not initialized
    """
    if _auth_middleware is None:
        raise RuntimeError("Authentication middleware not initialized")
    return _auth_middleware


# Dependency functions for FastAPI routes
async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[Session, Depends(get_database_session)]
) -> Optional[User]:
    """
    FastAPI dependency to get the current user (optional).
    
    Returns None if not authenticated, doesn't raise an exception.
    """
    middleware = get_auth_middleware()
    return await middleware.get_current_user(credentials, db)


async def require_authentication(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[Session, Depends(get_database_session)]
) -> User:
    """
    FastAPI dependency to require authentication.
    
    Raises HTTPException if not authenticated.
    """
    middleware = get_auth_middleware()
    return await middleware.require_authentication(credentials, db)


async def require_instructor(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[Session, Depends(get_database_session)]
) -> User:
    """
    FastAPI dependency to require instructor privileges.
    
    Raises HTTPException if not authenticated or not an instructor.
    """
    middleware = get_auth_middleware()
    return await middleware.require_instructor(credentials, db)


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[Optional[User], Depends(get_current_user)]
AuthenticatedUser = Annotated[User, Depends(require_authentication)]
InstructorUser = Annotated[User, Depends(require_instructor)]