from django.urls import path
from . import views

app_name = 'collections'

urlpatterns = [
    path('', views.collection_list, name='list'),
    path('<uuid:pk>/', views.choreography_detail, name='detail'),
    path('<uuid:pk>/edit/', views.choreography_edit, name='edit'),
    path('<uuid:pk>/update/', views.choreography_update, name='update'),  # API update endpoint
    path('<uuid:pk>/delete/', views.delete_choreography, name='delete'),  # Delete single choreography
    path('delete-all/', views.delete_all_choreographies, name='delete_all'),  # Delete all choreographies
    path('save/', views.save_choreography, name='save'),
    path('stats/', views.collection_stats, name='stats'),
    path('cleanup/', views.collection_cleanup, name='cleanup'),  # Cleanup orphaned files
]
