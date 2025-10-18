from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model extending Django's AbstractUser"""
    display_name = models.CharField(max_length=200, blank=True)
    is_instructor = models.BooleanField(default=False)
    preferences = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return self.display_name or self.username
