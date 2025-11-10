#!/usr/bin/env python3
"""
Data Migration Script for Blueprint Architecture

This script migrates existing move data to the new blueprint-based architecture:
1. Scans video files in data/Bachata_steps directory
2. Creates MoveEmbedding records with placeholder embeddings
3. Creates sample blueprints for testing
4. Verifies data integrity

Usage:
    # Dry run (no database changes)
    python scripts/migrate_to_blueprint_architecture.py --dry-run
    
    # Actual migration
    python scripts/migrate_to_blueprint_architecture.py
    
    # With custom video directory
    python scripts/migrate_to_blueprint_architecture.py --video-dir data/Bachata_steps
    
    # Generate sample blueprints only
    python scripts/migrate_to_blueprint_architecture.py --blueprints-only

Requirements: Blueprint architecture migration support
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import django

# Setup Django environment
# Determine if we're running from root or backend directory
current_dir = Path(__file__).parent.parent
backend_dir = current_dir / 'backend'

if backend_dir.exists():
    # Running from root directory
    sys.path.insert(0, str(backend_dir))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
else:
    # Running from backend directory
    sys.path.insert(0, str(current_dir))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

django.setup()

from django.db import transaction
from apps.choreography.models import MoveEmbedding, Blueprint, ChoreographyTask, Song
from django.contrib.auth import get_user_model

User = get_user_model()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('migration.log')
    ]
)

logger = logging.getLogger(__name__)


class MigrationStats:
    """Track migration statistics."""
    
    def __init__(self):
        self.videos_found = 0
        self.embeddings_created = 0
        self.embeddings_skipped = 0
        self.embeddings_failed = 0
        self.blueprints_created = 0
        self.blueprints_failed = 0
        self.errors = []
    
    def log_summary(self):
        """Log migration summary."""
        logger.info("=" * 80)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Videos found: {self.videos_found}")
        logger.info(f"Embeddings created: {self.embeddings_created}")
        logger.info(f"Embeddings skipped (already exist): {self.embeddings_skipped}")
        logger.info(f"Embeddings failed: {self.embeddings_failed}")
        logger.info(f"Sample blueprints created: {self.blueprints_created}")
        logger.info(f"Sample blueprints failed: {self.blueprints_failed}")
        
        if self.errors:
            logger.warning(f"\nErrors encountered: {len(self.errors)}")
            for error in self.errors[:10]:  # Show first 10 errors
                logger.warning(f"  - {error}")
            if len(self.errors) > 10:
                logger.warning(f"  ... and {len(self.errors) - 10} more errors")
        
        logger.info("=" * 80)


class BlueprintArchitectureMigration:
    """Migrate existing move data to blueprint architecture."""
    
    # Difficulty mapping based on move type
    DIFFICULTY_MAP = {
        'basic_steps': 'beginner',
        'forward_backward': 'beginner',
        'arm_styling': 'intermediate',
        'body_roll': 'intermediate',
        'cross_body_lead': 'intermediate',
        'lady_right_turn': 'intermediate',
        'lady_left_turn': 'intermediate',
        'combination': 'intermediate',
        'hammerlock': 'advanced',
        'dip': 'advanced',
        'double_cross_body_lead': 'advanced',
        'shadow_position': 'advanced',
    }
    
    # Energy level mapping
    ENERGY_MAP = {
        'basic_steps': 'low',
        'forward_backward': 'low',
        'arm_styling': 'medium',
        'body_roll': 'medium',
        'cross_body_lead': 'medium',
        'lady_right_turn': 'high',
        'lady_left_turn': 'high',
        'combination': 'high',
        'hammerlock': 'high',
        'dip': 'medium',
        'double_cross_body_lead': 'high',
        'shadow_position': 'medium',
    }
    
    # Style mapping
    STYLE_MAP = {
        'basic_steps': 'romantic',
        'forward_backward': 'romantic',
        'arm_styling': 'sensual',
        'body_roll': 'sensual',
        'cross_body_lead': 'energetic',
        'lady_right_turn': 'energetic',
        'lady_left_turn': 'energetic',
        'combination': 'playful',
        'hammerlock': 'playful',
        'dip': 'romantic',
        'double_cross_body_lead': 'energetic',
        'shadow_position': 'sensual',
    }
    
    def __init__(self, video_dir: str, dry_run: bool = False):
        """
        Initialize migration.
        
        Args:
            video_dir: Directory containing video files
            dry_run: If True, don't make database changes
        """
        self.video_dir = Path(video_dir)
        self.dry_run = dry_run
        self.stats = MigrationStats()
        
        if not self.video_dir.exists():
            raise FileNotFoundError(f"Video directory not found: {self.video_dir}")
        
        logger.info("=" * 80)
        logger.info("BLUEPRINT ARCHITECTURE MIGRATION")
        logger.info("=" * 80)
        logger.info(f"Video directory: {self.video_dir}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("=" * 80)
    
    def find_all_videos(self) -> List[Path]:
        """
        Find all video files in the video directory.
        
        Returns:
            List of video file paths
        """
        video_extensions = {'.mp4', '.avi', '.mov', '.MP4', '.AVI', '.MOV'}
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(self.video_dir.rglob(f'*{ext}'))
        
        # Filter out .DS_Store and other system files
        video_files = [f for f in video_files if not f.name.startswith('.')]
        
        # Sort for consistent ordering
        video_files = sorted(video_files)
        
        self.stats.videos_found = len(video_files)
        logger.info(f"Found {len(video_files)} video files")
        
        return video_files
    
    def extract_metadata_from_path(self, video_path: Path) -> Dict:
        """
        Extract metadata from video file path.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with metadata
        """
        # Get move type from parent directory
        move_type = video_path.parent.name
        
        # Get move name from filename
        move_name = video_path.stem
        
        # Map to difficulty, energy, style
        difficulty = self.DIFFICULTY_MAP.get(move_type, 'intermediate')
        energy_level = self.ENERGY_MAP.get(move_type, 'medium')
        style = self.STYLE_MAP.get(move_type, 'romantic')
        
        # Estimate duration (default 8 seconds for bachata moves)
        duration = 8.0
        
        return {
            'move_type': move_type,
            'move_name': move_name,
            'difficulty': difficulty,
            'energy_level': energy_level,
            'style': style,
            'duration': duration,
        }
    
    def generate_placeholder_embeddings(self) -> Tuple[List[float], List[float], List[float]]:
        """
        Generate placeholder embeddings for testing.
        
        In production, these would be generated by the embedding pipeline.
        For migration, we use random normalized vectors.
        
        Returns:
            Tuple of (pose_embedding, audio_embedding, text_embedding)
        """
        import numpy as np
        
        # Generate random embeddings
        pose_emb = np.random.randn(512).astype(np.float32)
        audio_emb = np.random.randn(128).astype(np.float32)
        text_emb = np.random.randn(384).astype(np.float32)
        
        # Normalize to unit length (for cosine similarity)
        pose_emb = pose_emb / np.linalg.norm(pose_emb)
        audio_emb = audio_emb / np.linalg.norm(audio_emb)
        text_emb = text_emb / np.linalg.norm(text_emb)
        
        return pose_emb.tolist(), audio_emb.tolist(), text_emb.tolist()
    
    def create_move_embedding(self, video_path: Path) -> Optional[MoveEmbedding]:
        """
        Create MoveEmbedding record for a video file.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Created MoveEmbedding instance, or None if failed
        """
        try:
            # Extract metadata
            metadata = self.extract_metadata_from_path(video_path)
            
            # Create move_id
            move_id = f"{metadata['move_type']}_{metadata['move_name']}"
            
            # Check if already exists (skip in dry-run mode)
            if not self.dry_run and MoveEmbedding.objects.filter(move_id=move_id).exists():
                logger.debug(f"Skipping {move_id} (already exists)")
                self.stats.embeddings_skipped += 1
                return None
            
            # Get relative path from project root
            try:
                relative_path = video_path.relative_to(Path.cwd())
            except ValueError:
                # If not relative to cwd, use relative to video_dir parent
                relative_path = video_path.relative_to(self.video_dir.parent)
            
            video_path_str = str(relative_path)
            
            # Generate placeholder embeddings
            pose_emb, audio_emb, text_emb = self.generate_placeholder_embeddings()
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would create MoveEmbedding: {move_id}")
                self.stats.embeddings_created += 1
                return None
            
            # Create MoveEmbedding
            move_embedding = MoveEmbedding.objects.create(
                move_id=move_id,
                move_name=metadata['move_name'],
                video_path=video_path_str,
                pose_embedding=pose_emb,
                audio_embedding=audio_emb,
                text_embedding=text_emb,
                difficulty=metadata['difficulty'],
                energy_level=metadata['energy_level'],
                style=metadata['style'],
                duration=metadata['duration'],
            )
            
            logger.info(f"Created MoveEmbedding: {move_id} ({metadata['difficulty']}, {metadata['energy_level']}, {metadata['style']})")
            self.stats.embeddings_created += 1
            
            return move_embedding
            
        except Exception as e:
            error_msg = f"Failed to create MoveEmbedding for {video_path.name}: {e}"
            logger.error(error_msg)
            self.stats.errors.append(error_msg)
            self.stats.embeddings_failed += 1
            return None
    
    def migrate_move_embeddings(self):
        """Migrate all video files to MoveEmbedding records."""
        logger.info("\n" + "=" * 80)
        logger.info("MIGRATING MOVE EMBEDDINGS")
        logger.info("=" * 80)
        
        video_files = self.find_all_videos()
        
        if not video_files:
            logger.warning("No video files found to migrate")
            return
        
        if self.dry_run:
            # In dry run, don't use transaction or access database
            for video_path in video_files:
                self.create_move_embedding(video_path)
        else:
            with transaction.atomic():
                for video_path in video_files:
                    self.create_move_embedding(video_path)
        
        logger.info(f"\nMigration complete: {self.stats.embeddings_created} embeddings created")
    
    def create_sample_blueprint(
        self,
        task_id: str,
        song_path: str,
        num_moves: int = 5,
        difficulty: str = 'intermediate'
    ) -> Optional[Dict]:
        """
        Create a sample blueprint for testing.
        
        Args:
            task_id: Task ID for the blueprint
            song_path: Path to song audio file
            num_moves: Number of moves to include
            difficulty: Difficulty level filter
            
        Returns:
            Blueprint JSON dictionary, or None if failed
        """
        try:
            # Get random moves matching difficulty
            moves = list(MoveEmbedding.objects.filter(difficulty=difficulty)[:num_moves])
            
            if len(moves) < num_moves:
                logger.warning(f"Only found {len(moves)} moves for difficulty {difficulty}")
                if not moves:
                    return None
            
            # Build blueprint
            blueprint_moves = []
            current_time = 0.0
            
            for i, move in enumerate(moves):
                blueprint_moves.append({
                    'clip_id': f'move_{i+1}',
                    'video_path': move.video_path,
                    'start_time': current_time,
                    'duration': move.duration,
                    'transition_type': 'crossfade' if i > 0 else 'cut',
                    'original_duration': move.duration,
                    'trim_start': 0.0,
                    'trim_end': 0.0,
                    'volume_adjustment': 1.0,
                })
                current_time += move.duration
            
            total_duration = current_time
            
            blueprint = {
                'task_id': task_id,
                'audio_path': song_path,
                'audio_tempo': 129.2,
                'moves': blueprint_moves,
                'total_duration': total_duration,
                'difficulty_level': difficulty,
                'generation_timestamp': datetime.utcnow().isoformat() + 'Z',
                'generation_parameters': {
                    'energy_level': moves[0].energy_level if moves else 'medium',
                    'style': moves[0].style if moves else 'romantic',
                    'user_id': 1,
                },
                'output_config': {
                    'output_path': f'data/output/choreography_{task_id}.mp4',
                    'output_format': 'mp4',
                    'video_codec': 'libx264',
                    'audio_codec': 'aac',
                    'video_bitrate': '2M',
                    'audio_bitrate': '128k',
                    'frame_rate': 30,
                    'transition_duration': 0.5,
                    'fade_duration': 0.3,
                    'add_audio_overlay': True,
                    'normalize_audio': True,
                }
            }
            
            return blueprint
            
        except Exception as e:
            error_msg = f"Failed to create sample blueprint {task_id}: {e}"
            logger.error(error_msg)
            self.stats.errors.append(error_msg)
            return None
    
    def create_sample_blueprints(self, num_samples: int = 3):
        """
        Create sample blueprints for testing.
        
        Args:
            num_samples: Number of sample blueprints to create
        """
        logger.info("\n" + "=" * 80)
        logger.info("CREATING SAMPLE BLUEPRINTS")
        logger.info("=" * 80)
        
        if self.dry_run:
            logger.info("[DRY RUN] Would create 3 sample blueprints")
            logger.info("  - sample_task_1 (beginner)")
            logger.info("  - sample_task_2 (intermediate)")
            logger.info("  - sample_task_3 (advanced)")
            self.stats.blueprints_created = 3
            return
        
        # Check if we have any move embeddings
        try:
            move_count = MoveEmbedding.objects.count()
            if move_count == 0:
                logger.warning("No MoveEmbedding records found. Run migration first.")
                return
            
            logger.info(f"Found {move_count} move embeddings")
        except Exception as e:
            logger.error(f"Failed to check move embeddings: {e}")
            return
        
        # Get or create a test user
        try:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.first()
            if not user:
                logger.warning("No users found. Creating test user...")
                if not self.dry_run:
                    user = User.objects.create_user(
                        username='test_user',
                        email='test@example.com',
                        password='testpass123'
                    )
                else:
                    logger.info("[DRY RUN] Would create test user")
                    return
        except Exception as e:
            logger.error(f"Failed to get/create user: {e}")
            return
        
        # Get or create a test song
        try:
            song = Song.objects.first()
            if not song:
                logger.warning("No songs found. Creating test song...")
                if not self.dry_run:
                    song = Song.objects.create(
                        title='Test Song',
                        artist='Test Artist',
                        duration=180.0,
                        bpm=129,
                        genre='bachata',
                        audio_path='data/songs/test_song.mp3'
                    )
                else:
                    logger.info("[DRY RUN] Would create test song")
                    return
            
            song_path = song.audio_path
        except Exception as e:
            logger.error(f"Failed to get/create song: {e}")
            song_path = 'data/songs/test_song.mp3'
        
        # Create sample blueprints for different difficulties
        difficulties = ['beginner', 'intermediate', 'advanced']
        
        for i in range(num_samples):
            difficulty = difficulties[i % len(difficulties)]
            task_id = f'sample_task_{i+1}'
            
            try:
                # Create blueprint JSON
                blueprint_json = self.create_sample_blueprint(
                    task_id=task_id,
                    song_path=song_path,
                    num_moves=5,
                    difficulty=difficulty
                )
                
                if not blueprint_json:
                    logger.warning(f"Failed to create blueprint for {task_id}")
                    self.stats.blueprints_failed += 1
                    continue
                
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would create Blueprint for task {task_id}")
                    logger.info(f"  Difficulty: {difficulty}")
                    logger.info(f"  Moves: {len(blueprint_json['moves'])}")
                    logger.info(f"  Duration: {blueprint_json['total_duration']}s")
                    self.stats.blueprints_created += 1
                    continue
                
                # Create ChoreographyTask
                task = ChoreographyTask.objects.create(
                    task_id=task_id,
                    user=user,
                    status='completed',
                    progress=100,
                    stage='completed',
                    message='Sample blueprint for testing',
                    song=song if Song.objects.filter(pk=song.pk).exists() else None,
                )
                
                # Create Blueprint
                Blueprint.objects.create(
                    task=task,
                    blueprint_json=blueprint_json
                )
                
                logger.info(f"Created sample blueprint: {task_id}")
                logger.info(f"  Difficulty: {difficulty}")
                logger.info(f"  Moves: {len(blueprint_json['moves'])}")
                logger.info(f"  Duration: {blueprint_json['total_duration']}s")
                
                self.stats.blueprints_created += 1
                
            except Exception as e:
                error_msg = f"Failed to create sample blueprint {task_id}: {e}"
                logger.error(error_msg)
                self.stats.errors.append(error_msg)
                self.stats.blueprints_failed += 1
        
        logger.info(f"\nCreated {self.stats.blueprints_created} sample blueprints")
    
    def verify_data_integrity(self):
        """Verify data integrity after migration."""
        logger.info("\n" + "=" * 80)
        logger.info("VERIFYING DATA INTEGRITY")
        logger.info("=" * 80)
        
        try:
            # Check MoveEmbedding records
            move_count = MoveEmbedding.objects.count()
            logger.info(f"MoveEmbedding records: {move_count}")
        except Exception as e:
            logger.error(f"Failed to verify data integrity: {e}")
            return
        
        if move_count == 0:
            logger.warning("No MoveEmbedding records found")
            return
        
        # Check for required fields
        moves_with_embeddings = MoveEmbedding.objects.exclude(
            pose_embedding__isnull=True
        ).exclude(
            audio_embedding__isnull=True
        ).exclude(
            text_embedding__isnull=True
        ).count()
        
        logger.info(f"  With all embeddings: {moves_with_embeddings}/{move_count}")
        
        # Check difficulty distribution
        for difficulty in ['beginner', 'intermediate', 'advanced']:
            count = MoveEmbedding.objects.filter(difficulty=difficulty).count()
            logger.info(f"  {difficulty.capitalize()}: {count}")
        
        # Check energy level distribution
        for energy in ['low', 'medium', 'high']:
            count = MoveEmbedding.objects.filter(energy_level=energy).count()
            logger.info(f"  Energy {energy}: {count}")
        
        # Check style distribution
        for style in ['romantic', 'energetic', 'sensual', 'playful']:
            count = MoveEmbedding.objects.filter(style=style).count()
            logger.info(f"  Style {style}: {count}")
        
        # Check Blueprint records
        blueprint_count = Blueprint.objects.count()
        logger.info(f"\nBlueprint records: {blueprint_count}")
        
        if blueprint_count > 0:
            # Validate blueprint JSON structure
            valid_blueprints = 0
            for blueprint in Blueprint.objects.all():
                try:
                    bp_json = blueprint.blueprint_json
                    required_fields = ['task_id', 'audio_path', 'moves', 'total_duration', 'output_config']
                    if all(field in bp_json for field in required_fields):
                        valid_blueprints += 1
                except Exception as e:
                    logger.warning(f"Invalid blueprint for task {blueprint.task_id}: {e}")
            
            logger.info(f"  Valid blueprints: {valid_blueprints}/{blueprint_count}")
        
        logger.info("\nData integrity check complete")
    
    def run(self, blueprints_only: bool = False):
        """
        Run the complete migration.
        
        Args:
            blueprints_only: If True, only create sample blueprints
        """
        try:
            if not blueprints_only:
                # Migrate move embeddings
                self.migrate_move_embeddings()
            
            # Create sample blueprints
            self.create_sample_blueprints(num_samples=3)
            
            # Verify data integrity
            if not self.dry_run:
                self.verify_data_integrity()
            
            # Log summary
            self.stats.log_summary()
            
            if self.dry_run:
                logger.info("\n" + "=" * 80)
                logger.info("DRY RUN COMPLETE - No database changes made")
                logger.info("Run without --dry-run to apply changes")
                logger.info("=" * 80)
            else:
                logger.info("\n" + "=" * 80)
                logger.info("MIGRATION COMPLETE")
                logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            raise


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description='Migrate existing move data to blueprint architecture'
    )
    
    parser.add_argument(
        '--video-dir',
        type=str,
        default='data/Bachata_steps',
        help='Directory containing video files (default: data/Bachata_steps)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform dry run without making database changes'
    )
    
    parser.add_argument(
        '--blueprints-only',
        action='store_true',
        help='Only create sample blueprints (skip move embedding migration)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run migration
    try:
        migration = BlueprintArchitectureMigration(
            video_dir=args.video_dir,
            dry_run=args.dry_run
        )
        
        migration.run(blueprints_only=args.blueprints_only)
        
    except KeyboardInterrupt:
        logger.warning("\nMigration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
