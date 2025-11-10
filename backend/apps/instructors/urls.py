from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'class-plans', views.ClassPlanViewSet, basename='classplan')

urlpatterns = [
    path('stats/', views.instructor_stats, name='instructor-stats'),
    path('', include(router.urls)),
]
