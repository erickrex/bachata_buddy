"""
Integration tests for AI template flow.

Tests the complete flow from natural language input to parameter display.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from ai_services.services.gemini_service import ChoreographyParameters

User = get_user_model()


@pytest.fixture
def client():
    """Create test client."""
    return Client()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def mock_gemini_service():
    """Mock GeminiService for testing."""
    with patch('ai_services.services.gemini_service.GeminiService') as mock_service:
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        yield mock_instance


@pytest.mark.django_db
class TestAITemplateFlow:
    """Test AI template complete flow."""
    
    def test_get_ai_template(self, client):
        """Test GET request renders AI template."""
        response = client.get(reverse('choreography:describe-choreo'))
        
        assert response.status_code == 200
        assert b'AI Choreography Creator' in response.content or b'Describe Your Choreography' in response.content
    
    def test_post_query_without_confirmation(self, client, mock_gemini_service):
        """Test POST with query returns parsed parameters."""
        # Mock parse response
        mock_params = ChoreographyParameters(
            difficulty='beginner',
            energy_level='medium',
            style='romantic',
            tempo='slow'
        )
        mock_gemini_service.parse_choreography_request.return_value = mock_params
        
        response = client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': 'Create a romantic beginner bachata',
                'confirmed': 'false'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert 'parameters' in data
        assert data['parameters']['difficulty'] == 'beginner'
        assert data['parameters']['style'] == 'romantic'
        assert data['parameters']['tempo'] == 'slow'
    
    def test_post_empty_query(self, client):
        """Test POST with empty query returns error."""
        response = client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': '',
                'confirmed': 'false'
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'error' in data
    
    def test_post_query_parse_error_with_suggestions(self, client, mock_gemini_service):
        """Test POST with unparseable query returns suggestions."""
        # Mock parse error
        mock_gemini_service.parse_choreography_request.side_effect = Exception("Parse error")
        
        # Mock suggestions
        mock_gemini_service.suggest_alternatives.return_value = [
            "romantic beginner bachata",
            "energetic intermediate routine"
        ]
        
        response = client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': 'impossible query',
                'confirmed': 'false'
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.content)
        
        assert 'error' in data
        assert 'suggestions' in data
        assert len(data['suggestions']) > 0
    
    def test_post_confirmed_with_parameters(self, client, mock_gemini_service):
        """Test POST with confirmed=true generates choreography."""
        params_dict = {
            'difficulty': 'intermediate',
            'energy_level': 'high',
            'style': 'energetic',
            'tempo': 'fast'
        }
        
        response = client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': 'energetic intermediate routine',
                'confirmed': 'true',
                'parameters': json.dumps(params_dict)
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        # Should return result (placeholder for now)
        assert 'result' in data
    
    def test_post_confirmed_without_parameters_reparses(self, client, mock_gemini_service):
        """Test POST with confirmed=true but no parameters re-parses query."""
        mock_params = ChoreographyParameters(
            difficulty='beginner',
            energy_level='medium',
            style='romantic',
            tempo='slow'
        )
        mock_gemini_service.parse_choreography_request.return_value = mock_params
        
        response = client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': 'romantic beginner bachata',
                'confirmed': 'true'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.content)
        
        # Should call parse again
        mock_gemini_service.parse_choreography_request.assert_called()
        assert 'result' in data
    
    def test_gemini_service_not_configured(self, client):
        """Test error handling when Gemini service is not configured."""
        with patch('ai_services.services.gemini_service.GeminiService') as mock_service:
            mock_service.side_effect = ValueError("Google API key is required")
            
            response = client.post(
                reverse('choreography:describe-choreo'),
                data={
                    'query': 'test query',
                    'confirmed': 'false'
                }
            )
            
            assert response.status_code == 500
            data = json.loads(response.content)
            assert 'error' in data
            assert 'not configured' in data['error'].lower()


@pytest.mark.django_db
class TestAPIParseQuery:
    """Test API endpoint for query parsing."""
    
    def test_api_parse_query_success(self, client, mock_gemini_service):
        """Test successful query parsing via API."""
        with patch('ai_services.services.gemini_service.GeminiService') as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance
            
            mock_params = ChoreographyParameters(
                difficulty='advanced',
                energy_level='high',
                style='sensual',
                tempo='medium'
            )
            mock_instance.parse_choreography_request.return_value = mock_params
            
            response = client.post(
                reverse('choreography:api-parse-query'),
                data=json.dumps({'query': 'sensual advanced choreography'}),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.content)
            
            assert data['success'] is True
            assert 'parameters' in data
            assert data['parameters']['difficulty'] == 'advanced'
            assert data['parameters']['style'] == 'sensual'
    
    def test_api_parse_query_empty(self, client):
        """Test API with empty query."""
        response = client.post(
            reverse('choreography:api-parse-query'),
            data=json.dumps({'query': ''}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'error' in data
    
    def test_api_parse_query_error_with_suggestions(self, client):
        """Test API error handling with suggestions."""
        with patch('ai_services.services.gemini_service.GeminiService') as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance
            
            # Mock parse error
            mock_instance.parse_choreography_request.side_effect = Exception("Parse error")
            
            # Mock suggestions
            mock_instance.suggest_alternatives.return_value = [
                "romantic beginner bachata",
                "energetic intermediate routine"
            ]
            
            response = client.post(
                reverse('choreography:api-parse-query'),
                data=json.dumps({'query': 'invalid query'}),
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.content)
            
            assert 'error' in data
            assert 'suggestions' in data


@pytest.mark.django_db
class TestParameterEditing:
    """Test parameter editing functionality."""
    
    def test_edit_parameters_flow(self, client, mock_gemini_service):
        """Test editing parameters after initial parse."""
        # Step 1: Parse query
        mock_params = ChoreographyParameters(
            difficulty='beginner',
            energy_level='medium',
            style='romantic',
            tempo='slow'
        )
        mock_gemini_service.parse_choreography_request.return_value = mock_params
        
        response1 = client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': 'romantic beginner bachata',
                'confirmed': 'false'
            }
        )
        
        assert response1.status_code == 200
        data1 = json.loads(response1.content)
        
        # Step 2: User edits parameters (simulated by modifying dict)
        edited_params = data1['parameters'].copy()
        edited_params['difficulty'] = 'intermediate'
        edited_params['tempo'] = 'fast'
        
        # Step 3: Confirm with edited parameters
        response2 = client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': 'romantic beginner bachata',
                'confirmed': 'true',
                'parameters': json.dumps(edited_params)
            }
        )
        
        assert response2.status_code == 200
        data2 = json.loads(response2.content)
        
        # Should use edited parameters
        assert 'result' in data2


@pytest.mark.django_db
class TestErrorHandling:
    """Test error handling in AI template."""
    
    def test_invalid_json_parameters(self, client):
        """Test handling of invalid JSON in parameters."""
        response = client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': 'test query',
                'confirmed': 'true',
                'parameters': 'invalid json'
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'error' in data
    
    def test_unexpected_error(self, client):
        """Test handling of unexpected errors."""
        with patch('ai_services.services.gemini_service.GeminiService') as mock_service:
            mock_service.side_effect = RuntimeError("Unexpected error")
            
            response = client.post(
                reverse('choreography:describe-choreo'),
                data={
                    'query': 'test query',
                    'confirmed': 'false'
                }
            )
            
            assert response.status_code == 500
            data = json.loads(response.content)
            assert 'error' in data
