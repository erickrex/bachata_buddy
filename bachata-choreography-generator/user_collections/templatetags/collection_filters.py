"""
Custom template filters for collection templates.
"""
import os
from django import template

register = template.Library()


@register.filter
def basename(value):
    """
    Extract the basename (filename) from a file path.
    
    Usage: {{ choreography.video_path|basename }}
    """
    if not value:
        return ''
    
    # Handle FieldFile objects
    if hasattr(value, 'name'):
        value = value.name
    
    # Convert to string and extract basename
    return os.path.basename(str(value))
