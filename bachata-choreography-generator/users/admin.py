from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for custom User model"""
    
    list_display = ['email', 'display_name', 'is_instructor', 'is_staff', 'date_joined']
    list_filter = ['is_instructor', 'is_staff', 'is_active']
    search_fields = ['email', 'username', 'display_name']
    
    # Add custom fields to the fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('display_name', 'is_instructor', 'preferences')
        }),
    )
    
    # Add custom fields to add_fieldsets (for creating new users)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {
            'fields': ('display_name', 'is_instructor', 'preferences')
        }),
    )
