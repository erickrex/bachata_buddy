from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UserProfileForm


def register(request):
    """
    User registration view.
    
    Handles GET and POST requests for user registration.
    Creates a new User with hashed password and display_name.
    Redirects to login page on success.
    """
    try:
        if request.method == 'POST':
            form = UserRegistrationForm(request.POST)
            if form.is_valid():
                try:
                    user = form.save()
                    messages.success(request, 'Registration successful! Please log in.')
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"New user registered: {user.email}")
                    return redirect('users:login')
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error saving user during registration: {e}", exc_info=True)
                    messages.error(request, 'An error occurred during registration. Please try again.')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = UserRegistrationForm()
        
        return render(request, 'users/register.html', {
            'form': form
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in registration view: {e}", exc_info=True)
        messages.error(request, 'An unexpected error occurred. Please try again.')
        return render(request, 'users/register.html', {
            'form': UserRegistrationForm()
        })


@login_required
def profile(request):
    """
    User profile view.
    
    Displays user information and allows updating display_name and preferences.
    """
    try:
        if request.method == 'POST':
            form = UserProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                try:
                    form.save()
                    messages.success(request, 'Profile updated successfully!')
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Profile updated for user {request.user.id}")
                    return redirect('users:profile')
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error saving profile for user {request.user.id}: {e}", exc_info=True)
                    messages.error(request, 'An error occurred while saving your profile.')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = UserProfileForm(instance=request.user)
        
        return render(request, 'users/profile.html', {
            'form': form
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in profile view for user {request.user.id}: {e}", exc_info=True)
        messages.error(request, 'An unexpected error occurred.')
        return render(request, 'users/profile.html', {
            'form': UserProfileForm(instance=request.user)
        })


from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json


@login_required
def get_preferences(request):
    """
    Get current user's preferences.
    
    Returns JSON with user preferences including auto-save settings.
    FastAPI parity: GET /api/auth/preferences
    """
    preferences = request.user.preferences or {"auto_save_choreographies": True}
    return JsonResponse({"preferences": preferences})


@login_required
@require_http_methods(["POST", "PUT"])
def update_preferences(request):
    """
    Update current user's preferences.
    
    Accepts JSON body with preference updates.
    Validates preference keys and values.
    FastAPI parity: PUT /api/auth/preferences
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)
        
        # Validate preferences structure
        valid_keys = {"auto_save_choreographies"}
        if not all(key in valid_keys for key in data.keys()):
            return JsonResponse({
                'error': 'Invalid preference keys'
            }, status=400)
        
        # Validate auto_save_choreographies value
        if "auto_save_choreographies" in data:
            if not isinstance(data["auto_save_choreographies"], bool):
                return JsonResponse({
                    'error': 'auto_save_choreographies must be a boolean'
                }, status=400)
        
        # Update user preferences
        request.user.preferences = data
        request.user.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Preferences updated successfully',
            'preferences': request.user.preferences
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to update preferences: {str(e)}'
        }, status=500)



from django.contrib.auth import authenticate, login as auth_login
from django.shortcuts import render, redirect
from .rate_limiting import rate_limit_login, is_rate_limited, record_failed_attempt, record_successful_login, get_remaining_lockout_time


@rate_limit_login
def login_view(request):
    """
    Custom login view with rate limiting.
    
    FastAPI parity: POST /auth/login with rate limiting
    Implements protection against brute force attacks.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').lower().strip()
        password = request.POST.get('password', '')
        
        logger.info(f"Login attempt for email: {email}")
        
        if not email or not password:
            logger.warning(f"Login attempt missing credentials - email: {bool(email)}, password: {bool(password)}")
            messages.error(request, 'Please provide both email and password.')
            return render(request, 'users/login.html')
        
        # Try to find user by email first
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = None
        try:
            # Look up user by email
            user_obj = User.objects.get(email=email)
            logger.info(f"Found user by email: {email}, username: {user_obj.username}, is_active: {user_obj.is_active}")
            
            # Authenticate using the username field
            user = authenticate(request, username=user_obj.username, password=password)
            logger.info(f"Authentication result for {email}: {user is not None}")
            
        except User.DoesNotExist:
            logger.warning(f"User not found by email: {email}, trying email as username")
            # User not found by email, try authenticating with email as username (fallback)
            user = authenticate(request, username=email, password=password)
            logger.info(f"Fallback authentication result for {email}: {user is not None}")
        except Exception as e:
            logger.error(f"Error during user lookup for {email}: {e}", exc_info=True)
        
        if user is not None:
            # Login successful
            auth_login(request, user)
            record_successful_login(email)
            
            logger.info(f"✅ User logged in successfully: {email}")
            
            # Redirect to next page or home
            next_url = request.GET.get('next', '/')
            logger.info(f"Redirecting to: {next_url}")
            return redirect(next_url)
        else:
            # Login failed
            record_failed_attempt(email)
            
            logger.warning(f"❌ Failed login attempt for: {email} - authentication returned None")
            
            messages.error(request, 'Invalid email or password.')
            return render(request, 'users/login.html')
    
    # GET request - show login form
    return render(request, 'users/login.html')
