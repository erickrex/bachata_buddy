#!/usr/bin/env python
"""
Generate and load embeddings from annotations into the database.

This script creates embeddings for all video clips in bachata_annotations.json
and loads them directly into the MoveEmbedding model.
"""
import os
import sys
import json
import django
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env.local
env_path = Path(__file__).parent / '.env.local'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded environment from: {env_path}")
else:
    print(f"⚠️  No .env.local found, using system environment")

# Override DB_HOST to use localhost when running outside Docker (not in /app)
if not Path('/app').exists():
    os.environ['DB_HOST'] = 'localhost'
    print(f"✓ Using DB_HOST=localhost (running outside Docker)")
else:
    print(f"✓ Using DB_HOST={os.environ.get('DB_HOST', 'db')} (running inside Docker)")

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from apps.choreography.models import MoveEmbedding


def map_difficulty(annotation_difficulty):
    """Map annotation difficulty to model choices."""
    difficulty_map = {
        'low': 'beginner',
        'medium': 'intermediate',
        'high': 'advanced',
    }
    return difficulty_map.get(annotation_difficulty, 'intermediate')


def map_style(move_label):
    """Map move_label to style."""
    move_label_lower = move_label.lower()
    
    if any(word in move_label_lower for word in ['basic', 'intro', 'outro']):
        return 'romantic'
    elif any(word in move_label_lower for word in ['spin', 'footwork', 'golpes']):
        return 'energetic'
    elif any(word in move_label_lower for word in ['sensual', 'bodywave', 'hiproll', 'headroll', 'shadow']):
        return 'sensual'
    else:
        return 'playful'


def generate_dummy_embeddings():
    """Generate dummy embeddings for testing.
    
    In production, these would be generated from actual video/audio analysis.
    For now, we create random normalized vectors.
    """
    # Generate random embeddings
    pose_emb = np.random.randn(512).astype(np.float32)
    audio_emb = np.random.randn(128).astype(np.float32)
    text_emb = np.random.randn(384).astype(np.float32)
    
    # Normalize
    pose_emb = pose_emb / np.linalg.norm(pose_emb)
    audio_emb = audio_emb / np.linalg.norm(audio_emb)
    text_emb = text_emb / np.linalg.norm(text_emb)
    
    return pose_emb.tolist(), audio_emb.tolist(), text_emb.tolist()


def load_embeddings_from_annotations():
    """Load embeddings from annotations file into database."""
    
    # Load annotations file - try multiple possible paths
    possible_paths = [
        Path(__file__).parent.parent / 'data' / 'bachata_annotations.json',  # Local development
        Path('/app/data/bachata_annotations.json'),  # Docker
        Path('/data/bachata_annotations.json'),  # Alternative Docker path
    ]
    
    annotations_path = None
    for path in possible_paths:
        if path.exists():
            annotations_path = path
            break
    
    if not annotations_path:
        print(f"❌ Annotations file not found in any of these locations:")
        for path in possible_paths:
            print(f"   - {path}")
        return
    
    print(f"📂 Loading annotations from: {annotations_path}")
    
    with open(annotations_path, 'r') as f:
        data = json.load(f)
    
    clips = data.get('clips', [])
    print(f"📊 Found {len(clips)} clips in annotations file")
    
    # Clear existing embeddings
    existing_count = MoveEmbedding.objects.count()
    if existing_count > 0:
        print(f"🗑️  Deleting {existing_count} existing embeddings...")
        MoveEmbedding.objects.all().delete()
    
    # Load new embeddings
    loaded = 0
    skipped = 0
    
    for i, clip in enumerate(clips, 1):
        try:
            # Extract fields
            clip_id = clip.get('clip_id')
            video_path = clip.get('video_path')
            move_label = clip.get('move_label', 'unknown')
            
            if not clip_id or not video_path:
                print(f"⚠️  Skipping clip {i}: missing clip_id or video_path")
                skipped += 1
                continue
            
            # Generate move name from video path
            # e.g., "arm_styling/paseala.mp4" -> "Paseala"
            move_name = Path(video_path).stem.replace('_', ' ').title()
            
            # Generate embeddings (dummy for now)
            pose_emb, audio_emb, text_emb = generate_dummy_embeddings()
            
            # Get metadata
            difficulty = map_difficulty(clip.get('difficulty', 'medium'))
            energy_level = clip.get('energy_level', 'medium')
            style = map_style(move_label)
            
            # Estimate duration (assume 8 seconds per clip as default)
            duration = 8.0
            
            # Create full video path
            full_video_path = f"data/Bachata_steps/{video_path}"
            
            # Create embedding
            MoveEmbedding.objects.create(
                move_id=clip_id,
                move_name=move_name,
                video_path=full_video_path,
                pose_embedding=pose_emb,
                audio_embedding=audio_emb,
                text_embedding=text_emb,
                difficulty=difficulty,
                energy_level=energy_level,
                style=style,
                duration=duration
            )
            
            loaded += 1
            if loaded % 20 == 0:
                print(f"✅ Loaded {loaded}/{len(clips)} embeddings...")
            
        except Exception as e:
            print(f"❌ Error loading clip {i} ({clip.get('clip_id', 'unknown')}): {e}")
            skipped += 1
            continue
    
    print(f"\n{'='*80}")
    print(f"✅ Successfully loaded {loaded} embeddings")
    print(f"⚠️  Skipped {skipped} embeddings")
    print(f"{'='*80}")
    
    # Show summary by difficulty
    print("\n📊 Summary by difficulty:")
    for difficulty in ['beginner', 'intermediate', 'advanced']:
        count = MoveEmbedding.objects.filter(difficulty=difficulty).count()
        print(f"  {difficulty.capitalize()}: {count}")
    
    print("\n📊 Summary by energy level:")
    for energy in ['low', 'medium', 'high']:
        count = MoveEmbedding.objects.filter(energy_level=energy).count()
        print(f"  {energy.capitalize()}: {count}")
    
    print("\n📊 Summary by style:")
    for style in ['romantic', 'energetic', 'sensual', 'playful']:
        count = MoveEmbedding.objects.filter(style=style).count()
        print(f"  {style.capitalize()}: {count}")
    
    print("\n📊 Summary by move category:")
    move_categories = {}
    for emb in MoveEmbedding.objects.all():
        # Extract category from video path
        category = emb.video_path.split('/')[2] if '/' in emb.video_path else 'unknown'
        move_categories[category] = move_categories.get(category, 0) + 1
    
    for category, count in sorted(move_categories.items()):
        print(f"  {category}: {count}")


if __name__ == '__main__':
    try:
        print("\n" + "="*80)
        print("GENERATING AND LOADING EMBEDDINGS FROM ANNOTATIONS")
        print("="*80 + "\n")
        print("⚠️  NOTE: This script generates DUMMY embeddings for testing.")
        print("    In production, embeddings should be generated from actual video/audio analysis.")
        print()
        
        load_embeddings_from_annotations()
        
        print("\n" + "="*80)
        print("✅ COMPLETE!")
        print("="*80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
