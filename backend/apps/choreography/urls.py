from django.urls import path
from .views import (
    parse_natural_language_query,
    generate_with_ai,
    list_songs,
    song_detail,
    describe_choreography,
    generate_choreography
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
    
    # New synchronous video generation endpoint
    path('generate/', generate_choreography, name='generate-choreography'),
    
    # Path 2: Agent-based natural language choreography generation
    path('describe/', describe_choreography, name='describe-choreography'),
    
    # AI workflow endpoints (legacy)
    path('generate-with-ai/', generate_with_ai, name='generate-with-ai'),
    path('parse-query/', parse_natural_language_query, name='parse-query'),
    
    # Mock endpoints for local development
    path('mock/complete/<uuid:task_id>/', complete_mock_job, name='mock-complete'),
    path('mock/simulate/<uuid:task_id>/', simulate_mock_job, name='mock-simulate'),
    path('mock/progress/<uuid:task_id>/', update_mock_job_progress, name='mock-progress'),
    path('mock/jobs/', list_mock_jobs, name='mock-jobs'),
]
