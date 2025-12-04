"""
Parameter Extractor Service

Extracts structured choreography parameters from natural language using OpenAI GPT-4o-mini.
Provides keyword-based fallback extraction when OpenAI API is unavailable.
"""

import re
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


class ParameterExtractionError(Exception):
    """Raised when parameter extraction fails."""
    pass


class ParameterExtractor:
    """
    Extracts choreography parameters from natural language.
    
    Uses OpenAI GPT-4o-mini for intelligent extraction with keyword-based
    fallback for reliability.
    """
    
    # Allowed values for each parameter
    ALLOWED_DIFFICULTY = ['beginner', 'intermediate', 'advanced']
    ALLOWED_ENERGY_LEVEL = ['low', 'medium', 'high']
    ALLOWED_STYLE = ['traditional', 'modern', 'romantic', 'sensual']
    
    # Default values
    DEFAULT_DIFFICULTY = 'beginner'
    DEFAULT_ENERGY_LEVEL = 'medium'
    DEFAULT_STYLE = 'modern'
    DEFAULT_DURATION = 60
    
    # Extraction prompt template
    EXTRACTION_PROMPT = """You are a choreography assistant. Extract parameters from this request.

User request: "{user_text}"

Extract these parameters (use defaults if not specified):
- difficulty: beginner, intermediate, or advanced (default: beginner)
- energy_level: low, medium, or high (default: medium)
- style: traditional, modern, romantic, or sensual (default: modern)
- duration: approximate duration in seconds (default: 60)

Respond ONLY with JSON in this exact format:
{{"difficulty": "...", "energy_level": "...", "style": "...", "duration": ...}}"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize Parameter Extractor with OpenAI client.
        
        Args:
            openai_api_key: OpenAI API key (defaults to settings.OPENAI_API_KEY)
        """
        api_key = openai_api_key or settings.OPENAI_API_KEY
        
        if not api_key or api_key == 'your-openai-api-key-here':
            logger.warning(
                "OpenAI API key not configured. Parameter extraction will use "
                "keyword-based fallback only."
            )
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
    
    def extract_parameters(self, user_text: str) -> Dict[str, Any]:
        """
        Extract parameters from user text using OpenAI GPT-4o-mini.
        
        Args:
            user_text: Natural language choreography request
        
        Returns:
            Dictionary with difficulty, energy_level, style, duration
        
        Raises:
            ParameterExtractionError: If extraction fails completely
        """
        if not user_text or not user_text.strip():
            raise ParameterExtractionError("User text cannot be empty")
        
        user_text = user_text.strip()
        
        # Try OpenAI extraction first
        if self.client:
            try:
                params = self._extract_with_openai(user_text)
                logger.info(
                    f"OpenAI parameter extraction successful: {params}",
                    extra={'method': 'openai', 'user_text': user_text[:100]}
                )
                return params
            except Exception as e:
                logger.warning(
                    f"OpenAI extraction failed: {e}. Falling back to keyword extraction.",
                    extra={'error': str(e), 'user_text': user_text[:100]}
                )
        
        # Fallback to keyword extraction
        try:
            params = self._fallback_keyword_extraction(user_text)
            logger.info(
                f"Keyword parameter extraction successful: {params}",
                extra={'method': 'keyword', 'user_text': user_text[:100]}
            )
            return params
        except Exception as e:
            logger.error(
                f"Keyword extraction failed: {e}",
                extra={'error': str(e), 'user_text': user_text[:100]},
                exc_info=True
            )
            raise ParameterExtractionError(f"Parameter extraction failed: {e}")
    
    def _extract_with_openai(self, user_text: str) -> Dict[str, Any]:
        """
        Extract parameters using OpenAI GPT-4o-mini with JSON mode.
        
        Args:
            user_text: Natural language request
        
        Returns:
            Extracted and validated parameters
        """
        prompt = self.EXTRACTION_PROMPT.format(user_text=user_text)
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=150
        )
        
        # Parse JSON response
        import json
        content = response.choices[0].message.content
        params = json.loads(content)
        
        # Validate and normalize
        validated_params = self._validate_parameters(params)
        
        return validated_params
    
    def _fallback_keyword_extraction(self, user_text: str) -> Dict[str, Any]:
        """
        Fallback keyword-based extraction using regex and keyword matching.
        
        Args:
            user_text: Natural language request
        
        Returns:
            Extracted parameters with defaults for missing values
        """
        user_text_lower = user_text.lower()
        
        # Extract difficulty
        difficulty = self.DEFAULT_DIFFICULTY
        if any(word in user_text_lower for word in ['beginner', 'easy', 'simple', 'basic']):
            difficulty = 'beginner'
        elif any(word in user_text_lower for word in ['intermediate', 'medium']):
            difficulty = 'intermediate'
        elif any(word in user_text_lower for word in ['advanced', 'expert', 'difficult', 'hard']):
            difficulty = 'advanced'
        
        # Extract energy level
        energy_level = self.DEFAULT_ENERGY_LEVEL
        if any(word in user_text_lower for word in ['slow', 'calm', 'relaxed', 'gentle', 'low']):
            energy_level = 'low'
        elif any(word in user_text_lower for word in ['medium', 'moderate']):
            energy_level = 'medium'
        elif any(word in user_text_lower for word in ['fast', 'energetic', 'high', 'intense', 'upbeat']):
            energy_level = 'high'
        
        # Extract style
        style = self.DEFAULT_STYLE
        if any(word in user_text_lower for word in ['traditional', 'classic']):
            style = 'traditional'
        elif any(word in user_text_lower for word in ['modern', 'contemporary']):
            style = 'modern'
        elif any(word in user_text_lower for word in ['romantic', 'love', 'sweet']):
            style = 'romantic'
        elif any(word in user_text_lower for word in ['sensual', 'sexy', 'intimate']):
            style = 'sensual'
        
        # Extract duration (look for numbers followed by seconds/minutes)
        duration = self.DEFAULT_DURATION
        duration_match = re.search(r'(\d+)\s*(second|sec|minute|min)', user_text_lower)
        if duration_match:
            value = int(duration_match.group(1))
            unit = duration_match.group(2)
            if 'min' in unit:
                duration = value * 60
            else:
                duration = value
        
        params = {
            'difficulty': difficulty,
            'energy_level': energy_level,
            'style': style,
            'duration': duration
        }
        
        # Validate before returning
        return self._validate_parameters(params)
    
    def _validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize extracted parameters.
        
        Args:
            params: Raw extracted parameters
        
        Returns:
            Validated parameters with defaults for invalid values
        """
        validated = {}
        
        # Validate difficulty
        difficulty = params.get('difficulty', self.DEFAULT_DIFFICULTY)
        if isinstance(difficulty, str):
            difficulty = difficulty.lower().strip()
        if difficulty not in self.ALLOWED_DIFFICULTY:
            logger.warning(
                f"Invalid difficulty '{difficulty}', using default '{self.DEFAULT_DIFFICULTY}'"
            )
            difficulty = self.DEFAULT_DIFFICULTY
        validated['difficulty'] = difficulty
        
        # Validate energy_level
        energy_level = params.get('energy_level', self.DEFAULT_ENERGY_LEVEL)
        if isinstance(energy_level, str):
            energy_level = energy_level.lower().strip()
        if energy_level not in self.ALLOWED_ENERGY_LEVEL:
            logger.warning(
                f"Invalid energy_level '{energy_level}', using default '{self.DEFAULT_ENERGY_LEVEL}'"
            )
            energy_level = self.DEFAULT_ENERGY_LEVEL
        validated['energy_level'] = energy_level
        
        # Validate style
        style = params.get('style', self.DEFAULT_STYLE)
        if isinstance(style, str):
            style = style.lower().strip()
        if style not in self.ALLOWED_STYLE:
            logger.warning(
                f"Invalid style '{style}', using default '{self.DEFAULT_STYLE}'"
            )
            style = self.DEFAULT_STYLE
        validated['style'] = style
        
        # Validate duration
        duration = params.get('duration', self.DEFAULT_DURATION)
        try:
            duration = int(duration)
            if duration < 10:
                logger.warning(f"Duration {duration}s too short, using default {self.DEFAULT_DURATION}s")
                duration = self.DEFAULT_DURATION
            elif duration > 300:
                logger.warning(f"Duration {duration}s too long, using default {self.DEFAULT_DURATION}s")
                duration = self.DEFAULT_DURATION
        except (ValueError, TypeError):
            logger.warning(f"Invalid duration '{duration}', using default {self.DEFAULT_DURATION}s")
            duration = self.DEFAULT_DURATION
        validated['duration'] = duration
        
        return validated
