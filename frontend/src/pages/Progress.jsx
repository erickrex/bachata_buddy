import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { usePolling } from '../hooks/usePolling';
import { api } from '../utils/api';
import { useToast } from '../hooks/useToast';
import ProgressTracker from '../components/generation/ProgressTracker';
import Container from '../components/layout/Container';

/**
 * Progress Page
 * Displays real-time progress of choreography generation
 * Polls the backend API every 2 seconds for status updates
 * Navigates to VideoResult page when generation completes
 */
function Progress() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [taskData, setTaskData] = useState(null);
  const [hasNavigated, setHasNavigated] = useState(false);
  const timeoutRef = useRef(null);
  
  // Create a stable fetch function for polling
  const fetchTaskStatus = useCallback(async () => {
    if (!taskId) {
      throw new Error('No task ID provided');
    }
    return await api.tasks.getStatus(taskId);
  }, [taskId]);
  
  // Use polling hook to fetch task status every 2 seconds
  const { data, error, isLoading } = usePolling(
    fetchTaskStatus,
    2000, // Poll every 2 seconds
    !hasNavigated // Stop polling after navigation
  );
  
  // Update task data when polling returns new data
  useEffect(() => {
    if (data) {
      setTaskData(data);
    }
  }, [data]);
  
  // Handle task completion or failure
  useEffect(() => {
    if (!taskData || hasNavigated) return;
    
    if (taskData.status === 'completed') {
      // Navigate to video result page
      setHasNavigated(true);
      addToast('Choreography generated successfully!', 'success');
      navigate(`/video/${taskId}`);
    } else if (taskData.status === 'failed') {
      // Display error message
      setHasNavigated(true);
      const errorMessage = taskData.error || 'Generation failed. Please try again.';
      addToast(errorMessage, 'error');
    }
  }, [taskData, taskId, navigate, addToast, hasNavigated]);
  
  // Set up 5-minute timeout
  useEffect(() => {
    timeoutRef.current = setTimeout(() => {
      if (!hasNavigated && taskData?.status !== 'completed' && taskData?.status !== 'failed') {
        setHasNavigated(true);
        addToast('Generation timed out after 5 minutes. Please try again.', 'error');
        navigate('/');
      }
    }, 300000); // 5 minutes = 300,000 milliseconds
    
    // Cleanup timeout on unmount
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [navigate, addToast, hasNavigated, taskData]);
  
  // Handle cancel button click
  const handleCancel = async () => {
    try {
      await api.tasks.cancel(taskId);
      addToast('Generation cancelled', 'info');
      navigate('/');
    } catch (err) {
      addToast(err.message || 'Failed to cancel generation', 'error');
    }
  };
  
  // Handle initial loading state
  if (isLoading && !taskData) {
    return (
      <Container>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <div className="text-4xl mb-4">⏳</div>
            <p className="text-gray-600">Loading task status...</p>
          </div>
        </div>
      </Container>
    );
  }
  
  // Handle error state
  if (error && !taskData) {
    return (
      <Container>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center max-w-md">
            <div className="text-4xl mb-4">❌</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Failed to Load Task
            </h2>
            <p className="text-gray-600 mb-6">
              {error}
            </p>
            <button
              onClick={() => navigate('/')}
              className="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              Go Home
            </button>
          </div>
        </div>
      </Container>
    );
  }
  
  // Handle failed task state
  if (taskData?.status === 'failed') {
    return (
      <Container>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center max-w-md">
            <div className="text-4xl mb-4">❌</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Generation Failed
            </h2>
            <p className="text-gray-600 mb-6">
              {taskData.error || 'An error occurred during generation. Please try again.'}
            </p>
            <button
              onClick={() => navigate('/')}
              className="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </Container>
    );
  }
  
  // Display progress tracker
  return (
    <Container>
      <div className="py-12">
        <ProgressTracker
          progress={taskData?.progress || 0}
          stage={taskData?.stage || 'pending'}
          message={taskData?.message || 'Starting generation...'}
          taskId={taskId}
          onCancel={handleCancel}
        />
      </div>
    </Container>
  );
}

export default Progress;
