/**
 * Token Security Utilities
 * 
 * Provides security checks and best practices for token storage.
 */

/**
 * Perform security check on stored tokens
 * @returns {boolean} True if tokens are valid
 */
export function performSecurityCheck() {
  try {
    const accessToken = localStorage.getItem('accessToken');
    const refreshToken = localStorage.getItem('refreshToken');
    
    // If no tokens, nothing to check
    if (!accessToken && !refreshToken) {
      return true;
    }
    
    // Basic validation - tokens should be strings
    if (accessToken && typeof accessToken !== 'string') {
      console.warn('Invalid access token format');
      return false;
    }
    
    if (refreshToken && typeof refreshToken !== 'string') {
      console.warn('Invalid refresh token format');
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('Security check failed:', error);
    return false;
  }
}

/**
 * Check security best practices
 */
export function checkSecurityBestPractices() {
  if (import.meta.env.DEV) {
    // In development, just log warnings
    if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
      console.warn('Security Warning: Not using HTTPS in non-localhost environment');
    }
  }
}

/**
 * Validate token format (basic JWT structure check)
 * @param {string} token - Token to validate
 * @returns {boolean} True if token has valid JWT structure
 */
export function isValidTokenFormat(token) {
  if (!token || typeof token !== 'string') {
    return false;
  }
  
  // JWT tokens have 3 parts separated by dots
  const parts = token.split('.');
  return parts.length === 3;
}
