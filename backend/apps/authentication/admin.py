from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'display_name', 'is_instructor', 'is_staff']
    list_filter = ['is_instructor', 'is_staff', 'is_superuser']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('display_name', 'is_instructor', 'preferences')}),
    )
