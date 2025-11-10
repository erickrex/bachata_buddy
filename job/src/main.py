"""
Blueprint-Based Video Assembly Job

This job is triggered by the Django API via Cloud Run Jobs.
It receives a pre-computed blueprint and assembles the final video.

The blueprint contains all video generation instructions including:
- Song audio path
- Video clip paths and timing
- Transitions and effects
- Output configuration

This simplified architecture removes all intelligence from the job container,
making it a lightweight video assembly service.

Exit Codes:
- 0: Success - Video assembled and uploaded successfully
- 1: Failure - Any error during processing (validation, assembly, upload, etc.)

Error Handling:
- All major operations wrapped in try-catch blocks
- Structured logging with error context
- Database updates include error messages
- Storage operations include automatic retry (3 attempts with exponential backoff)
- FFmpeg operations include timeout protection
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Initialize logger
logger = logging.getLogger(__name__)


def configure_logging(log_level: str = 'INFO'):
    """
    Configure structured logging for the job
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    
    logger.info(
        "Logging configured",
        extra={
            'log_level': log_level,
            'timestamp': datetime.utcnow().isoformat()
        }
    )


def validate_required_env_vars():
    """Validate that all required environment variables are present"""
    required_vars = {
        # Blueprint (required)
        'BLUEPRINT_JSON': 'Complete blueprint JSON with video assembly instructions',
        
        # Database configuration
        'DB_HOST': 'Database host',
        'DB_PORT': 'Database port',
        'DB_NAME': 'Database name',
        'DB_USER': 'Database user',
        'DB_PASSWORD': 'Database password',
    }
    
    missing_vars = []
    for var_name, description in required_vars.items():
        if not os.environ.get(var_name):
            missing_vars.append(f"  - {var_name}: {description}")
    
    if missing_vars:
        logger.error(
            "Missing required environment variables",
            extra={
                'missing_count': len(missing_vars),
                'missing_vars': [var.split(':')[0].strip('- ') for var in missing_vars],
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        print("ERROR: Missing required environment variables:")
        print("\n".join(missing_vars))
        print("\nPlease ensure all required environment variables are set.")
        print("See .env.example for a complete list of required variables.")
        return False
    
    logger.info(
        "Environment variables validated successfully",
        extra={
            'validated_count': len(required_vars),
            'timestamp': datetime.utcnow().isoformat()
        }
    )
    return True


def get_env_config():
    """Get all environment configuration"""
    config = {
        # Blueprint JSON
        'blueprint_json': os.environ.get('BLUEPRINT_JSON'),
        
        # Database configuration
        'db_host': os.environ.get('DB_HOST'),
        'db_port': os.environ.get('DB_PORT', '5432'),
        'db_name': os.environ.get('DB_NAME'),
        'db_user': os.environ.get('DB_USER'),
        'db_password': os.environ.get('DB_PASSWORD'),
        'cloud_sql_connection_name': os.environ.get('CLOUD_SQL_CONNECTION_NAME'),
        
        # Storage configuration
        'use_gcs': os.environ.get('USE_GCS', 'false').lower() == 'true',
        'gcs_bucket_name': os.environ.get('GCS_BUCKET_NAME', ''),
        'gcp_project_id': os.environ.get('GCP_PROJECT_ID', ''),
        
        # Logging configuration
        'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
    }
    
    return config


class BlueprintVideoAssembler:
    """
    Assembles videos from pre-computed blueprints.
    
    This class is responsible for:
    1. Parsing and validating blueprint JSON
    2. Fetching media files from storage
    3. Assembling video with FFmpeg
    4. Uploading result to storage
    5. Updating database with status
    """
    
    def __init__(self, blueprint: Dict[str, Any], config: Dict[str, Any]):
        """
        Initialize the video assembler.
        
        Args:
            blueprint: Parsed blueprint dictionary
            config: Environment configuration
        """
        self.blueprint = blueprint
        self.config = config
        self.task_id = blueprint.get('task_id')
        
        # Import services
        from services.database import update_task_status, close_connection_pool
        self.update_task_status = update_task_status
        self.close_connection_pool = close_connection_pool
    
    def validate_blueprint(self) -> tuple[bool, Optional[str]]:
        """
        Validate blueprint schema and required fields.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.info("Validating blueprint schema")
        
        # Check required top-level fields
        required_fields = ['task_id', 'audio_path', 'moves', 'output_config']
        for field in required_fields:
            if field not in self.blueprint:
                error = f"Missing required field: {field}"
                logger.error(error)
                return False, error
        
        # Validate task_id
        if not self.blueprint['task_id']:
            error = "task_id cannot be empty"
            logger.error(error)
            return False, error
        
        # Validate audio_path
        audio_path = self.blueprint.get('audio_path', '')
        if not audio_path:
            error = "audio_path cannot be empty"
            logger.error(error)
            return False, error
        
        # Security: Validate no directory traversal in audio path
        if '..' in audio_path or audio_path.startswith('/'):
            error = f"Invalid audio_path (security): {audio_path}"
            logger.error(error)
            return False, error
        
        # Validate moves array
        moves = self.blueprint.get('moves', [])
        if not isinstance(moves, list):
            error = "moves must be an array"
            logger.error(error)
            return False, error
        
        if len(moves) == 0:
            error = "moves array cannot be empty"
            logger.error(error)
            return False, error
        
        # Validate each move
        for i, move in enumerate(moves):
            if not isinstance(move, dict):
                error = f"Move {i} is not an object"
                logger.error(error)
                return False, error
            
            # Check required move fields
            required_move_fields = ['video_path', 'start_time', 'duration']
            for field in required_move_fields:
                if field not in move:
                    error = f"Move {i} missing required field: {field}"
                    logger.error(error)
                    return False, error
            
            # Security: Validate no directory traversal in video paths
            video_path = move.get('video_path', '')
            if '..' in video_path or video_path.startswith('/'):
                error = f"Invalid video_path in move {i} (security): {video_path}"
                logger.error(error)
                return False, error
        
        # Validate output_config
        output_config = self.blueprint.get('output_config', {})
        if not isinstance(output_config, dict):
            error = "output_config must be an object"
            logger.error(error)
            return False, error
        
        if 'output_path' not in output_config:
            error = "output_config missing required field: output_path"
            logger.error(error)
            return False, error
        
        # Security: Validate no directory traversal in output path
        output_path = output_config.get('output_path', '')
        if '..' in output_path or output_path.startswith('/'):
            error = f"Invalid output_path (security): {output_path}"
            logger.error(error)
            return False, error
        
        logger.info(
            "Blueprint validation successful",
            extra={
                'task_id': self.task_id,
                'moves_count': len(moves),
                'audio_path': audio_path,
                'output_path': output_path
            }
        )
        
        return True, None
    
    def process(self) -> int:
        """
        Process the blueprint and generate video.
        
        Includes comprehensive error handling with:
        - Try-catch blocks for all major operations
        - Structured logging with error context
        - Database updates with error messages
        - Appropriate exit codes
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            # Step 1: Validate blueprint
            print("\n" + "-" * 80)
            print("Step 1: Validating Blueprint")
            print("-" * 80)
            
            try:
                is_valid, error_message = self.validate_blueprint()
                if not is_valid:
                    print(f"❌ Blueprint validation failed: {error_message}")
                    logger.error(
                        f"Blueprint validation failed",
                        extra={
                            'task_id': self.task_id,
                            'error_message': error_message
                        }
                    )
                    
                    # Update database with validation error
                    try:
                        self.update_task_status(
                            task_id=self.task_id,
                            status='failed',
                            progress=0,
                            stage='validation',
                            message=f'Blueprint validation failed: {error_message}',
                            error=error_message
                        )
                    except Exception as db_error:
                        logger.error(
                            f"Failed to update database with validation error",
                            extra={
                                'task_id': self.task_id,
                                'db_error': str(db_error)
                            }
                        )
                    
                    return 1
                
                print("✅ Blueprint validated successfully")
                print(f"   Task ID: {self.task_id}")
                print(f"   Moves: {len(self.blueprint['moves'])}")
                print(f"   Audio: {self.blueprint['audio_path']}")
                
            except Exception as e:
                error_msg = f"Unexpected error during blueprint validation: {str(e)}"
                print(f"❌ {error_msg}")
                logger.error(
                    error_msg,
                    extra={
                        'task_id': self.task_id,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    },
                    exc_info=True
                )
                
                try:
                    self.update_task_status(
                        task_id=self.task_id,
                        status='failed',
                        progress=0,
                        stage='validation',
                        message=error_msg,
                        error=str(e)
                    )
                except Exception:
                    pass
                
                return 1
            
            # Step 2: Update status to running
            print("\n" + "-" * 80)
            print("Step 2: Updating Task Status")
            print("-" * 80)
            
            try:
                self.update_task_status(
                    task_id=self.task_id,
                    status='running',
                    progress=10,
                    stage='assembling',
                    message='Blueprint validated, starting video assembly...'
                )
                print("✅ Task status updated to 'running'")
            except Exception as e:
                error_msg = f"Failed to update task status to running: {str(e)}"
                print(f"⚠️  {error_msg}")
                logger.warning(
                    error_msg,
                    extra={
                        'task_id': self.task_id,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                )
                # Continue processing even if status update fails
            
            # Step 3: Initialize storage service
            print("\n" + "-" * 80)
            print("Step 3: Initializing Storage Service")
            print("-" * 80)
            
            try:
                from services.storage_service import StorageService, StorageConfig
                
                storage_config = StorageConfig(
                    bucket_name=self.config.get('gcs_bucket_name', 'bachata-buddy-videos'),
                    project_id=self.config.get('gcp_project_id'),
                    use_local_storage=not self.config.get('use_gcs', False),
                    local_storage_path=os.environ.get('LOCAL_STORAGE_PATH', '/app/data')
                )
                
                storage_service = StorageService(config=storage_config)
                print("✅ Storage service initialized")
                print(f"   Mode: {'Google Cloud Storage' if self.config.get('use_gcs') else 'Local filesystem'}")
                
            except Exception as e:
                error_msg = f"Failed to initialize storage service: {str(e)}"
                print(f"❌ {error_msg}")
                logger.error(
                    error_msg,
                    extra={
                        'task_id': self.task_id,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    },
                    exc_info=True
                )
                
                try:
                    self.update_task_status(
                        task_id=self.task_id,
                        status='failed',
                        progress=0,
                        stage='initialization',
                        message=error_msg,
                        error=str(e)
                    )
                except Exception:
                    pass
                
                return 1
            
            # Step 4: Initialize video assembler
            print("\n" + "-" * 80)
            print("Step 4: Initializing Video Assembler")
            print("-" * 80)
            
            try:
                from services.video_assembler import VideoAssembler
                
                video_assembler = VideoAssembler(storage_service=storage_service)
                
                # Check FFmpeg availability
                if not video_assembler.check_ffmpeg_available():
                    error_msg = "FFmpeg not found or not executable"
                    print(f"❌ {error_msg}")
                    logger.error(
                        error_msg,
                        extra={
                            'task_id': self.task_id
                        }
                    )
                    
                    try:
                        self.update_task_status(
                            task_id=self.task_id,
                            status='failed',
                            progress=0,
                            stage='initialization',
                            message=error_msg,
                            error='FFmpeg executable not found in system PATH'
                        )
                    except Exception:
                        pass
                    
                    return 1
                
                print("✅ Video assembler initialized")
                print("✅ FFmpeg is available")
                
            except Exception as e:
                error_msg = f"Failed to initialize video assembler: {str(e)}"
                print(f"❌ {error_msg}")
                logger.error(
                    error_msg,
                    extra={
                        'task_id': self.task_id,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    },
                    exc_info=True
                )
                
                try:
                    self.update_task_status(
                        task_id=self.task_id,
                        status='failed',
                        progress=0,
                        stage='initialization',
                        message=error_msg,
                        error=str(e)
                    )
                except Exception:
                    pass
                
                return 1
            
            # Step 5: Assemble video
            print("\n" + "-" * 80)
            print("Step 5: Assembling Video")
            print("-" * 80)
            
            try:
                def progress_callback(stage: str, progress: int, message: str):
                    """Update task status with progress"""
                    print(f"   [{progress}%] {message}")
                    try:
                        self.update_task_status(
                            task_id=self.task_id,
                            status='running',
                            progress=progress,
                            stage=stage,
                            message=message
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to update progress",
                            extra={
                                'task_id': self.task_id,
                                'stage': stage,
                                'progress': progress,
                                'error': str(e)
                            }
                        )
                
                result_url = video_assembler.assemble_video(
                    blueprint=self.blueprint,
                    progress_callback=progress_callback
                )
                
                print(f"✅ Video assembled successfully")
                print(f"   Result: {result_url}")
                
            except Exception as e:
                error_msg = f"Video assembly failed: {str(e)}"
                print(f"❌ {error_msg}")
                logger.error(
                    error_msg,
                    extra={
                        'task_id': self.task_id,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    },
                    exc_info=True
                )
                
                try:
                    self.update_task_status(
                        task_id=self.task_id,
                        status='failed',
                        progress=0,
                        stage='assembly',
                        message=error_msg,
                        error=str(e)
                    )
                except Exception as db_error:
                    logger.error(
                        f"Failed to update database with assembly error",
                        extra={
                            'task_id': self.task_id,
                            'db_error': str(db_error)
                        }
                    )
                
                return 1
            
            # Step 6: Update task to completed
            print("\n" + "-" * 80)
            print("Step 6: Finalizing")
            print("-" * 80)
            
            try:
                # Get file size if available
                output_path = self.blueprint.get('output_config', {}).get('output_path')
                file_size = None
                
                if storage_config.use_local_storage and output_path:
                    full_path = os.path.join(storage_config.local_storage_path, output_path)
                    if os.path.exists(full_path):
                        file_size = os.path.getsize(full_path)
                
                self.update_task_status(
                    task_id=self.task_id,
                    status='completed',
                    progress=100,
                    stage='completed',
                    message='Video assembly completed successfully',
                    result={
                        'video_url': result_url,
                        'output_path': output_path,
                        'moves_count': len(self.blueprint['moves']),
                        'file_size': file_size
                    }
                )
                
                print("✅ Task completed successfully")
                logger.info(
                    f"Task completed successfully",
                    extra={
                        'task_id': self.task_id,
                        'result_url': result_url,
                        'file_size': file_size
                    }
                )
                
                return 0
                
            except Exception as e:
                error_msg = f"Failed to finalize task: {str(e)}"
                print(f"⚠️  {error_msg}")
                logger.warning(
                    error_msg,
                    extra={
                        'task_id': self.task_id,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                )
                # Video was assembled successfully, so return success even if final update fails
                return 0
            
        except Exception as e:
            # Catch-all for any unexpected errors
            error_msg = f"Unexpected error during blueprint processing: {str(e)}"
            print(f"\n❌ FATAL ERROR: {error_msg}")
            logger.critical(
                error_msg,
                extra={
                    'task_id': self.task_id,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            
            try:
                self.update_task_status(
                    task_id=self.task_id,
                    status='failed',
                    progress=0,
                    stage='failed',
                    message=error_msg,
                    error=str(e),
                    result={'error': str(e), 'error_type': type(e).__name__}
                )
            except Exception as db_error:
                logger.error(
                    f"Failed to update database with fatal error",
                    extra={
                        'task_id': self.task_id,
                        'db_error': str(db_error)
                    }
                )
            
            return 1


def main():
    """Main entry point for the blueprint-based video assembly job"""
    print("=" * 80)
    print("Blueprint Video Assembly Job - Starting")
    print("=" * 80)
    
    # Configure logging first (before any other operations)
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    configure_logging(log_level)
    
    logger.info(
        "Job started",
        extra={
            'timestamp': datetime.utcnow().isoformat(),
            'log_level': log_level
        }
    )
    
    # Validate required environment variables
    if not validate_required_env_vars():
        logger.critical(
            "Job failed: Missing required environment variables",
            extra={
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        print("\nJob failed: Missing required environment variables")
        return 1
    
    # Get configuration from environment variables
    config = get_env_config()
    
    # Parse blueprint JSON
    print("\n" + "-" * 80)
    print("Parsing Blueprint JSON")
    print("-" * 80)
    
    try:
        blueprint = json.loads(config['blueprint_json'])
        task_id = blueprint.get('task_id', 'unknown')
        
        logger.info(
            "Blueprint parsed successfully",
            extra={
                'task_id': task_id,
                'blueprint_size': len(config['blueprint_json']),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
        print(f"✅ Blueprint parsed successfully")
        print(f"   Task ID: {task_id}")
        print(f"   Blueprint size: {len(config['blueprint_json'])} bytes")
        
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse blueprint JSON: {str(e)}",
            extra={
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        print(f"\n❌ ERROR: Failed to parse blueprint JSON: {str(e)}")
        print("Please ensure BLUEPRINT_JSON is valid JSON")
        return 1
    except Exception as e:
        logger.error(
            f"Unexpected error parsing blueprint: {str(e)}",
            extra={
                'error_type': type(e).__name__,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        print(f"\n❌ ERROR: Unexpected error parsing blueprint: {str(e)}")
        return 1
    
    # Log configuration (excluding sensitive data)
    print("\nJob Configuration:")
    print(f"  Task ID: {task_id}")
    print(f"\nDatabase:")
    print(f"  Host: {config['db_host']}")
    print(f"  Port: {config['db_port']}")
    print(f"  Name: {config['db_name']}")
    print(f"  User: {config['db_user']}")
    print(f"\nStorage:")
    print(f"  Mode: {'Google Cloud Storage' if config['use_gcs'] else 'Local filesystem'}")
    if config['use_gcs']:
        print(f"  GCS Bucket: {config['gcs_bucket_name']}")
        print(f"  GCP Project: {config['gcp_project_id']}")
    print(f"\nLog Level: {config['log_level']}")
    print("=" * 80)
    
    # Import database service
    try:
        from services.database import close_connection_pool
    except ImportError as e:
        logger.error(f"Failed to import database service: {e}")
        print(f"\n❌ ERROR: Failed to import database service: {e}")
        return 1
    
    # Database connection will be tested when we make the first update_task_status call
    logger.info("Database service imported successfully")
    
    # Initialize and run the video assembler
    print("\n" + "=" * 80)
    print("Starting Blueprint Video Assembly")
    print("=" * 80)
    
    try:
        assembler = BlueprintVideoAssembler(blueprint=blueprint, config=config)
        exit_code = assembler.process()
        
        # Close database connection pool
        close_connection_pool()
        
        if exit_code == 0:
            logger.info(
                "Job completed successfully",
                extra={
                    'task_id': task_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
            print("\n" + "=" * 80)
            print("Job completed successfully")
            print("=" * 80)
        else:
            logger.error(
                "Job failed",
                extra={
                    'task_id': task_id,
                    'exit_code': exit_code,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
            print("\n" + "=" * 80)
            print("Job failed")
            print("=" * 80)
        
        return exit_code
        
    except Exception as e:
        # Handle unexpected exceptions
        logger.critical(
            f"Job execution failed with unexpected exception: {str(e)}",
            extra={
                'task_id': task_id,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            },
            exc_info=True
        )
        
        print(f"\n❌ FATAL ERROR: Job execution failed: {str(e)}")
        
        # Try to close database connection pool
        try:
            close_connection_pool()
        except Exception:
            pass
        
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        # Log any uncaught exceptions
        logger.critical(
            f"Job failed with uncaught exception: {str(e)}",
            extra={
                'error_type': type(e).__name__,
                'error_message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            },
            exc_info=True
        )
        print(f"\nFATAL ERROR: {str(e)}")
        sys.exit(1)
