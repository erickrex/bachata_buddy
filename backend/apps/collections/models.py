from django.db import models
from django.conf import settings
import uuid


class SavedChoreography(models.Model):
    """Model for storing user's saved choreographies
    
    NOTE: This model mirrors the original choreography.models.SavedChoreography
    from the monolithic app to work with the same database during migration.
    
    TODO Phase 2 Improvements:
    - Add full-text search index on title field for better search performance
    - Consider adding tags/categories field for better organization
    - Consider adding sharing/visibility options (public/private)
    - Consider adding favorites/likes functionality
    - Consider adding view count tracking
    - Consider optimizing indexes based on query patterns
    """
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='choreographies'  # Match original related_name
    )
    title = models.CharField(max_length=200)
    video_path = models.FileField(upload_to='choreographies/%Y/%m/', max_length=500)  # Match original FileField
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
        db_table = 'saved_choreographies'  # Match original table name
        verbose_name = 'Saved Choreography'
        verbose_name_plural = 'Saved Choreographies'
    
    def __str__(self):
        return f"{self.title} ({self.difficulty})"
