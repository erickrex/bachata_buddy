#!/usr/bin/env python
"""Create test move embeddings"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from apps.choreography.models import MoveEmbedding

# Create test move embeddings
moves = [
    {
        'move_id': 'move_001',
        'move_name': 'Basic Step',
        'video_path': 'data/Bachata_steps/basic_steps/basic_1.mp4',
        'pose_embedding': [0.1] * 512,
        'audio_embedding': [0.2] * 128,
        'text_embedding': [0.3] * 384,
        'difficulty': 'beginner',
        'energy_level': 'medium',
        'style': 'romantic',
        'duration': 8.0
    },
    {
        'move_id': 'move_002',
        'move_name': 'Body Roll',
        'video_path': 'data/Bachata_steps/body_roll/body_roll_1.mp4',
        'pose_embedding': [0.5] * 512,
        'audio_embedding': [0.6] * 128,
        'text_embedding': [0.7] * 384,
        'difficulty': 'intermediate',
        'energy_level': 'medium',
        'style': 'sensual',
        'duration': 8.0
    },
    {
        'move_id': 'move_003',
        'move_name': 'Turn',
        'video_path': 'data/Bachata_steps/lady_right_turn/turn_1.mp4',
        'pose_embedding': [0.9] * 512,
        'audio_embedding': [0.8] * 128,
        'text_embedding': [0.7] * 384,
        'difficulty': 'intermediate',
        'energy_level': 'medium',
        'style': 'modern',
        'duration': 8.0
    }
]

for move_data in moves:
    obj, created = MoveEmbedding.objects.get_or_create(
        move_id=move_data['move_id'],
        defaults=move_data
    )
    if created:
        print(f"Created: {obj.move_name}")
    else:
        print(f"Already exists: {obj.move_name}")

print(f"\nTotal move embeddings: {MoveEmbedding.objects.count()}")
