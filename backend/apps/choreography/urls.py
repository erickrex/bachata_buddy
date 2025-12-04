from django.urls import path
from .views import (
    task_detail,
    list_tasks,
    parse_natural_language_query,
    generate_with_ai,
    list_songs,
    song_detail,
    generate_from_song,
    serve_video,
    describe_choreography
)
from .mock_views import (
    complete_mock_job,
    simulate_mock_job,
    list_mock_jobs,
    update_mock_job_progress
)

urlpatterns = [
    # Song template endpoints (Path 1)
    path('songs/', list_songs, name='list-songs'),
    path('songs/<int:song_id>/', song_detail, name='song-detail'),
    path('generate-from-song/', generate_from_song, name='generate-from-song'),
    
    # Path 2: Agent-based natural language choreography generation
    path('describe/', describe_choreography, name='describe-choreography'),
    
    # AI workflow endpoints (legacy)
    path('generate-with-ai/', generate_with_ai, name='generate-with-ai'),
    path('parse-query/', parse_natural_language_query, name='parse-query'),
    
    # Task management endpoints
    path('tasks/', list_tasks, name='list-tasks'),
    path('tasks/<uuid:task_id>/', task_detail, name='task-detail'),
    
    # Video serving endpoint
    path('videos/<uuid:task_id>/', serve_video, name='serve-video'),
    
    # Mock endpoints for local development
    path('mock/complete/<uuid:task_id>/', complete_mock_job, name='mock-complete'),
    path('mock/simulate/<uuid:task_id>/', simulate_mock_job, name='mock-simulate'),
    path('mock/progress/<uuid:task_id>/', update_mock_job_progress, name='mock-progress'),
    path('mock/jobs/', list_mock_jobs, name='mock-jobs'),
]
