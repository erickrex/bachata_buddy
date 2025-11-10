"""
Test logging functionality in CloudRunJobsService

This test verifies that all job operations are properly logged with structured data.
"""
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from unittest.mock import patch, MagicMock
from jobs_service import CloudRunJobsService, JobExecutionError


def test_job_creation_logging(caplog):
    """Test that job creation logs all relevant information"""
    # Set up local-dev mode
    os.environ['GCP_PROJECT_ID'] = 'local-dev'
    
    with caplog.at_level(logging.INFO):
        service = CloudRunJobsService()
        
        # Create a job execution
        task_id = "test-task-123"
        user_id = 42
        parameters = {
            "blueprint_json": '{"task_id": "test-task-123", "song": {}, "moves_used": []}'
        }
        
        execution_name = service.create_job_execution(task_id, user_id, parameters)
        
        # Verify logging occurred
        assert "Job creation requested" in caplog.text
        assert task_id in caplog.text
        assert "Mock job execution created" in caplog.text
        
        # Verify structured logging extras
        log_records = [r for r in caplog.records if "Job creation requested" in r.message]
        assert len(log_records) > 0
        
        record = log_records[0]
        assert record.task_id == task_id
        assert record.user_id == user_id
        assert record.has_blueprint is True
        
        print("✓ Job creation logging test passed")


def test_local_dev_mode_logging(caplog):
    """Test that local-dev mode operations are properly logged"""
    os.environ['GCP_PROJECT_ID'] = 'local-dev'
    
    with caplog.at_level(logging.INFO):
        service = CloudRunJobsService()
        
        # Verify initialization logging
        assert "Running in local-dev mode" in caplog.text
        
        # Create job with blueprint_json (should work in local-dev mode)
        execution_name = service.create_job_execution(
            task_id="test-task-456",
            user_id=42,
            parameters={"blueprint_json": '{"task_id": "test-task-456", "song": {}, "moves_used": []}'}
        )
        
        # Verify job creation was logged
        assert "Job creation requested" in caplog.text
        assert "Mock job execution created" in caplog.text
        assert execution_name.startswith("local-dev-execution-")
        
        print("✓ Local dev mode logging test passed")


def test_job_cancellation_logging(caplog):
    """Test that job cancellation logs all relevant information"""
    os.environ['GCP_PROJECT_ID'] = 'local-dev'
    
    with caplog.at_level(logging.INFO):
        service = CloudRunJobsService()
        
        execution_name = "projects/test/locations/us-central1/jobs/video-processor/executions/test-123"
        result = service.cancel_job_execution(execution_name)
        
        assert result is True
        assert "Job cancellation requested" in caplog.text
        assert "Mock job execution cancelled" in caplog.text
        assert execution_name in caplog.text
        
        print("✓ Job cancellation logging test passed")


def test_job_status_logging(caplog):
    """Test that job status queries are logged"""
    os.environ['GCP_PROJECT_ID'] = 'local-dev'
    
    with caplog.at_level(logging.DEBUG):
        service = CloudRunJobsService()
        
        execution_name = "projects/test/locations/us-central1/jobs/video-processor/executions/test-789"
        status = service.get_job_execution_status(execution_name)
        
        assert status is not None
        assert status['status'] == 'running'
        assert "Job execution status requested" in caplog.text
        assert "Mock job execution status requested" in caplog.text
        
        print("✓ Job status logging test passed")


if __name__ == '__main__':
    import pytest
    
    print("\n=== Testing CloudRunJobsService Logging ===\n")
    
    # Run tests with pytest
    pytest.main([__file__, '-v', '-s'])
