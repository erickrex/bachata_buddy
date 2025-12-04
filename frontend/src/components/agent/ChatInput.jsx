// ChatInput Component
// Textarea for user input with submit button
// Handles Enter key submission and disables during generation

import { useRef, useEffect } from 'react';
import Button from '../common/Button';

const MAX_LENGTH = 500;

function ChatInput({ 
  value, 
  onChange, 
  onSubmit, 
  disabled = false,
  placeholder = "Describe the choreography you want to create..."
}) {
  const textareaRef = useRef(null);
  
  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [value]);
  
  // Focus textarea on mount
  useEffect(() => {
    if (textareaRef.current && !disabled) {
      textareaRef.current.focus();
    }
  }, [disabled]);
  
  const handleChange = (e) => {
    const newValue = e.target.value;
    // Enforce max length
    if (newValue.length <= MAX_LENGTH) {
      onChange(newValue);
    }
  };
  
  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSubmit();
      }
    }
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (value.trim() && !disabled) {
      onSubmit();
    }
  };
  
  const charCount = value.length;
  const isNearLimit = charCount > MAX_LENGTH * 0.9;
  
  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-200 bg-white p-4">
      <div className="flex gap-3 items-end">
        {/* Textarea */}
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            className={`
              w-full px-4 py-3 border border-gray-300 rounded-lg resize-none
              focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
              disabled:bg-gray-100 disabled:cursor-not-allowed
              min-h-[56px] max-h-[150px]
            `}
            rows={1}
            aria-label="Chat message input"
          />
          
          {/* Character Counter */}
          <div className="flex items-center justify-between mt-1 px-1">
            <p className="text-xs text-gray-500">
              Press Enter to send, Shift+Enter for new line
            </p>
            <p 
              className={`text-xs font-medium ${
                isNearLimit ? 'text-orange-600' : 'text-gray-500'
              }`}
            >
              {charCount} / {MAX_LENGTH}
            </p>
          </div>
        </div>
        
        {/* Submit Button */}
        <Button
          type="submit"
          disabled={!value.trim() || disabled}
          className="h-[56px] px-6"
        >
          {disabled ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
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
              Generating...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <span>Send</span>
              <svg 
                className="w-4 h-4" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" 
                />
              </svg>
            </span>
          )}
        </Button>
      </div>
    </form>
  );
}

export default ChatInput;
