"""
Test exception handling in main.py

This test verifies that the job properly handles exceptions and updates task status.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_import_error_handling():
    """Test that import errors are caught and task status is updated"""
    # Set required environment variables
    env_vars = {
        'TASK_ID': 'test-task-123',
        'USER_ID': '1',
        'AUDIO_INPUT': 'test.mp3',
        'DIFFICULTY': 'intermediate',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_pass',
        'ELASTICSEARCH_HOST': 'localhost',
        'ELASTICSEARCH_PORT': '9200',
        'ELASTICSEARCH_INDEX': 'test_index',
        'GCP_PROJECT_ID': 'test-project',
        'GCP_REGION': 'us-central1',
        'GOOGLE_API_KEY': 'test-key',
        'LOG_LEVEL': 'INFO',
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        # Mock database functions
        with patch('services.database.test_connection', return_value=True):
            with patch('services.database.update_task_status', return_value=True) as mock_update:
                with patch('services.database.close_connection_pool'):
                    # Import main first
                    from main import main
                    
                    # Mock pipeline module to fail on import
                    with patch.dict('sys.modules', {'pipeline': None}):
                        # Run main and expect it to return 1 (error)
                        result = main()
                        
                        # Verify task status was updated to 'failed'
                        assert result == 1
                        mock_update.assert_called()
                        
                        # Check that the last call was to set status to 'failed'
                        last_call = mock_update.call_args_list[-1]
                        assert last_call[1]['status'] == 'failed' or last_call[0][1] == 'failed'


def test_service_initialization_error_handling():
    """Test that service initialization errors are caught and task status is updated"""
    env_vars = {
        'TASK_ID': 'test-task-456',
        'USER_ID': '1',
        'AUDIO_INPUT': 'test.mp3',
        'DIFFICULTY': 'intermediate',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_pass',
        'ELASTICSEARCH_HOST': 'localhost',
        'ELASTICSEARCH_PORT': '9200',
        'ELASTICSEARCH_INDEX': 'test_index',
        'GCP_PROJECT_ID': 'test-project',
        'GCP_REGION': 'us-central1',
        'GOOGLE_API_KEY': 'test-key',
        'LOG_LEVEL': 'INFO',
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        with patch('services.database.test_connection', return_value=True):
            with patch('services.database.update_task_status', return_value=True) as mock_update:
                with patch('services.database.close_connection_pool'):
                    # Mock StorageService to raise an error
                    with patch('pipeline.StorageService', side_effect=Exception("Storage init failed")):
                        from main import main
                        
                        result = main()
                        
                        # Verify task status was updated to 'failed'
                        assert result == 1
                        mock_update.assert_called()


def test_pipeline_execution_error_handling():
    """Test that pipeline execution errors are caught and task status is updated"""
    env_vars = {
        'TASK_ID': 'test-task-789',
        'USER_ID': '1',
        'AUDIO_INPUT': 'test.mp3',
        'DIFFICULTY': 'intermediate',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_pass',
        'ELASTICSEARCH_HOST': 'localhost',
        'ELASTICSEARCH_PORT': '9200',
        'ELASTICSEARCH_INDEX': 'test_index',
        'GCP_PROJECT_ID': 'test-project',
        'GCP_REGION': 'us-central1',
        'GOOGLE_API_KEY': 'test-key',
        'LOG_LEVEL': 'INFO',
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        with patch('services.database.test_connection', return_value=True):
            with patch('services.database.update_task_status', return_value=True) as mock_update:
                with patch('services.database.close_connection_pool'):
                    # Mock all service imports
                    mock_storage = MagicMock()
                    mock_music = MagicMock()
                    mock_es = MagicMock()
                    mock_video_config = MagicMock()
                    
                    with patch('pipeline.StorageService', return_value=mock_storage):
                        with patch('pipeline.MusicAnalyzer', return_value=mock_music):
                            with patch('pipeline.ElasticsearchService', return_value=mock_es):
                                with patch('pipeline.VideoGenerationConfig', return_value=mock_video_config):
                                    # Mock pipeline to raise an error during execution
                                    mock_pipeline = MagicMock()
                                    mock_pipeline.generate.side_effect = Exception("Pipeline execution failed")
                                    
                                    with patch('pipeline.ChoreoGenerationPipeline', return_value=mock_pipeline):
                                        from main import main
                                        
                                        result = main()
                                        
                                        # Verify task status was updated to 'failed'
                                        assert result == 1
                                        mock_update.assert_called()
                                        
                                        # Check that the last call was to set status to 'failed'
                                        last_call = mock_update.call_args_list[-1]
                                        assert last_call[1]['status'] == 'failed' or last_call[0][1] == 'failed'


def test_missing_env_vars_handling():
    """Test that missing environment variables are handled properly"""
    # Clear all environment variables
    with patch.dict(os.environ, {}, clear=True):
        from main import main
        
        # Run main and expect it to return 1 (error)
        result = main()
        
        # Verify it returns error code
        assert result == 1


def test_logging_configuration():
    """Test that logging is configured properly"""
    from main import configure_logging
    import logging
    
    # Configure logging
    configure_logging('DEBUG')
    
    # Verify logger is configured
    logger = logging.getLogger(__name__)
    assert logger.level <= logging.DEBUG or logging.root.level <= logging.DEBUG


def test_env_config_extraction():
    """Test that environment configuration is extracted correctly"""
    env_vars = {
        'TASK_ID': 'test-task-123',
        'USER_ID': '42',
        'AUDIO_INPUT': 'test.mp3',
        'DIFFICULTY': 'advanced',
        'ENERGY_LEVEL': 'high',
        'STYLE': 'sensual',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_pass',
        'ELASTICSEARCH_HOST': 'localhost',
        'ELASTICSEARCH_PORT': '9200',
        'ELASTICSEARCH_INDEX': 'test_index',
        'GCP_PROJECT_ID': 'test-project',
        'GCP_REGION': 'us-central1',
        'GOOGLE_API_KEY': 'test-key',
        'LOG_LEVEL': 'DEBUG',
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        from main import get_env_config
        
        config = get_env_config()
        
        # Verify all values are extracted correctly
        assert config['task_id'] == 'test-task-123'
        assert config['user_id'] == '42'
        assert config['audio_input'] == 'test.mp3'
        assert config['difficulty'] == 'advanced'
        assert config['energy_level'] == 'high'
        assert config['style'] == 'sensual'
        assert config['db_host'] == 'localhost'
        assert config['log_level'] == 'DEBUG'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
