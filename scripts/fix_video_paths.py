"""
Fix video paths in Elasticsearch from Bachata_steps/ to training_videos/
"""

import logging
from common.config.environment_config import EnvironmentConfig
from ai_services.services.elasticsearch_service import ElasticsearchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Update all video paths in Elasticsearch."""
    # Initialize Elasticsearch
    config = EnvironmentConfig()
    es = ElasticsearchService(config.elasticsearch)
    
    # Get all embeddings
    logger.info("Fetching all embeddings from Elasticsearch...")
    embeddings = es.get_all_embeddings()
    logger.info(f"Found {len(embeddings)} embeddings")
    
    # Update paths
    updated_embeddings = []
    for emb in embeddings:
        old_path = emb['video_path']
        new_path = old_path.replace('Bachata_steps/', 'training_videos/')
        
        if old_path != new_path:
            logger.info(f"Updating: {old_path} -> {new_path}")
            emb['video_path'] = new_path
            updated_embeddings.append(emb)
        else:
            logger.info(f"Skipping (already correct): {old_path}")
            updated_embeddings.append(emb)
    
    # Re-index with updated paths
    logger.info(f"\nRe-indexing {len(updated_embeddings)} embeddings with updated paths...")
    es.bulk_index_embeddings(updated_embeddings)
    
    logger.info("\n✅ Video paths updated successfully!")
    
    # Verify
    logger.info("\nVerifying updates...")
    embeddings_after = es.get_all_embeddings()
    sample_paths = [emb['video_path'] for emb in embeddings_after[:5]]
    logger.info(f"Sample paths after update:")
    for i, path in enumerate(sample_paths, 1):
        logger.info(f"  {i}. {path}")


if __name__ == "__main__":
    main()
