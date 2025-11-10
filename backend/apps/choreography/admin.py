from django.contrib import admin
from .models import Song, ChoreographyTask, MoveEmbedding


@admin.register(MoveEmbedding)
class MoveEmbeddingAdmin(admin.ModelAdmin):
    list_display = ['move_id', 'move_name', 'difficulty', 'energy_level', 'style', 'duration', 'created_at']
    list_filter = ['difficulty', 'energy_level', 'style', 'created_at']
    search_fields = ['move_id', 'move_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['move_name']
    
    fieldsets = (
        ('Move Information', {
            'fields': ('move_id', 'move_name', 'video_path')
        }),
        ('Embeddings', {
            'fields': ('pose_embedding', 'audio_embedding', 'text_embedding'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('difficulty', 'energy_level', 'style', 'duration')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'artist', 'genre', 'bpm', 'duration', 'created_at']
    list_filter = ['genre', 'created_at']
    search_fields = ['title', 'artist']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['title']
    
    fieldsets = (
        ('Song Information', {
            'fields': ('title', 'artist', 'genre')
        }),
        ('Audio Metadata', {
            'fields': ('duration', 'bpm', 'audio_path')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ChoreographyTask)
class ChoreographyTaskAdmin(admin.ModelAdmin):
    list_display = ['task_id', 'user', 'status', 'progress', 'stage', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['task_id', 'user__username']
    readonly_fields = ['task_id', 'created_at', 'updated_at']
    ordering = ['-created_at']
