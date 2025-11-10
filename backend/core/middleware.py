"""
Custom middleware for the API
"""
import logging
import time

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Middleware to log all API requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log request
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Log response
        duration = time.time() - start_time
        logger.info(
            f"{request.method} {request.path} - {response.status_code} - {duration:.3f}s",
            extra={
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration': duration,
                'user': request.user.username if request.user.is_authenticated else 'anonymous',
            }
        )
        
        return response
