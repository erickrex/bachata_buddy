"""
Clear Elasticsearch Embeddings

This script deletes all embeddings from Elasticsearch and recreates the index.
Useful before regenerating embeddings with a new model (e.g., YOLOv8).

⚠️  WARNING: This will delete all existing embeddings!
    Make sure to backup first using backup_embeddings.py

Usage:
    python scripts/clear_embeddings.py --environment local --confirm
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.environment_config import EnvironmentConfig
from core.services.elasticsearch_service import ElasticsearchService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clear_embeddings(es_service: ElasticsearchService, confirm: bool = False) -> bool:
    """
    Clear all embeddings from Elasticsearch and recreate index.
    
    Args:
        es_service: Elasticsearch service instance
        confirm: If True, skip confirmation prompt
        
    Returns:
        True if successful, False otherwise
    """
    # Check if index exists
    if not es_service.index_exists():
        logger.info(f"Index '{es_service.index_name}' does not exist - nothing to clear")
        return True
    
    # Get document count
    count = es_service.count_documents()
    logger.info(f"Found {count} documents in index '{es_service.index_name}'")
    
    # Confirm deletion
    if not confirm:
        logger.warning("⚠️  This will DELETE ALL embeddings!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Operation cancelled")
            return False
    
    # Delete index
    logger.info("Deleting index...")
    es_service.delete_index()
    
    # Recreate index
    logger.info("Recreating index with fresh schema...")
    es_service.create_index()
    
    logger.info("✅ Index cleared and recreated successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Clear Elasticsearch embeddings and recreate index"
    )
    parser.add_argument(
        "--environment",
        type=str,
        choices=["local", "cloud"],
        default="local",
        help="Environment to use (local or cloud)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt (use with caution!)"
    )
    
    args = parser.parse_args()
    
    try:
        # Set environment variable
        os.environ["ENVIRONMENT"] = args.environment
        
        # Load configuration
        logger.info(f"Loading {args.environment} configuration...")
        config = EnvironmentConfig()
        
        # Initialize Elasticsearch service
        logger.info("Connecting to Elasticsearch...")
        es_service = ElasticsearchService(config.elasticsearch)
        
        # Clear embeddings
        success = clear_embeddings(es_service, confirm=args.confirm)
        
        if success:
            logger.info("✅ Ready for new embeddings!")
            logger.info("   Run: python scripts/generate_embeddings.py")
        
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"❌ Clear failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
