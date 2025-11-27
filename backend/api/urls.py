"""
URL configuration for Bachata Buddy REST API.
"""
import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint for Cloud Run"""
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check
    path('api/health', health_check, name='health-check'),
    
    # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # API endpoints
    path('api/auth/', include('apps.authentication.urls')),
    path('api/choreography/', include('apps.choreography.urls')),
    path('api/collections/', include('apps.collections.urls')),
    path('api/instructors/', include('apps.instructors.urls')),
]

# Include mock endpoints only in development
if os.environ.get('ENVIRONMENT', 'development') == 'development':
    urlpatterns += [
        path('api/choreography/mock/', include('apps.choreography.mock_urls')),
    ]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
