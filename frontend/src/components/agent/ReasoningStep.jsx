// ReasoningStep Component
// Displays individual reasoning step with icon, message, and status
// Styles differently for completed vs in-progress steps

import { useMemo } from 'react';

// Map stage names to icons and labels
const STAGE_CONFIG = {
  // Initial stages
  initializing: {
    icon: '🚀',
    label: 'Initializing Agent',
    color: 'blue'
  },
  parsing_request: {
    icon: '📝',
    label: 'Parsing Request',
    color: 'blue'
  },
  
  // Agent function calls
  analyze_music: {
    icon: '🎵',
    label: 'Function: analyze_music()',
    color: 'pink'
  },
  search_moves: {
    icon: '💃',
    label: 'Function: search_moves()',
    color: 'indigo'
  },
  generate_blueprint: {
    icon: '📋',
    label: 'Function: generate_blueprint()',
    color: 'violet'
  },
  assemble_video: {
    icon: '🎬',
    label: 'Function: assemble_video()',
    color: 'fuchsia'
  },
  
  // Legacy stage names (for compatibility)
  extracting_parameters: {
    icon: '🔍',
    label: 'Extracting Parameters',
    color: 'purple'
  },
  analyzing_music: {
    icon: '🎵',
    label: 'Analyzing Music',
    color: 'pink'
  },
  searching_moves: {
    icon: '💃',
    label: 'Searching Moves',
    color: 'indigo'
  },
  generating_blueprint: {
    icon: '📋',
    label: 'Generating Blueprint',
    color: 'violet'
  },
  assembling_video: {
    icon: '🎬',
    label: 'Assembling Video',
    color: 'fuchsia'
  },
  
  // Final stages
  completed: {
    icon: '✅',
    label: 'Completed',
    color: 'green'
  },
  failed: {
    icon: '❌',
    label: 'Failed',
    color: 'red'
  }
};

// Default config for unknown stages
const DEFAULT_CONFIG = {
  icon: '⚙️',
  label: 'Processing',
  color: 'gray'
};

function ReasoningStep({ 
  stage, 
  message, 
  isActive = false, 
  isComplete = false,
  isFailed = false 
}) {
  // Get stage configuration
  const config = useMemo(() => {
    return STAGE_CONFIG[stage] || DEFAULT_CONFIG;
  }, [stage]);
  
  // Determine status styling
  const getStatusStyles = () => {
    if (isFailed) {
      return {
        border: 'border-red-200',
        bg: 'bg-red-50',
        iconBg: 'bg-red-100',
        textColor: 'text-red-900',
        labelColor: 'text-red-700'
      };
    }
    
    if (isComplete) {
      return {
        border: 'border-green-200',
        bg: 'bg-green-50',
        iconBg: 'bg-green-100',
        textColor: 'text-green-900',
        labelColor: 'text-green-700'
      };
    }
    
    if (isActive) {
      return {
        border: 'border-purple-200',
        bg: 'bg-purple-50',
        iconBg: 'bg-purple-100',
        textColor: 'text-purple-900',
        labelColor: 'text-purple-700'
      };
    }
    
    return {
      border: 'border-gray-200',
      bg: 'bg-gray-50',
      iconBg: 'bg-gray-100',
      textColor: 'text-gray-900',
      labelColor: 'text-gray-700'
    };
  };
  
  const styles = getStatusStyles();
  
  return (
    <div className={`
      border ${styles.border} ${styles.bg} rounded-lg p-4
      transition-all duration-300
      ${isActive ? 'shadow-md' : 'shadow-sm'}
    `}>
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`
          ${styles.iconBg} rounded-full w-10 h-10 flex items-center justify-center
          flex-shrink-0
          ${isActive ? 'animate-pulse' : ''}
        `}>
          <span className="text-xl">
            {config.icon}
          </span>
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Stage Label */}
          <div className="flex items-center gap-2 mb-1">
            <h4 className={`font-semibold text-sm ${styles.labelColor}`}>
              {config.label}
            </h4>
            
            {/* Active Indicator */}
            {isActive && (
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse animation-delay-200" />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse animation-delay-400" />
              </div>
            )}
          </div>
          
          {/* Message */}
          <p className={`text-sm ${styles.textColor} leading-relaxed`}>
            {message}
          </p>
          
          {/* Timestamp */}
          <p className="text-xs text-gray-500 mt-2">
            {new Date().toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit',
              second: '2-digit'
            })}
          </p>
        </div>
      </div>
    </div>
  );
}

export default ReasoningStep;
