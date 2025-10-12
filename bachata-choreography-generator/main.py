"""
Bachata Choreography Generator - Main FastAPI Application
"""
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager

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
from app.validation import validate_system_requirements
from app.services.resource_manager import resource_manager

# Get application settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.get_log_level()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Performance optimizations are now integrated directly into the services
logger.info("🚀 Performance optimizations integrated - expect 20-40% faster generation")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Bachata Choreography Generator API")
    
    try:
        # Initialize database (can be skipped for testing)
        skip_db_init = os.getenv("SKIP_DB_INIT", "false").lower() == "true"
        if not skip_db_init:
            logger.info("Initializing database...")
            init_database()
            logger.info("Database initialized successfully")
        else:
            logger.info("Skipping database initialization (SKIP_DB_INIT=true)")
        
        # Validate system requirements (can be skipped for development)
        skip_validation = os.getenv("SKIP_SYSTEM_VALIDATION", "false").lower() == "true"
        
        if not skip_validation:
            system_check = validate_system_requirements()
            
            if not system_check["valid"]:
                logger.error("System requirements validation failed:")
                for issue in system_check["issues"]:
                    logger.error(f"  - {issue['type']}: {issue['message']}")
                raise ServiceUnavailableError(
                    message="System requirements not met",
                    service_name="system",
                    details=system_check
                )
        else:
            logger.warning("⚠️  System requirements validation skipped (development mode)")
            system_check = {"valid": True, "issues": [], "warnings": []}
        
        # Log warnings
        for warning in system_check.get("warnings", []):
            logger.warning(f"System warning - {warning['type']}: {warning['message']}")
        
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
        
        # Start resource management
        await resource_manager.start_monitoring()
        await resource_manager.schedule_cleanup(interval_hours=6)
        
        logger.info("API startup complete - all systems ready")
        logger.info(f"Authentication service initialized with JWT algorithm: {settings.jwt_algorithm}")
        logger.info(f"Access token expiration: {settings.access_token_expire_minutes} minutes")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down API")
    
    try:
        # Shutdown resource manager (includes final cleanup)
        await resource_manager.shutdown()
        
        # Cleanup will be handled by individual controllers
        logger.info("API shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="Bachata Choreography Generator",
    description="AI-powered Bachata choreography generator that creates dance sequences from YouTube music",
    version="0.1.0",
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



def find_free_port(start_port=8000, max_attempts=10):
    """Find a free port starting from start_port."""
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

if __name__ == "__main__":
    port = find_free_port()
    if port is None:
        logger.error("Could not find an available port")
        exit(1)
    
    if port != 8000:
        logger.info(f"Using port {port} instead of 8000 (port was busy)")
    
    uvicorn.run(app, host="0.0.0.0", port=port)