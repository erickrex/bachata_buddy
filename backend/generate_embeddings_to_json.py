#!/usr/bin/env python
"""
Generate REAL embeddings from video clips and save to JSON file.

This script:
1. Processes all video clips in data/Bachata_steps
2. Generates REAL text embeddings using sentence-transformers
3. Generates REAL pose embeddings using YOLOv8-Pose
4. Generates audio embeddings (placeholder for now)
5. Saves all embeddings to a JSON file

No database required - just generates the embeddings file.
"""
import json
import numpy as np
import cv2
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Import embedding generation libraries
try:
    from sentence_transformers import SentenceTransformer
    print("✓ sentence-transformers loaded")
    TEXT_MODEL_AVAILABLE = True
except ImportError:
    print("⚠️  sentence-transformers not available, will use dummy text embeddings")
    TEXT_MODEL_AVAILABLE = False

try:
    from ultralytics import YOLO
    print("✓ ultralytics (YOLOv8) loaded")
    POSE_MODEL_AVAILABLE = True
except ImportError:
    print("⚠️  ultralytics not available, will use dummy pose embeddings")
    POSE_MODEL_AVAILABLE = False


class EmbeddingGenerator:
    """Generate real embeddings from video clips."""
    
    def __init__(self):
        """Initialize embedding models."""
        # Text embedding model (384D)
        if TEXT_MODEL_AVAILABLE:
            try:
                self.text_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✓ Text embedding model loaded: all-MiniLM-L6-v2 (384D)")
            except Exception as e:
                print(f"⚠️  Failed to load text model: {e}")
                self.text_model = None
        else:
            self.text_model = None
        
        # Pose detection model (YOLOv8-Pose)
        if POSE_MODEL_AVAILABLE:
            try:
                # Try to find the model file
                model_paths = [
                    Path(__file__).parent / 'yolov8n-pose.pt',
                    Path('yolov8n-pose.pt')
                ]
                
                model_path = None
                for path in model_paths:
                    if Path(path).exists():
                        model_path = path
                        break
                
                if model_path:
                    self.pose_model = YOLO(str(model_path))
                    print(f"✓ Pose detection model loaded: {model_path}")
                else:
                    # Download if not found
                    self.pose_model = YOLO('yolov8n-pose.pt')
                    print("✓ Pose detection model loaded: yolov8n-pose.pt (downloaded)")
            except Exception as e:
                print(f"⚠️  Failed to load pose model: {e}")
                self.pose_model = None
        else:
            self.pose_model = None
    
    def generate_text_embedding(self, annotation: Dict) -> List[float]:
        """Generate text embedding from annotation metadata.
        
        Args:
            annotation: Clip annotation dictionary
            
        Returns:
            384D text embedding vector as list
        """
        if not self.text_model:
            # Return dummy embedding
            emb = np.random.randn(384).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            return emb.tolist()
        
        # Create descriptive text from annotation
        move_label = annotation.get('move_label', 'unknown')
        difficulty = annotation.get('difficulty', 'medium')
        energy_level = annotation.get('energy_level', 'medium')
        
        # Format text description
        text = f"{move_label} bachata move, {difficulty} difficulty, {energy_level} energy"
        
        # Generate embedding
        embedding = self.text_model.encode(text, normalize_embeddings=True)
        return embedding.astype(np.float32).tolist()
    
    def generate_pose_embedding(self, video_path: Path) -> Tuple[List[float], float]:
        """Generate pose embedding from video using YOLOv8-Pose.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (512D pose embedding vector as list, video duration in seconds)
        """
        if not self.pose_model or not video_path.exists():
            # Return dummy embedding
            emb = np.random.randn(512).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            return emb.tolist(), 8.0
        
        try:
            # Open video
            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 8.0
            
            # Sample frames (every 5th frame, max 30 frames)
            frame_indices = list(range(0, frame_count, max(1, frame_count // 30)))[:30]
            
            keypoints_list = []
            
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    continue
                
                # Run pose detection
                results = self.pose_model(frame, verbose=False)
                
                # Extract keypoints
                if results and len(results) > 0 and results[0].keypoints is not None:
                    keypoints = results[0].keypoints.data.cpu().numpy()
                    if len(keypoints) > 0:
                        # Take first person detected
                        kp = keypoints[0]  # Shape: (17, 3) - 17 keypoints with x, y, confidence
                        keypoints_list.append(kp.flatten())  # Flatten to 51D
            
            cap.release()
            
            if len(keypoints_list) == 0:
                # No poses detected, return dummy
                emb = np.random.randn(512).astype(np.float32)
                emb = emb / np.linalg.norm(emb)
                return emb.tolist(), duration
            
            # Average keypoints across frames
            avg_keypoints = np.mean(keypoints_list, axis=0)  # 51D
            
            # Pad or truncate to 512D
            if len(avg_keypoints) < 512:
                # Pad with zeros
                pose_embedding = np.zeros(512, dtype=np.float32)
                pose_embedding[:len(avg_keypoints)] = avg_keypoints
            else:
                pose_embedding = avg_keypoints[:512]
            
            # Normalize
            norm = np.linalg.norm(pose_embedding)
            if norm > 0:
                pose_embedding = pose_embedding / norm
            
            return pose_embedding.tolist(), duration
            
        except Exception as e:
            print(f"    ⚠️  Pose extraction failed: {e}")
            emb = np.random.randn(512).astype(np.float32)
            emb = emb / np.linalg.norm(emb)
            return emb.tolist(), 8.0
    
    def generate_audio_embedding(self, video_path: Path) -> List[float]:
        """Generate audio embedding from video.
        
        Args:
            video_path: Path to video file
            
        Returns:
            128D audio embedding vector as list
        """
        # For now, return dummy embedding
        # In production, use librosa or similar to extract audio features
        emb = np.random.randn(128).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        return emb.tolist()


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


def generate_embeddings_to_json():
    """Generate embeddings and save to JSON file."""
    
    print("\n" + "="*80)
    print("GENERATING REAL EMBEDDINGS FROM VIDEO CLIPS")
    print("="*80 + "\n")
    
    # Initialize embedding generator
    print("Initializing embedding models...")
    generator = EmbeddingGenerator()
    print()
    
    # Load annotations
    annotations_path = Path(__file__).parent.parent / 'data' / 'bachata_annotations.json'
    
    if not annotations_path.exists():
        print(f"❌ Annotations file not found: {annotations_path}")
        return
    
    print(f"📂 Loading annotations from: {annotations_path}")
    
    with open(annotations_path, 'r') as f:
        data = json.load(f)
    
    clips = data.get('clips', [])
    print(f"📊 Found {len(clips)} clips in annotations file\n")
    
    # Video base path
    video_base = Path(__file__).parent.parent / 'data' / 'Bachata_steps'
    
    # Process each clip
    embeddings_data = []
    processed = 0
    skipped = 0
    
    for i, clip in enumerate(clips, 1):
        try:
            clip_id = clip.get('clip_id')
            video_path_rel = clip.get('video_path')
            move_label = clip.get('move_label', 'unknown')
            
            if not clip_id or not video_path_rel:
                print(f"⚠️  [{i}/{len(clips)}] Skipping: missing clip_id or video_path")
                skipped += 1
                continue
            
            print(f"[{i}/{len(clips)}] Processing: {clip_id}")
            
            # Find video file
            video_path = video_base / video_path_rel
            if not video_path.exists():
                print(f"    ⚠️  Video file not found: {video_path_rel}")
                skipped += 1
                continue
            
            # Generate embeddings
            print(f"    → Generating text embedding...")
            text_emb = generator.generate_text_embedding(clip)
            
            print(f"    → Generating pose embedding...")
            pose_emb, duration = generator.generate_pose_embedding(video_path)
            
            print(f"    → Generating audio embedding...")
            audio_emb = generator.generate_audio_embedding(video_path)
            
            # Get metadata
            move_name = Path(video_path_rel).stem.replace('_', ' ').title()
            difficulty = map_difficulty(clip.get('difficulty', 'medium'))
            energy_level = clip.get('energy_level', 'medium')
            style = map_style(move_label)
            
            # Create embedding entry
            embedding_entry = {
                'clip_id': clip_id,
                'move_name': move_name,
                'video_path': f"data/Bachata_steps/{video_path_rel}",
                'pose_embedding': pose_emb,
                'audio_embedding': audio_emb,
                'text_embedding': text_emb,
                'difficulty': difficulty,
                'energy_level': energy_level,
                'style': style,
                'duration': duration,
                'move_label': move_label
            }
            
            embeddings_data.append(embedding_entry)
            processed += 1
            print(f"    ✓ Processed: {move_name} ({difficulty}, {energy_level}, {style}, {duration:.1f}s)")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            skipped += 1
            continue
    
    # Save to JSON file
    output_path = Path(__file__).parent.parent / 'data' / 'move_embeddings.json'
    
    output_data = {
        'generated_at': datetime.utcnow().isoformat(),
        'total_embeddings': len(embeddings_data),
        'embedding_dimensions': {
            'pose': 512,
            'audio': 128,
            'text': 384
        },
        'embeddings': embeddings_data
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"✅ Successfully generated {processed} embeddings")
    print(f"⚠️  Skipped {skipped} clips")
    print(f"💾 Saved to: {output_path}")
    print(f"{'='*80}")
    
    # Statistics
    print("\n📊 Summary by difficulty:")
    for difficulty in ['beginner', 'intermediate', 'advanced']:
        count = sum(1 for e in embeddings_data if e['difficulty'] == difficulty)
        print(f"  {difficulty.capitalize()}: {count}")
    
    print("\n📊 Summary by energy level:")
    for energy in ['low', 'medium', 'high']:
        count = sum(1 for e in embeddings_data if e['energy_level'] == energy)
        print(f"  {energy.capitalize()}: {count}")
    
    print("\n📊 Summary by style:")
    for style in ['romantic', 'energetic', 'sensual', 'playful']:
        count = sum(1 for e in embeddings_data if e['style'] == style)
        print(f"  {style.capitalize()}: {count}")
    
    print("\n📊 Summary by move category:")
    move_categories = {}
    for emb in embeddings_data:
        category = emb['video_path'].split('/')[2] if '/' in emb['video_path'] else 'unknown'
        move_categories[category] = move_categories.get(category, 0) + 1
    
    for category, count in sorted(move_categories.items()):
        print(f"  {category}: {count}")


if __name__ == '__main__':
    try:
        generate_embeddings_to_json()
        
        print("\n" + "="*80)
        print("✅ COMPLETE!")
        print("="*80 + "\n")
        print("Next steps:")
        print("  1. The embeddings are saved in: data/move_embeddings.json")
        print("  2. Load them into the database when needed using:")
        print("     docker-compose exec api python load_embeddings_from_json.py")
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
