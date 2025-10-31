"""
Text Embedding Service for Bachata Move Annotations.

This service generates 384-dimensional text embeddings from move annotations
using sentence-transformers. It creates natural language descriptions from
structured annotation data and converts them to semantic embeddings.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class TextEmbeddingService:
    """
    Service for generating text embeddings from move annotations.
    
    Features:
    - Loads annotations from bachata_annotations.json
    - Generates natural language descriptions
    - Creates 384D embeddings using sentence-transformers
    - Caches model instance for reuse across all clips
    - Handles missing/incomplete annotations gracefully
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize text embedding service.
        
        Args:
            model_name: Sentence-transformers model name (default: all-MiniLM-L6-v2)
        """
        logger.info(f"Initializing TextEmbeddingService with model: {model_name}")
        
        # Load and cache the sentence-transformers model
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        
        logger.info(f"Model loaded successfully. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
    
    def load_annotations(self, annotations_path: str) -> Dict[str, Dict]:
        """
        Load annotations from JSON file.
        
        Args:
            annotations_path: Path to bachata_annotations.json
            
        Returns:
            Dictionary mapping clip_id to annotation data
            
        Raises:
            FileNotFoundError: If annotations file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        annotations_file = Path(annotations_path)
        
        if not annotations_file.exists():
            raise FileNotFoundError(f"Annotations file not found: {annotations_path}")
        
        logger.info(f"Loading annotations from: {annotations_path}")
        
        with open(annotations_file, 'r') as f:
            data = json.load(f)
        
        # Convert list of clips to dictionary keyed by clip_id
        annotations_dict = {
            clip['clip_id']: clip
            for clip in data.get('clips', [])
        }
        
        logger.info(f"Loaded {len(annotations_dict)} annotations")
        
        return annotations_dict
    
    def create_text_description(self, annotation: Dict) -> str:
        """
        Create natural language description from annotation fields.
        
        Format: "Dance move: {move_label}. Difficulty: {difficulty}. 
                 Energy: {energy_level}. Role focus: {lead_follow_roles}. 
                 Tempo: {estimated_tempo} BPM. Description: {notes}"
        
        Args:
            annotation: Annotation dictionary with move metadata
            
        Returns:
            Natural language description string
        """
        # Extract fields with fallback values
        move_label = annotation.get('move_label', 'unknown')
        difficulty = annotation.get('difficulty', 'unknown')
        energy_level = annotation.get('energy_level', 'medium')
        lead_follow_roles = annotation.get('lead_follow_roles', 'both')
        estimated_tempo = annotation.get('estimated_tempo', 120)
        notes = annotation.get('notes', '')
        
        # Format move label (replace underscores with spaces and title case)
        formatted_move = move_label.replace('_', ' ').title()
        
        # Format role focus (replace underscores with spaces)
        formatted_roles = lead_follow_roles.replace('_', ' ')
        
        # Build description parts
        parts = [
            f"Dance move: {formatted_move}",
            f"Difficulty: {difficulty}",
            f"Energy: {energy_level}",
            f"Role focus: {formatted_roles}",
            f"Tempo: {estimated_tempo} BPM"
        ]
        
        # Add notes if available
        if notes:
            parts.append(f"Description: {notes}")
        
        description = ". ".join(parts)
        
        return description
    
    def generate_embedding(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Generate 384D text embedding from text description.
        
        Args:
            text: Natural language description
            normalize: Whether to apply L2 normalization (default: True)
            
        Returns:
            384-dimensional embedding as numpy array (float32)
        """
        # Generate embedding
        embedding = self.model.encode(
            text,
            normalize_embeddings=normalize,
            show_progress_bar=False
        )
        
        # Convert to float32 for consistency
        embedding = embedding.astype(np.float32)
        
        return embedding
    
    def generate_embedding_from_annotation(
        self,
        annotation: Dict,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Generate text embedding directly from annotation dictionary.
        
        Args:
            annotation: Annotation dictionary with move metadata
            normalize: Whether to apply L2 normalization (default: True)
            
        Returns:
            384-dimensional embedding as numpy array (float32)
        """
        # Create text description
        text = self.create_text_description(annotation)
        
        # Generate embedding
        embedding = self.generate_embedding(text, normalize=normalize)
        
        return embedding
    
    def generate_embeddings_batch(
        self,
        annotations: List[Dict],
        normalize: bool = True,
        show_progress: bool = True
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple annotations efficiently.
        
        Args:
            annotations: List of annotation dictionaries
            normalize: Whether to apply L2 normalization (default: True)
            show_progress: Whether to show progress bar (default: True)
            
        Returns:
            List of 384-dimensional embeddings
        """
        # Create text descriptions for all annotations
        texts = [self.create_text_description(ann) for ann in annotations]
        
        logger.info(f"Generating embeddings for {len(texts)} annotations")
        
        # Generate embeddings in batch (more efficient)
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=show_progress,
            batch_size=32
        )
        
        # Convert to float32
        embeddings = [emb.astype(np.float32) for emb in embeddings]
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        return embeddings
    
    def generate_all_embeddings(
        self,
        annotations_path: str,
        normalize: bool = True
    ) -> Dict[str, np.ndarray]:
        """
        Generate embeddings for all clips in annotations file.
        
        Args:
            annotations_path: Path to bachata_annotations.json
            normalize: Whether to apply L2 normalization (default: True)
            
        Returns:
            Dictionary mapping clip_id to embedding
        """
        # Load annotations
        annotations_dict = self.load_annotations(annotations_path)
        
        # Get list of annotations in consistent order
        clip_ids = sorted(annotations_dict.keys())
        annotations_list = [annotations_dict[clip_id] for clip_id in clip_ids]
        
        # Generate embeddings in batch
        embeddings_list = self.generate_embeddings_batch(
            annotations_list,
            normalize=normalize,
            show_progress=True
        )
        
        # Create dictionary mapping clip_id to embedding
        embeddings_dict = {
            clip_id: embedding
            for clip_id, embedding in zip(clip_ids, embeddings_list)
        }
        
        return embeddings_dict
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimensionality of embeddings produced by this service.
        
        Returns:
            Embedding dimension (384 for all-MiniLM-L6-v2)
        """
        return self.model.get_sentence_embedding_dimension()
