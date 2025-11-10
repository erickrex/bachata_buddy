import { formatTime } from '../../utils/format';

const ProgressBar = ({ 
  current, 
  duration, 
  loopStart, 
  loopEnd, 
  loopEnabled, 
  onSeek 
}) => {
  const handleClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percentage = clickX / rect.width;
    const newTime = percentage * duration;
    onSeek(newTime);
  };

  const currentPercentage = duration > 0 ? (current / duration) * 100 : 0;
  const loopStartPercentage = duration > 0 ? (loopStart / duration) * 100 : 0;
  const loopEndPercentage = duration > 0 ? (loopEnd / duration) * 100 : 0;
  const loopWidth = loopEndPercentage - loopStartPercentage;

  return (
    <div className="space-y-2">
      {/* Progress bar */}
      <div 
        className="relative h-2 bg-gray-200 rounded-full cursor-pointer hover:h-3 transition-all"
        onClick={handleClick}
        role="slider"
        aria-label="Video progress"
        aria-valuemin={0}
        aria-valuemax={duration}
        aria-valuenow={current}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'ArrowLeft') {
            e.preventDefault();
            onSeek(Math.max(0, current - 5));
          } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            onSeek(Math.min(duration, current + 5));
          }
        }}
      >
        {/* Loop segment overlay (green) */}
        {loopEnabled && (
          <div
            className="absolute top-0 h-full bg-green-400 opacity-50 rounded-full"
            style={{
              left: `${loopStartPercentage}%`,
              width: `${loopWidth}%`
            }}
          />
        )}
        
        {/* Current progress (blue) */}
        <div
          className="absolute top-0 left-0 h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${currentPercentage}%` }}
        />
        
        {/* Progress handle */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-blue-600 rounded-full shadow-md"
          style={{ left: `${currentPercentage}%`, marginLeft: '-8px' }}
        />
      </div>

      {/* Time display */}
      <div className="flex justify-between text-sm text-gray-600">
        <span>{formatTime(current)}</span>
        <span>{formatTime(duration)}</span>
      </div>
    </div>
  );
};

export default ProgressBar;
