"""
URL Configuration for Mock Job Control Endpoints

⚠️ DEVELOPMENT ONLY - These URLs should NOT be included in production!

Include in main urls.py only when ENVIRONMENT=development:

    if os.environ.get('ENVIRONMENT', 'development') == 'development':
        urlpatterns += [
            path('api/choreography/mock/', include('apps.choreography.mock_urls')),
        ]
"""
from django.urls import path
from .mock_views import (
    complete_mock_job,
    simulate_mock_job,
    list_mock_jobs,
    update_mock_job_progress
)

urlpatterns = [
    path('complete/<uuid:task_id>', complete_mock_job, name='mock-complete'),
    path('simulate/<uuid:task_id>', simulate_mock_job, name='mock-simulate'),
    path('progress/<uuid:task_id>', update_mock_job_progress, name='mock-progress'),
    path('jobs', list_mock_jobs, name='mock-jobs'),
]
