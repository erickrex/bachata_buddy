"""
Django settings for Bachata Buddy REST API.

Microservices architecture - API service only.

This settings file is configured to work in two environments:
1. Local Development: Docker Compose with local PostgreSQL and Elasticsearch
2. Cloud Run Production: Cloud SQL (Unix socket), Elasticsearch Serverless, GCS

Environment detection:
- IS_CLOUD_RUN: Detected via K_SERVICE environment variable (set by Cloud Run)
- ENVIRONMENT: Explicitly set to 'local', 'staging', or 'production'
"""

from pathlib import Path
from datetime import timedelta
import os
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Environment detection
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'local')
IS_CLOUD_RUN = os.environ.get('K_SERVICE') is not None  # Cloud Run sets K_SERVICE

# ALLOWED_HOSTS configuration
if IS_CLOUD_RUN:
    # Cloud Run: Allow Cloud Run URLs
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
else:
    # Local development
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')

# Add testserver for Django tests
if 'test' in sys.argv or os.environ.get('PYTEST_CURRENT_TEST'):
    ALLOWED_HOSTS.append('testserver')

# CSRF trusted origins for Cloud Run
CSRF_TRUSTED_ORIGINS = [
    f'https://{host}' for host in ALLOWED_HOSTS 
    if host not in ['localhost', '127.0.0.1', '0.0.0.0', '*']
]

# Add Cloud Run service URL if available
if IS_CLOUD_RUN:
    service_url = os.environ.get('K_SERVICE_URL')
    if service_url and service_url not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(service_url)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'drf_spectacular_sidecar',  # Provides Swagger UI static files
    'django_filters',
    
    # Local apps
    'apps.authentication',
    'apps.choreography',
    'apps.collections',
    'apps.instructors',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'api.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

CLOUD_SQL_CONNECTION_NAME = os.environ.get('CLOUD_SQL_CONNECTION_NAME')

# Database configuration
import sys

# Use SQLite for testing
if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
elif IS_CLOUD_RUN and CLOUD_SQL_CONNECTION_NAME:
    # Production: Cloud Run with Cloud SQL Unix socket
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'bachata_buddy'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': f'/cloudsql/{CLOUD_SQL_CONNECTION_NAME}',
            'CONN_MAX_AGE': 60,  # Connection pooling
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }
else:
    # Local development: TCP/IP connection
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'bachata_buddy'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('DB_HOST', 'db'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 0,  # No connection pooling for local dev
        }
    }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
# Disabled: Allow any password for easier user registration
AUTH_PASSWORD_VALIDATORS = []

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'authentication.User'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS Settings
if IS_CLOUD_RUN:
    # Production: Specific frontend origins
    CORS_ALLOWED_ORIGINS = os.environ.get(
        'CORS_ALLOWED_ORIGINS',
        ''
    ).split(',')
    # Filter out empty strings
    CORS_ALLOWED_ORIGINS = [origin for origin in CORS_ALLOWED_ORIGINS if origin]
    CORS_ALLOW_ALL_ORIGINS = False
else:
    # Local development: Allow all origins for easier development
    # This includes Swagger UI, frontend, and any other local tools
    CORS_ALLOW_ALL_ORIGINS = True
    # Fallback to specific origins if CORS_ALLOW_ALL_ORIGINS causes issues
    CORS_ALLOWED_ORIGINS = os.environ.get(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,http://localhost:3000,http://localhost:8001,http://127.0.0.1:5173,http://127.0.0.1:3000,http://127.0.0.1:8001'
    ).split(',')

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# OpenAPI/Swagger Settings
# Determine the correct server URL based on environment
if IS_CLOUD_RUN:
    # In production, use the Cloud Run service URL
    SPECTACULAR_SERVERS = [
        {'url': os.environ.get('K_SERVICE_URL', 'https://api.example.com'), 'description': 'Production server'},
    ]
else:
    # In local development, use localhost:8001 (external port)
    SPECTACULAR_SERVERS = [
        {'url': 'http://localhost:8001', 'description': 'Local development server'},
        {'url': 'http://127.0.0.1:8001', 'description': 'Local development server (127.0.0.1)'},
    ]

SPECTACULAR_SETTINGS = {
    'TITLE': 'Bachata Buddy API',
    'DESCRIPTION': 'REST API for Bachata Buddy choreography generation platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVERS': SPECTACULAR_SERVERS,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
    'PREPROCESSING_HOOKS': [],
    'POSTPROCESSING_HOOKS': [],
    'ENUM_NAME_OVERRIDES': {},
}

# Google Cloud Settings
GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'local-dev')
GCP_REGION = os.environ.get('GCP_REGION', 'us-central1')

# Cloud Run Jobs Settings
CLOUD_RUN_JOB_NAME = os.environ.get('CLOUD_RUN_JOB_NAME', 'video-processor')

# Elasticsearch Settings
if IS_CLOUD_RUN:
    # Production: Elasticsearch Serverless
    ELASTICSEARCH_HOST = os.environ.get('ELASTICSEARCH_HOST', '')
    ELASTICSEARCH_API_KEY = os.environ.get('ELASTICSEARCH_API_KEY', '')
    ELASTICSEARCH_URL = f'https://{ELASTICSEARCH_HOST}' if ELASTICSEARCH_HOST else ''
else:
    # Local development: Docker Elasticsearch
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL', 'http://elasticsearch:9200')
    ELASTICSEARCH_HOST = ''
    ELASTICSEARCH_API_KEY = ''

ELASTICSEARCH_INDEX = os.environ.get('ELASTICSEARCH_INDEX', 'bachata_move_embeddings')

# Google Cloud Storage Settings
if IS_CLOUD_RUN:
    # Production: Use GCS
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
    USE_GCS = True
else:
    # Local development: Use local filesystem
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', '')
    USE_GCS = False

# Media files configuration
if USE_GCS:
    # Production: Store media in GCS
    DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
    GS_BUCKET_NAME = GCS_BUCKET_NAME
    MEDIA_URL = f'https://storage.googleapis.com/{GCS_BUCKET_NAME}/'
else:
    # Local development: Store media locally
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# Logging
if IS_CLOUD_RUN:
    # Production: Structured logging for Cloud Logging
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                'format': '{"severity": "%(levelname)s", "time": "%(asctime)s", "message": "%(message)s", "module": "%(module)s"}',
                'datefmt': '%Y-%m-%dT%H:%M:%S',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'json',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': os.environ.get('LOG_LEVEL', 'INFO'),
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
                'propagate': False,
            },
            'django.request': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
        },
    }
else:
    # Local development: Human-readable logging
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
                'propagate': False,
            },
        },
    }

# Security settings for production
if IS_CLOUD_RUN:
    # Production security settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    # Local development: Disable security features
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# =============================================================================
# CORS Configuration
# =============================================================================
# Allow frontend to make requests to the API from different origins

if IS_CLOUD_RUN:
    # Production: Allow specific frontend domains
    CORS_ALLOWED_ORIGINS = os.environ.get(
        'CORS_ALLOWED_ORIGINS',
        ''
    ).split(',') if os.environ.get('CORS_ALLOWED_ORIGINS') else []
    
    # Allow credentials (cookies, authorization headers)
    CORS_ALLOW_CREDENTIALS = True
else:
    # Local development: Allow localhost on common ports
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:5173',  # Vite dev server
        'http://localhost:3000',  # Alternative React port
        'http://127.0.0.1:5173',
        'http://127.0.0.1:3000',
    ]
    
    # Allow credentials
    CORS_ALLOW_CREDENTIALS = True
    
    # For local development, you can also use CORS_ALLOW_ALL_ORIGINS = True
    # but it's better to be explicit for security

# Allow common headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Allow common methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# =============================================================================
# GPU Acceleration Configuration
# =============================================================================
# GPU acceleration for vector search, video encoding, and audio processing
# Requires NVIDIA GPU with CUDA support (e.g., L4 on Cloud Run)

# Global GPU enable/disable flag
USE_GPU = os.environ.get('USE_GPU', 'false').lower() == 'true'

# Per-service GPU flags
FAISS_USE_GPU = os.environ.get('FAISS_USE_GPU', str(USE_GPU)).lower() == 'true'
FFMPEG_USE_NVENC = os.environ.get('FFMPEG_USE_NVENC', str(USE_GPU)).lower() == 'true'
AUDIO_USE_GPU = os.environ.get('AUDIO_USE_GPU', str(USE_GPU)).lower() == 'true'

# GPU memory settings
GPU_MEMORY_FRACTION = float(os.environ.get('GPU_MEMORY_FRACTION', '0.8'))

# GPU fallback settings
GPU_FALLBACK_ENABLED = os.environ.get('GPU_FALLBACK_ENABLED', 'true').lower() == 'true'
GPU_TIMEOUT_SECONDS = int(os.environ.get('GPU_TIMEOUT_SECONDS', '30'))
GPU_RETRY_COUNT = int(os.environ.get('GPU_RETRY_COUNT', '3'))
