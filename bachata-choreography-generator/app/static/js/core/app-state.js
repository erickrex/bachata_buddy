/**
 * Global Application State for Alpine.js
 * Manages authentication, UI state, and notifications
 */

function appState() {
    return {
        // User authentication state
        user: {
            isAuthenticated: false,
            email: '',
            displayName: '',
            isInstructor: false,
            token: ''
        },
        
        // UI state
        showLogin: false,
        showRegister: false,
        showProfileSettings: false,
        isLoggingIn: false,
        isRegistering: false,
        isUpdatingProfile: false,
        
        // Notification system
        notification: {
            show: false,
            message: '',
            type: 'info'
        },
        
        // Initialize app
        initApp() {
            this.checkAuthStatus();
            this.setupHTMXHeaders();
        },
        
        // Check authentication status
        async checkAuthStatus() {
            const token = localStorage.getItem('auth_token');
            const userData = localStorage.getItem('user_data');
            
            if (token && userData) {
                try {
                    const response = await fetch('/api/auth/status', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    if (response.ok) {
                        const authData = await response.json();
                        this.user = { ...authData.user, isAuthenticated: true, token };
                    } else {
                        this.clearAuthData();
                    }
                } catch (e) {
                    this.clearAuthData();
                }
            } else {
                this.user.isAuthenticated = false;
            }
        },
        
        // Set up HTMX headers for authentication
        setupHTMXHeaders() {
            document.body.addEventListener('htmx:configRequest', (event) => {
                const token = this.user.token || localStorage.getItem('auth_token');
                if (token) {
                    event.detail.headers['Authorization'] = `Bearer ${token}`;
                }
            });
        },
        
        // Handle auth responses
        handleLoginResponse(event) {
            this.isLoggingIn = false;
            const xhr = event.detail.xhr;
            
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    this.user = {
                        isAuthenticated: true,
                        email: response.user.email,
                        displayName: response.user.display_name,
                        isInstructor: response.user.is_instructor,
                        token: response.tokens.access_token
                    };
                    
                    // Store in localStorage
                    localStorage.setItem('auth_token', response.tokens.access_token);
                    localStorage.setItem('user_data', JSON.stringify({
                        email: response.user.email,
                        displayName: response.user.display_name,
                        isInstructor: response.user.is_instructor
                    }));
                    
                    this.showLogin = false;
                    this.showNotification('Login successful!', 'success');
                    setTimeout(() => window.location.reload(), 1000);
                    
                } catch (e) {
                    this.showNotification('Login failed. Please try again.', 'error');
                }
            } else {
                let errorMsg = 'Login failed. Please check your credentials.';
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    errorMsg = errorData.detail || errorMsg;
                } catch (e) {}
                this.showNotification(errorMsg, 'error');
            }
        },
        
        handleRegisterResponse(event) {
            this.isRegistering = false;
            const xhr = event.detail.xhr;
            
            if (xhr.status === 201) {
                this.showRegister = false;
                this.showLogin = true;
                this.showNotification('Registration successful! Please login.', 'success');
            } else {
                let errorMsg = 'Registration failed. Please try again.';
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    errorMsg = errorData.detail || errorMsg;
                } catch (e) {}
                this.showNotification(errorMsg, 'error');
            }
        },
        
        handleProfileUpdateResponse(event) {
            this.isUpdatingProfile = false;
            const xhr = event.detail.xhr;
            
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    this.user.displayName = response.display_name;
                    
                    const userData = JSON.parse(localStorage.getItem('user_data') || '{}');
                    userData.displayName = response.display_name;
                    localStorage.setItem('user_data', JSON.stringify(userData));
                    
                    this.showProfileSettings = false;
                    this.showNotification('Profile updated successfully!', 'success');
                    
                } catch (e) {
                    this.showNotification('Profile update failed. Please try again.', 'error');
                }
            } else {
                let errorMsg = 'Profile update failed. Please try again.';
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    errorMsg = errorData.detail || errorMsg;
                } catch (e) {}
                this.showNotification(errorMsg, 'error');
            }
        },
        
        // Auth actions
        startLogin() { this.isLoggingIn = true; },
        startRegistration() { this.isRegistering = true; },
        startProfileUpdate() { this.isUpdatingProfile = true; },
        
        logout() {
            this.clearAuthData();
            this.showNotification('Logged out successfully', 'info');
            setTimeout(() => window.location.reload(), 1000);
        },
        
        clearAuthData() {
            this.user = {
                isAuthenticated: false, email: '', displayName: '', 
                isInstructor: false, token: ''
            };
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_data');
        },
        
        // Notification system
        showNotification(message, type = 'info') {
            this.notification = { show: true, message, type };
            setTimeout(() => this.hideNotification(), 5000);
        },
        
        hideNotification() {
            this.notification.show = false;
        }
    }
}

// Make available globally for Alpine.js
window.appState = appState;
