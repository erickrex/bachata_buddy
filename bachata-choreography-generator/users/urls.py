from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication views - custom login with rate limiting
    path('login/', views.login_view, name='login'),  # Custom view with rate limiting
    
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Custom registration and profile views
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    
    # User preferences API endpoints (FastAPI parity)
    path('api/preferences/', views.get_preferences, name='get_preferences'),
    path('api/preferences/update/', views.update_preferences, name='update_preferences'),
]
