import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class ChoreographyTask(models.Model):
    """Model for tracking choreography generation tasks"""
    
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    task_id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='choreography_tasks'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started', db_index=True)
    progress = models.IntegerField(default=0)
    stage = models.CharField(max_length=50, default='initializing')
    message = models.TextField(default='Starting choreography generation...')
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'choreography_tasks'
        verbose_name = 'Choreography Task'
        verbose_name_plural = 'Choreography Tasks'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Task {self.task_id} - {self.status}"
    
    def to_dict(self):
        """Convert task to dictionary for API responses"""
        return {
            'task_id': self.task_id,
            'status': self.status,
            'progress': self.progress,
            'stage': self.stage,
            'message': self.message,
            'result': self.result,
            'error': self.error,
            'user_id': self.user_id,
            'created_at': self.created_at.timestamp(),
            'updated_at': self.updated_at.timestamp(),
        }


class SavedChoreography(models.Model):
    """Model for storing user's saved choreographies"""
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='choreographies'
    )
    title = models.CharField(max_length=200)
    video_path = models.FileField(upload_to='choreographies/%Y/%m/', max_length=500)
    thumbnail_path = models.ImageField(
        upload_to='thumbnails/%Y/%m/',
        null=True,
        blank=True,
        max_length=500
    )
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, db_index=True)
    duration = models.FloatField(help_text="Duration in seconds")
    music_info = models.JSONField(null=True, blank=True)
    generation_parameters = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'saved_choreographies'
        verbose_name = 'Saved Choreography'
        verbose_name_plural = 'Saved Choreographies'
    
    def __str__(self):
        return f"{self.title} ({self.difficulty})"
