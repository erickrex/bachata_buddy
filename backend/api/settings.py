"""
Django settings for Bachata Buddy REST API.

Microservices architecture - API service only.

This settings file is configured to work in two environments:
1. Local Development: Docker Compose with local PostgreSQL and Elasticsearch
2. Production: Standard PostgreSQL connection, Elasticsearch, S3 storage

Environment detection:
- ENVIRONMENT: Explicitly set to 'local', 'staging', or 'production'
"""

from pathlib import Path
from datetime import timedelta
import os
import sys
import logging

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Environment detection
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'local')
IS_PRODUCTION = ENVIRONMENT == 'production'

# ALLOWED_HOSTS configuration
if IS_PRODUCTION:
    # Production: Allow specific hosts
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
else:
    # Local development
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')

# Add testserver for Django tests
if 'test' in sys.argv or os.environ.get('PYTEST_CURRENT_TEST'):
    ALLOWED_HOSTS.append('testserver')

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    f'https://{host}' for host in ALLOWED_HOSTS 
    if host not in ['localhost', '127.0.0.1', '0.0.0.0', '*']
]

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
else:
    # Standard PostgreSQL connection (local or RDS Aurora)
    db_options = {
        'connect_timeout': 10,
    }
    
    # Add SSL/TLS configuration for production (RDS Aurora)
    if IS_PRODUCTION:
        db_options['sslmode'] = os.environ.get('DB_SSLMODE', 'require')
    
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'bachata_buddy'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('DB_HOST', 'db'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60 if IS_PRODUCTION else 0,  # Connection pooling in production
            'OPTIONS': db_options,
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
if IS_PRODUCTION:
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
if IS_PRODUCTION:
    # In production, use the configured API URL
    api_url = os.environ.get('API_URL', 'https://api.example.com')
    SPECTACULAR_SERVERS = [
        {'url': api_url, 'description': 'Production server'},
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

# Elasticsearch Settings
if IS_PRODUCTION:
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

# Storage Settings
# Storage backend will be configured via abstraction layer (local or S3)
STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'local')  # 'local' or 's3'

# AWS S3 Configuration (for production)
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_CLOUDFRONT_DOMAIN = os.environ.get('AWS_CLOUDFRONT_DOMAIN', '')

# AWS Credentials (optional - boto3 will use IAM roles if not provided)
# In AWS App Runner, use IAM roles instead of access keys for better security
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')

# Media files configuration
# Point to data directory where videos are stored
MEDIA_URL = '/media/'
# In Docker: /app/data, locally: backend/../data
if os.path.exists('/app/data'):
    MEDIA_ROOT = Path('/app/data')
else:
    MEDIA_ROOT = BASE_DIR.parent / 'data'

# Logging
if IS_PRODUCTION:
    # Production: Structured logging for CloudWatch
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
if IS_PRODUCTION:
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

# OpenAI Configuration
# =============================================================================
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Agent Service Configuration
# =============================================================================
# Feature flag to enable/disable agent orchestration
AGENT_ENABLED = os.environ.get('AGENT_ENABLED', 'True').lower() in ('true', '1', 'yes')

# Timeout for agent workflow execution (in seconds)
AGENT_TIMEOUT = int(os.environ.get('AGENT_TIMEOUT', '300'))  # 5 minutes default

# Validate OpenAI API key at startup (only if not in test mode and agent is enabled)
if not ('test' in sys.argv or os.environ.get('PYTEST_CURRENT_TEST')):
    if AGENT_ENABLED:
        if not OPENAI_API_KEY or OPENAI_API_KEY == 'your-openai-api-key-here':
            import warnings
            warnings.warn(
                "OPENAI_API_KEY is not configured but AGENT_ENABLED is True. "
                "Agent orchestration features will not work. "
                "Please set OPENAI_API_KEY in your environment variables or set AGENT_ENABLED=False.",
                RuntimeWarning
            )
            # Log the warning
            logger = logging.getLogger(__name__)
            logger.warning(
                "Agent service is enabled but OpenAI API key is not configured. "
                "Set OPENAI_API_KEY environment variable or disable with AGENT_ENABLED=False"
            )
        else:
            # Log successful configuration
            logger = logging.getLogger(__name__)
            logger.info(
                f"Agent service enabled with timeout={AGENT_TIMEOUT}s"
            )




