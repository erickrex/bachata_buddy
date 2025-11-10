"""
Google Cloud Storage Service

Handles file uploads and downloads from GCS.
"""
import os
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing Google Cloud Storage"""
    
    def __init__(self):
        self.bucket_name = os.environ.get('GCS_BUCKET_NAME', '')
        
        # Only import google-cloud-storage in production
        if self.bucket_name:
            try:
                from google.cloud import storage
                self.client = storage.Client()
                self.bucket = self.client.bucket(self.bucket_name)
            except ImportError:
                logger.warning("google-cloud-storage not installed")
                self.client = None
                self.bucket = None
        else:
            self.client = None
            self.bucket = None
            logger.info("GCS_BUCKET_NAME not set, storage disabled")
    
    def upload_file(self, local_path, gcs_path):
        """Upload a file to GCS"""
        if not self.bucket:
            logger.warning(f"GCS not configured, skipping upload: {gcs_path}")
            return None
        
        try:
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_filename(local_path)
            logger.info(f"Uploaded {local_path} to gs://{self.bucket_name}/{gcs_path}")
            return blob.public_url
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise
    
    def download_file(self, gcs_path, local_path):
        """Download a file from GCS"""
        if not self.bucket:
            logger.warning(f"GCS not configured, skipping download: {gcs_path}")
            return None
        
        try:
            blob = self.bucket.blob(gcs_path)
            blob.download_to_filename(local_path)
            logger.info(f"Downloaded gs://{self.bucket_name}/{gcs_path} to {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise
    
    def get_signed_url(self, gcs_path, expiration=3600):
        """Generate a signed URL for temporary access"""
        if not self.bucket:
            return None
        
        try:
            blob = self.bucket.blob(gcs_path)
            url = blob.generate_signed_url(expiration=expiration)
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            raise
    
    def file_exists(self, gcs_path):
        """Check if a file exists in GCS"""
        if not self.bucket:
            logger.warning(f"GCS not configured, cannot check file existence: {gcs_path}")
            return False
        
        try:
            # Remove gs://bucket-name/ prefix if present
            if gcs_path.startswith('gs://'):
                # Extract path after bucket name
                parts = gcs_path.replace('gs://', '').split('/', 1)
                if len(parts) > 1:
                    gcs_path = parts[1]
                else:
                    gcs_path = ''
            
            # Remove /media/ prefix if present (from FileField)
            if gcs_path.startswith('/media/'):
                gcs_path = gcs_path[7:]
            elif gcs_path.startswith('media/'):
                gcs_path = gcs_path[6:]
            
            blob = self.bucket.blob(gcs_path)
            exists = blob.exists()
            logger.debug(f"File existence check for {gcs_path}: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check file existence for {gcs_path}: {e}")
            return False
