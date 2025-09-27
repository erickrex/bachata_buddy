"""
Authentication controller for user registration, login, and session management.
"""

from typing import Annotated
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from .base_controller import BaseController
from app.database import get_database_session
from app.services.authentication_service import AuthenticationService
from app.middleware.auth_middleware import CurrentUser, AuthenticatedUser
from app.models.auth_models import (
    UserRegistrationRequest,
    UserLoginRequest,
    AuthenticationResponse,
    UserResponse,
    TokenResponse,
    UserProfileUpdateRequest,
    ErrorResponse,
    RateLimitResponse
)


class AuthController(BaseController):
    """Controller for authentication endpoints."""
    
    def __init__(self, auth_service: AuthenticationService):
        """
        Initialize the authentication controller.
        
        Args:
            auth_service: Authentication service instance
        """
        super().__init__(prefix="/api/auth", tags=["authentication"])
        self.auth_service = auth_service
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up authentication routes."""
        
        @self.router.post(
            "/register",
            response_model=AuthenticationResponse,
            status_code=status.HTTP_201_CREATED,
            responses={
                400: {"model": ErrorResponse, "description": "Invalid input or email already exists"},
                422: {"model": ErrorResponse, "description": "Validation error"}
            }
        )
        async def register(
            request: UserRegistrationRequest,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Register a new user account.
            
            Creates a new user account with the provided email, password, and display name.
            Returns authentication tokens upon successful registration.
            """
            try:
                # Register the user
                user = await self.auth_service.register_user(
                    db=db,
                    email=request.email,
                    password=request.password,
                    display_name=request.display_name,
                    is_instructor=request.is_instructor
                )
                
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email address already registered"
                    )
                
                # Generate tokens
                access_token = self.auth_service.create_access_token(
                    user_id=user.id,
                    email=user.email,
                    is_instructor=user.is_instructor
                )
                refresh_token = self.auth_service.create_refresh_token(user_id=user.id)
                
                return AuthenticationResponse(
                    user=UserResponse.from_orm(user),
                    tokens=TokenResponse(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_in=self.auth_service.access_token_expire_minutes * 60
                    )
                )
                
            except HTTPException:
                # Re-raise HTTP exceptions (like duplicate email)
                raise
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                # Log the actual error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Registration error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Registration failed"
                )
        
        @self.router.post(
            "/login",
            response_model=AuthenticationResponse,
            responses={
                400: {"model": ErrorResponse, "description": "Invalid credentials"},
                429: {"model": RateLimitResponse, "description": "Too many login attempts"},
                422: {"model": ErrorResponse, "description": "Validation error"}
            }
        )
        async def login(
            request: UserLoginRequest,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Authenticate user and create session.
            
            Validates user credentials and returns authentication tokens.
            Implements rate limiting to prevent brute force attacks.
            """
            try:
                # Check rate limiting first
                if self.auth_service.is_rate_limited(request.email):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many login attempts. Please try again later.",
                        headers={"Retry-After": str(self.auth_service.lockout_duration_minutes * 60)}
                    )
                
                # Authenticate user
                user = await self.auth_service.authenticate_user(
                    db=db,
                    email=request.email,
                    password=request.password
                )
                
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid email or password"
                    )
                
                # Generate tokens
                access_token = self.auth_service.create_access_token(
                    user_id=user.id,
                    email=user.email,
                    is_instructor=user.is_instructor
                )
                refresh_token = self.auth_service.create_refresh_token(user_id=user.id)
                
                return AuthenticationResponse(
                    user=UserResponse.from_orm(user),
                    tokens=TokenResponse(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_in=self.auth_service.access_token_expire_minutes * 60
                    )
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Login failed"
                )
        
        @self.router.post(
            "/logout",
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                401: {"model": ErrorResponse, "description": "Authentication required"}
            }
        )
        async def logout(current_user: AuthenticatedUser):
            """
            Log out current user and clear session.
            
            In a JWT-based system, logout is handled client-side by discarding tokens.
            This endpoint validates that the user is authenticated and can be used
            for logging purposes or future server-side token blacklisting.
            """
            # In JWT systems, logout is typically handled client-side
            # This endpoint serves as a validation that the user is authenticated
            # and can be extended for server-side token blacklisting if needed
            return None
        
        @self.router.get(
            "/profile",
            response_model=UserResponse,
            responses={
                401: {"model": ErrorResponse, "description": "Authentication required"}
            }
        )
        async def get_profile(current_user: AuthenticatedUser):
            """
            Get current user profile information.
            
            Returns the authenticated user's profile data.
            """
            return UserResponse.from_orm(current_user)
        
        @self.router.put(
            "/profile",
            response_model=UserResponse,
            responses={
                400: {"model": ErrorResponse, "description": "Invalid input"},
                401: {"model": ErrorResponse, "description": "Authentication required"},
                422: {"model": ErrorResponse, "description": "Validation error"}
            }
        )
        async def update_profile(
            request: UserProfileUpdateRequest,
            current_user: AuthenticatedUser,
            db: Annotated[Session, Depends(get_database_session)]
        ):
            """
            Update current user's profile information.
            
            Allows updating display name and/or password.
            """
            try:
                updated_user = await self.auth_service.update_user_profile(
                    db=db,
                    user_id=current_user.id,
                    display_name=request.display_name,
                    new_password=request.new_password
                )
                
                if not updated_user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                
                return UserResponse.from_orm(updated_user)
                
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Profile update failed"
                )
        
        @self.router.get(
            "/me",
            response_model=UserResponse,
            responses={
                401: {"model": ErrorResponse, "description": "Authentication required"}
            }
        )
        async def get_current_user_info(current_user: AuthenticatedUser):
            """
            Get current authenticated user information.
            
            Alternative endpoint to /profile for getting user info.
            """
            return UserResponse.from_orm(current_user)
        
        @self.router.get(
            "/status",
            responses={
                200: {"description": "User is authenticated"},
                401: {"model": ErrorResponse, "description": "User is not authenticated"}
            }
        )
        async def check_auth_status(current_user: CurrentUser):
            """
            Check authentication status.
            
            Returns user info if authenticated, 401 if not.
            Useful for frontend to check auth state.
            """
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            return {
                "authenticated": True,
                "user": UserResponse.from_orm(current_user)
            }