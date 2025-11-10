"""
Blueprint Parser and Validator

This module provides JSON schema validation and security checks for blueprints.
Validates required fields, data types, and file paths to prevent security issues.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class BlueprintValidationError(Exception):
    """Raised when blueprint validation fails."""
    
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Blueprint validation failed: {'; '.join(errors)}")


class BlueprintParser:
    """
    Parses and validates blueprint JSON documents.
    
    Validates:
    - Required fields presence
    - Data types
    - File path security (no directory traversal)
    - Value constraints
    """
    
    # Required top-level fields
    REQUIRED_FIELDS = {
        'task_id': str,
        'audio_path': str,
        'moves': list,
        'output_config': dict,
    }
    
    # Required fields in each move
    REQUIRED_MOVE_FIELDS = {
        'clip_id': str,
        'video_path': str,
        'start_time': (int, float),
        'duration': (int, float),
    }
    
    # Required fields in output_config
    REQUIRED_OUTPUT_FIELDS = {
        'output_path': str,
    }
    
    # Valid transition types
    VALID_TRANSITION_TYPES = {'cut', 'crossfade', 'fade_black', 'fade_white'}
    
    # Valid difficulty levels
    VALID_DIFFICULTY_LEVELS = {'beginner', 'intermediate', 'advanced'}
    
    def __init__(self, allow_absolute_paths: bool = False):
        """
        Initialize blueprint parser.
        
        Args:
            allow_absolute_paths: If True, allow absolute paths (for testing).
                                 In production, should be False for security.
        """
        self.allow_absolute_paths = allow_absolute_paths
    
    def parse_and_validate(self, blueprint_json: str) -> Dict:
        """
        Parse and validate a blueprint JSON string.
        
        Args:
            blueprint_json: JSON string containing the blueprint
            
        Returns:
            Parsed and validated blueprint dictionary
            
        Raises:
            BlueprintValidationError: If validation fails
        """
        errors = []
        
        # Parse JSON
        try:
            blueprint = json.loads(blueprint_json)
        except json.JSONDecodeError as e:
            raise BlueprintValidationError([f"Invalid JSON: {str(e)}"])
        
        if not isinstance(blueprint, dict):
            raise BlueprintValidationError(["Blueprint must be a JSON object"])
        
        # Validate required fields
        errors.extend(self._validate_required_fields(blueprint))
        
        # Validate field types
        errors.extend(self._validate_field_types(blueprint))
        
        # Validate file paths for security
        errors.extend(self._validate_file_paths(blueprint))
        
        # Validate moves array
        errors.extend(self._validate_moves(blueprint.get('moves', [])))
        
        # Validate output config
        errors.extend(self._validate_output_config(blueprint.get('output_config', {})))
        
        # Validate optional fields if present
        errors.extend(self._validate_optional_fields(blueprint))
        
        if errors:
            raise BlueprintValidationError(errors)
        
        return blueprint
    
    def _validate_required_fields(self, blueprint: Dict) -> List[str]:
        """Validate that all required top-level fields are present."""
        errors = []
        
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in blueprint:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(blueprint[field], expected_type):
                errors.append(
                    f"Field '{field}' must be of type {expected_type.__name__}, "
                    f"got {type(blueprint[field]).__name__}"
                )
        
        return errors
    
    def _validate_field_types(self, blueprint: Dict) -> List[str]:
        """Validate data types of fields."""
        errors = []
        
        # Validate task_id is non-empty string
        task_id = blueprint.get('task_id')
        if task_id and not task_id.strip():
            errors.append("Field 'task_id' cannot be empty")
        
        # Validate audio_path is non-empty string
        audio_path = blueprint.get('audio_path')
        if audio_path and not audio_path.strip():
            errors.append("Field 'audio_path' cannot be empty")
        
        # Validate moves is a non-empty list
        moves = blueprint.get('moves')
        if isinstance(moves, list) and len(moves) == 0:
            errors.append("Field 'moves' cannot be an empty array")
        
        # Validate optional numeric fields
        if 'audio_tempo' in blueprint:
            tempo = blueprint['audio_tempo']
            if not isinstance(tempo, (int, float)) or tempo <= 0:
                errors.append("Field 'audio_tempo' must be a positive number")
        
        if 'total_duration' in blueprint:
            duration = blueprint['total_duration']
            if not isinstance(duration, (int, float)) or duration <= 0:
                errors.append("Field 'total_duration' must be a positive number")
        
        return errors
    
    def _validate_file_paths(self, blueprint: Dict) -> List[str]:
        """
        Validate file paths for security.
        
        Prevents directory traversal attacks by checking for:
        - Parent directory references (..)
        - Absolute paths (unless explicitly allowed)
        - Null bytes
        """
        errors = []
        
        # Validate audio_path
        audio_path = blueprint.get('audio_path', '')
        path_errors = self._validate_single_path(audio_path, 'audio_path')
        errors.extend(path_errors)
        
        return errors
    
    def _validate_single_path(self, path: str, field_name: str) -> List[str]:
        """
        Validate a single file path for security issues.
        
        Args:
            path: File path to validate
            field_name: Name of the field (for error messages)
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not path:
            return errors
        
        # Check for null bytes
        if '\0' in path:
            errors.append(f"Field '{field_name}' contains null bytes")
            return errors
        
        # Check for directory traversal
        if '..' in path:
            errors.append(
                f"Field '{field_name}' contains parent directory reference (..): {path}"
            )
        
        # Check for absolute paths (unless allowed)
        if not self.allow_absolute_paths and os.path.isabs(path):
            errors.append(
                f"Field '{field_name}' contains absolute path (not allowed): {path}"
            )
        
        # Normalize path and check again
        try:
            normalized = os.path.normpath(path)
            if '..' in normalized.split(os.sep):
                errors.append(
                    f"Field '{field_name}' resolves to parent directory: {path}"
                )
        except (ValueError, TypeError) as e:
            errors.append(f"Field '{field_name}' has invalid path format: {str(e)}")
        
        return errors
    
    def _validate_moves(self, moves: List) -> List[str]:
        """Validate the moves array."""
        errors = []
        
        if not isinstance(moves, list):
            return [f"Field 'moves' must be an array, got {type(moves).__name__}"]
        
        for idx, move in enumerate(moves):
            if not isinstance(move, dict):
                errors.append(f"Move at index {idx} must be an object")
                continue
            
            # Validate required move fields
            for field, expected_type in self.REQUIRED_MOVE_FIELDS.items():
                if field not in move:
                    errors.append(f"Move at index {idx} missing required field: {field}")
                elif not isinstance(move[field], expected_type):
                    type_name = expected_type.__name__ if not isinstance(expected_type, tuple) else ' or '.join(t.__name__ for t in expected_type)
                    errors.append(
                        f"Move at index {idx} field '{field}' must be of type {type_name}, "
                        f"got {type(move[field]).__name__}"
                    )
            
            # Validate video_path security
            video_path = move.get('video_path', '')
            path_errors = self._validate_single_path(
                video_path, 
                f"moves[{idx}].video_path"
            )
            errors.extend(path_errors)
            
            # Validate numeric constraints
            start_time = move.get('start_time')
            if isinstance(start_time, (int, float)) and start_time < 0:
                errors.append(f"Move at index {idx} 'start_time' cannot be negative")
            
            duration = move.get('duration')
            if isinstance(duration, (int, float)) and duration <= 0:
                errors.append(f"Move at index {idx} 'duration' must be positive")
            
            # Validate transition_type if present
            transition = move.get('transition_type')
            if transition and transition not in self.VALID_TRANSITION_TYPES:
                errors.append(
                    f"Move at index {idx} has invalid transition_type: {transition}. "
                    f"Valid types: {', '.join(sorted(self.VALID_TRANSITION_TYPES))}"
                )
            
            # Validate optional numeric fields
            if 'trim_start' in move:
                trim_start = move['trim_start']
                if not isinstance(trim_start, (int, float)) or trim_start < 0:
                    errors.append(
                        f"Move at index {idx} 'trim_start' must be a non-negative number"
                    )
            
            if 'trim_end' in move:
                trim_end = move['trim_end']
                if not isinstance(trim_end, (int, float)) or trim_end < 0:
                    errors.append(
                        f"Move at index {idx} 'trim_end' must be a non-negative number"
                    )
            
            if 'volume_adjustment' in move:
                volume = move['volume_adjustment']
                if not isinstance(volume, (int, float)) or volume < 0 or volume > 1:
                    errors.append(
                        f"Move at index {idx} 'volume_adjustment' must be between 0 and 1"
                    )
        
        return errors
    
    def _validate_output_config(self, output_config: Dict) -> List[str]:
        """Validate the output_config object."""
        errors = []
        
        if not isinstance(output_config, dict):
            return [f"Field 'output_config' must be an object, got {type(output_config).__name__}"]
        
        # Validate required output fields
        for field, expected_type in self.REQUIRED_OUTPUT_FIELDS.items():
            if field not in output_config:
                errors.append(f"output_config missing required field: {field}")
            elif not isinstance(output_config[field], expected_type):
                errors.append(
                    f"output_config field '{field}' must be of type {expected_type.__name__}, "
                    f"got {type(output_config[field]).__name__}"
                )
        
        # Validate output_path security
        output_path = output_config.get('output_path', '')
        path_errors = self._validate_single_path(output_path, 'output_config.output_path')
        errors.extend(path_errors)
        
        # Validate optional numeric fields
        if 'frame_rate' in output_config:
            frame_rate = output_config['frame_rate']
            if not isinstance(frame_rate, (int, float)) or frame_rate <= 0:
                errors.append("output_config 'frame_rate' must be a positive number")
        
        if 'transition_duration' in output_config:
            duration = output_config['transition_duration']
            if not isinstance(duration, (int, float)) or duration < 0:
                errors.append("output_config 'transition_duration' must be non-negative")
        
        if 'fade_duration' in output_config:
            duration = output_config['fade_duration']
            if not isinstance(duration, (int, float)) or duration < 0:
                errors.append("output_config 'fade_duration' must be non-negative")
        
        return errors
    
    def _validate_optional_fields(self, blueprint: Dict) -> List[str]:
        """Validate optional fields if present."""
        errors = []
        
        # Validate difficulty_level if present
        if 'difficulty_level' in blueprint:
            difficulty = blueprint['difficulty_level']
            if difficulty not in self.VALID_DIFFICULTY_LEVELS:
                errors.append(
                    f"Field 'difficulty_level' has invalid value: {difficulty}. "
                    f"Valid values: {', '.join(sorted(self.VALID_DIFFICULTY_LEVELS))}"
                )
        
        # Validate generation_parameters if present
        if 'generation_parameters' in blueprint:
            params = blueprint['generation_parameters']
            if not isinstance(params, dict):
                errors.append(
                    f"Field 'generation_parameters' must be an object, "
                    f"got {type(params).__name__}"
                )
        
        return errors
    
    def get_summary(self, blueprint: Dict) -> Dict:
        """
        Get a summary of the blueprint for logging.
        
        Args:
            blueprint: Validated blueprint dictionary
            
        Returns:
            Dictionary with summary information
        """
        return {
            'task_id': blueprint.get('task_id'),
            'audio_path': blueprint.get('audio_path'),
            'num_moves': len(blueprint.get('moves', [])),
            'total_duration': blueprint.get('total_duration'),
            'difficulty_level': blueprint.get('difficulty_level'),
            'output_path': blueprint.get('output_config', {}).get('output_path'),
        }


def parse_blueprint(blueprint_json: str, allow_absolute_paths: bool = False) -> Dict:
    """
    Convenience function to parse and validate a blueprint.
    
    Args:
        blueprint_json: JSON string containing the blueprint
        allow_absolute_paths: If True, allow absolute paths (for testing)
        
    Returns:
        Parsed and validated blueprint dictionary
        
    Raises:
        BlueprintValidationError: If validation fails
    """
    parser = BlueprintParser(allow_absolute_paths=allow_absolute_paths)
    return parser.parse_and_validate(blueprint_json)
