import Button from '../common/Button';

/**
 * ProgressTracker Component
 * Displays animated progress bar with stage-specific indicators for choreography generation
 * 
 * @param {number} progress - Progress percentage (0-100)
 * @param {string} stage - Current generation stage
 * @param {string} message - Current stage message
 * @param {string} taskId - Task identifier
 * @param {Function} onCancel - Callback for cancel button
 */
function ProgressTracker({ progress = 0, stage = '', message = '', taskId = '', onCancel }) {
  // Stage-specific emoji indicators
  const stageEmojis = {
    generating_blueprint: '⏳',
    submitting_job: '📤',
    video_assembly: '🎬',
    uploading_result: '☁️',
    completed: '✨',
    pending: '⏳',
    started: '🚀',
    running: '🎬'
  };

  // Get emoji for current stage, default to hourglass
  const currentEmoji = stageEmojis[stage] || '⏳';

  return (
    <div className="max-w-2xl mx-auto p-8">
      {/* Stage Indicator */}
      <div className="text-center mb-8">
        <div className="text-6xl mb-4 animate-pulse-slow">
          {currentEmoji}
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Generating Your Choreography
        </h2>
        <p className="text-gray-600 text-lg">
          {message || 'Processing your request...'}
        </p>
      </div>

      {/* Progress Bar */}
      <div className="relative mb-6">
        <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500 ease-out"
            style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Choreography generation progress"
          />
        </div>
        <p className="text-center mt-2 text-sm font-medium text-gray-700">
          {Math.round(progress)}%
        </p>
      </div>

      {/* Task ID */}
      {taskId && (
        <p className="text-center text-xs text-gray-500 mb-6">
          Task ID: {taskId}
        </p>
      )}

      {/* Cancel Button */}
      {onCancel && (
        <Button 
          onClick={onCancel} 
          variant="secondary" 
          className="w-full"
        >
          Cancel Generation
        </Button>
      )}

      {/* Screen reader announcement for progress updates */}
      <div 
        role="status" 
        aria-live="polite" 
        aria-atomic="true" 
        className="sr-only"
      >
        {message} - {Math.round(progress)}% complete
      </div>
    </div>
  );
}

export default ProgressTracker;
