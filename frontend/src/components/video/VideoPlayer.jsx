import { useState, useRef, useEffect } from 'react';
import ProgressBar from './ProgressBar';
import LoopControls from './LoopControls';
import Button from '../common/Button';

const VideoPlayer = ({ videoUrl, taskId, onSave }) => {
  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [loopEnabled, setLoopEnabled] = useState(false);
  const [loopStart, setLoopStart] = useState(0);
  const [loopEnd, setLoopEnd] = useState(10);
  const [blobUrl, setBlobUrl] = useState(null);
  const [isLoadingVideo, setIsLoadingVideo] = useState(true);

  // Fetch video with authentication and create blob URL
  useEffect(() => {
    let objectUrl = null;
    
    const fetchVideo = async () => {
      try {
        setIsLoadingVideo(true);
        const token = localStorage.getItem('accessToken');
        
        const response = await fetch(videoUrl, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to load video');
        }
        
        const blob = await response.blob();
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      } catch (error) {
        console.error('Error loading video:', error);
      } finally {
        setIsLoadingVideo(false);
      }
    };
    
    if (videoUrl) {
      fetchVideo();
    }
    
    // Cleanup blob URL on unmount
    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [videoUrl]);

  // Update current time
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
    };

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
      // Set initial loop end to 10 seconds or video duration, whichever is smaller
      setLoopEnd(Math.min(10, video.duration));
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
    };
  }, []);

  // Loop logic
  useEffect(() => {
    if (!loopEnabled || !videoRef.current) return;

    const checkLoop = () => {
      const video = videoRef.current;
      if (video && video.currentTime >= loopEnd) {
        video.currentTime = loopStart;
      }
    };

    const interval = setInterval(checkLoop, 100);
    return () => clearInterval(interval);
  }, [loopEnabled, loopStart, loopEnd]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if user is typing in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
      }

      const video = videoRef.current;
      if (!video) return;

      switch (e.key) {
        case ' ':
          e.preventDefault();
          togglePlay();
          break;
        case 'l':
        case 'L':
          e.preventDefault();
          setLoopStart(video.currentTime);
          break;
        case 'k':
        case 'K':
          e.preventDefault();
          setLoopEnd(video.currentTime);
          break;
        case 'r':
        case 'R':
          e.preventDefault();
          toggleLoop();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          handleSeek(Math.max(0, video.currentTime - 5));
          break;
        case 'ArrowRight':
          e.preventDefault();
          handleSeek(Math.min(duration, video.currentTime + 5));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setVolume(prev => Math.min(1, prev + 0.1));
          break;
        case 'ArrowDown':
          e.preventDefault();
          setVolume(prev => Math.max(0, prev - 0.1));
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [duration, loopStart, loopEnd]);

  // Update video volume when state changes
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.volume = volume;
    }
  }, [volume]);

  // Update video playback rate when state changes
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.playbackRate = playbackRate;
    }
  }, [playbackRate]);

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;

    if (video.paused) {
      video.play();
      setIsPlaying(true);
    } else {
      video.pause();
      setIsPlaying(false);
    }
  };

  const handleSeek = (time) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = time;
    setCurrentTime(time);
  };

  const toggleLoop = () => {
    if (!loopEnabled) {
      // When enabling loop, center it on current time
      const video = videoRef.current;
      if (video) {
        const currentPos = video.currentTime;
        const newStart = Math.max(0, currentPos - 5);
        const newEnd = Math.min(duration, currentPos + 5);
        setLoopStart(newStart);
        setLoopEnd(newEnd);
      }
    }
    setLoopEnabled(!loopEnabled);
  };

  const toggleFullscreen = () => {
    const video = videoRef.current;
    if (!video) return;

    if (!document.fullscreenElement) {
      video.requestFullscreen().catch(err => {
        console.error('Error attempting to enable fullscreen:', err);
      });
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = videoUrl;
    link.download = `choreography-${taskId}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Video Element */}
      {isLoadingVideo && (
        <div className="w-full aspect-video rounded-lg shadow-lg bg-gray-900 flex items-center justify-center">
          <div className="text-white text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
            <p>Loading video...</p>
          </div>
        </div>
      )}
      <video
        ref={videoRef}
        src={blobUrl || ''}
        className={`w-full rounded-lg shadow-lg bg-black ${isLoadingVideo ? 'hidden' : ''}`}
        onClick={togglePlay}
      />
      
      {/* Custom Controls */}
      <div className="mt-4 space-y-4">
        {/* Play/Pause & Progress Bar */}
        <div className="flex items-center gap-4">
          <Button 
            onClick={togglePlay}
            variant="secondary"
            size="sm"
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? '⏸️' : '▶️'}
          </Button>
          <div className="flex-1">
            <ProgressBar
              current={currentTime}
              duration={duration}
              loopStart={loopStart}
              loopEnd={loopEnd}
              loopEnabled={loopEnabled}
              onSeek={handleSeek}
            />
          </div>
        </div>
        
        {/* Additional Controls */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            {/* Volume Control */}
            <div className="flex items-center gap-2 min-h-[44px]">
              <span className="text-sm text-gray-600">🔊</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={volume}
                onChange={(e) => setVolume(parseFloat(e.target.value))}
                className="flex-1 sm:w-24"
                aria-label="Volume"
              />
              <span className="text-sm text-gray-600 min-w-[40px]">
                {Math.round(volume * 100)}%
              </span>
            </div>
            
            {/* Playback Speed */}
            <div className="flex items-center gap-2 min-h-[44px]">
              <span className="text-sm text-gray-600">Speed:</span>
              <select
                value={playbackRate}
                onChange={(e) => setPlaybackRate(parseFloat(e.target.value))}
                className="px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 min-h-[44px]"
                aria-label="Playback speed"
              >
                <option value="0.5">0.5x</option>
                <option value="0.75">0.75x</option>
                <option value="1">1x</option>
                <option value="1.25">1.25x</option>
                <option value="1.5">1.5x</option>
              </select>
            </div>
          </div>
          
          <Button 
            onClick={toggleFullscreen}
            variant="secondary"
            size="sm"
            className="w-full sm:w-auto"
          >
            ⛶ Fullscreen
          </Button>
        </div>
        
        {/* Loop Controls */}
        <LoopControls
          enabled={loopEnabled}
          start={loopStart}
          end={loopEnd}
          onToggle={toggleLoop}
          onStartChange={setLoopStart}
          onEndChange={setLoopEnd}
        />
        
        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-2 pt-4 border-t border-gray-200">
          <Button onClick={handleDownload} variant="secondary" className="w-full sm:w-auto">
            ⬇️ Download
          </Button>
          {onSave && (
            <Button onClick={onSave} variant="primary" className="w-full sm:w-auto">
              💾 Save to Collection
            </Button>
          )}
        </div>
      </div>

      {/* Keyboard Shortcuts Help */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">⌨️ Keyboard Shortcuts</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs text-gray-600">
          <div><kbd className="px-2 py-1 bg-white border border-gray-300 rounded">Space</kbd> Play/Pause</div>
          <div><kbd className="px-2 py-1 bg-white border border-gray-300 rounded">L</kbd> Set Loop Start</div>
          <div><kbd className="px-2 py-1 bg-white border border-gray-300 rounded">K</kbd> Set Loop End</div>
          <div><kbd className="px-2 py-1 bg-white border border-gray-300 rounded">R</kbd> Toggle Loop</div>
          <div><kbd className="px-2 py-1 bg-white border border-gray-300 rounded">←/→</kbd> Seek ±5s</div>
          <div><kbd className="px-2 py-1 bg-white border border-gray-300 rounded">↑/↓</kbd> Volume ±10%</div>
        </div>
      </div>
    </div>
  );
};

export default VideoPlayer;
