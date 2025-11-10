// VideoResult Page
// Displays the generated choreography video with playback controls and save functionality

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import VideoPlayer from '../components/video/VideoPlayer';
import SaveModal from '../components/collection/SaveModal';
import Button from '../components/common/Button';
import Spinner from '../components/common/Spinner';
import Container from '../components/layout/Container';
import { api } from '../utils/api';
import { useToast } from '../hooks/useToast';
import { capitalize } from '../utils/format';

function VideoResult() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [taskData, setTaskData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  // Load task details
  useEffect(() => {
    const loadTaskDetails = async () => {
      if (!taskId) {
        setError('No task ID provided');
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        const data = await api.tasks.getStatus(taskId);
        
        // Check if task is completed
        if (data.status !== 'completed') {
          if (data.status === 'failed') {
            setError(data.error || 'Choreography generation failed');
          } else {
            // Task is still in progress, redirect to progress page
            navigate(`/progress/${taskId}`);
            return;
          }
        } else {
          setTaskData(data);
        }
      } catch (err) {
        console.error('Error loading task details:', err);
        setError(err.message || 'Failed to load choreography details');
        addToast('Failed to load choreography', 'error');
      } finally {
        setIsLoading(false);
      }
    };

    loadTaskDetails();
  }, [taskId, navigate, addToast]);

  const handleSaveClick = () => {
    setShowSaveModal(true);
  };

  const handleSaveSuccess = () => {
    setIsSaved(true);
    addToast('Choreography saved successfully!', 'success');
  };

  const handleCloseSaveModal = () => {
    setShowSaveModal(false);
  };

  // Generate default title from task data
  const getDefaultTitle = () => {
    if (!taskData) return 'My Choreography';
    
    const { song, difficulty, style } = taskData;
    
    if (song && song.title) {
      return `${song.title} - ${capitalize(difficulty || 'intermediate')}`;
    }
    
    if (style) {
      return `${capitalize(style)} ${capitalize(difficulty || 'intermediate')} Choreography`;
    }
    
    return `${capitalize(difficulty || 'intermediate')} Choreography`;
  };

  // Loading state
  if (isLoading) {
    return (
      <Container>
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
          <Spinner size="lg" />
          <p className="text-gray-600">Loading your choreography...</p>
        </div>
      </Container>
    );
  }

  // Error state
  if (error) {
    return (
      <Container>
        <div className="max-w-2xl mx-auto py-12">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <div className="text-4xl mb-4">❌</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Unable to Load Choreography
            </h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button 
                onClick={() => navigate('/select-song')}
                variant="secondary"
                className="w-full sm:w-auto"
              >
                Generate New Choreography
              </Button>
              <Button onClick={() => navigate('/collections')} className="w-full sm:w-auto">
                View My Collections
              </Button>
            </div>
          </div>
        </div>
      </Container>
    );
  }

  // No task data
  if (!taskData || !taskData.result || !taskData.result.video_url) {
    return (
      <Container>
        <div className="max-w-2xl mx-auto py-12">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
            <div className="text-4xl mb-4">⚠️</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Video Not Available
            </h2>
            <p className="text-gray-600 mb-6">
              The choreography video is not available. It may have been deleted or expired.
            </p>
            <Button onClick={() => navigate('/select-song')}>
              Generate New Choreography
            </Button>
          </div>
        </div>
      </Container>
    );
  }

  const { result, difficulty, song } = taskData;
  const videoUrl = result.video_url;

  return (
    <Container>
      <div className="max-w-5xl mx-auto py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🎬 Your Choreography is Ready!
          </h1>
          <p className="text-gray-600">
            Watch, practice with loop controls, and save to your collection
          </p>
        </div>

        {/* Video Player */}
        <div className="mb-8">
          <VideoPlayer 
            videoUrl={videoUrl}
            taskId={taskId}
            onSave={handleSaveClick}
          />
        </div>

        {/* Choreography Details */}
        {(song || difficulty || result.num_moves) && (
          <div className="bg-gray-50 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Choreography Details
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {song && (
                <div>
                  <p className="text-sm text-gray-600">Song</p>
                  <p className="font-medium text-gray-900">
                    {song.title}
                    {song.artist && ` - ${song.artist}`}
                  </p>
                </div>
              )}
              {difficulty && (
                <div>
                  <p className="text-sm text-gray-600">Difficulty</p>
                  <p className="font-medium text-gray-900">
                    {capitalize(difficulty)}
                  </p>
                </div>
              )}
              {result.num_moves && (
                <div>
                  <p className="text-sm text-gray-600">Number of Moves</p>
                  <p className="font-medium text-gray-900">
                    {result.num_moves} moves
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4">
          {!isSaved && (
            <Button 
              onClick={handleSaveClick}
              className="flex-1"
            >
              💾 Save to Collection
            </Button>
          )}
          
          {isSaved && (
            <Link to="/collections" className="flex-1">
              <Button className="w-full">
                📚 View My Collections
              </Button>
            </Link>
          )}
          
          <Button 
            onClick={() => navigate('/select-song')}
            variant="secondary"
            className="flex-1"
          >
            ✨ Generate Another
          </Button>
        </div>

        {/* Success Message */}
        {isSaved && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl">✅</span>
              <div>
                <p className="font-medium text-green-900">
                  Saved to Your Collection!
                </p>
                <p className="text-sm text-green-700">
                  You can access this choreography anytime from your collections page.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Save Modal */}
      <SaveModal
        isOpen={showSaveModal}
        onClose={handleCloseSaveModal}
        taskId={taskId}
        defaultTitle={getDefaultTitle()}
        defaultDifficulty={difficulty || 'intermediate'}
        onSaveSuccess={handleSaveSuccess}
      />
    </Container>
  );
}

export default VideoResult;
