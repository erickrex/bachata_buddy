#!/usr/bin/env python3
"""
Test script to verify the fixes for video choreography generation.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.choreography_pipeline import ChoreoGenerationPipeline, PipelineConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_choreography_generation():
    """Test choreography generation with a local audio file."""
    
    # Check if test audio file exists
    test_audio = Path("data/songs/Veneno.mp3")
    if not test_audio.exists():
        logger.error(f"Test audio file not found: {test_audio}")
        logger.info("Please ensure you have audio files in data/songs/ directory")
        return False
    
    try:
        logger.info("🧪 Testing choreography generation fixes...")
        
        # Create pipeline with balanced quality
        config = PipelineConfig(
            quality_mode="balanced",
            enable_caching=True,
            max_workers=2,  # Reduced for testing
            cleanup_after_generation=False  # Keep files for inspection
        )
        
        pipeline = ChoreoGenerationPipeline(config)
        
        # Generate choreography
        logger.info(f"📁 Processing: {test_audio}")
        result = await pipeline.generate_choreography(
            audio_input=str(test_audio),
            difficulty="intermediate",
            energy_level="high"
        )
        
        if result.success:
            logger.info("✅ Choreography generation completed successfully!")
            logger.info(f"📹 Output: {result.output_path}")
            logger.info(f"📊 Metadata: {result.metadata_path}")
            logger.info(f"⏱️  Processing time: {result.processing_time:.2f}s")
            logger.info(f"🎵 Sequence duration: {result.sequence_duration:.1f}s")
            logger.info(f"💃 Moves analyzed: {result.moves_analyzed}")
            logger.info(f"🎯 Recommendations: {result.recommendations_generated}")
            
            # Check if output file exists and has reasonable size
            if result.output_path and Path(result.output_path).exists():
                file_size = Path(result.output_path).stat().st_size
                logger.info(f"📦 Output file size: {file_size / (1024*1024):.1f} MB")
                
                if file_size > 1024 * 1024:  # At least 1MB
                    logger.info("✅ Output file appears to be valid")
                    return True
                else:
                    logger.warning("⚠️  Output file seems too small")
                    return False
            else:
                logger.error("❌ Output file not found")
                return False
        else:
            logger.error(f"❌ Choreography generation failed: {result.error_message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False

async def main():
    """Run the test."""
    logger.info("🎵 Bachata Choreography Generator - Fix Verification Test")
    logger.info("=" * 60)
    
    success = await test_choreography_generation()
    
    logger.info("=" * 60)
    if success:
        logger.info("🎉 All tests passed! The fixes are working correctly.")
        sys.exit(0)
    else:
        logger.error("💥 Tests failed. Please check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())