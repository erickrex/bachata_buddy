"""
Configuration settings for the Bachata Choreography Generator.
"""

import os
import secrets
from typing import Optional


class Settings:
    """Application settings and configuration."""
    
    def __init__(self):
        """Initialize settings from environment variables with defaults."""
        
        # JWT Configuration
        self.jwt_secret_key: str = os.getenv(
            "JWT_SECRET_KEY", 
            "dev-secret-key-for-bachata-choreography-generator-change-in-production"
        )
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )
        
        # Database Configuration
        self.database_url: str = os.getenv(
            "DATABASE_URL", 
            "sqlite:///data/database.db"
        )
        
        # Application Configuration
        self.app_name: str = os.getenv("APP_NAME", "Bachata Choreography Generator")
        self.app_version: str = os.getenv("APP_VERSION", "0.1.0")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        
        # CORS Configuration
        self.cors_origins: list = self._parse_cors_origins(
            os.getenv("CORS_ORIGINS", "*")
        )
        
        # Rate Limiting Configuration
        self.max_login_attempts: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.lockout_duration_minutes: int = int(
            os.getenv("LOCKOUT_DURATION_MINUTES", "15")
        )
        
        # File Storage Configuration
        self.upload_max_size_mb: int = int(os.getenv("UPLOAD_MAX_SIZE_MB", "100"))
        self.temp_file_cleanup_hours: int = int(
            os.getenv("TEMP_FILE_CLEANUP_HOURS", "24")
        )
        
        # Security Configuration
        self.password_min_length: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
        self.require_email_verification: bool = os.getenv(
            "REQUIRE_EMAIL_VERIFICATION", "false"
        ).lower() == "true"
    
    def _generate_secret_key(self) -> str:
        """
        Generate a secure random secret key for JWT tokens.
        
        Returns:
            str: Secure random secret key
        """
        return secrets.token_urlsafe(32)
    
    def _parse_cors_origins(self, origins_str: str) -> list:
        """
        Parse CORS origins from environment variable.
        
        Args:
            origins_str: Comma-separated list of origins or "*"
            
        Returns:
            list: List of allowed origins
        """
        if origins_str == "*":
            return ["*"]
        
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]
    
    def get_database_url(self) -> str:
        """
        Get the database URL for SQLAlchemy.
        
        Returns:
            str: Database connection URL
        """
        return self.database_url
    
    def is_production(self) -> bool:
        """
        Check if the application is running in production mode.
        
        Returns:
            bool: True if in production, False otherwise
        """
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    def get_log_level(self) -> str:
        """
        Get the logging level for the application.
        
        Returns:
            str: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        if self.debug:
            return "DEBUG"
        return os.getenv("LOG_LEVEL", "INFO").upper()


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    Returns:
        Settings: Application settings
    """
    return settings