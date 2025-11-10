// DescribeChoreo Page
// Natural language choreography description interface (Path 2)
// Allows users to describe desired choreography in plain text

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Container from '../components/layout/Container';
import QueryInput from '../components/generation/QueryInput';
import Modal from '../components/common/Modal';
import Button from '../components/common/Button';
import { api } from '../utils/api';
import { useToast } from '../hooks/useToast';

function DescribeChoreo() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Preview modal state
  const [showPreview, setShowPreview] = useState(false);
  const [parsedParameters, setParsedParameters] = useState(null);
  const [isParsing, setIsParsing] = useState(false);
  
  // Step 1: Parse the query and show parameters
  const handleParseQuery = async () => {
    setIsParsing(true);
    setError(null);
    
    try {
      const result = await api.generation.parseQuery(query);
      setParsedParameters(result.parameters);
      setShowPreview(true);
      addToast('Query parsed successfully!', 'success');
    } catch (err) {
      setError(err.message || 'Failed to parse query. Please try again.');
      addToast(err.message || 'Failed to parse query', 'error');
    } finally {
      setIsParsing(false);
    }
  };
  
  // Step 2: Generate choreography with confirmed parameters
  const handleConfirmAndGenerate = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await api.generation.withAI(query);
      
      // Navigate to progress page with task_id
      if (result.task_id) {
        addToast('Choreography generation started!', 'success');
        navigate(`/progress/${result.task_id}`);
      } else {
        throw new Error('No task ID received from server');
      }
    } catch (err) {
      const errorMessage = err.message || 'Failed to generate choreography';
      setError(errorMessage);
      addToast(errorMessage, 'error');
      setShowPreview(false);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Handle edit from preview modal
  const handleEditQuery = () => {
    setShowPreview(false);
    setParsedParameters(null);
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 py-12">
      <Container maxWidth="lg">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            ✨ Describe Your Choreography
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Tell us what kind of bachata choreography you want to create. 
            Our AI will understand your description and generate a custom routine just for you.
          </p>
        </div>
        
        {/* Main Content Card */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-6">
          <QueryInput
            value={query}
            onChange={setQuery}
            onSubmit={handleParseQuery}
            isLoading={isParsing}
            error={error}
            submitButtonText={isParsing ? 'Parsing...' : '🔍 Parse & Preview'}
          />
          
          {/* Info about the two-step process */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <div className="flex items-center justify-center gap-2 text-sm text-gray-600">
              <span className="flex items-center gap-1">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-purple-100 text-purple-600 font-semibold text-xs">1</span>
                Parse your description
              </span>
              <span className="text-gray-400">→</span>
              <span className="flex items-center gap-1">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-purple-100 text-purple-600 font-semibold text-xs">2</span>
                Review parameters
              </span>
              <span className="text-gray-400">→</span>
              <span className="flex items-center gap-1">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-purple-100 text-purple-600 font-semibold text-xs">3</span>
                Generate video
              </span>
            </div>
          </div>
        </div>
        
        {/* Info Section */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
          <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
            <span>💡</span>
            Tips for Better Results
          </h3>
          <ul className="space-y-2 text-sm text-blue-800">
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Mention the <strong>difficulty level</strong> (beginner, intermediate, or advanced)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Describe the <strong>style</strong> (romantic, energetic, sensual, playful, or modern)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Specify the <strong>energy level</strong> (low, medium, or high)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>Include any <strong>special moves</strong> or requirements you want</span>
            </li>
          </ul>
        </div>
      </Container>
      
      {/* Parameter Preview Modal */}
      {showPreview && parsedParameters && (
        <Modal
          isOpen={showPreview}
          onClose={handleEditQuery}
          title="AI Extracted Parameters"
          className="max-w-2xl"
        >
          <div className="space-y-6">
            {/* Original Query */}
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Your Query:</p>
              <div className="bg-gray-100 rounded-lg p-4">
                <p className="text-gray-800 italic">"{query}"</p>
              </div>
            </div>
            
            {/* Parsed Parameters Grid */}
            <div>
              <p className="text-sm font-medium text-gray-700 mb-3">
                ✨ AI Extracted Parameters:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Difficulty */}
                <div className="bg-purple-50 border-2 border-purple-200 rounded-lg p-4">
                  <p className="text-xs font-medium text-purple-700 mb-1">Difficulty</p>
                  <p className="text-lg font-semibold text-purple-900 capitalize">
                    {parsedParameters?.difficulty || 'intermediate'}
                  </p>
                </div>
                
                {/* Energy Level */}
                <div className="bg-pink-50 border-2 border-pink-200 rounded-lg p-4">
                  <p className="text-xs font-medium text-pink-700 mb-1">Energy Level</p>
                  <p className="text-lg font-semibold text-pink-900 capitalize">
                    {parsedParameters?.energy_level || 'medium'}
                  </p>
                </div>
                
                {/* Style */}
                <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4">
                  <p className="text-xs font-medium text-blue-700 mb-1">Style</p>
                  <p className="text-lg font-semibold text-blue-900 capitalize">
                    {parsedParameters?.style || 'modern'}
                  </p>
                </div>
                
                {/* Tempo */}
                {parsedParameters?.tempo && (
                  <div className="bg-orange-50 border-2 border-orange-200 rounded-lg p-4">
                    <p className="text-xs font-medium text-orange-700 mb-1">Tempo</p>
                    <p className="text-lg font-semibold text-orange-900 capitalize">
                      {parsedParameters.tempo}
                    </p>
                  </div>
                )}
              </div>
            </div>
            
            {/* Confidence Score */}
            {parsedParameters?.confidence !== undefined && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-gray-700">AI Confidence</p>
                  <p className="text-sm font-semibold text-gray-900">
                    {Math.round(parsedParameters.confidence * 100)}%
                  </p>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all"
                    style={{ width: `${parsedParameters.confidence * 100}%` }}
                  />
                </div>
                {parsedParameters.confidence < 0.7 && (
                  <p className="text-xs text-gray-600 mt-2">
                    💡 Low confidence - consider being more specific in your description
                  </p>
                )}
              </div>
            )}
            
            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-gray-200">
              <Button
                onClick={handleEditQuery}
                variant="secondary"
                className="flex-1"
                disabled={isLoading}
              >
                ✏️ Edit Description
              </Button>
              <Button
                onClick={handleConfirmAndGenerate}
                variant="primary"
                className="flex-1"
                disabled={isLoading}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle 
                        className="opacity-25" 
                        cx="12" 
                        cy="12" 
                        r="10" 
                        stroke="currentColor" 
                        strokeWidth="4"
                        fill="none"
                      />
                      <path 
                        className="opacity-75" 
                        fill="currentColor" 
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Generating Video...
                  </span>
                ) : (
                  '🎬 Generate Video'
                )}
              </Button>
            </div>
            
            {/* Help Text */}
            <p className="text-xs text-center text-gray-500 mt-2">
              Review the parameters above. If they look good, click "Generate Video" to start creating your choreography!
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
}

export default DescribeChoreo;
