"""
Blueprint Generator Service

This service orchestrates the full blueprint generation flow:
1. Analyze audio features using MusicAnalyzer
2. Search for matching moves using VectorSearchService
3. Generate choreography sequence using rule-based approach
4. Create blueprint JSON matching the schema

This is the core intelligence that was previously in the job container,
now moved to the API/backend for the blueprint-based architecture.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BlueprintConfig:
    """Configuration for blueprint generation."""
    task_id: str
    song_path: str
    difficulty: str
    energy_level: str
    style: str
    user_id: Optional[int] = None
    tempo_preference: Optional[str] = None  # slow, medium, fast
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class BlueprintGenerator:
    """
    Generates video assembly blueprints from choreography requests.
    
    This service orchestrates the full flow:
    1. Audio analysis (tempo, beats, energy)
    2. Vector search for matching moves
    3. AI choreography sequencing
    4. Blueprint JSON creation
    """
    
    def __init__(
        self,
        vector_search_service,
        music_analyzer
    ):
        """
        Initialize blueprint generator.
        
        Args:
            vector_search_service: VectorSearchService instance
            music_analyzer: MusicAnalyzer instance
        """
        self.vector_search = vector_search_service
        self.music_analyzer = music_analyzer
        
        logger.info("BlueprintGenerator initialized")
    
    def generate_blueprint(
        self,
        task_id: str,
        song_path: str,
        difficulty: str,
        energy_level: str,
        style: str,
        user_id: Optional[int] = None,
        tempo_preference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete blueprint for video assembly.
        
        This is the main entry point that orchestrates the full flow.
        
        Args:
            task_id: Unique task identifier
            song_path: Path to audio file (local or GCS)
            difficulty: beginner, intermediate, or advanced
            energy_level: low, medium, or high
            style: romantic, energetic, sensual, or playful
            user_id: Optional user ID
            tempo_preference: Optional tempo preference
        
        Returns:
            Blueprint dictionary matching the schema
        
        Raises:
            BlueprintGenerationError: If generation fails
        """
        try:
            logger.info(f"Starting blueprint generation for task {task_id}")
            logger.info(f"Parameters: difficulty={difficulty}, energy={energy_level}, style={style}")
            
            # Step 1: Analyze audio features
            logger.info("Step 1: Analyzing audio features...")
            music_features = self._analyze_audio(song_path)
            
            # Step 2: Search for matching moves
            logger.info("Step 2: Searching for matching moves...")
            matching_moves = self._search_matching_moves(
                music_features,
                difficulty,
                energy_level,
                style
            )
            
            # Step 3: Generate choreography sequence
            logger.info("Step 3: Generating choreography sequence...")
            choreography_sequence = self._generate_choreography_sequence(
                music_features,
                matching_moves,
                difficulty,
                energy_level,
                style
            )
            
            # Step 4: Create blueprint JSON
            logger.info("Step 4: Creating blueprint JSON...")
            blueprint = self._create_blueprint_json(
                task_id,
                song_path,
                music_features,
                choreography_sequence,
                difficulty,
                energy_level,
                style,
                user_id
            )
            
            logger.info(f"Blueprint generation complete: {len(choreography_sequence)} moves")
            return blueprint
            
        except Exception as e:
            logger.error(f"Blueprint generation failed: {e}", exc_info=True)
            raise BlueprintGenerationError(f"Failed to generate blueprint: {e}") from e
    
    def _analyze_audio(self, song_path: str) -> Any:
        """
        Analyze audio features using MusicAnalyzer.
        
        Args:
            song_path: Path to audio file
        
        Returns:
            MusicFeatures object
        """
        try:
            # Convert relative path to absolute path
            if not os.path.isabs(song_path):
                # Prepend data directory
                data_dir = os.environ.get('DATA_DIR', '/app/data')
                song_path = os.path.join(data_dir, song_path)
            
            logger.info(f"Loading audio from: {song_path}")
            
            if not os.path.exists(song_path):
                raise FileNotFoundError(f"Audio file not found: {song_path}")
            
            music_features = self.music_analyzer.analyze_audio(song_path)
            
            logger.info(
                f"Audio analysis complete: "
                f"tempo={music_features.tempo:.1f} BPM, "
                f"duration={music_features.duration:.1f}s, "
                f"{len(music_features.sections)} sections"
            )
            
            return music_features
            
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            raise BlueprintGenerationError(f"Audio analysis failed: {e}") from e
    
    def _search_matching_moves(
        self,
        music_features: Any,
        difficulty: str,
        energy_level: str,
        style: str
    ) -> List[Dict[str, Any]]:
        """
        Search for matching moves using vector search.
        
        Uses a fallback strategy if no exact matches are found:
        1. Try exact match (difficulty + energy + style)
        2. Try relaxing energy level
        3. Try relaxing style
        4. Try difficulty only
        5. Try no filters (best semantic matches)
        
        Args:
            music_features: MusicFeatures from audio analysis
            difficulty: Difficulty level
            energy_level: Energy level
            style: Style preference
        
        Returns:
            List of matching moves with metadata
        """
        try:
            # Create weighted query embedding matching stored embeddings
            # Music queries use audio (35%) + zero vectors for pose (35%) and text (30%)
            # This ensures dimensional consistency with stored move embeddings
            from services.vector_search_service import VectorSearchService
            
            query_embedding = VectorSearchService.combine_embeddings_weighted(
                pose_embedding=None,  # Music doesn't have pose info
                audio_embedding=np.array(music_features.audio_embedding, dtype=np.float32),
                text_embedding=None   # No text info from music analysis
            )
            
            logger.info(
                f"Created weighted query embedding: dim={len(query_embedding)}, "
                f"audio_weight={VectorSearchService.AUDIO_WEIGHT}"
            )
            
            top_k = int(os.getenv('VECTOR_SEARCH_TOP_K', '20'))
            
            # Strategy 1: Try exact match (all filters)
            filters = {
                'difficulty': difficulty,
                'energy_level': energy_level,
                'style': style
            }
            
            results = self.vector_search.search_similar_moves(
                query_embedding,
                filters=filters,
                top_k=top_k
            )
            
            if len(results) > 0:
                matching_moves = [result.to_dict() for result in results]
                logger.info(f"Found {len(matching_moves)} moves with exact filters")
                return matching_moves
            
            # Strategy 2: Relax energy level (keep difficulty + style)
            logger.warning(f"No exact matches found. Relaxing energy_level filter...")
            filters = {
                'difficulty': difficulty,
                'style': style
            }
            
            results = self.vector_search.search_similar_moves(
                query_embedding,
                filters=filters,
                top_k=top_k
            )
            
            if len(results) > 0:
                matching_moves = [result.to_dict() for result in results]
                logger.info(f"Found {len(matching_moves)} moves without energy_level filter")
                return matching_moves
            
            # Strategy 3: Relax style (keep difficulty only)
            logger.warning(f"Still no matches. Relaxing style filter...")
            filters = {
                'difficulty': difficulty
            }
            
            results = self.vector_search.search_similar_moves(
                query_embedding,
                filters=filters,
                top_k=top_k
            )
            
            if len(results) > 0:
                matching_moves = [result.to_dict() for result in results]
                logger.info(f"Found {len(matching_moves)} moves with difficulty filter only")
                return matching_moves
            
            # Strategy 4: No filters - use best semantic matches
            logger.warning(f"Still no matches. Using semantic similarity only (no filters)...")
            results = self.vector_search.search_similar_moves(
                query_embedding,
                filters=None,
                top_k=top_k
            )
            
            matching_moves = [result.to_dict() for result in results]
            
            if len(matching_moves) == 0:
                raise BlueprintGenerationError(
                    "No moves found in database. Please ensure move embeddings are generated."
                )
            
            logger.info(f"Found {len(matching_moves)} moves using semantic similarity")
            return matching_moves
            
        except Exception as e:
            logger.error(f"Move search failed: {e}")
            raise BlueprintGenerationError(f"Move search failed: {e}") from e
    
    def _generate_choreography_sequence(
        self,
        music_features: Any,
        matching_moves: List[Dict[str, Any]],
        difficulty: str,
        energy_level: str,
        style: str
    ) -> List[Dict[str, Any]]:
        """
        Generate choreography sequence using rule-based approach.
        
        Args:
            music_features: MusicFeatures from audio analysis
            matching_moves: List of matching moves
            difficulty: Difficulty level
            energy_level: Energy level
            style: Style preference
        
        Returns:
            List of selected moves with timing
        """
        return self._generate_rule_based_sequence(
            music_features,
            matching_moves
        )
    
    def _generate_rule_based_sequence(
        self,
        music_features: Any,
        matching_moves: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate choreography sequence using rule-based approach.
        
        This is a fallback when AI is not available.
        Loops through available moves to fill the ENTIRE song duration.
        
        Args:
            music_features: MusicFeatures from audio analysis
            matching_moves: List of matching moves
        
        Returns:
            List of selected moves with timing
        """
        sequence = []
        current_time = 0.0
        move_index = 0
        
        if not matching_moves:
            logger.error("No matching moves available for rule-based sequence")
            return sequence
        
        # Iterate through musical sections
        for section in music_features.sections:
            section_duration = section.end_time - section.start_time
            section_time = 0.0
            
            logger.info(f"Filling section {section.section_type}: {section_duration:.1f}s")
            
            # Fill section with moves - LOOP through moves if needed
            while section_time < section_duration:
                # Use modulo to loop through moves indefinitely
                move = matching_moves[move_index % len(matching_moves)]
                
                # Use move duration or default to 8 seconds
                move_duration = min(move.get('duration', 8.0), section_duration - section_time)
                
                sequence.append({
                    'move_id': move['move_id'],
                    'move_name': move['move_name'],
                    'video_path': move['video_path'],
                    'start_time': current_time,
                    'duration': move_duration,
                    'similarity_score': move['similarity_score']
                })
                
                current_time += move_duration
                section_time += move_duration
                move_index += 1
        
        logger.info(f"Rule-based sequence generated with {len(sequence)} moves covering {current_time:.1f}s")
        
        return sequence
    
    def _create_blueprint_json(
        self,
        task_id: str,
        song_path: str,
        music_features: Any,
        choreography_sequence: List[Dict[str, Any]],
        difficulty: str,
        energy_level: str,
        style: str,
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """
        Create blueprint JSON matching the schema.
        
        Args:
            task_id: Task identifier
            song_path: Path to audio file
            music_features: MusicFeatures from analysis
            choreography_sequence: List of selected moves
            difficulty: Difficulty level
            energy_level: Energy level
            style: Style preference
            user_id: Optional user ID
        
        Returns:
            Blueprint dictionary
        """
        # Build moves array
        moves = []
        for i, move in enumerate(choreography_sequence):
            moves.append({
                'clip_id': f"move_{i+1}",
                'video_path': move['video_path'],
                'start_time': move['start_time'],
                'duration': move['duration'],
                'transition_type': 'crossfade' if i > 0 else 'cut',
                'original_duration': move['duration'],
                'trim_start': 0.0,
                'trim_end': 0.0,
                'volume_adjustment': 1.0
            })
        
        # Calculate total duration
        total_duration = max(
            [m['start_time'] + m['duration'] for m in moves],
            default=music_features.duration
        )
        
        # Create blueprint
        blueprint = {
            'task_id': task_id,
            'audio_path': song_path,
            'audio_tempo': music_features.tempo,
            'moves': moves,
            'total_duration': total_duration,
            'difficulty_level': difficulty,
            'generation_timestamp': datetime.utcnow().isoformat() + 'Z',
            'generation_parameters': {
                'energy_level': energy_level,
                'style': style,
                'user_id': user_id
            },
            'output_config': {
                'output_path': f"output/user_{user_id}/choreography_{task_id}.mp4",
                'output_format': 'mp4',
                'video_codec': 'libx264',
                'audio_codec': 'aac',
                'video_bitrate': '2M',
                'audio_bitrate': '128k',
                'frame_rate': 30,
                'transition_duration': 0.5,
                'fade_duration': 0.3,
                'add_audio_overlay': True,
                'normalize_audio': True
            }
        }
        
        return blueprint
    
    def validate_blueprint(self, blueprint: Dict[str, Any]) -> bool:
        """
        Validate blueprint schema and required fields.
        
        Args:
            blueprint: Blueprint dictionary
        
        Returns:
            True if valid
        
        Raises:
            ValueError: If validation fails
        """
        required_fields = [
            'task_id',
            'audio_path',
            'moves',
            'total_duration',
            'difficulty_level',
            'generation_timestamp',
            'output_config'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in blueprint:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate moves array
        if not isinstance(blueprint['moves'], list):
            raise ValueError("'moves' must be a list")
        
        if len(blueprint['moves']) == 0:
            raise ValueError("'moves' array cannot be empty")
        
        # Validate each move
        required_move_fields = [
            'clip_id',
            'video_path',
            'start_time',
            'duration'
        ]
        
        for i, move in enumerate(blueprint['moves']):
            for field in required_move_fields:
                if field not in move:
                    raise ValueError(f"Move {i} missing required field: {field}")
        
        # Validate output config
        if not isinstance(blueprint['output_config'], dict):
            raise ValueError("'output_config' must be a dictionary")
        
        logger.info("Blueprint validation passed")
        return True


class BlueprintGenerationError(Exception):
    """Raised when blueprint generation fails."""
    pass
