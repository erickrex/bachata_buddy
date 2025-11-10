/**
 * Input Sanitization Utilities
 * 
 * Provides functions to sanitize user input and prevent XSS attacks.
 * React automatically escapes content in JSX, but these utilities provide
 * additional protection for edge cases.
 */

/**
 * Sanitize user input by removing potentially dangerous characters
 * @param {string} input - User input to sanitize
 * @returns {string} Sanitized input
 */
export function sanitizeUserInput(input) {
  if (typeof input !== 'string') {
    return '';
  }
  
  // Remove any HTML tags
  return input
    .replace(/<[^>]*>/g, '')
    .trim();
}

/**
 * Alias for sanitizeUserInput for backward compatibility
 */
export const sanitizeString = sanitizeUserInput;

/**
 * Check if input is safe (doesn't contain dangerous patterns)
 * @param {string} input - Input to check
 * @returns {boolean} True if input is safe
 */
export function isSafeInput(input) {
  if (typeof input !== 'string') {
    return false;
  }
  
  // Check for script tags
  if (/<script/i.test(input)) {
    return false;
  }
  
  // Check for javascript: protocol
  if (/javascript:/i.test(input)) {
    return false;
  }
  
  // Check for on* event handlers
  if (/on\w+\s*=/i.test(input)) {
    return false;
  }
  
  return true;
}

/**
 * Sanitize URL to prevent javascript: and data: URLs
 * @param {string} url - URL to sanitize
 * @returns {string} Sanitized URL or empty string if invalid
 */
export function sanitizeUrl(url) {
  if (typeof url !== 'string') {
    return '';
  }
  
  const trimmedUrl = url.trim().toLowerCase();
  
  // Block dangerous protocols
  if (
    trimmedUrl.startsWith('javascript:') ||
    trimmedUrl.startsWith('data:') ||
    trimmedUrl.startsWith('vbscript:')
  ) {
    return '';
  }
  
  return url.trim();
}

/**
 * Escape HTML special characters
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
export function escapeHtml(text) {
  if (typeof text !== 'string') {
    return '';
  }
  
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
    '/': '&#x2F;'
  };
  
  return text.replace(/[&<>"'/]/g, (char) => map[char]);
}

/**
 * Validate and sanitize email address
 * @param {string} email - Email to sanitize
 * @returns {string} Sanitized email
 */
export function sanitizeEmail(email) {
  if (typeof email !== 'string') {
    return '';
  }
  
  return email.trim().toLowerCase();
}
