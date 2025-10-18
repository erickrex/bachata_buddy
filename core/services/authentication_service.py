"""
Authentication service for the Bachata Choreography Generator.

Handles user registration, login, JWT token management, and password security.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.db import IntegrityError

User = get_user_model()


class AuthenticationService:
    """
    Service for handling user authentication and authorization.
    
    Features:
    - Secure password hashing with bcrypt
    - JWT token generation and validation
    - User registration and login
    - Session management
    - Rate limiting protection
    """
    
    def __init__(self, jwt_secret: str, jwt_algorithm: str = "HS256", access_token_expire_minutes: int = 30):
        """
        Initialize the authentication service.
        
        Args:
            jwt_secret: Secret key for JWT token signing
            jwt_algorithm: JWT algorithm to use (default: HS256)
            access_token_expire_minutes: Access token expiration time in minutes
        """
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        
        # Simple in-memory rate limiting (in production, use Redis or similar)
        self._login_attempts: Dict[str, list] = {}
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 15
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using Django's password hashing.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return make_password(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash using Django's check_password.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password(plain_password, hashed_password)
    
    def create_access_token(self, user_id: str, email: str, is_instructor: bool = False) -> str:
        """
        Create a JWT access token for a user.
        
        Args:
            user_id: User's unique identifier
            email: User's email address
            is_instructor: Whether the user is an instructor
            
        Returns:
            str: JWT access token
        """
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "is_instructor": is_instructor,
            "exp": expire,
            "iat": datetime.utcnow(),  # Issued at
            "type": "access"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str) -> str:
        """
        Create a JWT refresh token for a user.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            str: JWT refresh token
        """
        expire = datetime.utcnow() + timedelta(days=7)  # Refresh tokens last longer
        
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Optional[Dict[str, Any]]: Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except JWTError:
            return None
    
    def is_rate_limited(self, email: str) -> bool:
        """
        Check if a user is rate limited for login attempts.
        
        Args:
            email: User's email address
            
        Returns:
            bool: True if rate limited, False otherwise
        """
        if email not in self._login_attempts:
            return False
        
        # Clean up old attempts
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.lockout_duration_minutes)
        self._login_attempts[email] = [
            attempt for attempt in self._login_attempts[email] 
            if attempt > cutoff_time
        ]
        
        return len(self._login_attempts[email]) >= self.max_login_attempts
    
    def record_login_attempt(self, email: str, success: bool):
        """
        Record a login attempt for rate limiting.
        
        Args:
            email: User's email address
            success: Whether the login was successful
        """
        if success:
            # Clear failed attempts on successful login
            if email in self._login_attempts:
                del self._login_attempts[email]
        else:
            # Record failed attempt
            if email not in self._login_attempts:
                self._login_attempts[email] = []
            self._login_attempts[email].append(datetime.utcnow())
    
    async def register_user(
        self, 
        email: str, 
        password: str, 
        display_name: str, 
        is_instructor: bool = False
    ) -> Optional[User]:
        """
        Register a new user.
        
        Args:
            email: User's email address
            password: Plain text password
            display_name: User's display name
            is_instructor: Whether the user should have instructor privileges
            
        Returns:
            Optional[User]: Created user if successful, None if email already exists
            
        Raises:
            ValueError: If input validation fails
        """
        # Validate input
        if not email or not email.strip():
            raise ValueError("Email is required")
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not display_name or not display_name.strip():
            raise ValueError("Display name is required")
        
        # Check if user already exists
        if User.objects.filter(email=email.lower().strip()).exists():
            return None  # User already exists
        
        try:
            # Create new user using Django's create_user method
            user = User.objects.create_user(
                username=email.lower().strip(),  # Use email as username
                email=email.lower().strip(),
                password=password,  # Django will hash this automatically
                display_name=display_name.strip(),
                is_instructor=is_instructor
            )
            
            return user
            
        except IntegrityError:
            return None  # Email constraint violation
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            Optional[User]: User if authentication successful, None otherwise
        """
        email = email.lower().strip()
        
        # Check rate limiting
        if self.is_rate_limited(email):
            self.record_login_attempt(email, False)
            return None
        
        # Find user
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            self.record_login_attempt(email, False)
            return None
        
        # Use Django's authenticate with username (which is email in our case)
        authenticated_user = authenticate(username=user.username, password=password)
        
        if not authenticated_user:
            self.record_login_attempt(email, False)
            return None
        
        # Successful authentication
        self.record_login_attempt(email, True)
        return authenticated_user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get a user by their ID.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            Optional[User]: User if found and active, None otherwise
        """
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return None
    
    async def update_user_profile(
        self, 
        user_id: str, 
        display_name: Optional[str] = None,
        new_password: Optional[str] = None
    ) -> Optional[User]:
        """
        Update a user's profile information.
        
        Args:
            user_id: User's unique identifier
            display_name: New display name (optional)
            new_password: New password (optional)
            
        Returns:
            Optional[User]: Updated user if successful, None if user not found
            
        Raises:
            ValueError: If input validation fails
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Update display name if provided
        if display_name is not None:
            if not display_name.strip():
                raise ValueError("Display name cannot be empty")
            user.display_name = display_name.strip()
        
        # Update password if provided
        if new_password is not None:
            if len(new_password) < 8:
                raise ValueError("Password must be at least 8 characters long")
            user.set_password(new_password)  # Django's method to hash and set password
        
        user.save()
        return user
    
    async def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user account (soft delete).
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            bool: True if successful, False if user not found
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        user.save()
        return True