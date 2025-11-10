from django.urls import path
from .views import (
    collection_list,
    collection_detail,
    collection_stats,
    save_choreography,
    delete_all_choreographies,
    cleanup_collection
)

urlpatterns = [
    path('', collection_list, name='collection-list'),
    path('save/', save_choreography, name='save-choreography'),
    path('delete-all/', delete_all_choreographies, name='delete-all-choreographies'),
    path('cleanup/', cleanup_collection, name='cleanup-collection'),
    path('stats/', collection_stats, name='collection-stats'),
    path('<uuid:pk>/', collection_detail, name='collection-detail'),
]
