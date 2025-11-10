"""
Test script for Cloud Run Jobs Service error handling and retry logic
"""
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.jobs_service import CloudRunJobsService, JobExecutionError, JobCancellationError


def test_create_job_execution_success():
    """Test successful job creation"""
    print("Test 1: Successful job creation")
    
    service = CloudRunJobsService()
    
    # Mock mode (local-dev)
    result = service.create_job_execution(
        task_id="test-123",
        user_id=1,
        parameters={
            'blueprint_json': '{"task_id": "test-123", "song": {}, "moves_used": []}'
        }
    )
    
    assert result == "local-dev-execution-test-123"
    print("✓ Test 1 passed: Job created successfully in mock mode\n")


def test_create_job_execution_missing_parameters():
    """Test job creation with missing required parameters"""
    print("Test 2: Job creation with missing parameters")
    
    # Create service with mock client to test validation
    service = CloudRunJobsService()
    service.client = Mock()  # Enable validation by setting client
    
    try:
        service.create_job_execution(
            task_id="test-123",
            user_id=1,
            parameters={'difficulty': 'intermediate'}  # Missing blueprint_json
        )
        assert False, "Should have raised JobExecutionError"
    except JobExecutionError as e:
        assert "Missing required parameter: blueprint_json" in str(e)
        print(f"✓ Test 2 passed: Validation error caught: {e}\n")


def test_create_job_execution_retry_logic():
    """Test retry logic with transient failures"""
    print("Test 3: Retry logic with transient failures")
    
    service = CloudRunJobsService()
    service.client = Mock()
    
    # Mock the internal method to fail twice, then succeed
    call_count = [0]
    
    def mock_create_internal(task_id, user_id, parameters):
        call_count[0] += 1
        if call_count[0] < 3:
            raise Exception("Transient error")
        return "execution-name-123"
    
    service._create_job_execution_internal = mock_create_internal
    
    result = service.create_job_execution(
        task_id="test-123",
        user_id=1,
        parameters={
            'blueprint_json': '{"task_id": "test-123", "song": {}, "moves_used": []}'
        }
    )
    
    assert result == "execution-name-123"
    assert call_count[0] == 3, f"Expected 3 attempts, got {call_count[0]}"
    print(f"✓ Test 3 passed: Retry succeeded after {call_count[0]} attempts\n")


def test_create_job_execution_non_retryable_error():
    """Test that non-retryable errors are not retried"""
    print("Test 4: Non-retryable error handling")
    
    service = CloudRunJobsService()
    service.client = Mock()
    
    # Mock the internal method to raise a non-retryable error
    call_count = [0]
    
    def mock_create_internal(task_id, user_id, parameters):
        call_count[0] += 1
        raise Exception("Permission denied")
    
    service._create_job_execution_internal = mock_create_internal
    
    try:
        service.create_job_execution(
            task_id="test-123",
            user_id=1,
            parameters={
                'blueprint_json': '{"task_id": "test-123", "song": {}, "moves_used": []}'
            }
        )
        assert False, "Should have raised JobExecutionError"
    except JobExecutionError as e:
        assert "Permission denied" in str(e)
        assert call_count[0] == 1, f"Expected 1 attempt (no retry), got {call_count[0]}"
        print(f"✓ Test 4 passed: Non-retryable error not retried (attempts: {call_count[0]})\n")


def test_create_job_execution_max_retries_exhausted():
    """Test that max retries are respected"""
    print("Test 5: Max retries exhausted")
    
    service = CloudRunJobsService()
    service.client = Mock()
    
    # Mock the internal method to always fail
    call_count = [0]
    
    def mock_create_internal(task_id, user_id, parameters):
        call_count[0] += 1
        raise Exception("Transient error")
    
    service._create_job_execution_internal = mock_create_internal
    
    try:
        service.create_job_execution(
            task_id="test-123",
            user_id=1,
            parameters={
                'blueprint_json': '{"task_id": "test-123", "song": {}, "moves_used": []}'
            }
        )
        assert False, "Should have raised JobExecutionError"
    except JobExecutionError as e:
        assert "Failed to create job execution after 3 attempts" in str(e)
        assert call_count[0] == 3, f"Expected 3 attempts, got {call_count[0]}"
        print(f"✓ Test 5 passed: Max retries exhausted after {call_count[0]} attempts\n")


def test_cancel_job_execution_success():
    """Test successful job cancellation"""
    print("Test 6: Successful job cancellation")
    
    service = CloudRunJobsService()
    
    # Mock mode (local-dev)
    result = service.cancel_job_execution("execution-123")
    
    assert result is True
    print("✓ Test 6 passed: Job cancelled successfully in mock mode\n")


def test_cancel_job_execution_retry_logic():
    """Test cancellation retry logic"""
    print("Test 7: Cancellation retry logic")
    
    service = CloudRunJobsService()
    service.client = Mock()
    
    # Mock the internal method to fail once, then succeed
    call_count = [0]
    
    def mock_cancel_internal(execution_name):
        call_count[0] += 1
        if call_count[0] < 2:
            raise Exception("Transient error")
        return True
    
    service._cancel_job_execution_internal = mock_cancel_internal
    
    result = service.cancel_job_execution("execution-123")
    
    assert result is True
    assert call_count[0] == 2, f"Expected 2 attempts, got {call_count[0]}"
    print(f"✓ Test 7 passed: Cancellation retry succeeded after {call_count[0]} attempts\n")


def test_cancel_job_execution_already_completed():
    """Test cancellation of already completed job"""
    print("Test 8: Cancellation of already completed job")
    
    service = CloudRunJobsService()
    service.client = Mock()
    
    # Mock the internal method to return False (already completed)
    def mock_cancel_internal(execution_name):
        return False
    
    service._cancel_job_execution_internal = mock_cancel_internal
    
    result = service.cancel_job_execution("execution-123")
    
    assert result is False
    print("✓ Test 8 passed: Correctly handled already completed job\n")


def test_get_job_execution_status():
    """Test getting job execution status"""
    print("Test 9: Get job execution status")
    
    service = CloudRunJobsService()
    
    # Mock mode (local-dev)
    result = service.get_job_execution_status("execution-123")
    
    assert result is not None
    assert result['name'] == "execution-123"
    assert result['status'] == 'running'
    print("✓ Test 9 passed: Job status retrieved successfully in mock mode\n")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Testing Cloud Run Jobs Service Error Handling and Retries")
    print("=" * 60 + "\n")
    
    tests = [
        test_create_job_execution_success,
        test_create_job_execution_missing_parameters,
        test_create_job_execution_retry_logic,
        test_create_job_execution_non_retryable_error,
        test_create_job_execution_max_retries_exhausted,
        test_cancel_job_execution_success,
        test_cancel_job_execution_retry_logic,
        test_cancel_job_execution_already_completed,
        test_get_job_execution_status,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  Error: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
