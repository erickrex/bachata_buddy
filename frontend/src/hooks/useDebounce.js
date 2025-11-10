import { useState, useEffect } from 'react';

/**
 * Custom hook for debouncing a value
 * Useful for optimizing search inputs and reducing API calls
 * @param {*} value - The value to debounce
 * @param {number} delay - The delay in milliseconds (default: 500ms)
 * @returns {*} - The debounced value
 */
export function useDebounce(value, delay = 500) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    // Set up a timer to update the debounced value after the delay
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    // Clean up the timer if value changes before delay expires
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  
  return debouncedValue;
}
