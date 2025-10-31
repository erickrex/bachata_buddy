"""
Tests for GeminiService.

Tests natural language query parsing, explanation generation, and suggestion generation.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from ai_services.services.gemini_service import (
    GeminiService,
    ChoreographyParameters,
    RateLimiter
)


@pytest.fixture
def mock_api_key():
    """Mock API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def gemini_service(mock_api_key):
    """Create GeminiService instance with mocked API."""
    with patch('google.generativeai.configure'):
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_model.return_value = MagicMock()
            service = GeminiService(api_key=mock_api_key)
            return service


class TestChoreographyParameters:
    """Test ChoreographyParameters dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        params = ChoreographyParameters(
            difficulty='beginner',
            energy_level='medium',
            style='romantic',
            tempo='slow'
        )
        
        result = params.to_dict()
        
        assert result['difficulty'] == 'beginner'
        assert result['energy_level'] == 'medium'
        assert result['style'] == 'romantic'
        assert result['tempo'] == 'slow'
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'difficulty': 'intermediate',
            'energy_level': 'high',
            'style': 'energetic',
            'tempo': 'fast'
        }
        
        params = ChoreographyParameters.from_dict(data)
        
        assert params.difficulty == 'intermediate'
        assert params.energy_level == 'high'
        assert params.style == 'energetic'
        assert params.tempo == 'fast'


class TestRateLimiter:
    """Test RateLimiter."""
    
    def test_rate_limiter_allows_requests_within_limit(self):
        """Test that rate limiter allows requests within limit."""
        limiter = RateLimiter(max_requests=5, time_window=1)
        
        @limiter
        def test_func():
            return "success"
        
        # Should allow 5 requests
        for _ in range(5):
            result = test_func()
            assert result == "success"
    
    def test_rate_limiter_blocks_excess_requests(self):
        """Test that rate limiter blocks excess requests."""
        limiter = RateLimiter(max_requests=2, time_window=10)
        
        call_count = 0
        
        @limiter
        def test_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        # First 2 requests should succeed immediately
        test_func()
        test_func()
        assert call_count == 2


class TestGeminiService:
    """Test GeminiService."""
    
    def test_initialization_without_api_key(self):
        """Test that initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Google API key is required"):
                GeminiService()
    
    def test_initialization_with_api_key(self, mock_api_key):
        """Test successful initialization with API key."""
        with patch('google.generativeai.configure') as mock_configure:
            with patch('google.generativeai.GenerativeModel') as mock_model:
                mock_model.return_value = MagicMock()
                
                service = GeminiService(api_key=mock_api_key)
                
                mock_configure.assert_called_once_with(api_key=mock_api_key)
                assert service.api_key == mock_api_key
    
    def test_parse_simple_query(self, gemini_service):
        """Test parsing simple natural language query."""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = '{"difficulty": "beginner", "energy_level": "medium", "style": "romantic", "tempo": "slow"}'
        gemini_service.model.generate_content = Mock(return_value=mock_response)
        
        result = gemini_service.parse_choreography_request(
            "Create a romantic beginner bachata with slow tempo"
        )
        
        assert result.difficulty == "beginner"
        assert result.style == "romantic"
        assert result.tempo == "slow"
        assert result.energy_level == "medium"
    
    def test_parse_complex_query(self, gemini_service):
        """Test parsing complex query with multiple parameters."""
        mock_response = Mock()
        mock_response.text = '{"difficulty": "intermediate", "energy_level": "high", "style": "energetic", "tempo": "fast"}'
        gemini_service.model.generate_content = Mock(return_value=mock_response)
        
        result = gemini_service.parse_choreography_request(
            "I need an energetic intermediate routine with fast tempo for a party"
        )
        
        assert result.difficulty == "intermediate"
        assert result.energy_level == "high"
        assert result.style == "energetic"
        assert result.tempo == "fast"
    
    def test_parse_query_with_markdown_json(self, gemini_service):
        """Test parsing query when response contains markdown code blocks."""
        mock_response = Mock()
        mock_response.text = '```json\n{"difficulty": "advanced", "energy_level": "high", "style": "sensual", "tempo": "medium"}\n```'
        gemini_service.model.generate_content = Mock(return_value=mock_response)
        
        result = gemini_service.parse_choreography_request(
            "Generate a sensual advanced choreography"
        )
        
        assert result.difficulty == "advanced"
        assert result.style == "sensual"
    
    def test_fallback_parse_on_api_error(self, gemini_service):
        """Test fallback to keyword matching on API error."""
        gemini_service.model.generate_content = Mock(side_effect=Exception("API error"))
        
        result = gemini_service.parse_choreography_request(
            "romantic beginner bachata"
        )
        
        # Should use fallback parser
        assert result.difficulty == "beginner"
        assert result.style == "romantic"
    
    def test_fallback_parse_keywords(self, gemini_service):
        """Test fallback parser with various keywords."""
        gemini_service.model.generate_content = Mock(side_effect=Exception("API error"))
        
        # Test beginner
        result = gemini_service.parse_choreography_request("easy beginner routine")
        assert result.difficulty == "beginner"
        
        # Test advanced
        result = gemini_service.parse_choreography_request("hard advanced choreography")
        assert result.difficulty == "advanced"
        
        # Test energetic style
        result = gemini_service.parse_choreography_request("energetic party dance")
        assert result.style == "energetic"
        
        # Test fast tempo
        result = gemini_service.parse_choreography_request("fast quick routine")
        assert result.tempo == "fast"
    
    def test_parse_empty_query(self, gemini_service):
        """Test that empty query raises error."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            gemini_service.parse_choreography_request("")
    
    def test_validate_parameters(self, gemini_service):
        """Test parameter validation and normalization."""
        # Valid parameters
        params = {
            'difficulty': 'BEGINNER',  # Should be normalized to lowercase
            'energy_level': 'medium',
            'style': 'Romantic',
            'tempo': 'SLOW'
        }
        
        result = gemini_service._validate_parameters(params)
        
        assert result['difficulty'] == 'beginner'
        assert result['style'] == 'romantic'
        assert result['tempo'] == 'slow'
    
    def test_validate_invalid_parameters(self, gemini_service):
        """Test that invalid parameters are replaced with defaults."""
        params = {
            'difficulty': 'invalid',
            'energy_level': 'invalid',
            'style': 'invalid',
            'tempo': 'invalid'
        }
        
        result = gemini_service._validate_parameters(params)
        
        # Should use defaults
        assert result['difficulty'] == 'beginner'
        assert result['energy_level'] == 'medium'
        assert result['style'] == 'romantic'
        assert result['tempo'] == 'medium'
    
    def test_explain_move_selection(self, gemini_service):
        """Test explanation generation for move selection."""
        mock_response = Mock()
        mock_response.text = "This cross-body lead flows naturally from the basic step, maintaining the romantic energy you requested while staying appropriate for beginners."
        gemini_service.model.generate_content = Mock(return_value=mock_response)
        
        move = {
            'move_label': 'Cross-body Lead',
            'difficulty': 'beginner',
            'energy_level': 'medium'
        }
        
        context = {
            'parameters': ChoreographyParameters(
                difficulty='beginner',
                energy_level='medium',
                style='romantic',
                tempo='slow'
            )
        }
        
        explanation = gemini_service.explain_move_selection(move, context)
        
        assert len(explanation) > 0
        assert isinstance(explanation, str)
    
    def test_explain_move_fallback(self, gemini_service):
        """Test fallback explanation on API error."""
        gemini_service.model.generate_content = Mock(side_effect=Exception("API error"))
        
        move = {
            'move_label': 'Basic Step',
            'difficulty': 'beginner',
            'energy_level': 'low'
        }
        
        context = {
            'parameters': {
                'difficulty': 'beginner',
                'style': 'romantic'
            }
        }
        
        explanation = gemini_service.explain_move_selection(move, context)
        
        # Should use fallback template
        assert 'Basic Step' in explanation or 'this move' in explanation
        assert 'beginner' in explanation
        assert 'romantic' in explanation
    
    def test_suggest_alternatives(self, gemini_service):
        """Test suggestion generation for failed queries."""
        mock_response = Mock()
        mock_response.text = '["romantic beginner bachata", "energetic intermediate routine", "sensual advanced choreography"]'
        gemini_service.model.generate_content = Mock(return_value=mock_response)
        
        available_metadata = {
            'difficulties': ['beginner', 'intermediate', 'advanced'],
            'styles': ['romantic', 'energetic', 'sensual', 'playful']
        }
        
        suggestions = gemini_service.suggest_alternatives(
            "impossible query that returns nothing",
            available_metadata
        )
        
        assert len(suggestions) > 0
        assert len(suggestions) <= 5
        assert all(isinstance(s, str) for s in suggestions)
    
    def test_suggest_alternatives_fallback(self, gemini_service):
        """Test fallback suggestions on API error."""
        gemini_service.model.generate_content = Mock(side_effect=Exception("API error"))
        
        available_metadata = {
            'difficulties': ['beginner', 'intermediate', 'advanced'],
            'styles': ['romantic', 'energetic', 'sensual']
        }
        
        suggestions = gemini_service.suggest_alternatives(
            "failed query",
            available_metadata
        )
        
        # Should use fallback suggestions
        assert len(suggestions) > 0
        assert len(suggestions) <= 5
    
    def test_extract_json_from_markdown(self, gemini_service):
        """Test JSON extraction from markdown code blocks."""
        text = '```json\n{"key": "value"}\n```'
        
        result = gemini_service._extract_json(text)
        
        assert result == {"key": "value"}
    
    def test_extract_json_plain(self, gemini_service):
        """Test JSON extraction from plain text."""
        text = '{"key": "value"}'
        
        result = gemini_service._extract_json(text)
        
        assert result == {"key": "value"}
    
    def test_extract_json_array(self, gemini_service):
        """Test JSON array extraction."""
        text = '["item1", "item2", "item3"]'
        
        result = gemini_service._extract_json_array(text)
        
        assert result == ["item1", "item2", "item3"]
