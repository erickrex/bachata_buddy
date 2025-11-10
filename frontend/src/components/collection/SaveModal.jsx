// SaveModal Component
// Modal for saving choreography to user's collection with title, difficulty, and notes

import { useState } from 'react';
import Modal from '../common/Modal';
import Input from '../common/Input';
import Select from '../common/Select';
import Button from '../common/Button';
import { api } from '../../utils/api';
import { useToast } from '../../hooks/useToast';

function SaveModal({ 
  isOpen,
  onClose,
  taskId,
  defaultTitle = '',
  defaultDifficulty = 'intermediate',
  onSaveSuccess
}) {
  const [title, setTitle] = useState(defaultTitle);
  const [difficulty, setDifficulty] = useState(defaultDifficulty);
  const [notes, setNotes] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const { addToast } = useToast();

  const difficultyOptions = [
    { value: 'beginner', label: 'Beginner' },
    { value: 'intermediate', label: 'Intermediate' },
    { value: 'advanced', label: 'Advanced' }
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate title
    if (!title.trim()) {
      setError('Title is required');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await api.collections.save(taskId, title.trim(), difficulty, notes.trim());
      
      // Show success toast
      addToast('Choreography saved to your collection!', 'success');
      
      // Call success callback if provided
      if (onSaveSuccess) {
        onSaveSuccess();
      }
      
      // Close modal
      onClose();
      
      // Reset form
      setTitle(defaultTitle);
      setDifficulty(defaultDifficulty);
      setNotes('');
    } catch (err) {
      console.error('Error saving to collection:', err);
      setError(err.message || 'Failed to save choreography. Please try again.');
      addToast('Failed to save choreography', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkip = () => {
    // Reset form and close
    setTitle(defaultTitle);
    setDifficulty(defaultDifficulty);
    setNotes('');
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={handleSkip}
      title="💾 Save to Your Collection"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="My Awesome Choreography"
          required
          disabled={isLoading}
          error={error && !title.trim() ? 'Title is required' : null}
        />
        
        <Select
          label="Difficulty"
          value={difficulty}
          onChange={setDifficulty}
          options={difficultyOptions}
          required
          disabled={isLoading}
        />
        
        <div>
          <label 
            htmlFor="notes-textarea"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Notes (optional)
          </label>
          <textarea
            id="notes-textarea"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="Add any notes about this choreography..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            disabled={isLoading}
            maxLength={500}
          />
          <p className="mt-1 text-xs text-gray-500">
            {notes.length}/500 characters
          </p>
        </div>
        
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
        
        <div className="flex gap-3 pt-2">
          <Button 
            type="button" 
            onClick={handleSkip} 
            variant="secondary"
            disabled={isLoading}
            className="flex-1"
          >
            Skip
          </Button>
          <Button 
            type="submit" 
            disabled={isLoading || !title.trim()}
            className="flex-1"
          >
            {isLoading ? 'Saving...' : '💾 Save to Collection'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default SaveModal;
