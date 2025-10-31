"""
Backup Elasticsearch Embeddings

This script exports all embeddings from Elasticsearch to a JSON file for backup.
Useful before regenerating embeddings with a new model (e.g., YOLOv8).

Usage:
    python scripts/backup_embeddings.py --output data/embeddings_backup.json --environment local
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import numpy as np

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


def convert_numpy_to_list(obj):
    """
    Recursively convert numpy arrays to lists for JSON serialization.
    
    Args:
        obj: Object to convert
        
    Returns:
        Converted object with numpy arrays as lists
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_list(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_list(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    else:
        return obj


def backup_embeddings(
    es_service: ElasticsearchService,
    output_path: Path
) -> int:
    """
    Backup all embeddings from Elasticsearch to JSON file.
    
    Args:
        es_service: Elasticsearch service instance
        output_path: Path to save backup file
        
    Returns:
        Number of embeddings backed up
    """
    logger.info("Starting embedding backup...")
    
    # Get all embeddings
    embeddings = es_service.get_all_embeddings()
    
    if not embeddings:
        logger.warning("No embeddings found in Elasticsearch")
        return 0
    
    # Convert numpy arrays to lists for JSON serialization
    logger.info("Converting numpy arrays to lists...")
    embeddings_serializable = convert_numpy_to_list(embeddings)
    
    # Prepare backup data
    backup_data = {
        "backup_date": datetime.now().isoformat(),
        "index_name": es_service.index_name,
        "count": len(embeddings),
        "embeddings": embeddings_serializable
    }
    
    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    logger.info(f"✅ Backed up {len(embeddings)} embeddings to {output_path}")
    logger.info(f"   File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    return len(embeddings)


def main():
    parser = argparse.ArgumentParser(
        description="Backup Elasticsearch embeddings to JSON file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/embeddings_backup.json",
        help="Output path for backup file (default: data/embeddings_backup.json)"
    )
    parser.add_argument(
        "--environment",
        type=str,
        choices=["local", "cloud"],
        default="local",
        help="Environment to use (local or cloud)"
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
        
        # Check if index exists
        if not es_service.index_exists():
            logger.warning(f"Index '{es_service.index_name}' does not exist - nothing to backup")
            logger.info("💡 Tip: Generate embeddings first with: python scripts/generate_embeddings.py")
            return 0
        
        # Get document count
        count = es_service.count_documents()
        logger.info(f"Found {count} documents in index '{es_service.index_name}'")
        
        # Backup embeddings
        output_path = Path(args.output)
        backed_up = backup_embeddings(es_service, output_path)
        
        if backed_up > 0:
            logger.info("✅ Backup completed successfully!")
            logger.info(f"   To restore: python scripts/restore_embeddings.py --input {output_path}")
        else:
            logger.warning("⚠️  No embeddings to backup")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
