import uuid
from django.conf import settings
from django.db import models


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
