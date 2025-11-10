"""
Unit tests for CloudRunJobsService with mocks

Tests the Cloud Run Jobs integration service with proper mocking
to avoid actual API calls during testing.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.jobs_service import (
    CloudRunJobsService,
    JobExecutionError,
    JobCancellationError
)


class TestCloudRunJobsServiceInit:
    """Test CloudRunJobsService initialization"""
    
    def test_init_local_dev_mode(self, monkeypatch):
        """Test initialization in local-dev mode"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        monkeypatch.setenv('GCP_REGION', 'us-central1')
        
        service = CloudRunJobsService()
        
        assert service.project_id == 'local-dev'
        assert service.region == 'us-central1'
        assert service.job_name == 'video-processor'
        assert service.client is None
    
    def test_init_production_mode(self, monkeypatch):
        """Test initialization in production mode"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        monkeypatch.setenv('GCP_REGION', 'us-west1')
        
        # Mock the google.cloud.run_v2 module before importing
        with patch('google.cloud.run_v2.JobsClient') as mock_client_class:
            mock_client_class.return_value = Mock()
            service = CloudRunJobsService()
            
            assert service.project_id == 'my-project'
            assert service.region == 'us-west1'
            assert service.client is not None


class TestCreateJobExecution:
    """Test create_job_execution method"""
    
    def test_create_job_execution_local_dev(self, monkeypatch):
        """Test job creation in local-dev mode"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        task_id = "test-task-123"
        user_id = 42
        blueprint = {
            "task_id": task_id,
            "audio_path": "gs://bucket/test.mp3",
            "moves": []
        }
        parameters = {
            "blueprint_json": '{"task_id": "test-task-123", "audio_path": "gs://bucket/test.mp3", "moves": []}'
        }
        
        result = service.create_job_execution(task_id, user_id, parameters)
        
        assert result == f"local-dev-execution-{task_id}"
    
    def test_create_job_execution_missing_blueprint_json(self, monkeypatch):
        """Test job creation fails with missing blueprint_json"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        service = CloudRunJobsService()
        service.client = Mock()  # Enable validation
        
        with pytest.raises(JobExecutionError) as exc_info:
            service.create_job_execution(
                task_id="test-123",
                user_id=1,
                parameters={}
            )
        
        assert "Missing required parameter: blueprint_json" in str(exc_info.value)
    
    def test_create_job_execution_success_with_retry(self, monkeypatch):
        """Test job creation succeeds after retry"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        service = CloudRunJobsService()
        service.client = Mock()
        
        # Mock internal method to fail once, then succeed
        call_count = [0]
        
        def mock_create_internal(task_id, user_id, parameters):
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Transient error")
            return "execution-name-123"
        
        service._create_job_execution_internal = mock_create_internal
        
        result = service.create_job_execution(
            task_id="test-123",
            user_id=1,
            parameters={
                "blueprint_json": '{"task_id": "test-123", "audio_path": "gs://bucket/test.mp3", "moves": []}'
            }
        )
        
        assert result == "execution-name-123"
        assert call_count[0] == 2
    
    def test_create_job_execution_non_retryable_error(self, monkeypatch):
        """Test non-retryable errors are not retried"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        service = CloudRunJobsService()
        service.client = Mock()
        
        call_count = [0]
        
        def mock_create_internal(task_id, user_id, parameters):
            call_count[0] += 1
            raise Exception("Permission denied")
        
        service._create_job_execution_internal = mock_create_internal
        
        with pytest.raises(JobExecutionError) as exc_info:
            service.create_job_execution(
                task_id="test-123",
                user_id=1,
                parameters={
                    "blueprint_json": '{"task_id": "test-123", "audio_path": "gs://bucket/test.mp3", "moves": []}'
                }
            )
        
        assert "Permission denied" in str(exc_info.value)
        assert call_count[0] == 1  # No retry
    
    def test_create_job_execution_max_retries_exhausted(self, monkeypatch):
        """Test max retries are respected"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        service = CloudRunJobsService()
        service.client = Mock()
        
        call_count = [0]
        
        def mock_create_internal(task_id, user_id, parameters):
            call_count[0] += 1
            raise Exception("Transient error")
        
        service._create_job_execution_internal = mock_create_internal
        
        with pytest.raises(JobExecutionError) as exc_info:
            service.create_job_execution(
                task_id="test-123",
                user_id=1,
                parameters={
                    "blueprint_json": '{"task_id": "test-123", "audio_path": "gs://bucket/test.mp3", "moves": []}'
                }
            )
        
        assert "Failed to create job execution after 3 attempts" in str(exc_info.value)
        assert call_count[0] == 3


class TestCreateJobExecutionInternal:
    """Test _create_job_execution_internal method"""
    
    def test_create_job_execution_internal_success(self, monkeypatch):
        """Test internal job creation with mocked Cloud Run API"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        monkeypatch.setenv('GCP_REGION', 'us-central1')
        
        # Mock the Cloud Run API
        mock_execution = Mock()
        mock_execution.name = "projects/my-project/locations/us-central1/jobs/video-processor/executions/exec-123"
        
        mock_operation = Mock()
        mock_operation.result = Mock(return_value=mock_execution)
        mock_operation.operation.name = "operations/op-123"
        
        mock_client = Mock()
        mock_client.run_job = Mock(return_value=mock_operation)
        
        with patch('google.cloud.run_v2') as mock_run_v2:
            mock_run_v2.JobsClient.return_value = mock_client
            mock_run_v2.RunJobRequest = Mock()
            
            service = CloudRunJobsService()
            service.client = mock_client
            
            result = service._create_job_execution_internal(
                task_id="test-123",
                user_id=42,
                parameters={
                    "blueprint_json": '{"task_id": "test-123", "audio_path": "gs://bucket/test.mp3", "moves": [], "difficulty_level": "intermediate", "generation_parameters": {"energy_level": "high", "style": "modern"}}'
                }
            )
            
            assert result == mock_execution.name
            mock_client.run_job.assert_called_once()
    
    def test_create_job_execution_internal_timeout(self, monkeypatch):
        """Test internal job creation handles timeout"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        mock_operation = Mock()
        mock_operation.result = Mock(side_effect=Exception("Timeout"))
        mock_operation.operation.name = "operations/op-123"
        
        mock_client = Mock()
        mock_client.run_job = Mock(return_value=mock_operation)
        
        with patch('google.cloud.run_v2'):
            service = CloudRunJobsService()
            service.client = mock_client
            
            with pytest.raises(Exception) as exc_info:
                service._create_job_execution_internal(
                    task_id="test-123",
                    user_id=42,
                    parameters={
                        "blueprint_json": '{"task_id": "test-123", "audio_path": "gs://bucket/test.mp3", "moves": []}'
                    }
                )
            
            assert "Timeout" in str(exc_info.value)


class TestCancelJobExecution:
    """Test cancel_job_execution method"""
    
    def test_cancel_job_execution_local_dev(self, monkeypatch):
        """Test job cancellation in local-dev mode"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        result = service.cancel_job_execution("execution-123")
        
        assert result is True
    
    def test_cancel_job_execution_missing_name(self, monkeypatch):
        """Test cancellation fails with missing execution name"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        service = CloudRunJobsService()
        service.client = Mock()
        
        with pytest.raises(JobCancellationError) as exc_info:
            service.cancel_job_execution("")
        
        assert "Execution name is required" in str(exc_info.value)
    
    def test_cancel_job_execution_success_with_retry(self, monkeypatch):
        """Test cancellation succeeds after retry"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        service = CloudRunJobsService()
        service.client = Mock()
        
        call_count = [0]
        
        def mock_cancel_internal(execution_name):
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Transient error")
            return True
        
        service._cancel_job_execution_internal = mock_cancel_internal
        
        result = service.cancel_job_execution("execution-123")
        
        assert result is True
        assert call_count[0] == 2
    
    def test_cancel_job_execution_already_completed(self, monkeypatch):
        """Test cancellation of already completed job"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        service = CloudRunJobsService()
        service.client = Mock()
        
        def mock_cancel_internal(execution_name):
            raise Exception("Job already completed")
        
        service._cancel_job_execution_internal = mock_cancel_internal
        
        result = service.cancel_job_execution("execution-123")
        
        assert result is False
    
    def test_cancel_job_execution_max_retries_exhausted(self, monkeypatch):
        """Test cancellation returns False after max retries"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        service = CloudRunJobsService()
        service.client = Mock()
        
        call_count = [0]
        
        def mock_cancel_internal(execution_name):
            call_count[0] += 1
            raise Exception("Transient error")
        
        service._cancel_job_execution_internal = mock_cancel_internal
        
        result = service.cancel_job_execution("execution-123")
        
        assert result is False
        assert call_count[0] == 3


class TestCancelJobExecutionInternal:
    """Test _cancel_job_execution_internal method"""
    
    def test_cancel_job_execution_internal_success(self, monkeypatch):
        """Test internal cancellation with mocked Cloud Run API"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        # Mock execution that is still running
        mock_execution = Mock()
        mock_execution.completion_time = None
        
        mock_operation = Mock()
        mock_operation.result = Mock(return_value=None)
        mock_operation.operation.name = "operations/op-123"
        
        mock_client = Mock()
        mock_client.get_execution = Mock(return_value=mock_execution)
        mock_client.delete_execution = Mock(return_value=mock_operation)
        
        with patch('google.cloud.run_v2'):
            service = CloudRunJobsService()
            service.client = mock_client
            
            result = service._cancel_job_execution_internal("execution-123")
            
            assert result is True
            mock_client.get_execution.assert_called_once()
            mock_client.delete_execution.assert_called_once()
    
    def test_cancel_job_execution_internal_already_completed(self, monkeypatch):
        """Test internal cancellation when job already completed"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        # Mock execution that is already completed
        mock_execution = Mock()
        mock_execution.completion_time = "2024-01-01T00:00:00Z"
        
        mock_client = Mock()
        mock_client.get_execution = Mock(return_value=mock_execution)
        
        with patch('google.cloud.run_v2'):
            service = CloudRunJobsService()
            service.client = mock_client
            
            result = service._cancel_job_execution_internal("execution-123")
            
            assert result is False
            mock_client.get_execution.assert_called_once()
            mock_client.delete_execution.assert_not_called()


class TestGetJobExecutionStatus:
    """Test get_job_execution_status method"""
    
    def test_get_job_execution_status_local_dev(self, monkeypatch):
        """Test status query in local-dev mode"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        result = service.get_job_execution_status("execution-123")
        
        assert result is not None
        assert result['name'] == "execution-123"
        assert result['status'] == 'running'
    
    def test_get_job_execution_status_success(self, monkeypatch):
        """Test status query with mocked Cloud Run API"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        # Mock execution
        mock_execution = Mock()
        mock_execution.name = "execution-123"
        mock_execution.start_time = "2024-01-01T00:00:00Z"
        mock_execution.completion_time = "2024-01-01T00:05:00Z"
        mock_execution.succeeded_count = 1
        mock_execution.failed_count = 0
        mock_execution.running_count = 0
        
        mock_client = Mock()
        mock_client.get_execution = Mock(return_value=mock_execution)
        
        with patch('google.cloud.run_v2'):
            service = CloudRunJobsService()
            service.client = mock_client
            
            result = service.get_job_execution_status("execution-123")
            
            assert result is not None
            assert result['name'] == "execution-123"
            assert result['status'] == 'succeeded'
            assert result['succeeded_count'] == 1
            assert result['failed_count'] == 0
    
    def test_get_job_execution_status_error(self, monkeypatch):
        """Test status query handles errors"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'my-project')
        
        mock_client = Mock()
        mock_client.get_execution = Mock(side_effect=Exception("Not found"))
        
        with patch('google.cloud.run_v2'):
            service = CloudRunJobsService()
            service.client = mock_client
            
            result = service.get_job_execution_status("execution-123")
            
            assert result is None


class TestGetExecutionStatusString:
    """Test _get_execution_status_string method"""
    
    def test_status_string_pending(self, monkeypatch):
        """Test status string for pending execution"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        
        mock_execution = Mock()
        mock_execution.start_time = None
        mock_execution.completion_time = None
        
        status = service._get_execution_status_string(mock_execution)
        assert status == 'pending'
    
    def test_status_string_running(self, monkeypatch):
        """Test status string for running execution"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        
        mock_execution = Mock()
        mock_execution.start_time = "2024-01-01T00:00:00Z"
        mock_execution.completion_time = None
        
        status = service._get_execution_status_string(mock_execution)
        assert status == 'running'
    
    def test_status_string_succeeded(self, monkeypatch):
        """Test status string for succeeded execution"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        
        mock_execution = Mock()
        mock_execution.start_time = "2024-01-01T00:00:00Z"
        mock_execution.completion_time = "2024-01-01T00:05:00Z"
        mock_execution.succeeded_count = 1
        mock_execution.failed_count = 0
        
        status = service._get_execution_status_string(mock_execution)
        assert status == 'succeeded'
    
    def test_status_string_failed(self, monkeypatch):
        """Test status string for failed execution"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        
        mock_execution = Mock()
        mock_execution.start_time = "2024-01-01T00:00:00Z"
        mock_execution.completion_time = "2024-01-01T00:05:00Z"
        mock_execution.succeeded_count = 0
        mock_execution.failed_count = 1
        
        status = service._get_execution_status_string(mock_execution)
        assert status == 'failed'
    
    def test_status_string_cancelled(self, monkeypatch):
        """Test status string for cancelled execution"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        
        mock_execution = Mock()
        mock_execution.start_time = "2024-01-01T00:00:00Z"
        mock_execution.completion_time = "2024-01-01T00:05:00Z"
        mock_execution.succeeded_count = 0
        mock_execution.failed_count = 0
        
        status = service._get_execution_status_string(mock_execution)
        assert status == 'cancelled'


class TestIsNonRetryableError:
    """Test _is_non_retryable_error method"""
    
    def test_is_non_retryable_permission_denied(self, monkeypatch):
        """Test permission denied is non-retryable"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        error = Exception("Permission denied")
        
        assert service._is_non_retryable_error(error) is True
    
    def test_is_non_retryable_not_found(self, monkeypatch):
        """Test not found is non-retryable"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        error = Exception("Resource not found")
        
        assert service._is_non_retryable_error(error) is True
    
    def test_is_retryable_transient_error(self, monkeypatch):
        """Test transient error is retryable"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        error = Exception("Temporary network error")
        
        assert service._is_non_retryable_error(error) is False


class TestIsCancellationNonRetryableError:
    """Test _is_cancellation_non_retryable_error method"""
    
    def test_is_cancellation_non_retryable_not_found(self, monkeypatch):
        """Test not found is non-retryable for cancellation"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        error = Exception("Execution not found")
        
        assert service._is_cancellation_non_retryable_error(error) is True
    
    def test_is_cancellation_non_retryable_already_completed(self, monkeypatch):
        """Test already completed is non-retryable for cancellation"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        error = Exception("Job already completed")
        
        assert service._is_cancellation_non_retryable_error(error) is True
    
    def test_is_cancellation_retryable_transient_error(self, monkeypatch):
        """Test transient error is retryable for cancellation"""
        monkeypatch.setenv('GCP_PROJECT_ID', 'local-dev')
        
        service = CloudRunJobsService()
        error = Exception("Temporary network error")
        
        assert service._is_cancellation_non_retryable_error(error) is False
