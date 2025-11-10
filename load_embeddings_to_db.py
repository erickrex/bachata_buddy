#!/usr/bin/env python
"""
Load embeddings from embeddings_backup.json into the database.

This script loads the 38 real move embeddings from the backup file
into the MoveEmbedding model for vector search.
"""
import os
import sys
import json
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
sys.path.insert(0, str(Path(__file__).parent / 'backend'))
django.setup()

from apps.choreography.models import MoveEmbedding


def map_style(move_data):
    """Map move characteristics to style."""
    # Use move_label or other fields to infer style
    move_label = move_data.get('move_label', '').lower()
    
    if any(word in move_label for word in ['romantic', 'slow', 'close']):
        return 'romantic'
    elif any(word in move_label for word in ['energetic', 'fast', 'jump']):
        return 'energetic'
    elif any(word in move_label for word in ['sensual', 'body', 'roll', 'wave']):
        return 'sensual'
    else:
        return 'playful'  # Default


def create_pose_embedding(move_data):
    """Create pose embedding from lead and follow embeddings."""
    lead_emb = move_data.get('lead_embedding', [])
    follow_emb = move_data.get('follow_embedding', [])
    
    # If we have lead/follow embeddings, concatenate them
    if lead_emb and follow_emb:
        # Take first 256 from each to make 512D
        return lead_emb[:256] + follow_emb[:256]
    
    # Otherwise create a zero vector
    return [0.0] * 512


def load_embeddings():
    """Load embeddings from backup file into database."""
    
    # Load backup file
    backup_path = Path(__file__).parent / 'data' / 'embeddings_backup.json'
    
    if not backup_path.exists():
        print(f"❌ Backup file not found: {backup_path}")
        return
    
    print(f"📂 Loading embeddings from: {backup_path}")
    
    with open(backup_path, 'r') as f:
        data = json.load(f)
    
    embeddings = data.get('embeddings', [])
    print(f"📊 Found {len(embeddings)} embeddings in backup file")
    
    # Clear existing embeddings
    existing_count = MoveEmbedding.objects.count()
    if existing_count > 0:
        print(f"🗑️  Deleting {existing_count} existing embeddings...")
        MoveEmbedding.objects.all().delete()
    
    # Load new embeddings
    loaded = 0
    skipped = 0
    
    for i, emb_data in enumerate(embeddings, 1):
        try:
            # Extract fields
            clip_id = emb_data.get('clip_id', f'move_{i}')
            video_path = emb_data.get('video_path', '')
            
            # Skip if no video path
            if not video_path:
                print(f"⚠️  Skipping embedding {i}: no video path")
                skipped += 1
                continue
            
            # Extract move name from video path
            # e.g., "Bachata_steps/arm_styling/arm_styling_1.mp4" -> "Arm Styling"
            path_parts = video_path.split('/')
            if len(path_parts) >= 2:
                move_name = path_parts[-2].replace('_', ' ').title()
            else:
                move_name = emb_data.get('move_label', f'Move {i}')
            
            # Get embeddings
            audio_emb = emb_data.get('audio_embedding', [])
            text_emb = emb_data.get('text_embedding', [])
            pose_emb = create_pose_embedding(emb_data)
            
            # Validate embedding dimensions
            if len(audio_emb) != 128:
                print(f"⚠️  Skipping {move_name}: audio embedding has {len(audio_emb)} dims (expected 128)")
                skipped += 1
                continue
            
            if len(text_emb) != 384:
                print(f"⚠️  Skipping {move_name}: text embedding has {len(text_emb)} dims (expected 384)")
                skipped += 1
                continue
            
            if len(pose_emb) != 512:
                print(f"⚠️  Skipping {move_name}: pose embedding has {len(pose_emb)} dims (expected 512)")
                skipped += 1
                continue
            
            # Get metadata
            difficulty = emb_data.get('difficulty', 'intermediate')
            energy_level = emb_data.get('energy_level', 'medium')
            style = map_style(emb_data)
            
            # Estimate duration from frame count (assuming 30 fps)
            frame_count = emb_data.get('frame_count', 240)
            duration = frame_count / 30.0
            
            # Create embedding
            MoveEmbedding.objects.create(
                move_id=clip_id,
                move_name=move_name,
                video_path=video_path,
                pose_embedding=pose_emb,
                audio_embedding=audio_emb,
                text_embedding=text_emb,
                difficulty=difficulty,
                energy_level=energy_level,
                style=style,
                duration=duration
            )
            
            loaded += 1
            print(f"✅ {i}/{len(embeddings)}: {move_name} ({difficulty}, {energy_level}, {style})")
            
        except Exception as e:
            print(f"❌ Error loading embedding {i}: {e}")
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


if __name__ == '__main__':
    try:
        load_embeddings()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
