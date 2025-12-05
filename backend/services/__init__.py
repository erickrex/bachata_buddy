"""
Services package for Bachata Buddy backend.

This module provides factory functions for creating service instances
with proper dependency injection.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Global instance for reuse across requests
_agent_service = None


def get_agent_service():
    """
    Get or create the global agent service instance.
    
    This factory function initializes the AgentService with all required
    dependencies (parameter_extractor, music_analyzer, vector_search,
    blueprint_generator, storage_service).
    
    Returns:
        AgentService instance
    
    Raises:
        ValueError: If OPENAI_API_KEY is not configured
    """
    global _agent_service
    
    if _agent_service is not None:
        return _agent_service
    
    # Get OpenAI API key
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please configure it in your .env file."
        )
    
    logger.info("Initializing AgentService with dependencies...")
    
    try:
        # Import dependencies
        from services.agent_service import AgentService
        from services.parameter_extractor import ParameterExtractor
        from services.vector_search_service import get_vector_search_service
        from services.blueprint_generator import BlueprintGenerator
        from services.storage_service import get_storage_service
        
        # Import MusicAnalyzer from backend
        from music_analyzer import MusicAnalyzer
        
        # Initialize dependencies
        parameter_extractor = ParameterExtractor(openai_api_key=openai_api_key)
        music_analyzer = MusicAnalyzer()
        vector_search = get_vector_search_service()
        
        blueprint_generator = BlueprintGenerator(
            vector_search_service=vector_search,
            music_analyzer=music_analyzer
        )
        
        storage_service = get_storage_service()
        
        # Create agent service
        _agent_service = AgentService(
            openai_api_key=openai_api_key,
            parameter_extractor=parameter_extractor,
            music_analyzer=music_analyzer,
            vector_search=vector_search,
            blueprint_generator=blueprint_generator,
            storage_service=storage_service
        )
        
        logger.info("AgentService initialized successfully")
        return _agent_service
        
    except Exception as e:
        logger.error(f"Failed to initialize AgentService: {e}", exc_info=True)
        raise
