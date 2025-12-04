// ReasoningPanel Component
// Displays agent reasoning steps and function calls in real-time
// Shows progress indicators and current status

import { useState, useEffect } from 'react';
import ReasoningStep from './ReasoningStep';

function ReasoningPanel({ taskStatus, taskId }) {
  const [copiedTaskId, setCopiedTaskId] = useState(false);
  const [stepHistory, setStepHistory] = useState([]);
  
  // Extract values safely (hooks must be called before any conditional returns)
  const stage = taskStatus?.stage;
  const message = taskStatus?.message;
  const progress = taskStatus?.progress;
  const status = taskStatus?.status;
  const song = taskStatus?.song;
  
  // Track step history
  useEffect(() => {
    if (stage && message) {
      setStepHistory(prev => {
        // Check if this step already exists
        const exists = prev.some(step => step.stage === stage && step.message === message);
        if (!exists) {
          return [...prev, { stage, message, timestamp: new Date().toISOString() }];
        }
        return prev;
      });
    }
  }, [stage, message]);
  
  // Don't render if no task status (after all hooks)
  if (!taskStatus) {
    return null;
  }
  
  // Copy task ID to clipboard
  const copyTaskId = () => {
    if (taskId) {
      navigator.clipboard.writeText(taskId);
      setCopiedTaskId(true);
      setTimeout(() => setCopiedTaskId(false), 2000);
    }
  };
  
  // Determine if workflow is active
  const isActive = status === 'pending' || status === 'started' || status === 'running';
  const isComplete = status === 'completed';
  const isFailed = status === 'failed';
  
  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <span className="text-2xl">🧠</span>
          <span>Agent Reasoning</span>
        </h3>
        
        {/* Status Badge */}
        <div className={`
          px-3 py-1 rounded-full text-xs font-medium
          ${isActive ? 'bg-blue-100 text-blue-700' : ''}
          ${isComplete ? 'bg-green-100 text-green-700' : ''}
          ${isFailed ? 'bg-red-100 text-red-700' : ''}
        `}>
          {isActive && '⚡ Working'}
          {isComplete && '✅ Complete'}
          {isFailed && '❌ Failed'}
        </div>
      </div>
      
      {/* Task ID - Prominently displayed */}
      {taskId && (
        <div className="mb-4 p-3 bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg">
          <div className="flex items-center justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-purple-700 mb-1">Task ID</p>
              <code className="text-xs text-purple-900 font-mono break-all">
                {taskId}
              </code>
            </div>
            <button
              onClick={copyTaskId}
              className="flex-shrink-0 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-xs rounded-md transition-colors"
              title="Copy Task ID"
            >
              {copiedTaskId ? '✓ Copied!' : '📋 Copy'}
            </button>
          </div>
          {isComplete && (
            <div className="mt-2 pt-2 border-t border-purple-200">
              <p className="text-xs text-purple-700 font-medium mb-1">
                🎬 Generate Video:
              </p>
              <code className="text-xs bg-purple-100 text-purple-900 px-2 py-1 rounded block font-mono">
                uv run python run_local_job.py {taskId}
              </code>
            </div>
          )}
        </div>
      )}
      
      {/* Song Information */}
      {song && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs font-medium text-blue-700 mb-1">🎵 Selected Song</p>
          <p className="text-sm text-blue-900 font-semibold">{song.title}</p>
          {song.artist && (
            <p className="text-xs text-blue-700">by {song.artist}</p>
          )}
          {song.bpm && (
            <p className="text-xs text-blue-600 mt-1">Tempo: {song.bpm} BPM</p>
          )}
        </div>
      )}
      
      {/* Extracted Parameters - Parse from messages */}
      {message && message.includes('BPM') && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-xs font-medium text-green-700 mb-2">🎼 Music Analysis</p>
          <div className="text-xs text-green-900 space-y-1">
            {message.match(/(\d+\.?\d*)\s*BPM/) && (
              <p>• Tempo: {message.match(/(\d+\.?\d*)\s*BPM/)[1]} BPM</p>
            )}
            {message.match(/(\d+\.?\d*)s/) && (
              <p>• Duration: {message.match(/(\d+\.?\d*)s/)[1]}s</p>
            )}
          </div>
        </div>
      )}
      
      {/* Found Moves Count */}
      {message && message.includes('matching moves') && (
        <div className="mb-4 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
          <p className="text-xs font-medium text-indigo-700 mb-1">💃 Move Search Results</p>
          <p className="text-sm text-indigo-900">
            {message.match(/Found (\d+)/) ? message.match(/Found (\d+)/)[1] : '?'} moves found
          </p>
        </div>
      )}
      
      {/* Blueprint Info */}
      {message && message.includes('blueprint') && message.includes('moves') && (
        <div className="mb-4 p-3 bg-violet-50 border border-violet-200 rounded-lg">
          <p className="text-xs font-medium text-violet-700 mb-1">📋 Blueprint Generated</p>
          <p className="text-xs text-violet-900">
            {message}
          </p>
        </div>
      )}
      
      {/* Progress Bar */}
      {isActive && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              Progress
            </span>
            <span className="text-sm font-semibold text-purple-600">
              {progress || 0}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-purple-500 to-pink-500 h-2.5 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress || 0}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Step History */}
      {stepHistory.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            🔄 Execution Steps
          </h4>
          {stepHistory.map((step, index) => {
            const isCurrentStep = step.stage === stage && step.message === message;
            const isLastStep = index === stepHistory.length - 1;
            
            return (
              <ReasoningStep
                key={`${step.stage}-${index}`}
                stage={step.stage}
                message={step.message}
                isActive={isCurrentStep && isActive}
                isComplete={!isCurrentStep || (isLastStep && isComplete)}
                isFailed={isLastStep && isFailed}
              />
            );
          })}
        </div>
      )}
      
      {/* Empty State */}
      {stepHistory.length === 0 && !stage && !message && (
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-2">💭</div>
          <p className="text-sm">
            Waiting for agent to start...
          </p>
        </div>
      )}
    </div>
  );
}

export default ReasoningPanel;
