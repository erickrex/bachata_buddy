import { useState } from 'react';
import { formatTime } from '../../utils/format';
import Button from '../common/Button';

const LoopControls = ({ 
  enabled, 
  start, 
  end, 
  onToggle, 
  onStartChange, 
  onEndChange 
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const loopDuration = end - start;

  const adjustStart = (delta) => {
    const newStart = Math.max(0, start + delta);
    // Ensure start is before end
    if (newStart < end) {
      onStartChange(newStart);
    }
  };

  const adjustEnd = (delta) => {
    const newEnd = end + delta;
    // Ensure end is after start
    if (newEnd > start) {
      onEndChange(newEnd);
    }
  };

  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900">🔁 Loop Controls</h3>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-gray-500 hover:text-gray-700 transition-colors"
            aria-label={isExpanded ? 'Collapse loop controls' : 'Expand loop controls'}
          >
            {isExpanded ? '▼' : '▶'}
          </button>
        </div>
        <Button
          onClick={onToggle}
          variant={enabled ? 'primary' : 'secondary'}
          size="sm"
        >
          {enabled ? 'Disable Loop' : 'Enable Loop'}
        </Button>
      </div>
      
      {isExpanded && enabled && (
        <div className="space-y-3">
          {/* Loop Start */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700 font-medium">Loop Start:</span>
            <div className="flex items-center gap-2">
              <Button 
                size="sm" 
                variant="secondary"
                onClick={() => adjustStart(-1)}
                aria-label="Decrease loop start by 1 second"
              >
                -1s
              </Button>
              <span className="font-mono text-sm min-w-[60px] text-center">
                {formatTime(start)}
              </span>
              <Button 
                size="sm" 
                variant="secondary"
                onClick={() => adjustStart(1)}
                aria-label="Increase loop start by 1 second"
              >
                +1s
              </Button>
            </div>
          </div>
          
          {/* Loop End */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700 font-medium">Loop End:</span>
            <div className="flex items-center gap-2">
              <Button 
                size="sm" 
                variant="secondary"
                onClick={() => adjustEnd(-1)}
                aria-label="Decrease loop end by 1 second"
              >
                -1s
              </Button>
              <span className="font-mono text-sm min-w-[60px] text-center">
                {formatTime(end)}
              </span>
              <Button 
                size="sm" 
                variant="secondary"
                onClick={() => adjustEnd(1)}
                aria-label="Increase loop end by 1 second"
              >
                +1s
              </Button>
            </div>
          </div>
          
          {/* Loop Duration */}
          <div className="text-sm text-gray-600 text-center pt-2 border-t border-gray-200">
            Loop Duration: <span className="font-semibold">{formatTime(loopDuration)}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoopControls;
