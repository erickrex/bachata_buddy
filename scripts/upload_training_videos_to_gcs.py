#!/usr/bin/env python3
"""
Upload Training Videos to Google Cloud Storage

This script uploads all training videos from data/Bachata_steps to GCS
and updates Elasticsearch embeddings with new GCS URLs.

CRITICAL: Run this ONCE before deploying to Cloud Run to ensure all
training videos are accessible in production.

Usage:
    # Set environment variables
    export GCS_BUCKET_NAME=your-bucket-name
    export GCP_PROJECT_ID=your-project-id
    export ELASTICSEARCH_HOST=your-es-host
    export ELASTICSEARCH_API_KEY=your-api-key
    
    # Run upload
    python scripts/upload_training_videos_to_gcs.py \
        --video_dir data/Bachata_steps \
        --bucket_name your-bucket-name \
        --dry_run  # Test first without uploading
    
    # Actual upload
    python scripts/upload_training_videos_to_gcs.py \
        --video_dir data/Bachata_steps \
        --bucket_name your-bucket-name

Requirements:
    - google-cloud-storage
    - Elasticsearch with existing embeddings
    - GCS bucket created and accessible
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import storage
from core.services.elasticsearch_service import ElasticsearchService
from core.config.environment_config import EnvironmentConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('gcs_upload.log')
    ]
)

logger = logging.getLogger(__name__)


class TrainingVideoUploader:
    """
    Uploads training videos to GCS and updates Elasticsearch paths.
    
    This ensures training videos are accessible in Cloud Run production environment.
    """
    
    def __init__(
        self,
        video_dir: str,
        bucket_name: str,
        gcs_prefix: str = "training_videos",
        dry_run: bool = False
    ):
        """
        Initialize uploader.
        
        Args:
            video_dir: Local directory containing training videos
            bucket_name: GCS bucket name
            gcs_prefix: Prefix for videos in GCS (folder name)
            dry_run: If True, don't actually upload or update
        """
        self.video_dir = Path(video_dir)
        self.bucket_name = bucket_name
        self.gcs_prefix = gcs_prefix
        self.dry_run = dry_run
        
        if not self.video_dir.exists():
            raise FileNotFoundError(f"Video directory not found: {self.video_dir}")
        
        logger.info("=" * 80)
        logger.info("TRAINING VIDEO UPLOADER TO GCS")
        logger.info("=" * 80)
        logger.info(f"Video directory: {self.video_dir}")
        logger.info(f"GCS bucket: {self.bucket_name}")
        logger.info(f"GCS prefix: {self.gcs_prefix}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("=" * 80)
        
        # Initialize GCS client
        if not self.dry_run:
            logger.info("Initializing GCS client...")
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(self.bucket_name)
            
            # Verify bucket exists
            if not self.bucket.exists():
                raise ValueError(f"GCS bucket does not exist: {self.bucket_name}")
            logger.info(f"✅ GCS bucket verified: {self.bucket_name}")
        
        # Initialize Elasticsearch
        logger.info("Initializing Elasticsearch...")
        self.config = EnvironmentConfig()
        self.es_service = ElasticsearchService(self.config.elasticsearch)
        logger.info("✅ Elasticsearch connected")
        
        # Statistics
        self.stats = {
            'total_videos': 0,
            'uploaded': 0,
            'skipped': 0,
            'failed': 0,
            'embeddings_updated': 0,
            'total_size_mb': 0.0
        }
    
    def find_all_videos(self) -> List[Path]:
        """
        Find all video files in the directory recursively.
        
        Returns:
            List of video file paths
        """
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv'}
        videos = []
        
        for ext in video_extensions:
            videos.extend(self.video_dir.rglob(f'*{ext}'))
        
        logger.info(f"Found {len(videos)} video files")
        return sorted(videos)
    
    def get_gcs_path(self, local_path: Path) -> str:
        """
        Convert local path to GCS path.
        
        Args:
            local_path: Local file path
            
        Returns:
            GCS path (blob name)
            
        Example:
            data/Bachata_steps/basic/basic_1.mp4
            -> training_videos/basic/basic_1.mp4
        """
        # Get relative path from video_dir
        rel_path = local_path.relative_to(self.video_dir)
        
        # Construct GCS path
        gcs_path = f"{self.gcs_prefix}/{rel_path}"
        
        return gcs_path
    
    def get_gcs_url(self, gcs_path: str) -> str:
        """
        Get public URL for GCS object.
        
        Args:
            gcs_path: GCS blob name
            
        Returns:
            Public HTTPS URL
        """
        return f"https://storage.googleapis.com/{self.bucket_name}/{gcs_path}"
    
    def upload_video(self, local_path: Path) -> Tuple[bool, str, str]:
        """
        Upload a single video to GCS.
        
        Args:
            local_path: Local video file path
            
        Returns:
            Tuple of (success, gcs_path, gcs_url)
        """
        try:
            gcs_path = self.get_gcs_path(local_path)
            gcs_url = self.get_gcs_url(gcs_path)
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would upload: {local_path.name} -> {gcs_path}")
                return True, gcs_path, gcs_url
            
            # Check if already exists
            blob = self.bucket.blob(gcs_path)
            if blob.exists():
                logger.info(f"⏭️  Skipping (already exists): {gcs_path}")
                self.stats['skipped'] += 1
                return True, gcs_path, gcs_url
            
            # Upload file
            logger.info(f"⬆️  Uploading: {local_path.name} -> {gcs_path}")
            blob.upload_from_filename(str(local_path))
            
            # Note: Files are publicly accessible via bucket-level IAM policy
            # No need to set individual ACLs with uniform bucket-level access
            
            # Update stats
            file_size_mb = local_path.stat().st_size / (1024 * 1024)
            self.stats['total_size_mb'] += file_size_mb
            self.stats['uploaded'] += 1
            
            logger.info(f"✅ Uploaded: {gcs_url} ({file_size_mb:.2f} MB)")
            return True, gcs_path, gcs_url
            
        except Exception as e:
            logger.error(f"❌ Failed to upload {local_path.name}: {e}")
            self.stats['failed'] += 1
            return False, "", ""
    
    def update_elasticsearch_paths(self, path_mapping: Dict[str, str]) -> int:
        """
        Update video paths in Elasticsearch embeddings.
        
        Args:
            path_mapping: Dict mapping old local paths to new GCS URLs
            
        Returns:
            Number of embeddings updated
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update {len(path_mapping)} paths in Elasticsearch")
            return len(path_mapping)
        
        logger.info("Updating Elasticsearch embeddings with GCS URLs...")
        
        updated_count = 0
        
        try:
            # Get all embeddings
            all_embeddings = self.es_service.get_all_embeddings()
            logger.info(f"Retrieved {len(all_embeddings)} embeddings from Elasticsearch")
            
            for embedding in all_embeddings:
                clip_id = embedding.get('clip_id')
                old_path = embedding.get('video_path', '')
                
                # Normalize old path (remove data/ prefix if present)
                normalized_old_path = old_path.replace('data/', '')
                
                # Check if we have a mapping for this path
                new_url = None
                for local_path, gcs_url in path_mapping.items():
                    if normalized_old_path in local_path or local_path in normalized_old_path:
                        new_url = gcs_url
                        break
                
                if new_url:
                    # Update the embedding
                    embedding['video_path'] = new_url
                    
                    # Re-index with updated path
                    self.es_service.index_embedding(
                        clip_id=clip_id,
                        embedding_data=embedding
                    )
                    
                    updated_count += 1
                    logger.info(f"✅ Updated {clip_id}: {old_path} -> {new_url}")
                else:
                    logger.warning(f"⚠️  No GCS mapping found for: {old_path}")
            
            logger.info(f"✅ Updated {updated_count} embeddings in Elasticsearch")
            return updated_count
            
        except Exception as e:
            logger.error(f"❌ Failed to update Elasticsearch: {e}")
            return 0
    
    def run(self) -> bool:
        """
        Run the complete upload and update process.
        
        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()
        
        try:
            # Find all videos
            videos = self.find_all_videos()
            self.stats['total_videos'] = len(videos)
            
            if not videos:
                logger.error("No videos found to upload")
                return False
            
            # Upload all videos
            logger.info(f"\n{'='*80}")
            logger.info(f"UPLOADING {len(videos)} VIDEOS TO GCS")
            logger.info(f"{'='*80}\n")
            
            path_mapping = {}  # local_path -> gcs_url
            
            for i, video_path in enumerate(videos, 1):
                logger.info(f"[{i}/{len(videos)}] Processing: {video_path.name}")
                
                success, gcs_path, gcs_url = self.upload_video(video_path)
                
                if success:
                    # Store mapping for Elasticsearch update
                    path_mapping[str(video_path)] = gcs_url
            
            # Update Elasticsearch
            logger.info(f"\n{'='*80}")
            logger.info("UPDATING ELASTICSEARCH EMBEDDINGS")
            logger.info(f"{'='*80}\n")
            
            updated_count = self.update_elasticsearch_paths(path_mapping)
            self.stats['embeddings_updated'] = updated_count
            
            # Print summary
            elapsed_time = time.time() - start_time
            self._print_summary(elapsed_time)
            
            return self.stats['failed'] == 0
            
        except Exception as e:
            logger.error(f"Upload process failed: {e}")
            return False
    
    def _print_summary(self, elapsed_time: float):
        """Print upload summary."""
        logger.info(f"\n{'='*80}")
        logger.info("UPLOAD SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Total videos: {self.stats['total_videos']}")
        logger.info(f"Uploaded: {self.stats['uploaded']}")
        logger.info(f"Skipped (already exist): {self.stats['skipped']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Total size: {self.stats['total_size_mb']:.2f} MB")
        logger.info(f"Embeddings updated: {self.stats['embeddings_updated']}")
        logger.info(f"Time elapsed: {elapsed_time:.1f}s")
        logger.info(f"{'='*80}")
        
        if self.dry_run:
            logger.info("\n⚠️  DRY RUN MODE - No actual changes made")
        elif self.stats['failed'] == 0:
            logger.info("\n✅ All videos uploaded successfully!")
            logger.info(f"✅ GCS bucket: gs://{self.bucket_name}/{self.gcs_prefix}/")
            logger.info(f"✅ Public URL: https://storage.googleapis.com/{self.bucket_name}/{self.gcs_prefix}/")
        else:
            logger.warning(f"\n⚠️  {self.stats['failed']} videos failed to upload")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload training videos to Google Cloud Storage"
    )
    parser.add_argument(
        '--video_dir',
        type=str,
        default='data/Bachata_steps',
        help='Directory containing training videos'
    )
    parser.add_argument(
        '--bucket_name',
        type=str,
        required=True,
        help='GCS bucket name'
    )
    parser.add_argument(
        '--gcs_prefix',
        type=str,
        default='training_videos',
        help='Prefix (folder) for videos in GCS'
    )
    parser.add_argument(
        '--dry_run',
        action='store_true',
        help='Test run without actually uploading'
    )
    
    args = parser.parse_args()
    
    # Create uploader
    uploader = TrainingVideoUploader(
        video_dir=args.video_dir,
        bucket_name=args.bucket_name,
        gcs_prefix=args.gcs_prefix,
        dry_run=args.dry_run
    )
    
    # Run upload
    success = uploader.run()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
