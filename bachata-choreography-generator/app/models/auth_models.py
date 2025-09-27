"""
Pydantic models for authentication requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegistrationRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password (minimum 8 characters)")
    display_name: str = Field(..., min_length=1, max_length=100, description="User's display name")
    is_instructor: bool = Field(default=False, description="Whether the user should have instructor privileges")


class UserLoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class UserResponse(BaseModel):
    """Response model for user information."""
    id: str = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    display_name: str = Field(..., description="User's display name")
    is_instructor: bool = Field(..., description="Whether the user has instructor privileges")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last account update timestamp")
    
    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    """Request model for updating user profile."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100, description="New display name")
    new_password: Optional[str] = Field(None, min_length=8, description="New password (minimum 8 characters)")


class AuthenticationResponse(BaseModel):
    """Response model for successful authentication."""
    user: UserResponse = Field(..., description="User information")
    tokens: TokenResponse = Field(..., description="Authentication tokens")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(..., description="JWT refresh token")


class ErrorResponse(BaseModel):
    """Response model for authentication errors."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")


class PasswordResetRequest(BaseModel):
    """Request model for password reset (future feature)."""
    email: EmailStr = Field(..., description="User's email address")


class PasswordResetConfirmRequest(BaseModel):
    """Request model for password reset confirmation (future feature)."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class RateLimitResponse(BaseModel):
    """Response model for rate limit errors."""
    detail: str = Field(default="Too many login attempts. Please try again later.", description="Rate limit message")
    retry_after: int = Field(..., description="Seconds until retry is allowed")
    error_code: str = Field(default="RATE_LIMITED", description="Error code")