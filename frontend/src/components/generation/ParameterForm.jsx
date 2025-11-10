// ParameterForm Component
// Form for selecting choreography generation parameters

import { useState } from 'react';
import Card from '../common/Card';
import Button from '../common/Button';
import Select from '../common/Select';
import { formatDuration } from '../../utils/format';

function ParameterForm({ selectedSong, onSubmit, onCancel }) {
  // Form state with defaults
  const [difficulty, setDifficulty] = useState('');
  const [energyLevel, setEnergyLevel] = useState('medium');
  const [style, setStyle] = useState('modern');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validation
  const isValid = difficulty !== '';

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!isValid) return;
    
    setIsSubmitting(true);
    
    try {
      await onSubmit({
        songId: selectedSong.id,
        difficulty,
        energyLevel,
        style
      });
    } catch (error) {
      console.error('Form submission error:', error);
      setIsSubmitting(false);
    }
  };

  if (!selectedSong) return null;

  return (
    <Card className="p-6 mb-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Configure Your Choreography
          </h2>
          <p className="text-gray-600">
            Set the parameters for your custom choreography generation
          </p>
        </div>

        {/* Selected Song Display */}
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm text-purple-600 font-medium mb-1">
                Selected Song
              </p>
              <h3 className="text-lg font-semibold text-gray-900">
                {selectedSong.title}
              </h3>
              <p className="text-sm text-gray-600">
                {selectedSong.artist}
              </p>
              <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                <span>{selectedSong.bpm} BPM</span>
                <span>•</span>
                <span>{formatDuration(selectedSong.duration)}</span>
                {selectedSong.genre && (
                  <>
                    <span>•</span>
                    <span className="capitalize">{selectedSong.genre}</span>
                  </>
                )}
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onCancel}
            >
              Change Song
            </Button>
          </div>
        </div>

        {/* Difficulty Selection - Required */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Difficulty Level <span className="text-red-500">*</span>
          </label>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { value: 'beginner', label: 'Beginner', description: 'Simple moves, easy to follow' },
              { value: 'intermediate', label: 'Intermediate', description: 'Moderate complexity' },
              { value: 'advanced', label: 'Advanced', description: 'Complex moves and transitions' }
            ].map((option) => (
              <label
                key={option.value}
                className={`
                  relative flex flex-col p-4 border-2 rounded-lg cursor-pointer
                  transition-all duration-200
                  ${difficulty === option.value
                    ? 'border-purple-500 bg-purple-50'
                    : 'border-gray-200 hover:border-purple-300'
                  }
                `}
              >
                <input
                  type="radio"
                  name="difficulty"
                  value={option.value}
                  checked={difficulty === option.value}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="sr-only"
                  required
                />
                <span className="font-semibold text-gray-900 mb-1">
                  {option.label}
                </span>
                <span className="text-sm text-gray-600">
                  {option.description}
                </span>
                {difficulty === option.value && (
                  <div className="absolute top-3 right-3">
                    <svg className="w-5 h-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
              </label>
            ))}
          </div>
        </div>

        {/* Energy Level Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Energy Level
          </label>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { value: 'low', label: 'Low', description: 'Calm and relaxed' },
              { value: 'medium', label: 'Medium', description: 'Balanced energy' },
              { value: 'high', label: 'High', description: 'Fast and dynamic' }
            ].map((option) => (
              <label
                key={option.value}
                className={`
                  relative flex flex-col p-4 border-2 rounded-lg cursor-pointer
                  transition-all duration-200
                  ${energyLevel === option.value
                    ? 'border-purple-500 bg-purple-50'
                    : 'border-gray-200 hover:border-purple-300'
                  }
                `}
              >
                <input
                  type="radio"
                  name="energyLevel"
                  value={option.value}
                  checked={energyLevel === option.value}
                  onChange={(e) => setEnergyLevel(e.target.value)}
                  className="sr-only"
                />
                <span className="font-semibold text-gray-900 mb-1">
                  {option.label}
                </span>
                <span className="text-sm text-gray-600">
                  {option.description}
                </span>
                {energyLevel === option.value && (
                  <div className="absolute top-3 right-3">
                    <svg className="w-5 h-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
              </label>
            ))}
          </div>
        </div>

        {/* Style Selection */}
        <div>
          <Select
            label="Dance Style"
            value={style}
            onChange={setStyle}
            options={[
              { value: 'romantic', label: 'Romantic - Smooth and intimate' },
              { value: 'energetic', label: 'Energetic - Fast and lively' },
              { value: 'sensual', label: 'Sensual - Slow and expressive' },
              { value: 'playful', label: 'Playful - Fun and creative' },
              { value: 'modern', label: 'Modern - Contemporary fusion' }
            ]}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 pt-4">
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            className="sm:w-auto"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={!isValid || isSubmitting}
            className="flex-1 sm:flex-none"
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Generating...
              </span>
            ) : (
              '🎬 Generate Choreography'
            )}
          </Button>
        </div>

        {/* Validation Message */}
        {!isValid && (
          <p className="text-sm text-gray-500 text-center">
            Please select a difficulty level to continue
          </p>
        )}
      </form>
    </Card>
  );
}

export default ParameterForm;
