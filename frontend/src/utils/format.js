// Formatting Utilities
// Helper functions for formatting time, dates, file sizes, and strings

/**
 * Format seconds to MM:SS format
 * Used for video player current time display
 * @param {number} seconds - Time in seconds
 * @returns {string} Formatted time string (e.g., "3:45")
 */
export const formatTime = (seconds) => {
  if (!seconds || isNaN(seconds)) return '0:00';
  
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * Format seconds to HH:MM:SS or MM:SS format
 * Used for displaying total duration of choreographies
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration string (e.g., "1:23:45" or "23:45")
 */
export const formatDuration = (seconds) => {
  if (!seconds || isNaN(seconds)) return '0:00';
  
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * Format ISO date string to readable date
 * Used for displaying creation dates in collections
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date (e.g., "Nov 10, 2025")
 */
export const formatDate = (dateString) => {
  if (!dateString) return '';
  
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch (error) {
    console.error('Error formatting date:', error);
    return dateString;
  }
};

/**
 * Format bytes to human-readable file size
 * Used for displaying video file sizes
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size (e.g., "15.3 MB")
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  if (!bytes || isNaN(bytes)) return 'Unknown';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

/**
 * Capitalize first letter of a string
 * Used for formatting difficulty levels and other labels
 * @param {string} str - String to capitalize
 * @returns {string} Capitalized string (e.g., "beginner" -> "Beginner")
 */
export const capitalize = (str) => {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
};

/**
 * Format relative time (e.g., "2 hours ago", "3 days ago")
 * Used for showing when choreographies were created
 * @param {string} dateString - ISO date string
 * @returns {string} Relative time string
 */
export const formatRelativeTime = (dateString) => {
  if (!dateString) return '';
  
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffSecs < 60) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    
    return formatDate(dateString);
  } catch (error) {
    console.error('Error formatting relative time:', error);
    return formatDate(dateString);
  }
};

/**
 * Truncate text to specified length with ellipsis
 * Used for displaying long titles or descriptions
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} Truncated text with ellipsis if needed
 */
export const truncate = (text, maxLength = 50) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength).trim() + '...';
};

/**
 * Format BPM range for display
 * @param {number} min - Minimum BPM
 * @param {number} max - Maximum BPM
 * @returns {string} Formatted BPM range (e.g., "120-140 BPM")
 */
export const formatBPMRange = (min, max) => {
  if (!min && !max) return 'Any BPM';
  if (!max || min === max) return `${min} BPM`;
  return `${min}-${max} BPM`;
};

/**
 * Pluralize a word based on count
 * @param {number} count - Number to check
 * @param {string} singular - Singular form of word
 * @param {string} plural - Plural form of word (optional, defaults to singular + 's')
 * @returns {string} Pluralized string (e.g., "1 move", "5 moves")
 */
export const pluralize = (count, singular, plural = null) => {
  if (count === 1) return `${count} ${singular}`;
  return `${count} ${plural || singular + 's'}`;
};
