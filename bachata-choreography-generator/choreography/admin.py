from django.contrib import admin
from .models import SavedChoreography


@admin.register(SavedChoreography)
class SavedChoreographyAdmin(admin.ModelAdmin):
    """Admin interface for SavedChoreography model"""
    
    list_display = ['title', 'user', 'difficulty', 'duration', 'created_at']
    list_filter = ['difficulty', 'created_at']
    search_fields = ['title', 'user__email', 'user__display_name']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'title', 'difficulty')
        }),
        ('Media', {
            'fields': ('video_path', 'thumbnail_path')
        }),
        ('Metadata', {
            'fields': ('duration', 'music_info', 'generation_parameters')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
