"""
Test that main.py correctly reads all parameters from environment variables
"""
import os
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))


def test_get_env_config():
    """Test that get_env_config reads all required parameters"""
    # Set up test environment variables
    test_env = {
        # Task information
        'TASK_ID': 'test-task-123',
        'USER_ID': '42',
        
        # Choreography parameters (required)
        'AUDIO_INPUT': '/app/data/songs/test.mp3',
        'DIFFICULTY': 'intermediate',
        
        # Choreography parameters (optional)
        'ENERGY_LEVEL': 'high',
        'STYLE': 'romantic',
        
        # Database configuration
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_password',
        
        # Elasticsearch configuration
        'ELASTICSEARCH_HOST': 'localhost',
        'ELASTICSEARCH_PORT': '9200',
        'ELASTICSEARCH_INDEX': 'test_index',
        'ELASTICSEARCH_API_KEY': 'test_api_key',
        
        # Google Cloud configuration
        'GCP_PROJECT_ID': 'test-project',
        'GCP_REGION': 'us-central1',
        'GOOGLE_API_KEY': 'test-google-api-key',
        'GCS_BUCKET_NAME': 'test-bucket',
        
        # Video processing configuration
        'YOLOV8_MODEL': 'yolov8n-pose.pt',
        'YOLOV8_CONFIDENCE': '0.3',
        'YOLOV8_DEVICE': 'cpu',
        'YOLOV8_IOU_THRESHOLD': '0.5',
        'YOLOV8_MAX_DET': '10',
        
        # FFmpeg configuration
        'VIDEO_OUTPUT_FORMAT': 'mp4',
        'VIDEO_CODEC': 'libx264',
        'VIDEO_CRF': '23',
        'VIDEO_FPS': '30',
        'AUDIO_CODEC': 'aac',
        'AUDIO_BITRATE': '128k',
        
        # Logging configuration
        'LOG_LEVEL': 'INFO',
    }
    
    # Set environment variables
    for key, value in test_env.items():
        os.environ[key] = value
    
    # Import and test get_env_config
    from main import get_env_config
    
    config = get_env_config()
    
    # Verify all required parameters are present
    assert config['task_id'] == 'test-task-123', "task_id not read correctly"
    assert config['user_id'] == '42', "user_id not read correctly"
    assert config['audio_input'] == '/app/data/songs/test.mp3', "audio_input not read correctly"
    assert config['difficulty'] == 'intermediate', "difficulty not read correctly"
    assert config['energy_level'] == 'high', "energy_level not read correctly"
    assert config['style'] == 'romantic', "style not read correctly"
    
    # Verify database configuration
    assert config['db_host'] == 'localhost', "db_host not read correctly"
    assert config['db_port'] == '5432', "db_port not read correctly"
    assert config['db_name'] == 'test_db', "db_name not read correctly"
    assert config['db_user'] == 'test_user', "db_user not read correctly"
    assert config['db_password'] == 'test_password', "db_password not read correctly"
    
    # Verify Elasticsearch configuration
    assert config['elasticsearch_host'] == 'localhost', "elasticsearch_host not read correctly"
    assert config['elasticsearch_port'] == '9200', "elasticsearch_port not read correctly"
    assert config['elasticsearch_index'] == 'test_index', "elasticsearch_index not read correctly"
    assert config['elasticsearch_api_key'] == 'test_api_key', "elasticsearch_api_key not read correctly"
    
    # Verify Google Cloud configuration
    assert config['gcp_project_id'] == 'test-project', "gcp_project_id not read correctly"
    assert config['gcp_region'] == 'us-central1', "gcp_region not read correctly"
    assert config['google_api_key'] == 'test-google-api-key', "google_api_key not read correctly"
    assert config['gcs_bucket_name'] == 'test-bucket', "gcs_bucket_name not read correctly"
    
    # Verify video processing configuration
    assert config['yolov8_model'] == 'yolov8n-pose.pt', "yolov8_model not read correctly"
    assert config['yolov8_confidence'] == 0.3, "yolov8_confidence not read correctly"
    assert config['yolov8_device'] == 'cpu', "yolov8_device not read correctly"
    assert config['yolov8_iou_threshold'] == 0.5, "yolov8_iou_threshold not read correctly"
    assert config['yolov8_max_det'] == 10, "yolov8_max_det not read correctly"
    
    # Verify FFmpeg configuration
    assert config['video_output_format'] == 'mp4', "video_output_format not read correctly"
    assert config['video_codec'] == 'libx264', "video_codec not read correctly"
    assert config['video_crf'] == 23, "video_crf not read correctly"
    assert config['video_fps'] == 30, "video_fps not read correctly"
    assert config['audio_codec'] == 'aac', "audio_codec not read correctly"
    assert config['audio_bitrate'] == '128k', "audio_bitrate not read correctly"
    
    # Verify logging configuration
    assert config['log_level'] == 'INFO', "log_level not read correctly"
    
    print("✅ All environment variables read correctly")
    print(f"✅ Total parameters verified: {len(test_env)}")
    
    # Clean up environment variables
    for key in test_env.keys():
        del os.environ[key]


def test_validate_required_env_vars():
    """Test that validate_required_env_vars correctly identifies missing variables"""
    # Set up minimal required environment variables
    required_env = {
        'TASK_ID': 'test-task-123',
        'USER_ID': '42',
        'AUDIO_INPUT': '/app/data/songs/test.mp3',
        'DIFFICULTY': 'intermediate',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_password',
        'ELASTICSEARCH_HOST': 'localhost',
        'ELASTICSEARCH_PORT': '9200',
        'ELASTICSEARCH_INDEX': 'test_index',
        'GCP_PROJECT_ID': 'test-project',
        'GCP_REGION': 'us-central1',
        'GOOGLE_API_KEY': 'test-google-api-key',
    }
    
    # Set environment variables
    for key, value in required_env.items():
        os.environ[key] = value
    
    # Import and test validate_required_env_vars
    from main import validate_required_env_vars
    
    # Should return True when all required variables are present
    assert validate_required_env_vars() == True, "Validation should pass with all required variables"
    
    print("✅ Required environment variables validation passed")
    
    # Test with missing variable
    missing_var = 'TASK_ID'
    saved_value = os.environ[missing_var]
    del os.environ[missing_var]
    
    # Should return False when a required variable is missing
    assert validate_required_env_vars() == False, "Validation should fail with missing required variable"
    
    print(f"✅ Correctly detected missing variable: {missing_var}")
    
    # Restore variable
    os.environ[missing_var] = saved_value
    
    # Clean up environment variables
    for key in required_env.keys():
        del os.environ[key]


if __name__ == '__main__':
    print("=" * 80)
    print("Testing main.py Environment Variable Reading")
    print("=" * 80)
    
    print("\nTest 1: get_env_config reads all parameters")
    print("-" * 80)
    test_get_env_config()
    
    print("\nTest 2: validate_required_env_vars detects missing variables")
    print("-" * 80)
    test_validate_required_env_vars()
    
    print("\n" + "=" * 80)
    print("All tests passed! ✅")
    print("=" * 80)
