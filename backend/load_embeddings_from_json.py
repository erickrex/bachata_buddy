#!/usr/bin/env python
"""
Load embeddings from move_embeddings.json into the database.

Simple script that reads the JSON file and inserts into MoveEmbedding model.
"""
import os
import sys
import json
import django
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env.local'
if env_path.exists():
    load_dotenv(env_path)

# Override DB_HOST when running outside Docker
if not Path('/app').exists():
    os.environ['DB_HOST'] = 'localhost'

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from apps.choreography.models import MoveEmbedding


def load_embeddings():
    """Load embeddings from JSON file into database."""
    
    # Find JSON file
    possible_paths = [
        Path(__file__).parent.parent / 'data' / 'move_embeddings.json',
        Path('/app/data/move_embeddings.json'),
        Path('/data/move_embeddings.json'),
    ]
    
    json_path = None
    for path in possible_paths:
        if path.exists():
            json_path = path
            break
    
    if not json_path:
        print("❌ move_embeddings.json not found")
        print("   Generate it first with: uv run python generate_embeddings_to_json.py")
        return
    
    print(f"📂 Loading embeddings from: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    embeddings = data.get('embeddings', [])
    print(f"📊 Found {len(embeddings)} embeddings in file")
    print(f"   Generated at: {data.get('generated_at')}")
    print()
    
    # Clear existing embeddings
    existing_count = MoveEmbedding.objects.count()
    if existing_count > 0:
        print(f"🗑️  Deleting {existing_count} existing embeddings...")
        MoveEmbedding.objects.all().delete()
        print()
    
    # Load new embeddings
    loaded = 0
    skipped = 0
    
    for i, emb_data in enumerate(embeddings, 1):
        try:
            # Validate required fields
            required_fields = ['clip_id', 'move_name', 'video_path', 'pose_embedding', 
                             'audio_embedding', 'text_embedding', 'difficulty', 
                             'energy_level', 'style', 'duration']
            
            missing = [f for f in required_fields if f not in emb_data]
            if missing:
                print(f"⚠️  [{i}/{len(embeddings)}] Skipping {emb_data.get('clip_id', 'unknown')}: missing {missing}")
                skipped += 1
                continue
            
            # Validate embedding dimensions
            if len(emb_data['pose_embedding']) != 512:
                print(f"⚠️  [{i}/{len(embeddings)}] Skipping {emb_data['clip_id']}: pose embedding has {len(emb_data['pose_embedding'])} dims (expected 512)")
                skipped += 1
                continue
            
            if len(emb_data['audio_embedding']) != 128:
                print(f"⚠️  [{i}/{len(embeddings)}] Skipping {emb_data['clip_id']}: audio embedding has {len(emb_data['audio_embedding'])} dims (expected 128)")
                skipped += 1
                continue
            
            if len(emb_data['text_embedding']) != 384:
                print(f"⚠️  [{i}/{len(embeddings)}] Skipping {emb_data['clip_id']}: text embedding has {len(emb_data['text_embedding'])} dims (expected 384)")
                skipped += 1
                continue
            
            # Create embedding
            MoveEmbedding.objects.create(
                move_id=emb_data['clip_id'],
                move_name=emb_data['move_name'],
                video_path=emb_data['video_path'],
                pose_embedding=emb_data['pose_embedding'],
                audio_embedding=emb_data['audio_embedding'],
                text_embedding=emb_data['text_embedding'],
                difficulty=emb_data['difficulty'],
                energy_level=emb_data['energy_level'],
                style=emb_data['style'],
                duration=emb_data['duration']
            )
            
            loaded += 1
            if loaded % 20 == 0:
                print(f"✅ Loaded {loaded}/{len(embeddings)} embeddings...")
            
        except Exception as e:
            print(f"❌ [{i}/{len(embeddings)}] Error loading {emb_data.get('clip_id', 'unknown')}: {e}")
            skipped += 1
            continue
    
    print(f"\n{'='*80}")
    print(f"✅ Successfully loaded {loaded} embeddings")
    print(f"⚠️  Skipped {skipped} embeddings")
    print(f"{'='*80}")
    
    # Show summary
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
        print("\n" + "="*80)
        print("LOADING EMBEDDINGS FROM JSON INTO DATABASE")
        print("="*80 + "\n")
        
        load_embeddings()
        
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
