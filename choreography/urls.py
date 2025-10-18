from django.urls import path
from . import views

app_name = 'choreography'

urlpatterns = [
    path('', views.index, name='index'),
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
