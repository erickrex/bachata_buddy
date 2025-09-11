#!/usr/bin/env python3
"""
Development server that bypasses system requirements for testing authentication UI.
"""

import logging
import os
import socket
from pathlib import Path
from contextlib import asynccontextmanager

# Set environment variable to skip system validation
os.environ["SKIP_SYSTEM_VALIDATION"] = "true"

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError as PydanticValidationError
import uvicorn

from app.config import get_settings
from app.database import init_database
from app.services.authentication_service import AuthenticationService
from app.services.collection_service import CollectionService
from app.services.instructor_dashboard_service import InstructorDashboardService
from app.middleware.auth_middleware import AuthMiddleware, set_auth_middleware
from app.controllers import (
    AuthController,
    ChoreographyController,
    CollectionController,
    InstructorController,
    MediaController
)
from app.exceptions import (
    ChoreographyGenerationError, YouTubeDownloadError, MusicAnalysisError,
    VideoGenerationError, ValidationError, ResourceError, ServiceUnavailableError,
    choreography_exception_handler, validation_exception_handler, 
    http_exception_handler, general_exception_handler
)

# Get application settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.get_log_level()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("🚀 Starting Development Server (System validation bypassed)")

def find_free_port(start_port=8000, max_attempts=10):
    """Find a free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Bachata Choreography Generator API (Development Mode)")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_database()
        logger.info("Database initialized successfully")
        
        # Ensure required directories exist
        directories = [
            "app/static",
            "app/templates", 
            "data/temp",
            "data/output",
            "data/cache"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        logger.info("Development server startup complete - authentication system ready")
        logger.info(f"Authentication service initialized with JWT algorithm: {settings.jwt_algorithm}")
        logger.info(f"Access token expiration: {settings.access_token_expire_minutes} minutes")
        logger.info("⚠️  System validation bypassed for development")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down development server")

app = FastAPI(
    title="Bachata Choreography Generator - Development",
    description="AI-powered Bachata choreography generator (Development Mode)",
    version="0.1.0-dev",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(ChoreographyGenerationError, choreography_exception_handler)
app.add_exception_handler(PydanticValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize authentication service
auth_service = AuthenticationService(
    jwt_secret=settings.jwt_secret_key,
    jwt_algorithm=settings.jwt_algorithm,
    access_token_expire_minutes=settings.access_token_expire_minutes
)

# Initialize authentication middleware
auth_middleware_instance = AuthMiddleware(auth_service)
set_auth_middleware(auth_middleware_instance)

# Initialize services
collection_service = CollectionService(storage_base_path="data")
instructor_service = InstructorDashboardService()

# Initialize controllers
auth_controller = AuthController(auth_service)
choreography_controller = ChoreographyController()
collection_controller = CollectionController(collection_service)
instructor_controller = InstructorController(instructor_service)
media_controller = MediaController()

# Register controller routes
app.include_router(auth_controller.get_router())
app.include_router(choreography_controller.get_router())
app.include_router(collection_controller.get_router())
app.include_router(instructor_controller.get_router())
app.include_router(media_controller.get_router())



if __name__ == "__main__":
    # Find available port
    port = find_free_port()
    if port is None:
        print("❌ Could not find an available port. Please check if other servers are running.")
        exit(1)
    
    print("🎯 Development Server for Authentication UI Testing")
    print("📝 This server bypasses system requirements validation")
    print(f"🌐 Access the application at: http://localhost:{port}")
    print("🔐 Test the authentication UI components")
    if port != 8000:
        print(f"⚠️  Using port {port} instead of 8000 (port was busy)")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)