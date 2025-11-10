import { useState, useEffect, useRef } from 'react';

/**
 * Custom hook for polling an API endpoint at regular intervals
 * Automatically stops polling when status is 'completed' or 'failed'
 * @param {Function} fetchFn - The async function to call for polling
 * @param {number} interval - The polling interval in milliseconds (default: 2000ms)
 * @param {boolean} shouldPoll - Whether polling should be active (default: true)
 * @returns {Object} - Returns { data, error, isLoading }
 */
export function usePolling(fetchFn, interval = 2000, shouldPoll = true) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const intervalRef = useRef(null);
  
  useEffect(() => {
    if (!shouldPoll) {
      setIsLoading(false);
      return;
    }
    
    const poll = async () => {
      try {
        const result = await fetchFn();
        setData(result);
        setError(null);
        
        // Stop polling if completed or failed
        if (result.status === 'completed' || result.status === 'failed') {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      } catch (err) {
        setError(err.message || 'An error occurred');
        // Stop polling on error
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } finally {
        setIsLoading(false);
      }
    };
    
    // Initial poll
    poll();
    
    // Set up interval for subsequent polls
    intervalRef.current = setInterval(poll, interval);
    
    // Cleanup function
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fetchFn, interval, shouldPoll]);
  
  return { data, error, isLoading };
}
