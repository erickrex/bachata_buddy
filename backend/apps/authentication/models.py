from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model for Bachata Buddy
    
    NOTE: This model extends Django's AbstractUser and uses the 'users' table
    from the monolithic app to work with the same database during migration.
    """
    display_name = models.CharField(max_length=200, blank=True)
    is_instructor = models.BooleanField(default=False)
    preferences = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'users'  # Match original table name (not 'auth_user')
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.username
