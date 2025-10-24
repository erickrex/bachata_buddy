"""
URL configuration for bachata_buddy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

from choreography import views as choreography_views

def health_check(request):
    """Simple health check endpoint for Cloud Run"""
    return JsonResponse({"status": "healthy", "service": "bachata-buddy"})

urlpatterns = [
    path('health', health_check, name='health_check'),  # Health check for Cloud Run
    path('admin/', admin.site.urls),
    path('', include('choreography.urls')),
    path('api/', include('choreography.urls')),  # API endpoints with /api/ prefix
    # Direct video serving endpoints (for both /video/ and /api/video/)
    path('video/<str:filename>/', choreography_views.serve_video, name='serve_video'),
    path('api/video/<str:filename>/', choreography_views.serve_video, name='api_serve_video'),
    path('collections/', include('user_collections.urls')),
    path('auth/', include('users.urls')),
    path('instructor/', include('instructors.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
