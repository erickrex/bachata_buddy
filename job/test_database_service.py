"""
Unit Tests for Database Service

Tests for the simplified database service used by the video processing job.
These tests focus on the core functionality without requiring a live database.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import (
    update_task_status,
    close_connection_pool,
    get_db_connection,
    get_db_cursor,
    retry_on_db_error,
    _reset_connection_pool
)


class TestDatabaseService:
    """Test database service functionality."""
    
    def test_update_task_status_validation_invalid_status(self):
        """Test update_task_status with invalid status value."""
        with pytest.raises(ValueError) as exc_info:
            update_task_status(
                task_id='test-123',
                status='invalid_status',
                progress=50,
                stage='test',
                message='Test'
            )
        
        assert 'Invalid status' in str(exc_info.value)
        assert 'invalid_status' in str(exc_info.value)
    
    def test_update_task_status_validation_invalid_progress_negative(self):
        """Test update_task_status with negative progress."""
        with pytest.raises(ValueError) as exc_info:
            update_task_status(
                task_id='test-123',
                status='running',
                progress=-10,
                stage='test',
                message='Test'
            )
        
        assert 'Progress must be between 0 and 100' in str(exc_info.value)
    
    def test_update_task_status_validation_invalid_progress_over_100(self):
        """Test update_task_status with progress over 100."""
        with pytest.raises(ValueError) as exc_info:
            update_task_status(
                task_id='test-123',
                status='running',
                progress=150,
                stage='test',
                message='Test'
            )
        
        assert 'Progress must be between 0 and 100' in str(exc_info.value)
    
    def test_update_task_status_valid_statuses(self):
        """Test that all valid status values are accepted."""
        valid_statuses = ['started', 'running', 'completed', 'failed']
        
        for status in valid_statuses:
            # Should not raise ValueError
            try:
                # Mock the database cursor to avoid actual DB calls
                with patch('services.database.get_db_cursor') as mock_cursor:
                    mock_cursor_instance = MagicMock()
                    mock_cursor_instance.__enter__ = Mock(return_value=mock_cursor_instance)
                    mock_cursor_instance.__exit__ = Mock(return_value=False)
                    mock_cursor_instance.rowcount = 1
                    mock_cursor.return_value = mock_cursor_instance
                    
                    result = update_task_status(
                        task_id='test-123',
                        status=status,
                        progress=50,
                        stage='test',
                        message='Test'
                    )
                    
                    assert result is True
            except ValueError as e:
                pytest.fail(f"Valid status '{status}' raised ValueError: {e}")
    
    @patch('services.database.get_db_cursor')
    def test_update_task_status_success(self, mock_cursor):
        """Test successful task status update."""
        # Setup mock
        mock_cursor_instance = MagicMock()
        mock_cursor_instance.__enter__ = Mock(return_value=mock_cursor_instance)
        mock_cursor_instance.__exit__ = Mock(return_value=False)
        mock_cursor_instance.rowcount = 1
        mock_cursor.return_value = mock_cursor_instance
        
        # Call function
        result = update_task_status(
            task_id='test-task-123',
            status='running',
            progress=50,
            stage='processing',
            message='Processing video...'
        )
        
        # Verify
        assert result is True
        mock_cursor_instance.execute.assert_called_once()
        
        # Verify SQL query structure
        call_args = mock_cursor_instance.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        assert 'UPDATE choreography_tasks' in query
        assert 'status = %s' in query
        assert 'progress = %s' in query
        assert 'stage = %s' in query
        assert 'message = %s' in query
        assert 'WHERE task_id = %s' in query
        
        assert params[0] == 'running'
        assert params[1] == 50
        assert params[2] == 'processing'
        assert params[3] == 'Processing video...'
        assert params[6] == 'test-task-123'
    
    @patch('services.database.get_db_cursor')
    def test_update_task_status_with_result(self, mock_cursor):
        """Test task status update with result data."""
        # Setup mock
        mock_cursor_instance = MagicMock()
        mock_cursor_instance.__enter__ = Mock(return_value=mock_cursor_instance)
        mock_cursor_instance.__exit__ = Mock(return_value=False)
        mock_cursor_instance.rowcount = 1
        mock_cursor.return_value = mock_cursor_instance
        
        # Call function with result
        result_data = {
            'video_url': 'gs://bucket/video.mp4',
            'duration': 180.5,
            'moves_count': 12
        }
        
        result = update_task_status(
            task_id='test-task-123',
            status='completed',
            progress=100,
            stage='completed',
            message='Success!',
            result=result_data
        )
        
        # Verify
        assert result is True
        
        # Verify result was JSON serialized
        call_args = mock_cursor_instance.execute.call_args
        params = call_args[0][1]
        result_json = params[4]
        
        assert result_json is not None
        assert 'video_url' in result_json
        assert 'duration' in result_json
    
    @patch('services.database.get_db_cursor')
    def test_update_task_status_with_error(self, mock_cursor):
        """Test task status update with error message."""
        # Setup mock
        mock_cursor_instance = MagicMock()
        mock_cursor_instance.__enter__ = Mock(return_value=mock_cursor_instance)
        mock_cursor_instance.__exit__ = Mock(return_value=False)
        mock_cursor_instance.rowcount = 1
        mock_cursor.return_value = mock_cursor_instance
        
        # Call function with error
        result = update_task_status(
            task_id='test-task-123',
            status='failed',
            progress=50,
            stage='processing',
            message='Processing failed',
            error='FFmpeg error: file not found'
        )
        
        # Verify
        assert result is True
        
        # Verify error was passed
        call_args = mock_cursor_instance.execute.call_args
        params = call_args[0][1]
        error_msg = params[5]
        
        assert error_msg == 'FFmpeg error: file not found'
    
    @patch('services.database.get_db_cursor')
    def test_update_task_status_task_not_found(self, mock_cursor):
        """Test update when task doesn't exist in database."""
        # Setup mock - rowcount 0 means no rows updated
        mock_cursor_instance = MagicMock()
        mock_cursor_instance.__enter__ = Mock(return_value=mock_cursor_instance)
        mock_cursor_instance.__exit__ = Mock(return_value=False)
        mock_cursor_instance.rowcount = 0
        mock_cursor.return_value = mock_cursor_instance
        
        # Call function
        result = update_task_status(
            task_id='nonexistent-task',
            status='running',
            progress=50,
            stage='test',
            message='Test'
        )
        
        # Verify returns False when task not found
        assert result is False
    
    def test_retry_decorator_success_on_first_try(self):
        """Test retry decorator when function succeeds on first try."""
        mock_func = Mock(return_value='success')
        decorated_func = retry_on_db_error()(mock_func)
        
        result = decorated_func()
        
        assert result == 'success'
        assert mock_func.call_count == 1
    
    def test_retry_decorator_success_after_retry(self):
        """Test retry decorator when function succeeds after retries."""
        import psycopg2
        
        # Mock function that fails twice then succeeds
        mock_func = Mock(
            __name__='mock_func',
            side_effect=[
                psycopg2.OperationalError('Connection failed'),
                psycopg2.OperationalError('Connection failed'),
                'success'
            ]
        )
        
        with patch('services.database._reset_connection_pool'):
            decorated_func = retry_on_db_error(max_retries=3, delay=0.01)(mock_func)
            result = decorated_func()
        
        assert result == 'success'
        assert mock_func.call_count == 3
    
    def test_retry_decorator_exhausts_retries(self):
        """Test retry decorator when all retries are exhausted."""
        import psycopg2
        
        # Mock function that always fails
        mock_func = Mock(
            __name__='mock_func',
            side_effect=psycopg2.OperationalError('Connection failed')
        )
        
        with patch('services.database._reset_connection_pool'):
            decorated_func = retry_on_db_error(max_retries=2, delay=0.01)(mock_func)
            
            with pytest.raises(psycopg2.OperationalError):
                decorated_func()
        
        # Should try 3 times (initial + 2 retries)
        assert mock_func.call_count == 3
    
    def test_retry_decorator_non_retryable_error(self):
        """Test retry decorator doesn't retry non-database errors."""
        # Mock function that raises non-database error
        mock_func = Mock(
            __name__='mock_func',
            side_effect=ValueError('Invalid value')
        )
        
        decorated_func = retry_on_db_error()(mock_func)
        
        with pytest.raises(ValueError):
            decorated_func()
        
        # Should only try once
        assert mock_func.call_count == 1
    
    def test_close_connection_pool(self):
        """Test closing connection pool."""
        # This should not raise any errors even if pool doesn't exist
        close_connection_pool()
        
        # Call again to ensure it's idempotent
        close_connection_pool()


class TestDatabaseConnectionConfig:
    """Test database connection configuration."""
    
    @patch.dict(os.environ, {
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_pass'
    })
    @patch('services.database.psycopg2.pool.ThreadedConnectionPool')
    def test_connection_pool_creation_local(self, mock_pool):
        """Test connection pool creation for local development."""
        from services.database import _create_connection_pool
        
        # Reset global pool
        import services.database
        services.database._connection_pool = None
        
        pool = _create_connection_pool()
        
        # Verify pool was created with correct parameters
        mock_pool.assert_called_once()
        call_kwargs = mock_pool.call_args[1]
        
        assert call_kwargs['dbname'] == 'test_db'
        assert call_kwargs['user'] == 'test_user'
        assert call_kwargs['password'] == 'test_pass'
        assert call_kwargs['host'] == 'localhost'
        assert call_kwargs['port'] == '5432'
        assert call_kwargs['connect_timeout'] == 10
    
    @patch.dict(os.environ, {
        'DB_NAME': 'prod_db',
        'DB_USER': 'prod_user',
        'DB_PASSWORD': 'prod_pass',
        'CLOUD_SQL_CONNECTION_NAME': 'project:region:instance',
        'K_SERVICE': 'video-processor'
    })
    @patch('services.database.psycopg2.pool.ThreadedConnectionPool')
    def test_connection_pool_creation_cloud_run(self, mock_pool):
        """Test connection pool creation for Cloud Run."""
        from services.database import _create_connection_pool
        
        # Reset global pool
        import services.database
        services.database._connection_pool = None
        
        pool = _create_connection_pool()
        
        # Verify pool was created with Unix socket
        mock_pool.assert_called_once()
        call_kwargs = mock_pool.call_args[1]
        
        assert call_kwargs['dbname'] == 'prod_db'
        assert call_kwargs['user'] == 'prod_user'
        assert call_kwargs['password'] == 'prod_pass'
        assert '/cloudsql/project:region:instance' in call_kwargs['host']
        assert 'port' not in call_kwargs  # Unix socket doesn't use port


class TestDatabaseCursorContextManager:
    """Test database cursor context manager."""
    
    @patch('services.database.get_db_connection')
    def test_cursor_context_manager_success(self, mock_get_conn):
        """Test cursor context manager with successful operation."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        # Use context manager
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Verify commit was called
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    @patch('services.database.get_db_connection')
    def test_cursor_context_manager_error(self, mock_get_conn):
        """Test cursor context manager with error."""
        import psycopg2
        
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        # Simulate error during query
        mock_cursor.execute.side_effect = psycopg2.DatabaseError('Query failed')
        
        # Use context manager
        with pytest.raises(psycopg2.DatabaseError):
            with get_db_cursor() as cursor:
                cursor.execute("SELECT 1")
        
        # Verify rollback was called
        mock_conn.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
