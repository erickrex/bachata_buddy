"""
Video processing models module.

This module contains models related to video processing and storage.
"""

from .video_models import (
    TransitionType,
    SelectedMove,
    ChoreographySequence,
    VideoGenerationConfig,
    VideoGenerationResult,
)

from .annotation_schema import (
    AnnotationCollection,
    MoveAnnotation,
    DifficultyLevel,
    EnergyLevel,
    MoveCategory,
)

__all__ = [
    'TransitionType',
    'SelectedMove',
    'ChoreographySequence',
    'VideoGenerationConfig',
    'VideoGenerationResult',
    'AnnotationCollection',
    'MoveAnnotation',
    'DifficultyLevel',
    'EnergyLevel',
    'MoveCategory',
]
