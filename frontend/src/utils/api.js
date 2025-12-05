// API Client Utility
// Handles all HTTP requests to the backend API with authentication, token refresh, and error handling

import { sanitizeUserInput, sanitizeUrl } from './sanitize';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 30000; // 30 seconds

// DEBUG: Log the API URL being used
console.log('🔍 API_BASE_URL:', API_BASE_URL);
console.log('🔍 import.meta.env.VITE_API_URL:', import.meta.env.VITE_API_URL);
console.log('🔍 All env vars:', import.meta.env);

// DEBUG: Log all API requests
const originalFetch = window.fetch;
window.fetch = function(...args) {
  console.log('🌐 Fetch request:', args[0], args[1]);
  return originalFetch.apply(this, args);
};

// Helper to get auth token from localStorage
// Security: Token is retrieved from localStorage (secured by XSS prevention)
const getAuthToken = () => {
  return localStorage.getItem('accessToken');
};

// Helper to refresh authentication token
// Security: Automatic token refresh on 401 responses
const refreshAuthToken = async () => {
  const refreshToken = localStorage.getItem('refreshToken');
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }
  
  const response = await fetch(`${API_BASE_URL}/api/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken })
  });
  
  if (!response.ok) {
    throw new Error('Token refresh failed');
  }
  
  const data = await response.json();
  
  // Store new access token (secured by XSS prevention measures)
  localStorage.setItem('accessToken', data.access);
  
  // Don't log tokens in production
  if (import.meta.env.DEV) {
    console.log('Token refreshed in API client');
  }
  
  return data.access;
};

// Main API client function with enhanced error handling
const apiClient = async (endpoint, options = {}) => {
  const {
    method = 'GET',
    body = null,
    headers = {},
    requiresAuth = true,
    maxRetries = 3,
    currentRetry = 0
  } = options;
  
  const url = `${API_BASE_URL}${endpoint}`;
  
  const fetchOptions = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers
    }
  };
  
  // Add auth token if required
  if (requiresAuth) {
    const token = getAuthToken();
    if (token) {
      fetchOptions.headers['Authorization'] = `Bearer ${token}`;
    }
  }
  
  // Add body if present
  if (body) {
    fetchOptions.body = JSON.stringify(body);
  }
  
  // Add timeout using AbortController
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);
  fetchOptions.signal = controller.signal;
  
  try {
    const response = await fetch(url, fetchOptions);
    clearTimeout(timeoutId);
    
    // Handle 401 Unauthorized - Token expired
    // Security: Automatic token refresh or logout on auth failure
    if (response.status === 401 && requiresAuth) {
      try {
        await refreshAuthToken();
        // Retry the request with new token (don't count as retry)
        return apiClient(endpoint, { ...options, currentRetry });
      } catch (refreshError) {
        // Refresh failed - clear all auth data and redirect to login
        // Security: Complete cleanup prevents token reuse
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        window.location.href = '/login';
        throw new Error('Session expired. Please log in again.');
      }
    }
    
    // Handle 400 Bad Request - Validation errors
    if (response.status === 400) {
      const errorData = await response.json().catch(() => ({}));
      
      // Django returns validation errors as field: [messages] directly
      // Check if errorData itself contains field-level errors
      const hasFieldErrors = Object.keys(errorData).some(key => 
        Array.isArray(errorData[key]) || typeof errorData[key] === 'string'
      );
      
      if (hasFieldErrors) {
        // Format field-level validation errors
        const errorMessages = Object.entries(errorData)
          .map(([field, messages]) => {
            const msgArray = Array.isArray(messages) ? messages : [messages];
            return `${field}: ${msgArray.join(', ')}`;
          })
          .join('\n');
        throw new Error(errorMessages);
      }
      
      // Fallback to nested errors object
      if (errorData.errors && typeof errorData.errors === 'object') {
        const errorMessages = Object.entries(errorData.errors)
          .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
          .join('\n');
        throw new Error(errorMessages || 'Validation failed. Please check your input.');
      }
      
      throw new Error(errorData.detail || errorData.error || 'Invalid request. Please check your input.');
    }
    
    // Handle 500 Internal Server Error
    // Security: Don't expose system internals in error messages
    if (response.status === 500) {
      // Only log detailed errors in development
      if (import.meta.env.DEV) {
        console.error('Server error:', response.status, endpoint);
      }
      throw new Error('Something went wrong on our end. Our team has been notified. Please try again later.');
    }
    
    // Handle other HTTP errors
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || `Request failed with status ${response.status}`);
    }
    
    // Handle 204 No Content - return null instead of trying to parse JSON
    if (response.status === 204) {
      return null;
    }
    
    // Return JSON data
    return await response.json();
    
  } catch (error) {
    clearTimeout(timeoutId);
    
    // Handle timeout errors
    if (error.name === 'AbortError') {
      // Retry on timeout if retries available
      if (currentRetry < maxRetries) {
        console.log(`Request timeout, retrying... (${currentRetry + 1}/${maxRetries})`);
        // Exponential backoff: wait 1s, 2s, 4s
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, currentRetry) * 1000));
        return apiClient(endpoint, { ...options, currentRetry: currentRetry + 1 });
      }
      throw new Error('Request timeout. Please check your connection and try again.');
    }
    
    // Handle network errors
    if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
      // Retry on network error if retries available
      if (currentRetry < maxRetries) {
        console.log(`Network error, retrying... (${currentRetry + 1}/${maxRetries})`);
        // Exponential backoff: wait 1s, 2s, 4s
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, currentRetry) * 1000));
        return apiClient(endpoint, { ...options, currentRetry: currentRetry + 1 });
      }
      throw new Error('Failed to connect to server. Please check your internet connection.');
    }
    
    // Re-throw other errors (including our custom error messages)
    throw error;
  }
};

// Exported API methods organized by feature
export const api = {
  // Authentication endpoints
  auth: {
    login: (username, password) => 
      apiClient('/api/auth/login/', {
        method: 'POST',
        body: { username, password },
        requiresAuth: false
      }),
    
    register: (username, email, password) =>
      apiClient('/api/auth/register/', {
        method: 'POST',
        body: { username, email, password, password2: password },
        requiresAuth: false
      }),
    
    getProfile: () => 
      apiClient('/api/auth/me/'),
    
    updateProfile: (data) =>
      apiClient('/api/auth/me/', { 
        method: 'PUT', 
        body: data 
      }),
    
    getPreferences: () =>
      apiClient('/api/auth/preferences/'),
    
    updatePreferences: (data) =>
      apiClient('/api/auth/preferences/', {
        method: 'PUT',
        body: data
      })
  },
  
  // Song endpoints
  songs: {
    getAll: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return apiClient(`/api/choreography/songs/${query ? '?' + query : ''}`);
    },
    
    getById: (id) => 
      apiClient(`/api/choreography/songs/${id}/`)
  },
  
  // Choreography generation endpoints
  generation: {
    fromSong: (songId, difficulty, energyLevel, style) =>
      apiClient('/api/choreography/generate/', {
        method: 'POST',
        body: { 
          song_id: songId, 
          difficulty, 
          energy_level: energyLevel, 
          style 
        }
      }),
    
    withAI: (query) =>
      apiClient('/api/choreography/generate-with-ai/', {
        method: 'POST',
        body: { query }
      }),
    
    parseQuery: (query) =>
      apiClient('/api/choreography/parse-query/', {
        method: 'POST',
        body: { query }
      })
  },
  
  // Agent-based choreography generation (Path 2)
  choreography: {
    describe: (userRequest) =>
      apiClient('/api/choreography/describe/', {
        method: 'POST',
        body: { user_request: userRequest }
      })
  },
  
  // Task tracking endpoints
  tasks: {
    getStatus: (taskId) =>
      apiClient(`/api/choreography/tasks/${taskId}/`),
    
    cancel: (taskId) =>
      apiClient(`/api/choreography/tasks/${taskId}/`, { 
        method: 'DELETE' 
      }),
    
    getAll: () =>
      apiClient('/api/choreography/tasks/')
  },
  
  // Collection management endpoints
  collections: {
    getAll: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return apiClient(`/api/collections/${query ? '?' + query : ''}`);
    },
    
    getStats: () => 
      apiClient('/api/collections/stats/'),
    
    save: (taskId, title, difficulty, notes = '') =>
      apiClient('/api/collections/save/', {
        method: 'POST',
        body: { 
          task_id: taskId, 
          title, 
          difficulty, 
          notes 
        }
      }),
    
    getById: (id) =>
      apiClient(`/api/collections/${id}/`),
    
    update: (id, data) =>
      apiClient(`/api/collections/${id}/`, { 
        method: 'PUT', 
        body: data 
      }),
    
    delete: (id) =>
      apiClient(`/api/collections/${id}/`, { 
        method: 'DELETE' 
      })
  }
};

// Export the base apiClient for custom requests if needed
export default apiClient;
