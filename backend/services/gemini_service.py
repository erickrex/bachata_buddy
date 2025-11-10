"""
Gemini API service for natural language processing.

Features:
- Natural language query parsing for choreography parameters
- AI-generated explanations for move selections
- Smart search suggestions when no results found
- Rate limiting (60 requests/minute for free tier)
- Error handling with fallback strategies
"""

import os
import time
import json
import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from functools import wraps

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)


@dataclass
class ChoreographyParameters:
    """Structured choreography parameters extracted from natural language."""
    difficulty: str  # beginner, intermediate, advanced
    energy_level: str  # low, medium, high
    style: str  # romantic, energetic, sensual, playful
    tempo: str  # slow, medium, fast
    confidence: float = 0.8  # Confidence score for parsing
    specific_moves: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChoreographyParameters':
        """Create from dictionary."""
        return cls(**data)


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def __call__(self, func):
        """Decorator to apply rate limiting."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            
            # Remove old requests outside time window
            self.requests = [
                req_time for req_time in self.requests
                if now - req_time < self.time_window
            ]
            
            # Check if limit exceeded
            if len(self.requests) >= self.max_requests:
                wait_time = self.time_window - (now - self.requests[0])
                logger.warning(f"Rate limit exceeded. Waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                # Clear old requests after waiting
                self.requests = []
            
            # Execute function and record request
            result = func(*args, **kwargs)
            self.requests.append(time.time())
            return result
        
        return wrapper


# Rate limiter for Gemini API (60 requests/minute for free tier)
gemini_rate_limiter = RateLimiter(max_requests=60, time_window=60)


class GeminiService:
    """
    Service for interacting with Google Gemini API.
    
    Provides natural language understanding for choreography generation:
    - Parse user queries into structured parameters
    - Generate explanations for move selections
    - Suggest alternative queries when no results found
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini service.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            
        Raises:
            ValueError: If API key is not provided or genai not available
        """
        if not GENAI_AVAILABLE:
            raise ValueError(
                "google-generativeai package is not installed. "
                "Install it with: pip install google-generativeai"
            )
        
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Google API key is required. "
                "Set GOOGLE_API_KEY environment variable or pass api_key parameter. "
                "Get your key at: https://makersuite.google.com/app/apikey"
            )
        
        # Configure Gemini
        try:
            genai.configure(api_key=self.api_key)
            # Use gemini-1.5-flash (fast, free tier available)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise ValueError(f"Failed to initialize Gemini API: {e}")
    
    @gemini_rate_limiter
    def parse_choreography_request(self, query: str) -> ChoreographyParameters:
        """
        Parse natural language query into structured choreography parameters.
        
        Args:
            query: Natural language description (e.g., "romantic beginner bachata")
            
        Returns:
            ChoreographyParameters with extracted values
            
        Raises:
            ValueError: If query cannot be parsed
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        query = query.strip()
        
        # Create prompt for parameter extraction
        prompt = f"""
You are a dance choreography assistant. Extract choreography parameters from the user's query.

User Query: "{query}"

Extract the following parameters:
- difficulty: beginner, intermediate, or advanced (default: beginner)
- energy_level: low, medium, or high (default: medium)
- style: romantic, energetic, sensual, or playful (default: romantic)
- tempo: slow, medium, or fast (default: medium)

Return ONLY a JSON object with these exact keys. No markdown, no explanation.

Example output:
{{"difficulty": "beginner", "energy_level": "medium", "style": "romantic", "tempo": "slow"}}
"""
        
        try:
            # Call Gemini API
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            logger.debug(f"Gemini response: {response_text}")
            
            # Parse JSON from response
            params_dict = self._extract_json(response_text)
            
            # Validate and normalize parameters
            params_dict = self._validate_parameters(params_dict)
            
            # Create ChoreographyParameters object
            parameters = ChoreographyParameters(
                difficulty=params_dict.get('difficulty', 'beginner'),
                energy_level=params_dict.get('energy_level', 'medium'),
                style=params_dict.get('style', 'romantic'),
                tempo=params_dict.get('tempo', 'medium'),
                confidence=0.9,  # High confidence for AI parsing
                specific_moves=params_dict.get('specific_moves')
            )
            
            logger.info(f"Parsed parameters: {parameters}")
            return parameters
            
        except Exception as e:
            logger.warning(f"Gemini parsing failed: {e}. Trying fallback parser.")
            # Fallback to simple keyword matching
            return self._fallback_parse(query)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from response text.
        
        Handles markdown code blocks and plain JSON.
        
        Args:
            text: Response text from Gemini
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            ValueError: If JSON cannot be extracted
        """
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from response: {e}")
    
    def _validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize parameters.
        
        Args:
            params: Raw parameters dictionary
            
        Returns:
            Validated and normalized parameters
        """
        valid_difficulties = ['beginner', 'intermediate', 'advanced']
        valid_energies = ['low', 'medium', 'high']
        valid_styles = ['romantic', 'energetic', 'sensual', 'playful']
        valid_tempos = ['slow', 'medium', 'fast']
        
        # Normalize and validate
        difficulty = params.get('difficulty', 'beginner').lower()
        if difficulty not in valid_difficulties:
            logger.warning(f"Invalid difficulty '{difficulty}', using 'beginner'")
            difficulty = 'beginner'
        
        energy_level = params.get('energy_level', 'medium').lower()
        if energy_level not in valid_energies:
            logger.warning(f"Invalid energy_level '{energy_level}', using 'medium'")
            energy_level = 'medium'
        
        style = params.get('style', 'romantic').lower()
        if style not in valid_styles:
            logger.warning(f"Invalid style '{style}', using 'romantic'")
            style = 'romantic'
        
        tempo = params.get('tempo', 'medium').lower()
        if tempo not in valid_tempos:
            logger.warning(f"Invalid tempo '{tempo}', using 'medium'")
            tempo = 'medium'
        
        return {
            'difficulty': difficulty,
            'energy_level': energy_level,
            'style': style,
            'tempo': tempo,
            'specific_moves': params.get('specific_moves')
        }
    
    def _fallback_parse(self, query: str) -> ChoreographyParameters:
        """
        Fallback parser using simple keyword matching.
        
        Args:
            query: Natural language query
            
        Returns:
            ChoreographyParameters with best-guess values
        """
        query_lower = query.lower()
        
        # Difficulty
        if 'beginner' in query_lower or 'easy' in query_lower or 'simple' in query_lower:
            difficulty = 'beginner'
        elif 'advanced' in query_lower or 'expert' in query_lower or 'hard' in query_lower:
            difficulty = 'advanced'
        elif 'intermediate' in query_lower or 'medium' in query_lower:
            difficulty = 'intermediate'
        else:
            difficulty = 'beginner'
        
        # Energy level
        if 'low' in query_lower or 'calm' in query_lower or 'relaxed' in query_lower:
            energy_level = 'low'
        elif 'high' in query_lower or 'energetic' in query_lower or 'intense' in query_lower:
            energy_level = 'high'
        else:
            energy_level = 'medium'
        
        # Style
        if 'romantic' in query_lower or 'love' in query_lower or 'intimate' in query_lower:
            style = 'romantic'
        elif 'energetic' in query_lower or 'party' in query_lower or 'fun' in query_lower:
            style = 'energetic'
        elif 'sensual' in query_lower or 'sexy' in query_lower or 'body roll' in query_lower:
            style = 'sensual'
        elif 'playful' in query_lower or 'flirty' in query_lower:
            style = 'playful'
        else:
            style = 'romantic'
        
        # Tempo
        if 'slow' in query_lower or 'gentle' in query_lower:
            tempo = 'slow'
        elif 'fast' in query_lower or 'quick' in query_lower or 'rapid' in query_lower:
            tempo = 'fast'
        else:
            tempo = 'medium'
        
        logger.info(f"Fallback parse: {difficulty}, {energy_level}, {style}, {tempo}")
        
        return ChoreographyParameters(
            difficulty=difficulty,
            energy_level=energy_level,
            style=style,
            tempo=tempo,
            confidence=0.6  # Lower confidence for fallback parsing
        )
    
    @gemini_rate_limiter
    def suggest_alternatives(
        self, 
        failed_query: str, 
        available_metadata: Dict[str, Any]
    ) -> List[str]:
        """
        Suggest alternative queries when search returns no results.
        
        Args:
            failed_query: Original query that returned no results
            available_metadata: Available choreography metadata
            
        Returns:
            List of 3-5 suggested alternative queries
        """
        # Extract available options from metadata
        difficulties = available_metadata.get('difficulties', ['beginner', 'intermediate', 'advanced'])
        styles = available_metadata.get('styles', ['romantic', 'energetic', 'sensual', 'playful'])
        
        prompt = f"""
The user searched for: "{failed_query}"

No choreographies matched their query.

Available options:
- Difficulties: {', '.join(difficulties)}
- Styles: {', '.join(styles)}

Suggest 3-5 alternative search queries that might work better.
Return ONLY a JSON array of strings. No markdown, no explanation.

Example output:
["romantic beginner bachata", "energetic intermediate routine", "sensual advanced choreography"]
"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON array
            suggestions = self._extract_json_array(response_text)
            
            logger.info(f"Generated {len(suggestions)} suggestions")
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            logger.warning(f"Failed to generate suggestions: {e}")
            # Fallback to simple suggestions
            return self._fallback_suggestions(difficulties, styles)
    
    def _extract_json_array(self, text: str) -> List[str]:
        """
        Extract JSON array from response text.
        
        Args:
            text: Response text from Gemini
            
        Returns:
            List of strings
        """
        # Try to find JSON array in markdown code blocks
        json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON array without code blocks
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text
        
        try:
            result = json.loads(json_str)
            if isinstance(result, list):
                return [str(item) for item in result]
            return []
        except json.JSONDecodeError:
            return []
    
    def _fallback_suggestions(
        self, 
        difficulties: List[str], 
        styles: List[str]
    ) -> List[str]:
        """
        Generate fallback suggestions using templates.
        
        Args:
            difficulties: Available difficulty levels
            styles: Available styles
            
        Returns:
            List of suggested queries
        """
        suggestions = []
        
        # Generate combinations
        if 'beginner' in difficulties and 'romantic' in styles:
            suggestions.append("romantic beginner bachata with slow tempo")
        
        if 'intermediate' in difficulties and 'energetic' in styles:
            suggestions.append("energetic intermediate routine for a party")
        
        if 'advanced' in difficulties and 'sensual' in styles:
            suggestions.append("sensual advanced choreography with body rolls")
        
        # Add generic suggestions
        suggestions.append("beginner friendly bachata routine")
        suggestions.append("intermediate level dance sequence")
        
        return suggestions[:5]
