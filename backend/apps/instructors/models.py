import uuid
from django.conf import settings
from django.db import models


class ClassPlan(models.Model):
    """Model for instructor class plans
    
    NOTE: This model mirrors the original instructors.models.ClassPlan
    from the monolithic app to work with the same database during migration.
    """
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_plans',
        limit_choices_to={'is_instructor': True}
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, db_index=True)
    estimated_duration = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated duration in minutes"
    )
    instructor_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'class_plans'
        verbose_name = 'Class Plan'
        verbose_name_plural = 'Class Plans'
    
    def __str__(self):
        return f"{self.title} by {self.instructor.display_name or self.instructor.username}"


class ClassPlanSequence(models.Model):
    """Model for choreography sequences within a class plan
    
    NOTE: This model mirrors the original instructors.models.ClassPlanSequence
    from the monolithic app to work with the same database during migration.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class_plan = models.ForeignKey(
        ClassPlan,
        on_delete=models.CASCADE,
        related_name='sequences'
    )
    choreography = models.ForeignKey(
        'collections.SavedChoreography',
        on_delete=models.CASCADE,
        related_name='class_sequences'
    )
    sequence_order = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    estimated_time = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated time for this sequence in minutes"
    )
    
    class Meta:
        ordering = ['sequence_order']
        db_table = 'class_plan_sequences'
        verbose_name = 'Class Plan Sequence'
        verbose_name_plural = 'Class Plan Sequences'
        unique_together = [['class_plan', 'sequence_order']]
    
    def __str__(self):
        return f"{self.class_plan.title} - Sequence {self.sequence_order}"
