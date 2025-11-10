"""
Pytest configuration for backend tests
"""
import os
import sys
import django
import pytest

# Add 'test' to sys.argv so Django settings uses SQLite
if 'test' not in sys.argv:
    sys.argv.append('test')

# Configure Django settings before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

# Initialize Django
django.setup()
