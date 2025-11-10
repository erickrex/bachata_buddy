import { useState, useEffect } from 'react';

/**
 * Custom hook for syncing state with localStorage
 * @param {string} key - The localStorage key
 * @param {*} initialValue - The initial value if key doesn't exist
 * @returns {[*, Function]} - Returns [value, setValue] tuple
 */
export function useLocalStorage(key, initialValue) {
  // Initialize state with value from localStorage or initialValue
  const [value, setValue] = useState(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });
  
  // Update localStorage whenever value changes
  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, value]);
  
  return [value, setValue];
}
