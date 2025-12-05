"""
Pytest configuration for backend tests
"""
import os
import sys

# Set environment variable to indicate we're in test mode BEFORE importing Django
os.environ['DJANGO_TESTING'] = 'true'

# Add 'test' to sys.argv so Django settings uses SQLite
if 'test' not in sys.argv:
    sys.argv.append('test')

# Configure Django settings before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

# Now import and initialize Django
import django
import pytest

# Initialize Django
django.setup()
