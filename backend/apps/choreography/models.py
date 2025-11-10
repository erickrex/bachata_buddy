from django.db import models
from django.conf import settings
from django.utils import timezone


class MoveEmbedding(models.Model):
    """Store move embeddings for vector search.
    
    This model stores pre-computed embeddings for dance moves, enabling
    fast in-memory vector similarity search using FAISS.
    
    Embeddings are stored as JSON arrays and loaded into memory for search.
    """
    
    # Primary identification
    move_id = models.CharField(max_length=100, unique=True, db_index=True)
    move_name = models.CharField(max_length=200, db_index=True)
    video_path = models.CharField(
        max_length=500,
        help_text="Path to video file (local or GCS)"
    )
    
    # Embeddings stored as JSON arrays
    pose_embedding = models.JSONField(
        help_text="512D pose embedding vector"
    )
    audio_embedding = models.JSONField(
        help_text="128D audio embedding vector"
    )
    text_embedding = models.JSONField(
        help_text="384D text embedding vector"
    )
    
    # Metadata for filtering
    difficulty = models.CharField(
        max_length=20,
        db_index=True,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ]
    )
    energy_level = models.CharField(
        max_length=20,
        db_index=True,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ]
    )
    style = models.CharField(
        max_length=50,
        db_index=True,
        choices=[
            ('romantic', 'Romantic'),
            ('energetic', 'Energetic'),
            ('sensual', 'Sensual'),
            ('playful', 'Playful'),
        ]
    )
    duration = models.FloatField(help_text="Duration in seconds")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'move_embeddings'
        ordering = ['move_name']
        indexes = [
            models.Index(fields=['move_id']),
            models.Index(fields=['difficulty', 'energy_level', 'style']),
        ]
        verbose_name = 'Move Embedding'
        verbose_name_plural = 'Move Embeddings'
    
    def __str__(self):
        return f"{self.move_name} ({self.difficulty}, {self.energy_level}, {self.style})"


class Song(models.Model):
    """Pre-existing song template for choreography generation.
    
    Supports both local file paths (development) and GCS paths (production).
    Examples:
    - Local: "songs/bachata-rosa.mp3"
    - GCS: "gs://bachata-buddy-bucket/songs/bachata-rosa.mp3"
    """
    
    # Primary identification
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200, db_index=True)
    artist = models.CharField(max_length=200, db_index=True)
    
    # Audio metadata
    duration = models.FloatField(help_text="Duration in seconds")
    bpm = models.IntegerField(help_text="Beats per minute", null=True, blank=True)
    genre = models.CharField(max_length=50, db_index=True, null=True, blank=True)
    
    # Storage path (local or GCS)
    audio_path = models.CharField(
        max_length=500,
        help_text="Local path (songs/file.mp3) or GCS path (gs://bucket/songs/file.mp3)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'songs'
        ordering = ['title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['artist']),
            models.Index(fields=['genre']),
        ]
        verbose_name = 'Song'
        verbose_name_plural = 'Songs'
    
    def __str__(self):
        return f"{self.title} - {self.artist}"


class ChoreographyTask(models.Model):
    """Model for tracking choreography generation tasks
    
    NOTE: This model mirrors the original choreography.models.ChoreographyTask
    from the monolithic app to work with the same database during migration.
    The main difference is we added 'job_execution_name' for Cloud Run Jobs tracking.
    """
    
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    task_id = models.CharField(max_length=36, primary_key=True)  # Match original CharField
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
    job_execution_name = models.CharField(max_length=500, null=True, blank=True)  # New field for Cloud Run Jobs
    song = models.ForeignKey(
        'Song',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text="Song template used for generation (if applicable)"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'choreography_tasks'  # Match original table name
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


class Blueprint(models.Model):
    """Store generated blueprints for video assembly.
    
    A blueprint contains the complete specification for video generation,
    including song selection, video clip paths, timing, transitions, and
    all metadata needed to assemble the final choreography video.
    
    The blueprint is generated by the API/backend and passed to the job
    container as a JSON document via environment variable.
    """
    
    # One-to-one relationship with ChoreographyTask
    task = models.OneToOneField(
        ChoreographyTask,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='blueprint',
        help_text="The choreography task this blueprint belongs to"
    )
    
    # Blueprint JSON document
    blueprint_json = models.JSONField(
        help_text="Complete blueprint specification including moves, timing, and output config"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'blueprints'
        ordering = ['-created_at']
        verbose_name = 'Blueprint'
        verbose_name_plural = 'Blueprints'
    
    def __str__(self):
        return f"Blueprint for Task {self.task_id}"
