"""
Rate limiting utilities for authentication endpoints.

Provides protection against brute force attacks on login endpoints.
"""

import time
from collections import defaultdict
from threading import Lock
from functools import wraps
from django.http import JsonResponse


# In-memory storage for rate limiting
# Format: {email: {'attempts': count, 'locked_until': timestamp}}
_login_attempts = defaultdict(lambda: {'attempts': 0, 'locked_until': 0})
_rate_limit_lock = Lock()

# Configuration
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
ATTEMPT_WINDOW_MINUTES = 5


def is_rate_limited(email: str) -> bool:
    """
    Check if an email is currently rate limited.
    
    Args:
        email: Email address to check
        
    Returns:
        True if rate limited, False otherwise
    """
    with _rate_limit_lock:
        current_time = time.time()
        attempt_data = _login_attempts[email]
        
        # Check if currently locked out
        if attempt_data['locked_until'] > current_time:
            return True
        
        # Reset if lockout period has passed
        if attempt_data['locked_until'] > 0 and attempt_data['locked_until'] <= current_time:
            attempt_data['attempts'] = 0
            attempt_data['locked_until'] = 0
        
        return False


def record_failed_attempt(email: str) -> None:
    """
    Record a failed login attempt.
    
    Args:
        email: Email address that failed login
    """
    with _rate_limit_lock:
        current_time = time.time()
        attempt_data = _login_attempts[email]
        
        # Increment attempts
        attempt_data['attempts'] += 1
        
        # Lock out if max attempts reached
        if attempt_data['attempts'] >= MAX_LOGIN_ATTEMPTS:
            attempt_data['locked_until'] = current_time + (LOCKOUT_DURATION_MINUTES * 60)


def record_successful_login(email: str) -> None:
    """
    Record a successful login and reset attempts.
    
    Args:
        email: Email address that successfully logged in
    """
    with _rate_limit_lock:
        if email in _login_attempts:
            _login_attempts[email] = {'attempts': 0, 'locked_until': 0}


def get_remaining_lockout_time(email: str) -> int:
    """
    Get remaining lockout time in seconds.
    
    Args:
        email: Email address to check
        
    Returns:
        Remaining lockout time in seconds, 0 if not locked out
    """
    with _rate_limit_lock:
        current_time = time.time()
        attempt_data = _login_attempts[email]
        
        if attempt_data['locked_until'] > current_time:
            return int(attempt_data['locked_until'] - current_time)
        
        return 0


def rate_limit_login(view_func):
    """
    Decorator to apply rate limiting to login views.
    
    Usage:
        @rate_limit_login
        def login_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get email from POST data
        email = request.POST.get('email', '').lower().strip()
        
        if not email:
            # No email provided, let the view handle it
            return view_func(request, *args, **kwargs)
        
        # Check if rate limited
        if is_rate_limited(email):
            remaining_time = get_remaining_lockout_time(email)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Rate limit exceeded for email: {email}")
            
            # Return 429 Too Many Requests
            if request.headers.get('Accept') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': f'Too many login attempts. Please try again in {remaining_time // 60} minutes.',
                    'retry_after': remaining_time
                }, status=429)
            else:
                from django.contrib import messages
                messages.error(request, f'Too many login attempts. Please try again in {remaining_time // 60} minutes.')
                from django.shortcuts import render
                from .forms import UserRegistrationForm
                return render(request, 'users/login.html', {
                    'form': None,
                    'rate_limited': True,
                    'retry_after': remaining_time
                }, status=429)
        
        # Call the actual view
        response = view_func(request, *args, **kwargs)
        
        # Check if login was successful or failed
        # If response is a redirect (302), login was successful
        if response.status_code == 302:
            record_successful_login(email)
        # If response shows the form again or returns error, login failed
        elif response.status_code in [200, 400, 401]:
            # Check if there's an error message indicating failed login
            if hasattr(response, 'content') and b'error' in response.content.lower():
                record_failed_attempt(email)
        
        return response
    
    return wrapper


def cleanup_old_attempts():
    """
    Clean up old rate limiting data.
    Should be called periodically to prevent memory buildup.
    """
    with _rate_limit_lock:
        current_time = time.time()
        emails_to_remove = []
        
        for email, data in _login_attempts.items():
            # Remove if lockout has expired and no recent attempts
            if data['locked_until'] < current_time and data['attempts'] == 0:
                emails_to_remove.append(email)
        
        for email in emails_to_remove:
            del _login_attempts[email]
        
        return len(emails_to_remove)
