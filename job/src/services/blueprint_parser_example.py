"""
Example usage of BlueprintParser in the job container main.py

This demonstrates how to integrate the blueprint parser into the job workflow.
"""

import os
import sys
import logging
from blueprint_parser import BlueprintParser, BlueprintValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_job():
    """
    Example of how to use the blueprint parser in the job container.
    
    This would be called from main.py after the job starts.
    """
    # Get blueprint from environment variable
    blueprint_json = os.environ.get('BLUEPRINT_JSON')
    
    if not blueprint_json:
        logger.error("BLUEPRINT_JSON environment variable not set")
        sys.exit(1)
    
    # Parse and validate blueprint
    try:
        parser = BlueprintParser(allow_absolute_paths=False)
        blueprint = parser.parse_and_validate(blueprint_json)
        
        # Log summary
        summary = parser.get_summary(blueprint)
        logger.info(f"Blueprint validated successfully: {summary}")
        
        # Continue with video assembly...
        logger.info(f"Processing {len(blueprint['moves'])} moves")
        logger.info(f"Output will be saved to: {blueprint['output_config']['output_path']}")
        
        return blueprint
        
    except BlueprintValidationError as e:
        # Log all validation errors
        logger.error("Blueprint validation failed:")
        for error in e.errors:
            logger.error(f"  - {error}")
        
        # Update task status to failed (would call database service here)
        # database_service.update_task_status(
        #     task_id=blueprint.get('task_id', 'unknown'),
        #     status='failed',
        #     error=f"Blueprint validation failed: {'; '.join(e.errors)}"
        # )
        
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Unexpected error parsing blueprint: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Example usage
    example_blueprint = """{
        "task_id": "example-123",
        "audio_path": "data/songs/example.mp3",
        "moves": [
            {
                "clip_id": "move_1",
                "video_path": "data/Bachata_steps/basic_steps/basic_1.mp4",
                "start_time": 0.0,
                "duration": 8.0
            }
        ],
        "output_config": {
            "output_path": "data/output/choreography_example-123.mp4"
        }
    }"""
    
    os.environ['BLUEPRINT_JSON'] = example_blueprint
    blueprint = process_job()
    print(f"\n✅ Successfully processed blueprint for task: {blueprint['task_id']}")
