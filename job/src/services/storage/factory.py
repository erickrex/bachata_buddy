"""
Factory for creating storage backend instances.

Selects the appropriate storage backend based on environment configuration.
"""

import os
import logging
from typing import Optional

from .base import StorageBackend
from .local import LocalStorageBackend
from .s3 import S3StorageBackend

logger = logging.getLogger(__name__)

# Singleton instance
_storage_backend: Optional[StorageBackend] = None


def get_storage_backend(force_recreate: bool = False) -> StorageBackend:
    """
    Get the configured storage backend instance.
    
    This function returns a singleton instance of the storage backend
    based on the STORAGE_BACKEND environment variable.
    
    Args:
        force_recreate: If True, recreate the backend instance even if one exists
        
    Returns:
        StorageBackend instance (LocalStorageBackend or S3StorageBackend)
        
    Raises:
        ValueError: If STORAGE_BACKEND is set to an invalid value
        
    Environment Variables:
        STORAGE_BACKEND: 'local' or 's3' (default: 'local')
        USE_LOCAL_STORAGE: Alternative way to specify local storage (default: 'true')
        
        For local backend:
            LOCAL_STORAGE_PATH: Base directory for file storage (default: '/app/data')
        
        For S3 backend:
            AWS_STORAGE_BUCKET_NAME: S3 bucket name (required)
            AWS_REGION: AWS region (default: 'us-east-1')
            AWS_CLOUDFRONT_DOMAIN: Optional CloudFront domain for CDN URLs
    """
    global _storage_backend
    
    # Return existing instance unless force_recreate is True
    if _storage_backend is not None and not force_recreate:
        return _storage_backend
    
    # Check if running locally (K_SERVICE is set in Cloud Run/App Runner)
    is_local = os.getenv("K_SERVICE") is None
    
    # Determine backend type
    use_local = os.getenv("USE_LOCAL_STORAGE", str(is_local)).lower() == "true"
    backend_type = os.environ.get('STORAGE_BACKEND', 'local' if use_local else 's3').lower()
    
    if backend_type == 'local' or use_local:
        # Create local storage backend
        base_path = os.environ.get('LOCAL_STORAGE_PATH', '/app/data')
        
        _storage_backend = LocalStorageBackend(base_path=base_path)
        logger.info(f"Using LocalStorageBackend with base_path={base_path}")
        
    elif backend_type == 's3':
        # Create S3 storage backend
        bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
        if not bucket_name:
            raise ValueError(
                "AWS_STORAGE_BUCKET_NAME environment variable is required "
                "when STORAGE_BACKEND is set to 's3'"
            )
        
        region = os.environ.get('AWS_REGION', 'us-east-1')
        cloudfront_domain = os.environ.get('AWS_CLOUDFRONT_DOMAIN')
        
        _storage_backend = S3StorageBackend(
            bucket_name=bucket_name,
            region=region,
            cloudfront_domain=cloudfront_domain
        )
        logger.info(f"Using S3StorageBackend with bucket={bucket_name}")
        
    else:
        raise ValueError(
            f"Invalid STORAGE_BACKEND value: '{backend_type}'. "
            "Must be 'local' or 's3'"
        )
    
    return _storage_backend


def reset_storage_backend():
    """
    Reset the storage backend singleton.
    
    This is useful for testing when you need to switch between backends
    or reconfigure the backend with different settings.
    """
    global _storage_backend
    _storage_backend = None
    logger.debug("Storage backend singleton reset")
