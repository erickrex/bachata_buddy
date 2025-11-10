// QueryInput Component
// Large auto-resizing textarea for natural language choreography description
// with character counter, example queries, and validation

import { useEffect, useRef } from 'react';
import Button from '../common/Button';

const EXAMPLE_QUERIES = [
  "Create a romantic beginner bachata with smooth transitions",
  "I want an energetic intermediate choreography with lots of turns",
  "Make me an advanced sensual routine to a slow song",
  "Generate a playful beginner routine with simple footwork",
  "Create an intermediate modern bachata with body rolls and styling"
];

const MIN_LENGTH = 10;
const MAX_LENGTH = 500;

function QueryInput({ 
  value, 
  onChange, 
  onSubmit, 
  isLoading = false,
  error = null,
  submitButtonText = '✨ Generate Choreography'
}) {
  const textareaRef = useRef(null);
  
  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  }, [value]);
  
  const handleChange = (e) => {
    const newValue = e.target.value;
    // Enforce max length
    if (newValue.length <= MAX_LENGTH) {
      onChange(newValue);
    }
  };
  
  const handleExampleClick = (example) => {
    onChange(example);
    textareaRef.current?.focus();
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (isValid && !isLoading) {
      onSubmit();
    }
  };
  
  const isValid = value.trim().length >= MIN_LENGTH && value.length <= MAX_LENGTH;
  const charCount = value.length;
  const isNearLimit = charCount > MAX_LENGTH * 0.9;
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Main Textarea */}
      <div>
        <label 
          htmlFor="query-input"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          Describe Your Choreography
          <span className="text-red-500 ml-1">*</span>
        </label>
        
        <textarea
          ref={textareaRef}
          id="query-input"
          value={value}
          onChange={handleChange}
          placeholder="Describe the choreography you want to create. Be specific about difficulty, style, energy level, and any special moves or requirements..."
          className={`
            w-full px-4 py-3 border rounded-lg resize-none
            focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
            disabled:bg-gray-100 disabled:cursor-not-allowed
            min-h-[120px] max-h-[300px]
            ${error ? 'border-red-500' : 'border-gray-300'}
          `}
          disabled={isLoading}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? 'query-error' : 'query-help'}
          rows={4}
        />
        
        {/* Character Counter */}
        <div className="flex items-center justify-between mt-2">
          <p 
            id="query-help"
            className="text-sm text-gray-600"
          >
            Minimum {MIN_LENGTH} characters required
          </p>
          <p 
            className={`text-sm font-medium ${
              isNearLimit ? 'text-orange-600' : 
              charCount >= MIN_LENGTH ? 'text-green-600' : 
              'text-gray-500'
            }`}
          >
            {charCount} / {MAX_LENGTH}
          </p>
        </div>
        
        {/* Error Message */}
        {error && (
          <p 
            id="query-error"
            className="mt-2 text-sm text-red-600"
            role="alert"
          >
            {error}
          </p>
        )}
      </div>
      
      {/* Example Queries */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">
          💡 Example Queries (click to use):
        </p>
        <div className="space-y-2">
          {EXAMPLE_QUERIES.map((example, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleExampleClick(example)}
              disabled={isLoading}
              className="
                w-full text-left px-4 py-2 
                bg-gray-50 hover:bg-purple-50 
                border border-gray-200 hover:border-purple-300
                rounded-lg text-sm text-gray-700
                transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
                focus:outline-none focus:ring-2 focus:ring-purple-500
              "
            >
              "{example}"
            </button>
          ))}
        </div>
      </div>
      
      {/* Submit Button */}
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={!isValid || isLoading}
          size="lg"
          className="min-w-[200px]"
        >
          {submitButtonText}
        </Button>
      </div>
      
      {/* Validation Hint */}
      {!isValid && charCount > 0 && charCount < MIN_LENGTH && (
        <p className="text-sm text-orange-600 text-center">
          Please add {MIN_LENGTH - charCount} more character{MIN_LENGTH - charCount !== 1 ? 's' : ''} to continue
        </p>
      )}
    </form>
  );
}

export default QueryInput;
