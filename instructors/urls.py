from django.urls import path
from . import views

app_name = 'instructors'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),  # NEW: Dashboard statistics
    
    # Class Plan CRUD
    path('class-plan/create/', views.class_plan_create, name='class_plan_create'),
    path('class-plan/<uuid:pk>/', views.class_plan_detail, name='class_plan_detail'),
    path('class-plan/<uuid:pk>/edit/', views.class_plan_edit, name='class_plan_edit'),
    path('class-plan/<uuid:pk>/delete/', views.class_plan_delete, name='class_plan_delete'),
    
    # NEW: Advanced Class Plan Features
    path('class-plan/<uuid:pk>/summary/', views.class_plan_summary, name='class_plan_summary'),
    path('class-plan/<uuid:pk>/export/', views.class_plan_export, name='class_plan_export'),
    path('class-plan/<uuid:pk>/duplicate/', views.class_plan_duplicate, name='class_plan_duplicate'),
    
    # Sequence Management
    path('class-plan/<uuid:pk>/sequence/add/', views.sequence_add, name='sequence_add'),
    path('class-plan/<uuid:pk>/sequence/<uuid:sequence_id>/delete/', views.sequence_delete, name='sequence_delete'),
    path('class-plan/<uuid:pk>/sequence/<uuid:sequence_id>/update/', views.sequence_update, name='sequence_update'),  # NEW
    path('class-plan/<uuid:pk>/sequence/reorder/', views.sequence_reorder, name='sequence_reorder'),
]
