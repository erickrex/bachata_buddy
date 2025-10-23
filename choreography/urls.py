from django.urls import path
from . import views

app_name = 'choreography'

urlpatterns = [
    # Default redirect to legacy template (backward compatibility)
    path('', views.index, name='index'),
    
    # Legacy template (existing - song selection)
    path('select-song/', views.select_song, name='select-song'),
    
    # NEW AI template (natural language)
    path('describe-choreo/', views.describe_choreo, name='describe-choreo'),
    
    # API endpoint for AJAX query parsing (optional enhancement)
    path('api/parse-query/', views.api_parse_query, name='api-parse-query'),
    
    # Existing endpoints
    path('create/', views.create_choreography, name='create'),
    path('task/<str:task_id>/', views.task_status, name='task_status'),
    path('video/<str:filename>/', views.serve_video, name='serve_video'),
    
    # Task management endpoints (FastAPI parity)
    path('tasks/', views.list_tasks, name='list_tasks'),
    path('task/<str:task_id>/cancel/', views.cancel_task, name='cancel_task'),
    path('task/progress/', views.task_progress, name='task_progress'),  # HTMX polling endpoint
    
    # YouTube validation endpoint (FastAPI parity)
    path('validate/youtube/', views.validate_youtube_url, name='validate_youtube'),
]
