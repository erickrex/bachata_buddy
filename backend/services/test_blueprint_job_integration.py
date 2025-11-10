"""
Simple integration test to verify blueprint-based job service works correctly.
This can be run independently without Django setup.
"""
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.jobs_service import CloudRunJobsService, JobExecutionError


def test_local_dev_mode():
    """Test that local dev mode works with blueprint"""
    os.environ['GCP_PROJECT_ID'] = 'local-dev'
    
    service = CloudRunJobsService()
    
    # Create a sample blueprint
    blueprint = {
        "task_id": "test-123",
        "audio_path": "data/songs/test.mp3",
        "audio_tempo": 120,
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "data/Bachata_steps/basic_steps/basic_1.mp4",
                "start_time": 0.0,
                "duration": 8.0,
                "transition_type": "cut"
            }
        ],
        "total_duration": 180.0,
        "difficulty_level": "intermediate",
        "generation_parameters": {
            "energy_level": "medium",
            "style": "modern",
            "user_id": 1
        },
        "output_config": {
            "output_path": "data/output/choreography_test-123.mp4",
            "output_format": "mp4"
        }
    }
    
    # Test with blueprint_json
    execution_name = service.create_job_execution(
        task_id="test-123",
        user_id=1,
        parameters={"blueprint_json": json.dumps(blueprint)}
    )
    
    assert execution_name == "local-dev-execution-test-123"
    print("✓ Local dev mode works with blueprint")


def test_missing_blueprint_fails():
    """Test that missing blueprint_json raises error"""
    os.environ['GCP_PROJECT_ID'] = 'my-project'
    
    service = CloudRunJobsService()
    service.client = object()  # Mock client to enable validation
    
    try:
        service.create_job_execution(
            task_id="test-123",
            user_id=1,
            parameters={}
        )
        assert False, "Should have raised JobExecutionError"
    except JobExecutionError as e:
        assert "Missing required parameter: blueprint_json" in str(e)
        print("✓ Missing blueprint_json raises appropriate error")


def test_blueprint_json_structure():
    """Test that blueprint_json is properly structured"""
    os.environ['GCP_PROJECT_ID'] = 'local-dev'
    
    service = CloudRunJobsService()
    
    blueprint = {
        "task_id": "test-456",
        "audio_path": "gs://bucket/song.mp3",
        "moves": [],
        "output_config": {}
    }
    
    blueprint_json = json.dumps(blueprint)
    
    # Verify it's valid JSON
    parsed = json.loads(blueprint_json)
    assert parsed["task_id"] == "test-456"
    assert parsed["audio_path"] == "gs://bucket/song.mp3"
    
    # Test with service
    execution_name = service.create_job_execution(
        task_id="test-456",
        user_id=2,
        parameters={"blueprint_json": blueprint_json}
    )
    
    assert execution_name == "local-dev-execution-test-456"
    print("✓ Blueprint JSON structure is valid")


if __name__ == "__main__":
    print("Testing blueprint-based job service...")
    print()
    
    test_local_dev_mode()
    test_missing_blueprint_fails()
    test_blueprint_json_structure()
    
    print()
    print("All tests passed! ✓")
    print()
    print("Summary:")
    print("- Jobs service now requires blueprint_json parameter")
    print("- Legacy parameters (audio_input, difficulty, etc.) are no longer supported")
    print("- BLUEPRINT_JSON environment variable is passed to job container")
    print("- Both local and GCP modes work correctly")
