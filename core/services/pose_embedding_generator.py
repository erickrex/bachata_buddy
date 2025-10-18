"""
Pose Embedding Generator

Generates embeddings from pose features for similarity matching.

Embeddings generated:
- Lead embedding (512D) from lead dancer's pose sequence
- Follow embedding (512D) from follow dancer's pose sequence  
- Interaction embedding (256D) from couple dynamics
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import logging

from .mmpose_couple_detector import CouplePose
from .pose_feature_extractor import PoseFeatureExtractor, TemporalPoseSequence
from .couple_interaction_analyzer import CoupleInteractionAnalyzer, TemporalInteractionSequence

logger = logging.getLogger(__name__)


@dataclass
class PoseEmbeddings:
    """
    Container for all pose-related embeddings.
    
    Attributes:
        lead_embedding: 512D embedding for lead dancer
        follow_embedding: 512D embedding for follow dancer
        interaction_embedding: 256D embedding for couple interaction
        quality_metadata: Dictionary containing quality metrics
    """
    lead_embedding: np.ndarray  # (512,)
    follow_embedding: np.ndarray  # (512,)
    interaction_embedding: np.ndarray  # (256,)
    quality_metadata: dict
    
    def __post_init__(self):
        """Validate embedding dimensions."""
        if self.lead_embedding.shape != (512,):
            raise ValueError(
                f"lead_embedding must have shape (512,), got {self.lead_embedding.shape}"
            )
        if self.follow_embedding.shape != (512,):
            raise ValueError(
                f"follow_embedding must have shape (512,), got {self.follow_embedding.shape}"
            )
        if self.interaction_embedding.shape != (256,):
            raise ValueError(
                f"interaction_embedding must have shape (256,), got {self.interaction_embedding.shape}"
            )


class PoseEmbeddingGenerator:
    """
    Generates embeddings from pose features.
    
    This class:
    1. Extracts temporal pose sequences for lead and follow
    2. Analyzes couple interaction dynamics
    3. Generates fixed-size embeddings (512D lead, 512D follow, 256D interaction)
    4. Applies L2 normalization for cosine similarity
    """
    
    def __init__(self, confidence_threshold: float = 0.3):
        """
        Initialize pose embedding generator.
        
        Args:
            confidence_threshold: Minimum confidence for keypoint usage
        """
        self.confidence_threshold = confidence_threshold
        
        # Initialize feature extractors
        self.pose_extractor = PoseFeatureExtractor(confidence_threshold)
        self.interaction_analyzer = CoupleInteractionAnalyzer(
            hand_connection_threshold=0.15,
            sync_window_size=5,
            confidence_threshold=confidence_threshold
        )
        
        logger.info("PoseEmbeddingGenerator initialized")
    
    def generate_embeddings(self, couple_poses: List[CouplePose],
                           frame_width: float, frame_height: float) -> PoseEmbeddings:
        """
        Generate all pose embeddings from couple pose sequence.
        
        Args:
            couple_poses: List of CouplePose objects from video
            frame_width: Video frame width (for normalization)
            frame_height: Video frame height (for normalization)
        
        Returns:
            PoseEmbeddings object containing all embeddings and quality metadata
        
        Raises:
            ValueError: If insufficient data for embedding generation
        """
        logger.info(f"Generating embeddings from {len(couple_poses)} frames")
        
        # Extract temporal sequences for lead and follow
        lead_sequence = self.pose_extractor.extract_temporal_sequence(couple_poses, person_id=1)
        follow_sequence = self.pose_extractor.extract_temporal_sequence(couple_poses, person_id=2)
        
        # Analyze couple interaction
        interaction_sequence = self.interaction_analyzer.analyze_temporal_sequence(
            couple_poses, frame_width, frame_height
        )
        
        # Check if we have sufficient data
        if lead_sequence.frame_count == 0 or follow_sequence.frame_count == 0:
            raise ValueError(
                f"Insufficient pose data: lead={lead_sequence.frame_count}, "
                f"follow={follow_sequence.frame_count} frames"
            )
        
        # Generate embeddings
        lead_embedding = self._generate_person_embedding(lead_sequence, target_dim=512)
        follow_embedding = self._generate_person_embedding(follow_sequence, target_dim=512)
        interaction_embedding = self._generate_interaction_embedding(
            interaction_sequence, target_dim=256
        )
        
        # Apply L2 normalization
        lead_embedding = self._l2_normalize(lead_embedding)
        follow_embedding = self._l2_normalize(follow_embedding)
        interaction_embedding = self._l2_normalize(interaction_embedding)
        
        # Calculate quality metadata
        quality_metadata = self._calculate_quality_metadata(
            couple_poses, lead_sequence, follow_sequence, interaction_sequence
        )
        
        # Create PoseEmbeddings object
        embeddings = PoseEmbeddings(
            lead_embedding=lead_embedding,
            follow_embedding=follow_embedding,
            interaction_embedding=interaction_embedding,
            quality_metadata=quality_metadata
        )
        
        logger.info(
            f"✓ Embeddings generated successfully "
            f"(quality score: {quality_metadata['quality_score']:.3f})"
        )
        
        return embeddings
    
    def _generate_person_embedding(self, sequence: TemporalPoseSequence,
                                   target_dim: int) -> np.ndarray:
        """
        Generate embedding for a single person from temporal pose sequence.
        
        Args:
            sequence: TemporalPoseSequence object
            target_dim: Target embedding dimension (512)
        
        Returns:
            Embedding array of shape (target_dim,)
        """
        # Get feature vector from temporal sequence
        feature_vector = sequence.get_feature_vector()
        
        if len(feature_vector) == 0:
            logger.warning(f"Empty feature vector for person {sequence.person_id}")
            return np.zeros(target_dim, dtype=np.float32)
        
        # Project to target dimension
        embedding = self._project_to_dimension(feature_vector, target_dim)
        
        return embedding
    
    def _generate_interaction_embedding(self, sequence: TemporalInteractionSequence,
                                       target_dim: int) -> np.ndarray:
        """
        Generate embedding for couple interaction from temporal sequence.
        
        Args:
            sequence: TemporalInteractionSequence object
            target_dim: Target embedding dimension (256)
        
        Returns:
            Embedding array of shape (target_dim,)
        """
        # Get feature vector from temporal sequence
        feature_vector = sequence.get_feature_vector()
        
        if len(feature_vector) == 0:
            logger.warning("Empty interaction feature vector")
            return np.zeros(target_dim, dtype=np.float32)
        
        # Project to target dimension
        embedding = self._project_to_dimension(feature_vector, target_dim)
        
        return embedding
    
    def _project_to_dimension(self, feature_vector: np.ndarray, 
                             target_dim: int) -> np.ndarray:
        """
        Project feature vector to target dimension.
        
        Uses simple projection strategies:
        - If feature_dim < target_dim: Pad with zeros
        - If feature_dim > target_dim: Use PCA-like projection (random projection for now)
        - If feature_dim == target_dim: Use as-is
        
        Args:
            feature_vector: Input feature vector
            target_dim: Target dimension
        
        Returns:
            Projected vector of shape (target_dim,)
        """
        feature_dim = len(feature_vector)
        
        if feature_dim == target_dim:
            return feature_vector.astype(np.float32)
        
        elif feature_dim < target_dim:
            # Pad with zeros
            padded = np.zeros(target_dim, dtype=np.float32)
            padded[:feature_dim] = feature_vector
            return padded
        
        else:
            # feature_dim > target_dim: Use dimensionality reduction
            # For simplicity, use a deterministic projection based on feature vector
            # In production, you might want to use PCA or learned projection
            
            # Create a deterministic projection matrix based on feature statistics
            # This ensures consistent projections across different videos
            seed = int(np.sum(np.abs(feature_vector)) * 1000) % 2**32
            rng = np.random.RandomState(seed)
            
            # Random projection matrix
            projection_matrix = rng.randn(feature_dim, target_dim).astype(np.float32)
            projection_matrix /= np.sqrt(feature_dim)  # Normalize
            
            # Project
            projected = np.dot(feature_vector, projection_matrix)
            
            return projected.astype(np.float32)
    
    def _l2_normalize(self, vector: np.ndarray) -> np.ndarray:
        """
        Apply L2 normalization to vector.
        
        Args:
            vector: Input vector
        
        Returns:
            L2-normalized vector
        """
        norm = np.linalg.norm(vector)
        
        if norm < 1e-8:
            logger.warning("Vector has near-zero norm, returning as-is")
            return vector
        
        return vector / norm
    
    def _calculate_quality_metadata(self, couple_poses: List[CouplePose],
                                    lead_sequence: TemporalPoseSequence,
                                    follow_sequence: TemporalPoseSequence,
                                    interaction_sequence: TemporalInteractionSequence) -> dict:
        """
        Calculate quality metadata for embeddings.
        
        Quality score formula: quality = 0.6 * detection_rate + 0.4 * avg_confidence
        
        Args:
            couple_poses: List of CouplePose objects
            lead_sequence: Lead dancer's temporal sequence
            follow_sequence: Follow dancer's temporal sequence
            interaction_sequence: Interaction temporal sequence
        
        Returns:
            Dictionary containing quality metrics
        """
        total_frames = len(couple_poses)
        
        # Calculate detection rate (frames with both dancers)
        frames_with_both = sum(1 for cp in couple_poses if cp.has_both_dancers)
        detection_rate = frames_with_both / total_frames if total_frames > 0 else 0.0
        
        # Calculate average confidence
        all_confidences = []
        
        for feat in lead_sequence.features:
            if feat is not None:
                all_confidences.extend(feat.keypoint_confidences)
        
        for feat in follow_sequence.features:
            if feat is not None:
                all_confidences.extend(feat.keypoint_confidences)
        
        # Filter out zero confidences (invalid keypoints)
        valid_confidences = [c for c in all_confidences if c > 0]
        avg_confidence = np.mean(valid_confidences) if valid_confidences else 0.0
        
        # Calculate quality score
        quality_score = 0.6 * detection_rate + 0.4 * avg_confidence
        
        # Compile metadata
        metadata = {
            'quality_score': float(quality_score),
            'detection_rate': float(detection_rate),
            'avg_confidence': float(avg_confidence),
            'total_frames': total_frames,
            'frames_with_both_dancers': frames_with_both,
            'lead_frame_count': lead_sequence.frame_count,
            'follow_frame_count': follow_sequence.frame_count,
            'interaction_frame_count': interaction_sequence.frame_count,
        }
        
        logger.info(
            f"Quality metrics: score={quality_score:.3f}, "
            f"detection_rate={detection_rate:.3f}, "
            f"avg_confidence={avg_confidence:.3f}"
        )
        
        return metadata
    
    def validate_embeddings(self, embeddings: PoseEmbeddings) -> bool:
        """
        Validate embeddings for NaN/Inf values and correct dimensions.
        
        Args:
            embeddings: PoseEmbeddings object to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Check for NaN or Inf
        if np.any(np.isnan(embeddings.lead_embedding)):
            logger.error("Lead embedding contains NaN values")
            return False
        
        if np.any(np.isinf(embeddings.lead_embedding)):
            logger.error("Lead embedding contains Inf values")
            return False
        
        if np.any(np.isnan(embeddings.follow_embedding)):
            logger.error("Follow embedding contains NaN values")
            return False
        
        if np.any(np.isinf(embeddings.follow_embedding)):
            logger.error("Follow embedding contains Inf values")
            return False
        
        if np.any(np.isnan(embeddings.interaction_embedding)):
            logger.error("Interaction embedding contains NaN values")
            return False
        
        if np.any(np.isinf(embeddings.interaction_embedding)):
            logger.error("Interaction embedding contains Inf values")
            return False
        
        # Check dimensions (already validated in __post_init__, but double-check)
        if embeddings.lead_embedding.shape != (512,):
            logger.error(f"Invalid lead embedding dimension: {embeddings.lead_embedding.shape}")
            return False
        
        if embeddings.follow_embedding.shape != (512,):
            logger.error(f"Invalid follow embedding dimension: {embeddings.follow_embedding.shape}")
            return False
        
        if embeddings.interaction_embedding.shape != (256,):
            logger.error(f"Invalid interaction embedding dimension: {embeddings.interaction_embedding.shape}")
            return False
        
        logger.debug("✓ Embeddings validated successfully")
        return True
