"""
Simplified database service for blueprint-based video processing job

This module provides minimal database functionality for the job container:
- Connection pooling for efficient database access
- Task status updates only (no complex queries)
- Automatic retry logic for transient errors
- Support for both local (TCP/IP) and Cloud Run (Unix socket) connections

CRITICAL: This job writes directly to the existing 'choreography_tasks' table
using the same schema as the backend API for compatibility.
"""
import os
import logging
import psycopg2
import psycopg2.pool
import json
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
RETRY_BACKOFF = 2.0  # exponential backoff multiplier

# Global connection pool
_connection_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None


def retry_on_db_error(max_retries: int = MAX_RETRIES, 
                      delay: float = RETRY_DELAY,
                      backoff: float = RETRY_BACKOFF):
    """
    Decorator to retry database operations on transient errors
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for exponential backoff
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (psycopg2.OperationalError, 
                        psycopg2.InterfaceError,
                        psycopg2.DatabaseError) as e:
                    last_exception = e
                    
                    # Don't retry on last attempt
                    if attempt >= max_retries:
                        logger.error(
                            f"Database operation failed after {max_retries} retries",
                            extra={
                                'function': func.__name__,
                                'error': str(e),
                                'error_type': type(e).__name__,
                                'attempts': attempt + 1
                            }
                        )
                        break
                    
                    # Log retry attempt
                    logger.warning(
                        f"Database operation failed, retrying in {current_delay}s",
                        extra={
                            'function': func.__name__,
                            'error': str(e),
                            'error_type': type(e).__name__,
                            'attempt': attempt + 1,
                            'max_retries': max_retries,
                            'delay': current_delay
                        }
                    )
                    
                    # Wait before retry
                    time.sleep(current_delay)
                    
                    # Exponential backoff
                    current_delay *= backoff
                    
                    # Reset connection pool on connection errors
                    if isinstance(e, (psycopg2.OperationalError, psycopg2.InterfaceError)):
                        _reset_connection_pool()
                
                except Exception as e:
                    # Don't retry on non-database errors
                    logger.error(
                        f"Non-retryable error in database operation",
                        extra={
                            'function': func.__name__,
                            'error': str(e),
                            'error_type': type(e).__name__
                        }
                    )
                    raise
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper
    return decorator


def _reset_connection_pool():
    """
    Reset the connection pool (close all connections and recreate)
    
    This is called when connection errors occur to ensure we get fresh connections
    """
    global _connection_pool
    
    if _connection_pool:
        try:
            _connection_pool.closeall()
            logger.info("Connection pool closed for reset")
        except Exception as e:
            logger.warning(f"Error closing connection pool: {e}")
        finally:
            _connection_pool = None


@retry_on_db_error()
def get_db_connection():
    """
    Get a database connection from the pool with automatic retry
    
    Supports two connection modes:
    1. Local Development: TCP/IP connection to PostgreSQL in Docker
    2. Cloud Run Production: Unix socket connection to Cloud SQL
    
    Returns:
        psycopg2.connection: Database connection
        
    Raises:
        psycopg2.Error: If connection fails after retries
    """
    global _connection_pool
    
    # Initialize connection pool if not already created
    if _connection_pool is None:
        _connection_pool = _create_connection_pool()
    
    try:
        # Get connection from pool
        conn = _connection_pool.getconn()
        
        # Test connection is alive
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        except psycopg2.Error:
            # Connection is dead, close it and get a new one
            try:
                _connection_pool.putconn(conn, close=True)
            except Exception:
                pass
            raise psycopg2.OperationalError("Connection test failed")
        
        logger.debug("Database connection acquired from pool")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Failed to get database connection: {e}")
        raise


def _create_connection_pool():
    """
    Create a connection pool for database connections
    
    Returns:
        psycopg2.pool.ThreadedConnectionPool: Connection pool
    """
    # Get database configuration from environment
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    cloud_sql_connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
    
    # Determine connection mode
    is_cloud_run = os.environ.get('K_SERVICE') is not None
    
    # Build connection parameters
    if is_cloud_run and cloud_sql_connection_name:
        # Cloud Run: Use Unix socket connection to Cloud SQL
        connection_params = {
            'dbname': db_name,
            'user': db_user,
            'password': db_password,
            'host': f'/cloudsql/{cloud_sql_connection_name}',
        }
        logger.info(
            f"Creating Cloud SQL connection pool (Unix socket)",
            extra={
                'db_name': db_name,
                'db_user': db_user,
                'connection_name': cloud_sql_connection_name
            }
        )
    else:
        # Local development: Use TCP/IP connection
        connection_params = {
            'dbname': db_name,
            'user': db_user,
            'password': db_password,
            'host': db_host,
            'port': db_port,
        }
        logger.info(
            f"Creating PostgreSQL connection pool (TCP/IP)",
            extra={
                'db_name': db_name,
                'db_user': db_user,
                'db_host': db_host,
                'db_port': db_port
            }
        )
    
    # Add connection timeout
    connection_params['connect_timeout'] = 10
    
    try:
        # Create connection pool (min 1, max 5 connections)
        pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            **connection_params
        )
        logger.info("Database connection pool created successfully")
        return pool
    except psycopg2.Error as e:
        logger.error(f"Failed to create connection pool: {e}")
        raise


@contextmanager
def get_db_cursor():
    """
    Context manager for database cursor with automatic connection management and error handling
    
    Usage:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM table")
            results = cursor.fetchall()
    
    Yields:
        psycopg2.cursor: Database cursor
        
    Raises:
        psycopg2.Error: If database operation fails
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except psycopg2.Error as e:
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
        
        logger.error(
            f"Database operation failed",
            extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'error_code': e.pgcode if hasattr(e, 'pgcode') else None
            }
        )
        raise
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
        
        logger.error(f"Unexpected error in database operation: {e}")
        raise
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                logger.warning(f"Error closing cursor: {e}")
        
        if conn and _connection_pool:
            try:
                _connection_pool.putconn(conn)
                logger.debug("Database connection returned to pool")
            except Exception as e:
                logger.warning(f"Error returning connection to pool: {e}")


@retry_on_db_error()
def update_task_status(
    task_id: str,
    status: str,
    progress: int = 0,
    stage: str = '',
    message: str = '',
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> bool:
    """
    Update choreography task status in the database with automatic retry
    
    CRITICAL: This function writes to the 'choreography_tasks' table using
    the same schema as the original app for compatibility during migration.
    
    This function includes automatic retry logic for transient database errors:
    - Connection failures
    - Temporary network issues
    - Database unavailability
    
    Args:
        task_id: Task ID (UUID string)
        status: Task status ('started', 'running', 'completed', 'failed')
        progress: Progress percentage (0-100)
        stage: Current processing stage
        message: User-friendly status message
        result: Final result data (JSON)
        error: Error message if failed
        
    Returns:
        bool: True if update successful, False if task not found
        
    Raises:
        ValueError: If status or progress is invalid
        psycopg2.Error: If database operation fails after retries
    """
    # Validate status value (must match original app's choices)
    valid_statuses = ['started', 'running', 'completed', 'failed']
    if status not in valid_statuses:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Validate progress range
    if not 0 <= progress <= 100:
        raise ValueError(f"Progress must be between 0 and 100, got {progress}")
    
    logger.info(
        f"Updating task status",
        extra={
            'task_id': task_id,
            'status': status,
            'progress': progress,
            'stage': stage,
            'timestamp': datetime.utcnow().isoformat()
        }
    )
    
    try:
        with get_db_cursor() as cursor:
            # Build UPDATE query
            # CRITICAL: Table name MUST be 'choreography_tasks' to match original
            query = """
                UPDATE choreography_tasks
                SET 
                    status = %s,
                    progress = %s,
                    stage = %s,
                    message = %s,
                    result = %s,
                    error = %s,
                    updated_at = NOW()
                WHERE task_id = %s
            """
            
            # Convert result dict to JSON string if provided
            result_json = json.dumps(result) if result else None
            
            # Execute update
            cursor.execute(
                query,
                (status, progress, stage, message, result_json, error, task_id)
            )
            
            # Check if any rows were updated
            if cursor.rowcount == 0:
                logger.warning(
                    f"Task not found in database",
                    extra={
                        'task_id': task_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )
                return False
            
            logger.info(
                f"Task status updated successfully",
                extra={
                    'task_id': task_id,
                    'status': status,
                    'progress': progress,
                    'rows_updated': cursor.rowcount,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            return True
            
    except ValueError:
        # Re-raise validation errors without retry
        raise
    except psycopg2.Error as e:
        logger.error(
            f"Database error updating task status",
            extra={
                'task_id': task_id,
                'status': status,
                'error': str(e),
                'error_type': type(e).__name__,
                'error_message': str(e),
                'error_code': e.pgcode if hasattr(e, 'pgcode') else None,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        # Re-raise to trigger retry decorator
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error updating task status",
            extra={
                'task_id': task_id,
                'status': status,
                'error': str(e),
                'error_type': type(e).__name__,
                'error_message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        # Re-raise unexpected errors
        raise


def close_connection_pool():
    """
    Close all connections in the pool
    
    Should be called when the job is shutting down
    """
    global _connection_pool
    
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Database connection pool closed")
