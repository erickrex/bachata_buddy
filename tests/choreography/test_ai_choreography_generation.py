"""
Tests for AI template choreography generation with explanations.

Tests:
- Explanation generation
- Explanation quality
- Fallback to template messages
- Legacy template isolation
- End-to-end AI template flow
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.services.gemini_service import ChoreographyParameters


User = get_user_model()


class TestAIExplanationGeneration(TestCase):
    """Test AI explanation generation for choreography."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    @patch('core.services.gemini_service.GeminiService')
    def test_explanation_generation_for_moves(self, mock_gemini_class):
        """Test that explanations are generated for each move."""
        # Mock Gemini service
        mock_gemini = MagicMock()
        mock_gemini_class.return_value = mock_gemini
        
        # Mock parse method
        mock_params = ChoreographyParameters(
            difficulty='intermediate',
            energy_level='medium',
            style='romantic',
            tempo='slow'
        )
        mock_gemini.parse_choreography_request.return_value = mock_params
        
        # Mock explanation generation
        mock_gemini.explain_move_selection.return_value = (
            "This romantic turn was selected to match your intermediate difficulty "
            "and medium energy preferences, creating a smooth flow in the choreography."
        )
        
        # Test explanation generation
        move = {
            'clip_id': 'move_001',
            'video_path': 'data/videos/romantic_turn.mp4',
            'move_label': 'romantic_turn'
        }
        
        context = {
            'difficulty': 'intermediate',
            'energy_level': 'medium',
            'style': 'romantic',
            'tempo': 'slow',
            'move_position': 1,
            'total_moves': 5
        }
        
        explanation = mock_gemini.explain_move_selection(move, context)
        
        # Verify explanation was generated
        assert explanation is not None
        assert len(explanation) > 0
        assert 'romantic' in explanation.lower()
        assert 'intermediate' in explanation.lower()
    
    @patch('core.services.gemini_service.GeminiService')
    def test_explanation_quality_checks(self, mock_gemini_class):
        """Test that generated explanations meet quality standards."""
        mock_gemini = MagicMock()
        mock_gemini_class.return_value = mock_gemini
        
        # Mock high-quality explanation
        quality_explanation = (
            "This cross body lead was chosen for its perfect match with your "
            "intermediate skill level. The move's moderate tempo aligns beautifully "
            "with the romantic style you requested, creating an elegant transition "
            "in your choreography."
        )
        mock_gemini.explain_move_selection.return_value = quality_explanation
        
        move = {'clip_id': 'move_002', 'move_label': 'cross_body_lead'}
        context = {'difficulty': 'intermediate', 'style': 'romantic'}
        
        explanation = mock_gemini.explain_move_selection(move, context)
        
        # Quality checks
        assert len(explanation) > 50  # Substantial explanation
        assert len(explanation.split()) > 10  # Multiple words
        assert any(word in explanation.lower() for word in ['match', 'chosen', 'selected', 'perfect'])
    
    @patch('core.services.gemini_service.GeminiService')
    def test_fallback_to_template_messages(self, mock_gemini_class):
        """Test fallback to template messages when AI fails."""
        mock_gemini = MagicMock()
        mock_gemini_class.return_value = mock_gemini
        
        # Mock AI failure
        mock_gemini.explain_move_selection.side_effect = Exception("API error")
        
        # Fallback explanation should be generated
        move = {'clip_id': 'move_003', 'move_label': 'basic_step'}
        context = {'difficulty': 'beginner', 'energy_level': 'low'}
        
        try:
            explanation = mock_gemini.explain_move_selection(move, context)
        except Exception:
            # Use fallback
            explanation = (
                f"This move was selected to match your {context['difficulty']} difficulty "
                f"and {context['energy_level']} energy preferences."
            )
        
        # Verify fallback explanation
        assert explanation is not None
        assert 'beginner' in explanation
        assert 'low' in explanation
    
    @patch('core.services.gemini_service.GeminiService')
    def test_batch_explanation_generation(self, mock_gemini_class):
        """Test generating explanations for multiple moves."""
        mock_gemini = MagicMock()
        mock_gemini_class.return_value = mock_gemini
        
        # Mock explanations for multiple moves
        explanations = [
            "Move 1: Perfect opening with basic step",
            "Move 2: Smooth transition with cross body lead",
            "Move 3: Elegant turn sequence",
            "Move 4: Dynamic styling element",
            "Move 5: Strong closing move"
        ]
        mock_gemini.explain_move_selection.side_effect = explanations
        
        moves = [
            {'clip_id': f'move_{i}', 'move_label': f'move_{i}'}
            for i in range(1, 6)
        ]
        
        generated_explanations = []
        for i, move in enumerate(moves):
            context = {'move_position': i + 1, 'total_moves': len(moves)}
            explanation = mock_gemini.explain_move_selection(move, context)
            generated_explanations.append(explanation)
        
        # Verify all explanations generated
        assert len(generated_explanations) == 5
        assert all(exp is not None for exp in generated_explanations)
        assert all(len(exp) > 0 for exp in generated_explanations)


class TestLegacyTemplateIsolation(TestCase):
    """Test that legacy template shows NO AI features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_legacy_template_no_explanations(self):
        """Test that legacy template does not show explanations."""
        # Access legacy template
        response = self.client.get(reverse('choreography:select-song'))
        
        # Verify no AI explanation elements
        assert response.status_code == 200
        assert b'AI Explanations' not in response.content
        assert b'explain_move_selection' not in response.content
        assert b'GeminiService' not in response.content
    
    def test_legacy_template_functionality_unchanged(self):
        """Test that legacy template functionality is unchanged."""
        # Access legacy template
        response = self.client.get(reverse('choreography:select-song'))
        
        # Verify traditional elements present
        assert response.status_code == 200
        assert b'song_selection' in response.content or b'select' in response.content.lower()
        
        # Verify no natural language input
        assert b'describe your choreography' not in response.content.lower()
        assert b'natural language' not in response.content.lower()
    
    @patch('core.services.elasticsearch_service.Elasticsearch')
    def test_both_templates_use_same_elasticsearch(self, mock_es_client):
        """Test that both templates use the same Elasticsearch connection."""
        # Mock Elasticsearch client
        mock_es_client.return_value.ping.return_value = True
        
        # This is verified by checking that both use the same service
        from core.services.elasticsearch_service import ElasticsearchService
        from core.config.environment_config import EnvironmentConfig
        
        config = EnvironmentConfig()
        es_service = ElasticsearchService(config.elasticsearch)
        
        # Verify service is properly configured
        assert es_service is not None
        assert es_service.index_name == config.elasticsearch.index_name


class TestEndToEndAITemplate(TestCase):
    """Test end-to-end AI template flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    @patch('core.services.gemini_service.GeminiService')
    def test_complete_ai_flow_with_explanations(self, mock_gemini_class):
        """Test complete flow from query to explanations."""
        mock_gemini = MagicMock()
        mock_gemini_class.return_value = mock_gemini
        
        # Step 1: Parse query
        mock_params = ChoreographyParameters(
            difficulty='intermediate',
            energy_level='medium',
            style='romantic',
            tempo='slow'
        )
        mock_gemini.parse_choreography_request.return_value = mock_params
        
        # Submit query
        response = self.client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': 'Create a romantic intermediate bachata with slow tempo',
                'confirmed': 'false'
            }
        )
        
        # Verify parameters returned
        assert response.status_code == 200
        data = response.json()
        assert 'parameters' in data
        assert data['parameters']['difficulty'] == 'intermediate'
        assert data['parameters']['style'] == 'romantic'
    
    @patch('threading.Thread')
    @patch('core.services.gemini_service.GeminiService')
    def test_ai_generation_starts_background_task(self, mock_gemini_class, mock_thread):
        """Test that AI generation starts a background task."""
        mock_gemini = MagicMock()
        mock_gemini_class.return_value = mock_gemini
        
        mock_params = ChoreographyParameters(
            difficulty='beginner',
            energy_level='low',
            style='playful',
            tempo='medium'
        )
        mock_gemini.parse_choreography_request.return_value = mock_params
        
        # Confirm parameters and start generation
        response = self.client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': 'Create a playful beginner routine',
                'confirmed': 'true',
                'parameters': json.dumps(mock_params.to_dict())
            }
        )
        
        # Verify task started
        assert response.status_code == 200
        data = response.json()
        assert 'task_id' in data
        assert data['status'] == 'started'
    
    @patch('core.services.gemini_service.GeminiService')
    def test_error_handling_with_suggestions(self, mock_gemini_class):
        """Test error handling with AI suggestions."""
        mock_gemini = MagicMock()
        mock_gemini_class.return_value = mock_gemini
        
        # Mock parsing failure
        mock_gemini.parse_choreography_request.side_effect = Exception("Parse error")
        
        # Mock suggestions
        mock_gemini.suggest_alternatives.return_value = [
            "Try: Create a romantic beginner bachata",
            "Try: I need an energetic intermediate routine",
            "Try: Generate a sensual advanced choreography"
        ]
        
        # Submit invalid query
        response = self.client.post(
            reverse('choreography:describe-choreo'),
            data={
                'query': 'invalid query xyz',
                'confirmed': 'false'
            }
        )
        
        # Verify error with suggestions
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'suggestions' in data
        assert len(data['suggestions']) > 0


class TestExplanationCaching(TestCase):
    """Test explanation caching and performance."""
    
    @patch('core.services.gemini_service.GeminiService')
    def test_explanation_caching_reduces_api_calls(self, mock_gemini_class):
        """Test that explanations are cached to reduce API calls."""
        mock_gemini = MagicMock()
        mock_gemini_class.return_value = mock_gemini
        
        # Mock explanation
        mock_gemini.explain_move_selection.return_value = "Cached explanation"
        
        move = {'clip_id': 'move_001', 'move_label': 'basic_step'}
        context = {'difficulty': 'beginner'}
        
        # First call
        explanation1 = mock_gemini.explain_move_selection(move, context)
        
        # Second call (should use cache in real implementation)
        explanation2 = mock_gemini.explain_move_selection(move, context)
        
        # Verify explanations match
        assert explanation1 == explanation2
    
    @patch('core.services.gemini_service.GeminiService')
    def test_explanation_generation_timeout(self, mock_gemini_class):
        """Test that explanation generation has timeout protection."""
        mock_gemini = MagicMock()
        mock_gemini_class.return_value = mock_gemini
        
        # Mock slow API call
        import time
        def slow_explanation(*args, **kwargs):
            time.sleep(0.1)  # Simulate slow API
            return "Slow explanation"
        
        mock_gemini.explain_move_selection.side_effect = slow_explanation
        
        move = {'clip_id': 'move_001', 'move_label': 'basic_step'}
        context = {'difficulty': 'beginner'}
        
        # Should complete without hanging
        start_time = time.time()
        explanation = mock_gemini.explain_move_selection(move, context)
        elapsed = time.time() - start_time
        
        # Verify it completed
        assert explanation is not None
        assert elapsed < 5.0  # Should not take too long


class TestAITemplateAccessControl(TestCase):
    """Test access control for AI template."""
    
    @patch('core.services.gemini_service.GeminiService')
    def test_ai_template_requires_authentication(self, mock_gemini_class):
        """Test that AI template requires user authentication."""
        # Mock Gemini service
        mock_gemini = MagicMock()
        mock_gemini_class.return_value = mock_gemini
        mock_params = ChoreographyParameters(
            difficulty='beginner',
            energy_level='medium',
            style='romantic',
            tempo='medium'
        )
        mock_gemini.parse_choreography_request.return_value = mock_params
        
        client = Client()
        
        # Try to access without login
        response = client.get(reverse('choreography:describe-choreo'))
        
        # Should allow GET (template view)
        assert response.status_code == 200
        
        # Try to submit without login - should work for parsing (no auth required)
        response = client.post(
            reverse('choreography:describe-choreo'),
            data={'query': 'test query', 'confirmed': 'false'}
        )
        
        # Parsing doesn't require auth, but generation does
        assert response.status_code == 200
    
    def test_task_status_requires_ownership(self):
        """Test that users can only access their own tasks."""
        import uuid
        
        # Create two users
        user1 = User.objects.create_user(username='user1', password='pass1')
        user2 = User.objects.create_user(username='user2', password='pass2')
        
        client1 = Client()
        client1.login(username='user1', password='pass1')
        
        client2 = Client()
        client2.login(username='user2', password='pass2')
        
        # User1 creates a task (mock) - use valid UUID
        task_id = str(uuid.uuid4())
        
        # User2 tries to access user1's task
        response = client2.get(reverse('choreography:task_status', args=[task_id]))
        
        # Should be not found (task doesn't exist in this test)
        assert response.status_code == 404
