#!/usr/bin/env python3
"""
Upload local embeddings to Elasticsearch Serverless cloud instance.

This script reads embeddings from local backup files and uploads them
to a managed Elasticsearch serverless instance for the hackathon demo.

Usage:
    python scripts/upload_embeddings_to_cloud.py

Requirements:
    - ELASTICSEARCH_CLOUD_ID set in .env
    - ELASTICSEARCH_API_KEY set in .env
    - Local embeddings backup file exists

Features:
    - Bulk upload for efficiency
    - Progress tracking
    - Retry logic
    - Verification after upload
    - Summary statistics
"""

import sys
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import json

from common.config.environment_config import EnvironmentConfig
from ai_services.services.elasticsearch_service import ElasticsearchService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_embeddings_from_backup(backup_path: Path) -> List[Dict[str, Any]]:
    """
    Load embeddings from JSON backup file.
    
    Args:
        backup_path: Path to backup JSON file
        
    Returns:
        List of embedding documents
    """
    logger.info(f"Loading embeddings from: {backup_path}")
    
    if not backup_path.exists():
        raise FileNotFoundError(
            f"Backup file not found: {backup_path}\n"
            f"Please run: python scripts/backup_embeddings.py"
        )
    
    # Load JSON backup
    with open(backup_path, 'r') as f:
        data = json.load(f)
    
    embeddings = data.get('embeddings', [])
    
    logger.info(f"Loaded {len(embeddings)} embeddings from JSON backup")
    return embeddings


def verify_cloud_connection(config: EnvironmentConfig) -> bool:
    """
    Verify cloud connection is configured.
    
    Args:
        config: Environment configuration
        
    Returns:
        True if cloud connection is configured
    """
    if not config.elasticsearch.host:
        logger.error(
            "❌ Elasticsearch host not configured!\n"
            "\n"
            "Please add to your .env file:\n"
            "  ELASTICSEARCH_HOST=your-serverless-endpoint-here\n"
            "  ELASTICSEARCH_API_KEY=your-api-key-here\n"
            "\n"
            "Get credentials from: https://cloud.elastic.co/"
        )
        return False
    
    if not config.elasticsearch.api_key:
        logger.error(
            "❌ Elasticsearch API key not configured!\n"
            "\n"
            "Please add to your .env file:\n"
            "  ELASTICSEARCH_API_KEY=your-api-key-here\n"
            "\n"
            "Get credentials from: https://cloud.elastic.co/"
        )
        return False
    
    logger.info("✅ Cloud connection configured")
    return True


def upload_embeddings(
    es_service: ElasticsearchService,
    embeddings: List[Dict[str, Any]],
    batch_size: int = 10
) -> Dict[str, Any]:
    """
    Upload embeddings to Elasticsearch with progress tracking.
    
    Args:
        es_service: Elasticsearch service instance
        embeddings: List of embedding documents
        batch_size: Number of embeddings per batch
        
    Returns:
        Upload statistics
    """
    logger.info(f"Uploading {len(embeddings)} embeddings in batches of {batch_size}...")
    
    start_time = time.time()
    total_uploaded = 0
    failed_uploads = []
    
    # Upload in batches
    for i in range(0, len(embeddings), batch_size):
        batch = embeddings[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(embeddings) + batch_size - 1) // batch_size
        
        try:
            logger.info(f"Uploading batch {batch_num}/{total_batches} ({len(batch)} embeddings)...")
            es_service.bulk_index_embeddings(batch)
            total_uploaded += len(batch)
            logger.info(f"✅ Batch {batch_num}/{total_batches} uploaded successfully")
        except Exception as e:
            logger.error(f"❌ Batch {batch_num}/{total_batches} failed: {e}")
            failed_uploads.extend([emb['clip_id'] for emb in batch])
    
    elapsed_time = time.time() - start_time
    
    stats = {
        'total_embeddings': len(embeddings),
        'uploaded': total_uploaded,
        'failed': len(failed_uploads),
        'elapsed_time': elapsed_time,
        'failed_clip_ids': failed_uploads
    }
    
    return stats


def verify_upload(
    es_service: ElasticsearchService,
    expected_count: int
) -> bool:
    """
    Verify all embeddings were uploaded successfully.
    
    Args:
        es_service: Elasticsearch service instance
        expected_count: Expected number of documents
        
    Returns:
        True if verification passed
    """
    logger.info("Verifying upload...")
    
    # Wait a moment for indexing to complete
    time.sleep(2)
    
    # Count documents
    actual_count = es_service.count_documents()
    
    if actual_count == expected_count:
        logger.info(f"✅ Verification passed: {actual_count}/{expected_count} documents")
        return True
    else:
        logger.warning(
            f"⚠️  Verification warning: {actual_count}/{expected_count} documents\n"
            f"Expected {expected_count} but found {actual_count}"
        )
        return False


def print_summary(stats: Dict[str, Any], verified: bool):
    """
    Print upload summary.
    
    Args:
        stats: Upload statistics
        verified: Whether verification passed
    """
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Total embeddings:     {stats['total_embeddings']}")
    print(f"Successfully uploaded: {stats['uploaded']}")
    print(f"Failed uploads:       {stats['failed']}")
    print(f"Upload time:          {stats['elapsed_time']:.2f} seconds")
    print(f"Verification:         {'✅ PASSED' if verified else '⚠️  WARNING'}")
    
    if stats['failed'] > 0:
        print(f"\nFailed clip IDs:")
        for clip_id in stats['failed_clip_ids']:
            print(f"  - {clip_id}")
    
    print("=" * 60)


def main():
    """Main upload script."""
    print("=" * 60)
    print("UPLOAD EMBEDDINGS TO ELASTICSEARCH CLOUD")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    
    try:
        # Initialize configuration
        config = EnvironmentConfig()
        
        # Verify cloud connection is configured
        if not verify_cloud_connection(config):
            sys.exit(1)
        
        # Find backup file
        backup_path = project_root / "data" / "embeddings_backup.json"
        
        if not backup_path.exists():
            logger.error(
                f"❌ Backup file not found: {backup_path}\n"
                f"\nPlease run: python scripts/backup_embeddings.py"
            )
            sys.exit(1)
        
        logger.info(f"Using backup: {backup_path.name}")
        
        # Load embeddings
        embeddings = load_embeddings_from_backup(backup_path)
        
        if not embeddings:
            logger.error("❌ No embeddings found in backup file")
            sys.exit(1)
        
        # Initialize Elasticsearch service
        logger.info("Connecting to Elasticsearch cloud...")
        es_service = ElasticsearchService(config.elasticsearch)
        
        # Create index if it doesn't exist
        if not es_service.index_exists():
            logger.info("Creating index...")
            es_service.create_index()
        else:
            logger.info("Index already exists")
            
            # Ask user if they want to delete and recreate
            response = input(
                "\n⚠️  Index already exists. Delete and recreate? (yes/no): "
            ).lower()
            
            if response == 'yes':
                logger.info("Deleting existing index...")
                es_service.delete_index()
                logger.info("Creating new index...")
                es_service.create_index()
            else:
                logger.info("Keeping existing index (will update existing documents)")
        
        # Upload embeddings
        stats = upload_embeddings(es_service, embeddings, batch_size=10)
        
        # Verify upload
        verified = verify_upload(es_service, len(embeddings))
        
        # Print summary
        print_summary(stats, verified)
        
        # Close connection
        es_service.close()
        
        if stats['failed'] == 0 and verified:
            logger.info("✅ Upload completed successfully!")
            sys.exit(0)
        else:
            logger.warning("⚠️  Upload completed with warnings")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Upload cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
