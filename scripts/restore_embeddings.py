"""
Restore Elasticsearch Embeddings

This script restores embeddings from a backup JSON file to Elasticsearch.
Useful for rolling back after regenerating embeddings.

Usage:
    python scripts/restore_embeddings.py --input data/embeddings_backup.json --environment local
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config.environment_config import EnvironmentConfig
from ai_services.services.elasticsearch_service import ElasticsearchService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def restore_embeddings(
    es_service: ElasticsearchService,
    backup_path: Path
) -> int:
    """
    Restore embeddings from backup file to Elasticsearch.
    
    Args:
        es_service: Elasticsearch service instance
        backup_path: Path to backup file
        
    Returns:
        Number of embeddings restored
    """
    logger.info(f"Loading backup from {backup_path}...")
    
    # Load backup file
    with open(backup_path, 'r') as f:
        backup_data = json.load(f)
    
    embeddings = backup_data.get("embeddings", [])
    backup_date = backup_data.get("backup_date", "unknown")
    original_index = backup_data.get("index_name", "unknown")
    
    logger.info(f"Backup info:")
    logger.info(f"  Date: {backup_date}")
    logger.info(f"  Original index: {original_index}")
    logger.info(f"  Embeddings: {len(embeddings)}")
    
    if not embeddings:
        logger.warning("No embeddings found in backup file")
        return 0
    
    # Ensure index exists
    if not es_service.index_exists():
        logger.info("Creating index...")
        es_service.create_index()
    
    # Restore embeddings
    logger.info("Restoring embeddings...")
    es_service.bulk_index_embeddings(embeddings)
    
    # Verify
    count = es_service.count_documents()
    logger.info(f"✅ Restored {count} embeddings to index '{es_service.index_name}'")
    
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Restore Elasticsearch embeddings from backup file"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input path for backup file"
    )
    parser.add_argument(
        "--environment",
        type=str,
        choices=["local", "cloud"],
        default="local",
        help="Environment to use (local or cloud)"
    )
    parser.add_argument(
        "--clear-first",
        action="store_true",
        help="Clear existing embeddings before restoring"
    )
    
    args = parser.parse_args()
    
    try:
        # Check if backup file exists
        backup_path = Path(args.input)
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return 1
        
        # Set environment variable
        os.environ["ENVIRONMENT"] = args.environment
        
        # Load configuration
        logger.info(f"Loading {args.environment} configuration...")
        config = EnvironmentConfig()
        
        # Initialize Elasticsearch service
        logger.info("Connecting to Elasticsearch...")
        es_service = ElasticsearchService(config.elasticsearch)
        
        # Clear if requested
        if args.clear_first:
            if es_service.index_exists():
                logger.info("Clearing existing index...")
                es_service.delete_index()
            es_service.create_index()
        
        # Restore embeddings
        restored = restore_embeddings(es_service, backup_path)
        
        if restored > 0:
            logger.info("✅ Restore completed successfully!")
        else:
            logger.warning("⚠️  No embeddings restored")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Restore failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
