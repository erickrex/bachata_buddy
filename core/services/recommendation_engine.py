"""
Multi-factor scoring recommendation system for Bachata choreography generation.
Uses Elasticsearch-stored embeddings with weighted multimodal similarity computation.

Modality weights:
- Text semantic: 35%
- Audio: 35%
- Lead pose: 10%
- Follow pose: 10%
- Interaction: 10%
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import logging

from .elasticsearch_service import ElasticsearchService
from core.config.environment_config import EnvironmentConfig

logger = logging.getLogger(__name__)


@dataclass
class MoveCandidate:
    """Container for a move candidate with embeddings and metadata from Elasticsearch."""
    clip_id: str
    video_path: str
    move_label: str
    
    # Embeddings (from Elasticsearch)
    audio_embedding: np.ndarray  # 128D
    lead_embedding: np.ndarray  # 512D
    follow_embedding: np.ndarray  # 512D
    interaction_embedding: np.ndarray  # 256D
    text_embedding: np.ndarray  # 384D
    
    # Metadata from annotations
    energy_level: str = "medium"  # low/medium/high
    difficulty: str = "intermediate"  # beginner/intermediate/advanced
    estimated_tempo: float = 120.0
    lead_follow_roles: str = "both"  # lead_focus/follow_focus/both
    quality_score: float = 0.0
    detection_rate: float = 0.0


@dataclass
class RecommendationScore:
    """Container for detailed recommendation scoring results with multimodal breakdown."""
    move_candidate: MoveCandidate
    overall_score: float
    
    # Multimodal component scores (weighted)
    text_similarity: float
    audio_similarity: float
    lead_similarity: float
    follow_similarity: float
    interaction_similarity: float
    
    # Metadata matching scores
    difficulty_match: bool
    energy_match: bool
    tempo_difference: float
    
    # Weights used
    weights: Dict[str, float]


@dataclass
class RecommendationRequest:
    """Container for recommendation request parameters."""
    # Query embeddings (from user's music/input)
    query_audio_embedding: Optional[np.ndarray] = None  # 128D
    query_text_embedding: Optional[np.ndarray] = None  # 384D
    query_lead_embedding: Optional[np.ndarray] = None  # 512D
    query_follow_embedding: Optional[np.ndarray] = None  # 512D
    query_interaction_embedding: Optional[np.ndarray] = None  # 256D
    
    # Metadata filters
    difficulty: Optional[str] = None  # beginner/intermediate/advanced
    energy_level: Optional[str] = None  # low/medium/high
    move_label: Optional[str] = None  # Specific move type
    lead_follow_roles: Optional[str] = None  # lead_focus/follow_focus/both
    min_quality_score: Optional[float] = None  # Minimum quality threshold
    
    # Scoring weights (defaults to spec weights if not provided)
    weights: Optional[Dict[str, float]] = None


class RecommendationEngine:
    """
    Multimodal recommendation system using Elasticsearch-stored embeddings.
    
    Computes weighted similarity across 5 modalities:
    - Text semantic: 35%
    - Audio: 35%
    - Lead pose: 10%
    - Follow pose: 10%
    - Interaction: 10%
    """
    
    def __init__(self, elasticsearch_service: Optional[ElasticsearchService] = None):
        """
        Initialize the recommendation engine.
        
        Args:
            elasticsearch_service: Optional pre-configured Elasticsearch service.
                                  If None, will create from environment config.
        """
        # Initialize Elasticsearch service
        if elasticsearch_service is None:
            config = EnvironmentConfig()
            self.es_service = ElasticsearchService(config.elasticsearch)
        else:
            self.es_service = elasticsearch_service
        
        # Default modality weights (as per requirements)
        self.default_weights = {
            'text': 0.35,
            'audio': 0.35,
            'lead': 0.10,
            'follow': 0.10,
            'interaction': 0.10
        }
        
        logger.info(
            "RecommendationEngine initialized with Elasticsearch integration. "
            "Weights: text=35%, audio=35%, lead=10%, follow=10%, interaction=10%"
        )
    
    def recommend_moves(self, 
                       request: RecommendationRequest,
                       top_k: int = 10) -> List[RecommendationScore]:
        """
        Recommend top-k moves based on multimodal similarity.
        
        Retrieves all embeddings from Elasticsearch, computes weighted similarity
        across all 5 modalities, and returns top-k ranked results.
        
        Args:
            request: Recommendation request with query embeddings and filters
            top_k: Number of top recommendations to return
            
        Returns:
            List of RecommendationScore objects sorted by overall score (descending)
        """
        logger.info(f"Generating recommendations with top_k={top_k}")
        
        # Build metadata filters
        filters = {}
        if request.difficulty:
            filters['difficulty'] = request.difficulty
        if request.energy_level:
            filters['energy_level'] = request.energy_level
        if request.move_label:
            filters['move_label'] = request.move_label
        if request.lead_follow_roles:
            filters['lead_follow_roles'] = request.lead_follow_roles
        
        # Retrieve all embeddings from Elasticsearch
        logger.info(f"Retrieving embeddings from Elasticsearch with filters: {filters}")
        candidate_embeddings = self.es_service.get_all_embeddings(filters=filters if filters else None)
        
        if not candidate_embeddings:
            logger.warning("No candidate embeddings found in Elasticsearch")
            return []
        
        logger.info(f"Retrieved {len(candidate_embeddings)} candidate embeddings")
        
        # Filter by quality score if specified
        if request.min_quality_score is not None:
            candidate_embeddings = [
                emb for emb in candidate_embeddings
                if emb.get('quality_score', 0.0) >= request.min_quality_score
            ]
            logger.info(f"After quality filtering: {len(candidate_embeddings)} candidates")
        
        # Convert to MoveCandidate objects
        move_candidates = [self._embedding_to_candidate(emb) for emb in candidate_embeddings]
        
        # Use provided weights or defaults
        weights = request.weights or self.default_weights
        
        # Score all candidates
        scores = []
        for candidate in move_candidates:
            score = self._compute_multimodal_similarity(
                request,
                candidate,
                weights
            )
            scores.append(score)
        
        # Sort by overall score (descending)
        scores.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Return top-k
        top_scores = scores[:top_k]
        
        if top_scores:
            logger.info(
                f"Top 3 recommendations: " +
                ", ".join([f"{s.move_candidate.move_label}={s.overall_score:.3f}" for s in top_scores[:3]])
            )
        
        return top_scores
    
    def _embedding_to_candidate(self, embedding_doc: Dict[str, Any]) -> MoveCandidate:
        """
        Convert Elasticsearch embedding document to MoveCandidate.
        
        Args:
            embedding_doc: Document from Elasticsearch with embeddings and metadata
            
        Returns:
            MoveCandidate object
        """
        return MoveCandidate(
            clip_id=embedding_doc['clip_id'],
            video_path=embedding_doc.get('video_path', ''),
            move_label=embedding_doc.get('move_label', ''),
            audio_embedding=embedding_doc['audio_embedding'],
            lead_embedding=embedding_doc['lead_embedding'],
            follow_embedding=embedding_doc['follow_embedding'],
            interaction_embedding=embedding_doc['interaction_embedding'],
            text_embedding=embedding_doc['text_embedding'],
            energy_level=embedding_doc.get('energy_level', 'medium'),
            difficulty=embedding_doc.get('difficulty', 'intermediate'),
            estimated_tempo=embedding_doc.get('estimated_tempo', 120.0),
            lead_follow_roles=embedding_doc.get('lead_follow_roles', 'both'),
            quality_score=embedding_doc.get('quality_score', 0.0),
            detection_rate=embedding_doc.get('detection_rate', 0.0)
        )
    
    def _compute_multimodal_similarity(self,
                                      request: RecommendationRequest,
                                      candidate: MoveCandidate,
                                      weights: Dict[str, float]) -> RecommendationScore:
        """
        Compute weighted multimodal similarity between query and candidate.
        
        Args:
            request: Recommendation request with query embeddings
            candidate: Move candidate with embeddings
            weights: Modality weights
            
        Returns:
            RecommendationScore with detailed breakdown
        """
        # Compute individual cosine similarities for each modality
        text_sim = self._cosine_similarity(
            request.query_text_embedding,
            candidate.text_embedding
        ) if request.query_text_embedding is not None else 0.0
        
        audio_sim = self._cosine_similarity(
            request.query_audio_embedding,
            candidate.audio_embedding
        ) if request.query_audio_embedding is not None else 0.0
        
        lead_sim = self._cosine_similarity(
            request.query_lead_embedding,
            candidate.lead_embedding
        ) if request.query_lead_embedding is not None else 0.0
        
        follow_sim = self._cosine_similarity(
            request.query_follow_embedding,
            candidate.follow_embedding
        ) if request.query_follow_embedding is not None else 0.0
        
        interaction_sim = self._cosine_similarity(
            request.query_interaction_embedding,
            candidate.interaction_embedding
        ) if request.query_interaction_embedding is not None else 0.0
        
        # Calculate weighted overall score
        overall_score = (
            weights['text'] * text_sim +
            weights['audio'] * audio_sim +
            weights['lead'] * lead_sim +
            weights['follow'] * follow_sim +
            weights['interaction'] * interaction_sim
        )
        
        # Check metadata matches
        difficulty_match = (request.difficulty == candidate.difficulty) if request.difficulty else False
        energy_match = (request.energy_level == candidate.energy_level) if request.energy_level else False
        
        # Calculate tempo difference (if available)
        tempo_difference = 0.0
        if request.query_audio_embedding is not None and candidate.estimated_tempo:
            # This is a placeholder - actual tempo would come from music analysis
            tempo_difference = 0.0
        
        return RecommendationScore(
            move_candidate=candidate,
            overall_score=overall_score,
            text_similarity=text_sim,
            audio_similarity=audio_sim,
            lead_similarity=lead_sim,
            follow_similarity=follow_sim,
            interaction_similarity=interaction_sim,
            difficulty_match=difficulty_match,
            energy_match=energy_match,
            tempo_difference=tempo_difference,
            weights=weights
        )
    
    def _cosine_similarity(self, vec1: Optional[np.ndarray], vec2: Optional[np.ndarray]) -> float:
        """
        Compute cosine similarity between two vectors.
        
        Args:
            vec1: First vector (query)
            vec2: Second vector (candidate)
            
        Returns:
            Cosine similarity in range [0, 1] (normalized from [-1, 1])
        """
        if vec1 is None or vec2 is None:
            return 0.0
        
        # Ensure vectors are numpy arrays
        vec1 = np.asarray(vec1, dtype=np.float32)
        vec2 = np.asarray(vec2, dtype=np.float32)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 > 0 and norm2 > 0:
            similarity = dot_product / (norm1 * norm2)
            # Normalize to 0-1 range (cosine similarity is -1 to 1)
            return float((similarity + 1.0) / 2.0)
        
        return 0.0
    
    def get_all_candidates(self, filters: Optional[Dict[str, Any]] = None) -> List[MoveCandidate]:
        """
        Retrieve all move candidates from Elasticsearch.
        
        Args:
            filters: Optional metadata filters
            
        Returns:
            List of MoveCandidate objects
        """
        embeddings = self.es_service.get_all_embeddings(filters=filters)
        return [self._embedding_to_candidate(emb) for emb in embeddings]
    
    def get_candidate_by_id(self, clip_id: str) -> Optional[MoveCandidate]:
        """
        Retrieve a specific move candidate by clip_id.
        
        Args:
            clip_id: Unique clip identifier
            
        Returns:
            MoveCandidate or None if not found
        """
        embedding = self.es_service.get_embedding_by_id(clip_id)
        if embedding:
            return self._embedding_to_candidate(embedding)
        return None
    
    def get_scoring_explanation(self, score: RecommendationScore) -> Dict[str, str]:
        """
        Get human-readable explanation of scoring components.
        
        Args:
            score: RecommendationScore to explain
            
        Returns:
            Dictionary with component explanations
        """
        explanations = {}
        
        # Text similarity explanation
        if score.text_similarity > 0.8:
            explanations['text'] = "Excellent semantic match"
        elif score.text_similarity > 0.6:
            explanations['text'] = "Good semantic compatibility"
        elif score.text_similarity > 0.4:
            explanations['text'] = "Moderate semantic fit"
        else:
            explanations['text'] = "Limited semantic compatibility"
        
        # Audio similarity explanation
        if score.audio_similarity > 0.8:
            explanations['audio'] = "Excellent musical match"
        elif score.audio_similarity > 0.6:
            explanations['audio'] = "Good musical compatibility"
        elif score.audio_similarity > 0.4:
            explanations['audio'] = "Moderate musical fit"
        else:
            explanations['audio'] = "Limited musical compatibility"
        
        # Lead pose similarity
        if score.lead_similarity > 0.7:
            explanations['lead'] = "Strong lead movement match"
        elif score.lead_similarity > 0.5:
            explanations['lead'] = "Good lead movement fit"
        else:
            explanations['lead'] = "Different lead movement style"
        
        # Follow pose similarity
        if score.follow_similarity > 0.7:
            explanations['follow'] = "Strong follow movement match"
        elif score.follow_similarity > 0.5:
            explanations['follow'] = "Good follow movement fit"
        else:
            explanations['follow'] = "Different follow movement style"
        
        # Interaction similarity
        if score.interaction_similarity > 0.7:
            explanations['interaction'] = "Excellent partner dynamics match"
        elif score.interaction_similarity > 0.5:
            explanations['interaction'] = "Good partner dynamics fit"
        else:
            explanations['interaction'] = "Different partner dynamics"
        
        # Metadata matches
        if score.difficulty_match:
            explanations['difficulty'] = "Perfect difficulty match"
        else:
            explanations['difficulty'] = f"Different difficulty ({score.move_candidate.difficulty})"
        
        if score.energy_match:
            explanations['energy'] = "Perfect energy level match"
        else:
            explanations['energy'] = f"Different energy ({score.move_candidate.energy_level})"
        
        return explanations
    
    def get_detailed_breakdown(self, score: RecommendationScore) -> Dict[str, Any]:
        """
        Get detailed numerical breakdown of all scoring components.
        
        Args:
            score: RecommendationScore to analyze
            
        Returns:
            Dictionary with detailed scores and metadata
        """
        return {
            'overall_score': score.overall_score,
            'modality_scores': {
                'text': score.text_similarity,
                'audio': score.audio_similarity,
                'lead': score.lead_similarity,
                'follow': score.follow_similarity,
                'interaction': score.interaction_similarity
            },
            'weighted_contributions': {
                'text': score.text_similarity * score.weights['text'],
                'audio': score.audio_similarity * score.weights['audio'],
                'lead': score.lead_similarity * score.weights['lead'],
                'follow': score.follow_similarity * score.weights['follow'],
                'interaction': score.interaction_similarity * score.weights['interaction']
            },
            'metadata': {
                'clip_id': score.move_candidate.clip_id,
                'move_label': score.move_candidate.move_label,
                'difficulty': score.move_candidate.difficulty,
                'energy_level': score.move_candidate.energy_level,
                'estimated_tempo': score.move_candidate.estimated_tempo,
                'quality_score': score.move_candidate.quality_score,
                'detection_rate': score.move_candidate.detection_rate
            },
            'matches': {
                'difficulty_match': score.difficulty_match,
                'energy_match': score.energy_match
            },
            'weights': score.weights
        }
    
    def get_moves_by_semantic_group(self, move_label_pattern: str) -> List[MoveCandidate]:
        """
        Get all moves matching a semantic pattern (e.g., all "cross_body_lead" variations).
        
        This enables semantic grouping where similar move types cluster together
        based on text embeddings.
        
        Args:
            move_label_pattern: Pattern to match (e.g., "cross_body_lead", "arm_styling")
            
        Returns:
            List of matching MoveCandidate objects
        """
        filters = {'move_label': move_label_pattern}
        return self.get_all_candidates(filters=filters)
    
    def get_moves_by_difficulty(self, difficulty: str) -> List[MoveCandidate]:
        """
        Get all moves of a specific difficulty level.
        
        Enables difficulty-aware recommendations for smooth progression
        (beginner → intermediate → advanced).
        
        Args:
            difficulty: Difficulty level ('beginner', 'intermediate', 'advanced')
            
        Returns:
            List of MoveCandidate objects at the specified difficulty
        """
        filters = {'difficulty': difficulty}
        return self.get_all_candidates(filters=filters)
    
    def get_moves_by_role_focus(self, role_focus: str) -> List[MoveCandidate]:
        """
        Get moves filtered by role-specific focus.
        
        Enables role-specific matching (lead_focus vs follow_focus vs both).
        
        Args:
            role_focus: Role focus ('lead_focus', 'follow_focus', 'both')
            
        Returns:
            List of MoveCandidate objects with the specified role focus
        """
        filters = {'lead_follow_roles': role_focus}
        return self.get_all_candidates(filters=filters)
    
    def get_moves_by_energy_level(self, energy_level: str) -> List[MoveCandidate]:
        """
        Get all moves of a specific energy level.
        
        Args:
            energy_level: Energy level ('low', 'medium', 'high')
            
        Returns:
            List of MoveCandidate objects at the specified energy level
        """
        filters = {'energy_level': energy_level}
        return self.get_all_candidates(filters=filters)
    
    def recommend_with_filters(self,
                              request: RecommendationRequest,
                              difficulty: Optional[str] = None,
                              energy_level: Optional[str] = None,
                              role_focus: Optional[str] = None,
                              move_label: Optional[str] = None,
                              top_k: int = 10) -> List[RecommendationScore]:
        """
        Convenience method for recommendations with common filters.
        
        Args:
            request: Base recommendation request with query embeddings
            difficulty: Optional difficulty filter
            energy_level: Optional energy level filter
            role_focus: Optional role focus filter
            move_label: Optional move label filter
            top_k: Number of recommendations to return
            
        Returns:
            List of RecommendationScore objects sorted by overall score
        """
        # Update request with filters
        request.difficulty = difficulty or request.difficulty
        request.energy_level = energy_level or request.energy_level
        request.lead_follow_roles = role_focus or request.lead_follow_roles
        request.move_label = move_label or request.move_label
        
        return self.recommend_moves(request, top_k=top_k)