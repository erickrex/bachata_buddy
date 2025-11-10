from django.contrib import admin
from .models import SavedChoreography


@admin.register(SavedChoreography)
class SavedChoreographyAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'difficulty', 'duration', 'created_at']
    list_filter = ['difficulty', 'created_at']
    search_fields = ['title', 'user__username']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']
