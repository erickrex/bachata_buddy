"""
Property-based tests for Parameter Extractor service.

**Feature: agent-orchestration**

These tests verify the correctness properties of the parameter extraction service
as defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch, MagicMock

from .parameter_extractor import ParameterExtractor, ParameterExtractionError


# Hypothesis strategies for generating test data

@st.composite
def natural_language_request(draw):
    """Generate natural language choreography requests"""
    # Generate components
    difficulty_words = {
        'beginner': ['beginner', 'easy', 'simple', 'basic', 'starter'],
        'intermediate': ['intermediate', 'medium', 'moderate'],
        'advanced': ['advanced', 'expert', 'difficult', 'hard', 'challenging']
    }
    
    energy_words = {
        'low': ['slow', 'calm', 'relaxed', 'gentle', 'low energy'],
        'medium': ['medium', 'moderate', 'normal'],
        'high': ['fast', 'energetic', 'high energy', 'intense', 'upbeat']
    }
    
    style_words = {
        'traditional': ['traditional', 'classic'],
        'modern': ['modern', 'contemporary'],
        'romantic': ['romantic', 'love', 'sweet'],
        'sensual': ['sensual', 'sexy', 'intimate']
    }
    
    # Randomly include or exclude each parameter
    include_difficulty = draw(st.booleans())
    include_energy = draw(st.booleans())
    include_style = draw(st.booleans())
    
    parts = []
    expected = {}
    
    if include_difficulty:
        difficulty = draw(st.sampled_from(list(difficulty_words.keys())))
        word = draw(st.sampled_from(difficulty_words[difficulty]))
        parts.append(word)
        expected['difficulty'] = difficulty
    
    if include_energy:
        energy = draw(st.sampled_from(list(energy_words.keys())))
        word = draw(st.sampled_from(energy_words[energy]))
        parts.append(word)
        expected['energy_level'] = energy
    
    if include_style:
        style = draw(st.sampled_from(list(style_words.keys())))
        word = draw(st.sampled_from(style_words[style]))
        parts.append(word)
        expected['style'] = style
    
    # Add some filler words
    filler = draw(st.sampled_from([
        'choreography', 'routine', 'dance', 'bachata',
        'for me', 'please', 'I want', 'create'
    ]))
    parts.insert(0, filler)
    
    # Shuffle parts using hypothesis permutations
    if len(parts) > 1:
        shuffled_indices = draw(st.permutations(range(len(parts))))
        parts = [parts[i] for i in shuffled_indices]
    
    request = ' '.join(parts)
    
    return request, expected


@st.composite
def incomplete_request(draw):
    """Generate incomplete or ambiguous requests"""
    templates = [
        "create a choreography",
        "I want a dance",
        "make something",
        "bachata routine",
        "dance for me",
        "",  # Empty
        "   ",  # Whitespace only
    ]
    
    return draw(st.sampled_from(templates))


@st.composite
def parameter_dict(draw):
    """Generate parameter dictionaries with potentially invalid values"""
    difficulty = draw(st.one_of(
        st.sampled_from(['beginner', 'intermediate', 'advanced']),
        st.sampled_from(['BEGINNER', 'Intermediate', 'ADVANCED']),  # Case variations
        st.sampled_from(['easy', 'hard', 'invalid', '', None])  # Invalid values
    ))
    
    energy_level = draw(st.one_of(
        st.sampled_from(['low', 'medium', 'high']),
        st.sampled_from(['LOW', 'Medium', 'HIGH']),  # Case variations
        st.sampled_from(['slow', 'fast', 'invalid', '', None])  # Invalid values
    ))
    
    style = draw(st.one_of(
        st.sampled_from(['traditional', 'modern', 'romantic', 'sensual']),
        st.sampled_from(['Traditional', 'MODERN', 'Romantic']),  # Case variations
        st.sampled_from(['classic', 'invalid', '', None])  # Invalid values
    ))
    
    duration = draw(st.one_of(
        st.integers(min_value=10, max_value=300),  # Valid range
        st.integers(min_value=-100, max_value=5),  # Too short
        st.integers(min_value=301, max_value=1000),  # Too long
        st.just(None),
        st.just('invalid')
    ))
    
    return {
        'difficulty': difficulty,
        'energy_level': energy_level,
        'style': style,
        'duration': duration
    }


# Property 1: Parameter extraction completeness
# **Validates: Requirements 1.1, 1.4**

class TestParameterExtractionCompleteness:
    """
    **Feature: agent-orchestration, Property 1: Parameter extraction completeness**
    **Validates: Requirements 1.1, 1.4**
    
    For any natural language choreography request, the Parameter Extractor should
    return a dictionary containing all required parameter keys (difficulty, energy_level,
    style, duration) with valid values from the allowed option lists.
    """
    
    @settings(max_examples=100, deadline=None)
    @given(request_data=natural_language_request())
    def test_extraction_returns_all_required_keys(self, request_data):
        """
        Property: For any natural language request, extract_parameters() should
        return a dictionary with all required keys.
        """
        request_text, expected_params = request_data
        
        # Skip empty requests (they should raise an error)
        assume(request_text and request_text.strip())
        
        # Mock OpenAI to return expected parameters
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Mock OpenAI response
            mock_response = MagicMock()
            mock_message = MagicMock()
            
            # Build response with expected params and defaults for missing ones
            response_params = {
                'difficulty': expected_params.get('difficulty', 'beginner'),
                'energy_level': expected_params.get('energy_level', 'medium'),
                'style': expected_params.get('style', 'modern'),
                'duration': 60
            }
            
            import json
            mock_message.content = json.dumps(response_params)
            mock_response.choices = [MagicMock(message=mock_message)]
            mock_client.chat.completions.create.return_value = mock_response
            
            # Create extractor
            extractor = ParameterExtractor(openai_api_key='test-key')
            
            # Extract parameters
            result = extractor.extract_parameters(request_text)
            
            # Verify all required keys are present
            required_keys = {'difficulty', 'energy_level', 'style', 'duration'}
            assert set(result.keys()) == required_keys, \
                f"Result should contain exactly {required_keys}, got {set(result.keys())}"
    
    @settings(max_examples=100, deadline=None)
    @given(request_data=natural_language_request())
    def test_extraction_returns_valid_values(self, request_data):
        """
        Property: For any natural language request, all extracted parameter values
        should be from the allowed option lists.
        """
        request_text, expected_params = request_data
        
        # Skip empty requests
        assume(request_text and request_text.strip())
        
        # Mock OpenAI
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Mock OpenAI response
            mock_response = MagicMock()
            mock_message = MagicMock()
            
            response_params = {
                'difficulty': expected_params.get('difficulty', 'beginner'),
                'energy_level': expected_params.get('energy_level', 'medium'),
                'style': expected_params.get('style', 'modern'),
                'duration': 60
            }
            
            import json
            mock_message.content = json.dumps(response_params)
            mock_response.choices = [MagicMock(message=mock_message)]
            mock_client.chat.completions.create.return_value = mock_response
            
            # Create extractor
            extractor = ParameterExtractor(openai_api_key='test-key')
            
            # Extract parameters
            result = extractor.extract_parameters(request_text)
            
            # Verify values are from allowed lists
            assert result['difficulty'] in ParameterExtractor.ALLOWED_DIFFICULTY, \
                f"difficulty '{result['difficulty']}' not in allowed list"
            assert result['energy_level'] in ParameterExtractor.ALLOWED_ENERGY_LEVEL, \
                f"energy_level '{result['energy_level']}' not in allowed list"
            assert result['style'] in ParameterExtractor.ALLOWED_STYLE, \
                f"style '{result['style']}' not in allowed list"
            assert isinstance(result['duration'], int), \
                f"duration should be int, got {type(result['duration'])}"
            assert 10 <= result['duration'] <= 300, \
                f"duration {result['duration']} should be between 10 and 300"
    
    @settings(max_examples=50, deadline=None)
    @given(request_data=natural_language_request())
    def test_keyword_fallback_returns_all_required_keys(self, request_data):
        """
        Property: For any natural language request, keyword fallback extraction
        should also return all required keys with valid values.
        """
        request_text, expected_params = request_data
        
        # Skip empty requests
        assume(request_text and request_text.strip())
        
        # Create extractor without OpenAI API key (forces keyword fallback)
        extractor = ParameterExtractor(openai_api_key=None)
        
        # Extract parameters (will use keyword fallback)
        result = extractor.extract_parameters(request_text)
        
        # Verify all required keys are present
        required_keys = {'difficulty', 'energy_level', 'style', 'duration'}
        assert set(result.keys()) == required_keys, \
            f"Keyword fallback should return {required_keys}, got {set(result.keys())}"
        
        # Verify values are valid
        assert result['difficulty'] in ParameterExtractor.ALLOWED_DIFFICULTY
        assert result['energy_level'] in ParameterExtractor.ALLOWED_ENERGY_LEVEL
        assert result['style'] in ParameterExtractor.ALLOWED_STYLE
        assert isinstance(result['duration'], int)


# Property 2: Default parameter application
# **Validates: Requirements 1.2**

class TestDefaultParameterApplication:
    """
    **Feature: agent-orchestration, Property 2: Default parameter application**
    **Validates: Requirements 1.2**
    
    For any incomplete or ambiguous choreography request, the Parameter Extractor
    should apply default values for missing parameters, ensuring the returned
    dictionary is always complete and valid.
    """
    
    @settings(max_examples=50, deadline=None)
    @given(incomplete_text=incomplete_request())
    def test_incomplete_requests_get_defaults(self, incomplete_text):
        """
        Property: For any incomplete request, extract_parameters() should apply
        default values and return a complete, valid parameter dictionary.
        """
        # Skip completely empty strings (they should raise an error)
        if not incomplete_text or not incomplete_text.strip():
            # Create extractor
            extractor = ParameterExtractor(openai_api_key=None)
            
            # Verify empty requests raise an error
            with pytest.raises(ParameterExtractionError):
                extractor.extract_parameters(incomplete_text)
            return
        
        # Create extractor without OpenAI (use keyword fallback)
        extractor = ParameterExtractor(openai_api_key=None)
        
        # Extract parameters
        result = extractor.extract_parameters(incomplete_text)
        
        # Verify all keys are present
        required_keys = {'difficulty', 'energy_level', 'style', 'duration'}
        assert set(result.keys()) == required_keys, \
            f"Incomplete request should still return all keys"
        
        # Verify defaults are applied (since request is incomplete)
        # At least some parameters should have default values
        assert result['difficulty'] in ParameterExtractor.ALLOWED_DIFFICULTY
        assert result['energy_level'] in ParameterExtractor.ALLOWED_ENERGY_LEVEL
        assert result['style'] in ParameterExtractor.ALLOWED_STYLE
        assert isinstance(result['duration'], int)
    
    @settings(max_examples=50, deadline=None)
    @given(incomplete_text=incomplete_request())
    def test_defaults_are_valid_values(self, incomplete_text):
        """
        Property: For any incomplete request, default values should be from
        the allowed option lists.
        """
        # Skip empty strings
        if not incomplete_text or not incomplete_text.strip():
            return
        
        # Create extractor
        extractor = ParameterExtractor(openai_api_key=None)
        
        # Extract parameters
        result = extractor.extract_parameters(incomplete_text)
        
        # Verify defaults are valid
        assert result['difficulty'] in ParameterExtractor.ALLOWED_DIFFICULTY
        assert result['energy_level'] in ParameterExtractor.ALLOWED_ENERGY_LEVEL
        assert result['style'] in ParameterExtractor.ALLOWED_STYLE
        assert 10 <= result['duration'] <= 300
    
    def test_empty_request_raises_error(self):
        """
        Property: Empty or whitespace-only requests should raise
        ParameterExtractionError.
        """
        extractor = ParameterExtractor(openai_api_key=None)
        
        # Test empty string
        with pytest.raises(ParameterExtractionError, match="cannot be empty"):
            extractor.extract_parameters("")
        
        # Test whitespace only
        with pytest.raises(ParameterExtractionError, match="cannot be empty"):
            extractor.extract_parameters("   ")
        
        # Test None (should also fail)
        with pytest.raises((ParameterExtractionError, AttributeError)):
            extractor.extract_parameters(None)


# Property 5: Parameter validation
# **Validates: Requirements 7.3**

class TestParameterValidation:
    """
    **Feature: agent-orchestration, Property 5: Parameter validation**
    **Validates: Requirements 7.3**
    
    For any parameter dictionary (whether from OpenAI or keyword extraction),
    the Parameter Extractor should validate that difficulty is in [beginner,
    intermediate, advanced], energy_level is in [low, medium, high], and style
    is in [traditional, modern, romantic, sensual].
    """
    
    @settings(max_examples=100, deadline=None)
    @given(params=parameter_dict())
    def test_validation_catches_invalid_values(self, params):
        """
        Property: For any parameter dictionary, _validate_parameters() should
        replace invalid values with defaults.
        """
        # Create extractor
        extractor = ParameterExtractor(openai_api_key=None)
        
        # Validate parameters
        result = extractor._validate_parameters(params)
        
        # Verify all values are valid
        assert result['difficulty'] in ParameterExtractor.ALLOWED_DIFFICULTY, \
            f"Invalid difficulty should be replaced with default"
        assert result['energy_level'] in ParameterExtractor.ALLOWED_ENERGY_LEVEL, \
            f"Invalid energy_level should be replaced with default"
        assert result['style'] in ParameterExtractor.ALLOWED_STYLE, \
            f"Invalid style should be replaced with default"
        assert isinstance(result['duration'], int), \
            f"Invalid duration should be replaced with default int"
        assert 10 <= result['duration'] <= 300, \
            f"Duration should be in valid range"
    
    @settings(max_examples=50, deadline=None)
    @given(params=parameter_dict())
    def test_valid_values_pass_through_unchanged(self, params):
        """
        Property: For any parameter dictionary with valid values, _validate_parameters()
        should return those values unchanged (except for normalization like lowercasing).
        """
        # Create extractor
        extractor = ParameterExtractor(openai_api_key=None)
        
        # Only test if all values are valid and strings
        if not isinstance(params.get('difficulty'), str):
            return
        if not isinstance(params.get('energy_level'), str):
            return
        if not isinstance(params.get('style'), str):
            return
        
        valid_difficulty = params['difficulty'].lower() in ParameterExtractor.ALLOWED_DIFFICULTY
        valid_energy = params['energy_level'].lower() in ParameterExtractor.ALLOWED_ENERGY_LEVEL
        valid_style = params['style'].lower() in ParameterExtractor.ALLOWED_STYLE
        valid_duration = isinstance(params.get('duration'), int) and 10 <= params.get('duration', 0) <= 300
        
        if not (valid_difficulty and valid_energy and valid_style and valid_duration):
            # Skip if any value is invalid
            return
        
        # Validate parameters
        result = extractor._validate_parameters(params)
        
        # Verify valid values pass through (normalized to lowercase)
        assert result['difficulty'] == params['difficulty'].lower()
        assert result['energy_level'] == params['energy_level'].lower()
        assert result['style'] == params['style'].lower()
        assert result['duration'] == params['duration']
    
    @settings(max_examples=50, deadline=None)
    @given(
        difficulty=st.sampled_from(['beginner', 'intermediate', 'advanced']),
        energy=st.sampled_from(['low', 'medium', 'high']),
        style=st.sampled_from(['traditional', 'modern', 'romantic', 'sensual']),
        duration=st.integers(min_value=10, max_value=300)
    )
    def test_all_valid_combinations_are_accepted(self, difficulty, energy, style, duration):
        """
        Property: For any combination of valid parameter values, validation
        should accept them without modification.
        """
        # Create extractor
        extractor = ParameterExtractor(openai_api_key=None)
        
        # Create params dict
        params = {
            'difficulty': difficulty,
            'energy_level': energy,
            'style': style,
            'duration': duration
        }
        
        # Validate
        result = extractor._validate_parameters(params)
        
        # Verify values are unchanged
        assert result['difficulty'] == difficulty
        assert result['energy_level'] == energy
        assert result['style'] == style
        assert result['duration'] == duration
    
    @settings(max_examples=30, deadline=None)
    @given(
        difficulty=st.text(min_size=1, max_size=20),
        energy=st.text(min_size=1, max_size=20),
        style=st.text(min_size=1, max_size=20),
        duration=st.one_of(st.integers(), st.text(), st.none())
    )
    def test_arbitrary_invalid_values_get_defaults(self, difficulty, energy, style, duration):
        """
        Property: For any arbitrary invalid parameter values, validation should
        replace them with defaults.
        """
        # Skip if values happen to be valid
        assume(difficulty.lower() not in ParameterExtractor.ALLOWED_DIFFICULTY)
        assume(energy.lower() not in ParameterExtractor.ALLOWED_ENERGY_LEVEL)
        assume(style.lower() not in ParameterExtractor.ALLOWED_STYLE)
        
        # Skip if duration happens to be valid
        if isinstance(duration, int) and 10 <= duration <= 300:
            return
        
        # Create extractor
        extractor = ParameterExtractor(openai_api_key=None)
        
        # Create params dict
        params = {
            'difficulty': difficulty,
            'energy_level': energy,
            'style': style,
            'duration': duration
        }
        
        # Validate
        result = extractor._validate_parameters(params)
        
        # Verify defaults are applied
        assert result['difficulty'] == ParameterExtractor.DEFAULT_DIFFICULTY
        assert result['energy_level'] == ParameterExtractor.DEFAULT_ENERGY_LEVEL
        assert result['style'] == ParameterExtractor.DEFAULT_STYLE
        assert result['duration'] == ParameterExtractor.DEFAULT_DURATION
