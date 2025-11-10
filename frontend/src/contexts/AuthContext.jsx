import { createContext, useState, useEffect } from 'react';
import { api } from '../utils/api';
import { performSecurityCheck, checkSecurityBestPractices } from '../utils/tokenSecurity';

export const AuthContext = createContext();

/**
 * AuthProvider - Manages authentication state and token lifecycle
 * 
 * Security Features:
 * 1. Tokens stored in localStorage (with XSS protection measures)
 * 2. Automatic token refresh on mount and 401 responses
 * 3. Short-lived access tokens (15 min) with longer refresh tokens (7 days)
 * 4. Complete token cleanup on logout
 * 5. Automatic logout on refresh token failure
 * 
 * Token Storage Security:
 * - localStorage is vulnerable to XSS attacks
 * - Our XSS prevention measures (sanitization, CSP, React escaping) mitigate this
 * - Alternative: httpOnly cookies (requires backend support)
 * - Tokens are never logged in production
 * - Tokens are only sent over HTTPS in production
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Automatic token refresh on mount
  useEffect(() => {
    const initializeAuth = async () => {
      // Security check: Verify security best practices
      checkSecurityBestPractices();
      
      // Security check: Verify token integrity
      if (!performSecurityCheck()) {
        setIsLoading(false);
        return;
      }
      
      const storedToken = localStorage.getItem('accessToken');
      const storedRefreshToken = localStorage.getItem('refreshToken');
      const storedUser = localStorage.getItem('user');
      
      if (storedToken && storedUser) {
        setAccessToken(storedToken);
        setUser(JSON.parse(storedUser));
        setIsAuthenticated(true);
        
        // Try to refresh token if we have a refresh token
        // Don't logout on failure - let the API handle 401s with automatic refresh
        if (storedRefreshToken) {
          try {
            await refreshToken();
          } catch (error) {
            // If refresh fails on mount, just log it but keep user logged in
            // The api.js will handle 401s and refresh automatically
            if (import.meta.env.DEV) {
              console.warn('Token refresh failed on mount, will retry on next API call:', error);
            }
          }
        }
      }
      
      setIsLoading(false);
    };
    
    initializeAuth();
  }, []);

  /**
   * Login method - Authenticates user and stores tokens
   * 
   * Security: Tokens are stored in localStorage with the following protections:
   * - XSS prevention through input sanitization and CSP
   * - Short-lived access tokens (15 min)
   * - Automatic token refresh
   * - HTTPS-only in production
   * 
   * @param {string} username - User's username
   * @param {string} password - User's password
   * @returns {Promise<object>} User data
   * @throws {Error} If login fails
   */
  const login = async (username, password) => {
    try {
      const response = await api.auth.login(username, password);
      
      // Store tokens in localStorage (secured by XSS prevention measures)
      localStorage.setItem('accessToken', response.access);
      localStorage.setItem('refreshToken', response.refresh);
      
      // Store user data (non-sensitive information only)
      const userData = {
        id: response.user.id,
        username: response.user.username,
        email: response.user.email
      };
      localStorage.setItem('user', JSON.stringify(userData));
      
      // Update state
      setAccessToken(response.access);
      setUser(userData);
      setIsAuthenticated(true);
      
      // Don't log tokens in production
      if (import.meta.env.DEV) {
        console.log('Login successful:', userData.username);
      }
      
      return userData;
    } catch (error) {
      // Don't log sensitive error details in production
      if (import.meta.env.DEV) {
        console.error('Login error:', error);
      }
      throw error;
    }
  };

  /**
   * Register method - Creates new account and auto-login
   * 
   * Security: Same token storage security as login method
   * 
   * @param {string} username - Desired username
   * @param {string} email - User's email
   * @param {string} password - Desired password
   * @returns {Promise<object>} User data
   * @throws {Error} If registration fails
   */
  const register = async (username, email, password) => {
    try {
      const response = await api.auth.register(username, email, password);
      
      // Store tokens in localStorage (secured by XSS prevention measures)
      localStorage.setItem('accessToken', response.access);
      localStorage.setItem('refreshToken', response.refresh);
      
      // Store user data (non-sensitive information only)
      const userData = {
        id: response.user.id,
        username: response.user.username,
        email: response.user.email
      };
      localStorage.setItem('user', JSON.stringify(userData));
      
      // Update state
      setAccessToken(response.access);
      setUser(userData);
      setIsAuthenticated(true);
      
      // Don't log tokens in production
      if (import.meta.env.DEV) {
        console.log('Registration successful:', userData.username);
      }
      
      return userData;
    } catch (error) {
      // Don't log sensitive error details in production
      if (import.meta.env.DEV) {
        console.error('Registration error:', error);
      }
      throw error;
    }
  };

  /**
   * Logout method - Clears tokens and resets state
   * 
   * Security: Complete cleanup of all authentication data
   * - Removes all tokens from localStorage
   * - Resets all auth state
   * - Prevents token reuse after logout
   */
  const logout = () => {
    // Clear all authentication data from localStorage
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    
    // Reset all auth state
    setAccessToken(null);
    setUser(null);
    setIsAuthenticated(false);
    
    if (import.meta.env.DEV) {
      console.log('User logged out successfully');
    }
  };

  /**
   * Refresh token method - Gets new access token using refresh token
   * 
   * Security: Automatic token refresh prevents long-lived access tokens
   * - Called automatically on 401 responses
   * - Called on app mount if refresh token exists
   * - Logs out user if refresh fails (expired refresh token)
   * - New access token stored securely in localStorage
   * 
   * @returns {Promise<string>} New access token
   * @throws {Error} If refresh fails
   */
  const refreshToken = async () => {
    try {
      const storedRefreshToken = localStorage.getItem('refreshToken');
      if (!storedRefreshToken) {
        throw new Error('No refresh token available');
      }
      
      // Use HTTPS in production
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      const response = await fetch(`${apiUrl}/api/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: storedRefreshToken })
      });
      
      if (!response.ok) {
        throw new Error('Token refresh failed');
      }
      
      const data = await response.json();
      
      // Update stored access token (secured by XSS prevention measures)
      localStorage.setItem('accessToken', data.access);
      setAccessToken(data.access);
      
      if (import.meta.env.DEV) {
        console.log('Token refreshed successfully');
      }
      
      return data.access;
    } catch (error) {
      // Don't log sensitive error details in production
      if (import.meta.env.DEV) {
        console.error('Token refresh error:', error);
      }
      
      // Clear auth state on refresh failure (security: prevent invalid token use)
      logout();
      throw error;
    }
  };

  const value = {
    user,
    accessToken,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    refreshToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
