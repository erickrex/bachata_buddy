// Validation Utilities
// Helper functions for validating user input in forms with XSS prevention

import { isSafeInput, sanitizeString } from './sanitize';

/**
 * Validate email address format
 * @param {string} email - Email address to validate
 * @returns {boolean} True if email is valid
 */
export const validateEmail = (email) => {
  if (!email) return false;
  
  // Check for dangerous content first
  if (!isSafeInput(email)) return false;
  
  // Standard email regex pattern
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Validate username format
 * Requirements: 3-30 characters, alphanumeric + underscore only
 * @param {string} username - Username to validate
 * @returns {boolean} True if username is valid
 */
export const validateUsername = (username) => {
  if (!username) return false;
  
  // Check for dangerous content first
  if (!isSafeInput(username)) return false;
  
  // 3-30 characters, alphanumeric + underscore
  const usernameRegex = /^[a-zA-Z0-9_]{3,30}$/;
  return usernameRegex.test(username);
};

/**
 * Validate password strength
 * Requirements: Minimum 8 characters
 * @param {string} password - Password to validate
 * @returns {boolean} True if password meets minimum requirements
 */
export const validatePassword = (password) => {
  if (!password) return false;
  
  // Minimum 8 characters
  return password.length >= 8;
};

/**
 * Validate AI query length
 * Requirements: 10-500 characters
 * @param {string} query - Query text to validate
 * @returns {boolean} True if query length is valid
 */
export const validateQuery = (query) => {
  if (!query) return false;
  
  // Check for dangerous content first
  if (!isSafeInput(query)) return false;
  
  const trimmedQuery = query.trim();
  return trimmedQuery.length >= 10 && trimmedQuery.length <= 500;
};

/**
 * Get password strength assessment
 * Returns strength score (0-5) and label
 * @param {string} password - Password to assess
 * @returns {object} Object with strength (0-5) and label
 */
export const getPasswordStrength = (password) => {
  if (!password) {
    return { strength: 0, label: 'None', color: 'gray' };
  }
  
  let strength = 0;
  
  // Length checks
  if (password.length >= 8) strength++;
  if (password.length >= 12) strength++;
  
  // Character variety checks
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++; // Mixed case
  if (/\d/.test(password)) strength++; // Contains number
  if (/[^a-zA-Z0-9]/.test(password)) strength++; // Contains special character
  
  // Strength labels and colors
  const strengthLevels = [
    { label: 'Very Weak', color: 'red' },
    { label: 'Weak', color: 'orange' },
    { label: 'Fair', color: 'yellow' },
    { label: 'Good', color: 'lime' },
    { label: 'Strong', color: 'green' },
    { label: 'Very Strong', color: 'emerald' }
  ];
  
  const level = strengthLevels[Math.min(strength, 5)];
  
  return {
    strength: Math.min(strength, 5),
    label: level.label,
    color: level.color
  };
};

/**
 * Validate that two passwords match
 * @param {string} password - Original password
 * @param {string} confirmPassword - Confirmation password
 * @returns {boolean} True if passwords match
 */
export const validatePasswordMatch = (password, confirmPassword) => {
  if (!password || !confirmPassword) return false;
  return password === confirmPassword;
};

/**
 * Get detailed validation errors for username
 * @param {string} username - Username to validate
 * @returns {string|null} Error message or null if valid
 */
export const getUsernameError = (username) => {
  if (!username) {
    return 'Username is required';
  }
  
  if (username.length < 3) {
    return 'Username must be at least 3 characters';
  }
  
  if (username.length > 30) {
    return 'Username must be no more than 30 characters';
  }
  
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    return 'Username can only contain letters, numbers, and underscores';
  }
  
  return null;
};

/**
 * Get detailed validation errors for email
 * @param {string} email - Email to validate
 * @returns {string|null} Error message or null if valid
 */
export const getEmailError = (email) => {
  if (!email) {
    return 'Email is required';
  }
  
  if (!validateEmail(email)) {
    return 'Please enter a valid email address';
  }
  
  return null;
};

/**
 * Get detailed validation errors for password
 * @param {string} password - Password to validate
 * @returns {string|null} Error message or null if valid
 */
export const getPasswordError = (password) => {
  if (!password) {
    return 'Password is required';
  }
  
  if (password.length < 8) {
    return 'Password must be at least 8 characters';
  }
  
  return null;
};

/**
 * Get detailed validation errors for query
 * @param {string} query - Query to validate
 * @returns {string|null} Error message or null if valid
 */
export const getQueryError = (query) => {
  if (!query) {
    return 'Please describe your desired choreography';
  }
  
  const trimmedQuery = query.trim();
  
  if (trimmedQuery.length < 10) {
    return `Please provide more details (minimum 10 characters, currently ${trimmedQuery.length})`;
  }
  
  if (trimmedQuery.length > 500) {
    return `Description is too long (maximum 500 characters, currently ${trimmedQuery.length})`;
  }
  
  return null;
};

/**
 * Validate form data for registration
 * @param {object} formData - Form data object with username, email, password, confirmPassword
 * @returns {object} Object with isValid boolean and errors object
 */
export const validateRegistrationForm = (formData) => {
  const errors = {};
  
  const usernameError = getUsernameError(formData.username);
  if (usernameError) errors.username = usernameError;
  
  const emailError = getEmailError(formData.email);
  if (emailError) errors.email = emailError;
  
  const passwordError = getPasswordError(formData.password);
  if (passwordError) errors.password = passwordError;
  
  if (formData.password && formData.confirmPassword && 
      !validatePasswordMatch(formData.password, formData.confirmPassword)) {
    errors.confirmPassword = 'Passwords do not match';
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
};

/**
 * Validate form data for login
 * @param {object} formData - Form data object with username, password
 * @returns {object} Object with isValid boolean and errors object
 */
export const validateLoginForm = (formData) => {
  const errors = {};
  
  if (!formData.username) {
    errors.username = 'Username is required';
  }
  
  if (!formData.password) {
    errors.password = 'Password is required';
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
};

/**
 * Sanitize user input to prevent XSS
 * @param {string} input - User input to sanitize
 * @returns {string} Sanitized input
 * @deprecated Use sanitizeString from './sanitize' instead
 */
export const sanitizeInput = (input) => {
  if (!input) return '';
  
  // Use the more comprehensive sanitization from sanitize.js
  return sanitizeString(input);
};
