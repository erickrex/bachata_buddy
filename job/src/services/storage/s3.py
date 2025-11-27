"""
AWS S3 storage backend.

Stores files in Amazon S3, suitable for production deployments.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from .base import StorageBackend

logger = logging.getLogger(__name__)


class S3StorageBackend(StorageBackend):
    """Storage backend using AWS S3"""
    
    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        cloudfront_domain: Optional[str] = None
    ):
        """
        Initialize S3 storage backend.
        
        Args:
            bucket_name: Name of the S3 bucket
            region: AWS region (default: us-east-1)
            cloudfront_domain: Optional CloudFront domain for CDN URLs
        """
        self.bucket_name = bucket_name
        self.region = region
        self.cloudfront_domain = cloudfront_domain
        
        # Import boto3 only when S3 backend is used
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            self.boto3 = boto3
            self.ClientError = ClientError
            
            # Initialize S3 client
            self.s3_client = boto3.client('s3', region_name=region)
            
            # Verify bucket exists
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                logger.info(f"S3StorageBackend initialized with bucket={bucket_name}, region={region}")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    raise ValueError(f"S3 bucket '{bucket_name}' does not exist")
                elif error_code == '403':
                    raise ValueError(f"Access denied to S3 bucket '{bucket_name}'")
                else:
                    raise
                    
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 storage backend. "
                "Install it with: pip install boto3"
            )
    
    def _normalize_remote_path(self, remote_path: str) -> str:
        """Normalize remote path by removing prefixes"""
        # Remove leading slashes
        clean_path = remote_path.lstrip('/')
        
        # Remove common prefixes if present
        for prefix in ['media/', 'data/', 'choreographies/']:
            if clean_path.startswith(prefix):
                # Keep the prefix for S3 organization
                break
        
        # Remove S3 URL prefixes if present
        if clean_path.startswith('s3://'):
            parts = clean_path.replace('s3://', '').split('/', 1)
            clean_path = parts[1] if len(parts) > 1 else ''
        
        # Remove GCS URL prefixes if present (for backward compatibility)
        if clean_path.startswith('gs://'):
            parts = clean_path.replace('gs://', '').split('/', 1)
            clean_path = parts[1] if len(parts) > 1 else ''
        
        return clean_path
    
    def upload_file(self, local_path: str, remote_path: str) -> str:
        """Upload a file to S3"""
        try:
            s3_key = self._normalize_remote_path(remote_path)
            
            # Upload file to S3
            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ACL': 'private'}  # Files are private by default
            )
            
            logger.info(f"Uploaded {local_path} to s3://{self.bucket_name}/{s3_key}")
            
            # Return URL for accessing the file
            return self.get_url(s3_key)
            
        except self.ClientError as e:
            logger.error(f"Failed to upload file {local_path} to S3: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading file {local_path} to S3: {e}")
            raise
    
    def download_file(self, remote_path: str, local_path: str) -> str:
        """Download a file from S3"""
        try:
            s3_key = self._normalize_remote_path(remote_path)
            
            # Create parent directories for destination if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Download file from S3
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )
            
            logger.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_path}")
            return local_path
            
        except self.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise FileNotFoundError(f"File not found in S3: {remote_path}")
            logger.error(f"Failed to download file {remote_path} from S3: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading file {remote_path} from S3: {e}")
            raise
    
    def get_url(self, remote_path: str, expiration: int = 3600) -> str:
        """Get URL for accessing a file"""
        try:
            s3_key = self._normalize_remote_path(remote_path)
            
            # Use CloudFront URL if configured
            if self.cloudfront_domain:
                url = f"https://{self.cloudfront_domain}/{s3_key}"
                logger.debug(f"Generated CloudFront URL for {remote_path}: {url}")
                return url
            
            # Generate presigned URL for temporary access
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            logger.debug(f"Generated presigned URL for {remote_path} (expires in {expiration}s)")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate URL for {remote_path}: {e}")
            raise
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in S3"""
        try:
            s3_key = self._normalize_remote_path(remote_path)
            
            # Use head_object to check existence without downloading
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            logger.debug(f"File existence check for {remote_path}: True")
            return True
            
        except self.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.debug(f"File existence check for {remote_path}: False")
                return False
            logger.error(f"Error checking file existence for {remote_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking file existence for {remote_path}: {e}")
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from S3"""
        try:
            s3_key = self._normalize_remote_path(remote_path)
            
            # Delete object from S3
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            
            logger.info(f"Deleted file from S3: {remote_path}")
            return True
            
        except self.ClientError as e:
            logger.error(f"Failed to delete file {remote_path} from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting file {remote_path} from S3: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> list[str]:
        """List files in S3 with optional prefix filter"""
        try:
            s3_prefix = self._normalize_remote_path(prefix) if prefix else ""
            
            files = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append(obj['Key'])
            
            logger.debug(f"Listed {len(files)} files with prefix '{prefix}'")
            return files
            
        except self.ClientError as e:
            logger.error(f"Failed to list files with prefix '{prefix}': {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing files with prefix '{prefix}': {e}")
            return []
