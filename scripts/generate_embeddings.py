"""
Offline Embedding Generation Pipeline

This script processes all 38 Bachata video clips and generates multimodal embeddings:
- Pose embeddings (lead 512D, follow 512D, interaction 256D) using MMPose
- Audio embeddings (128D) using Librosa
- Text embeddings (384D) using sentence-transformers

All embeddings are indexed in Elasticsearch for fast retrieval during online serving.

Usage:
    python scripts/generate_embeddings.py --video_dir data/Bachata_steps --annotations data/bachata_annotations.json --environment local

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.environment_config import EnvironmentConfig
from core.services.mmpose_couple_detector import MMPoseCoupleDetector
from core.services.pose_embedding_generator import PoseEmbeddingGenerator
from core.services.music_analyzer import MusicAnalyzer
from core.services.text_embedding_service import TextEmbeddingService
from core.services.elasticsearch_service import ElasticsearchService
from core.services.embedding_validator import EmbeddingValidator
from core.services.quality_metrics import QualityReportGenerator, QualityMetrics


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('embedding_generation.log')
    ]
)

logger = logging.getLogger(__name__)


class EmbeddingGenerationPipeline:
    """
    Offline embedding generation pipeline for all Bachata video clips.
    
    This pipeline:
    1. Processes all videos recursively from specified directory
    2. Generates pose embeddings using MMPose
    3. Generates audio embeddings using Librosa
    4. Generates text embeddings from annotations
    5. Indexes all embeddings in Elasticsearch
    6. Generates processing report with quality metrics
    """
    
    def __init__(
        self,
        video_dir: str,
        annotations_path: str,
        environment: str = "local",
        checkpoint_path: Optional[str] = None
    ):
        """
        Initialize embedding generation pipeline.
        
        Args:
            video_dir: Directory containing video files
            annotations_path: Path to bachata_annotations.json
            environment: Environment name ("local" or "cloud")
            checkpoint_path: Optional path to MMPose checkpoints (overrides config)
        """
        self.video_dir = Path(video_dir)
        self.annotations_path = Path(annotations_path)
        self.environment = environment
        
        # Verify paths exist
        if not self.video_dir.exists():
            raise FileNotFoundError(f"Video directory not found: {self.video_dir}")
        if not self.annotations_path.exists():
            raise FileNotFoundError(f"Annotations file not found: {self.annotations_path}")
        
        logger.info("=" * 80)
        logger.info("EMBEDDING GENERATION PIPELINE")
        logger.info("=" * 80)
        logger.info(f"Video directory: {self.video_dir}")
        logger.info(f"Annotations: {self.annotations_path}")
        logger.info(f"Environment: {self.environment}")
        logger.info("=" * 80)
        
        # Load environment configuration
        logger.info("Loading environment configuration...")
        self.config = EnvironmentConfig()
        
        # Override checkpoint path if provided
        if checkpoint_path:
            self.config.mmpose.model_checkpoint_path = checkpoint_path
            logger.info(f"Using custom checkpoint path: {checkpoint_path}")
        
        # Initialize services
        logger.info("Initializing services...")
        self._initialize_services()
        
        # Load annotations
        logger.info("Loading annotations...")
        self.annotations = self._load_annotations()
        logger.info(f"Loaded {len(self.annotations)} annotations")
        
        # Processing statistics
        self.stats = {
            'total_videos': 0,
            'successful': 0,
            'failed': 0,
            'total_time': 0.0,
            'failed_videos': [],
            'quality_scores': []
        }
    
    def _initialize_services(self):
        """Initialize all required services."""
        # MMPose couple detector
        logger.info("Initializing MMPose couple detector...")
        self.pose_detector = MMPoseCoupleDetector(
            checkpoint_path=self.config.mmpose.model_checkpoint_path,
            confidence_threshold=self.config.mmpose.confidence_threshold,
            enable_hand_detection=self.config.mmpose.enable_hand_detection
        )
        
        # Pose embedding generator
        logger.info("Initializing pose embedding generator...")
        self.pose_embedding_generator = PoseEmbeddingGenerator(
            confidence_threshold=self.config.mmpose.confidence_threshold
        )
        
        # Music analyzer
        logger.info("Initializing music analyzer...")
        self.music_analyzer = MusicAnalyzer()
        
        # Text embedding service
        logger.info("Initializing text embedding service...")
        self.text_embedding_service = TextEmbeddingService()
        
        # Elasticsearch service
        logger.info("Initializing Elasticsearch service...")
        self.elasticsearch_service = ElasticsearchService(self.config.elasticsearch)
        
        # Embedding validator
        logger.info("Initializing embedding validator...")
        self.embedding_validator = EmbeddingValidator()
        
        # Quality report generator
        logger.info("Initializing quality report generator...")
        self.quality_report_generator = QualityReportGenerator()
        
        # Create index if it doesn't exist
        if not self.elasticsearch_service.index_exists():
            logger.info("Creating Elasticsearch index...")
            self.elasticsearch_service.create_index()
        else:
            logger.info("Elasticsearch index already exists")
        
        logger.info("✓ All services initialized successfully")
    
    def _load_annotations(self) -> Dict[str, Dict]:
        """
        Load annotations from JSON file.
        
        Returns:
            Dictionary mapping clip_id to annotation data
        """
        with open(self.annotations_path, 'r') as f:
            data = json.load(f)
        
        # Convert list to dictionary keyed by clip_id
        annotations_dict = {}
        for clip in data.get('clips', []):
            clip_id = clip.get('clip_id')
            if clip_id:
                annotations_dict[clip_id] = clip
        
        return annotations_dict
    
    def find_all_videos(self) -> List[Path]:
        """
        Find all video files recursively in video directory.
        
        Returns:
            List of video file paths
        """
        video_extensions = {'.mp4', '.avi', '.mov', '.MP4', '.AVI', '.MOV'}
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(self.video_dir.rglob(f'*{ext}'))
        
        # Sort for consistent ordering
        video_files = sorted(video_files)
        
        logger.info(f"Found {len(video_files)} video files")
        return video_files
    
    def extract_clip_id_from_path(self, video_path: Path) -> str:
        """
        Extract clip_id from video file path.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Clip ID (filename without extension)
        """
        return video_path.stem
    
    def process_video(self, video_path: Path) -> Optional[Dict]:
        """
        Process a single video and generate all embeddings.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary containing all embeddings and metadata, or None if processing fails
        """
        clip_id = self.extract_clip_id_from_path(video_path)
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Processing: {video_path.name}")
        logger.info(f"Clip ID: {clip_id}")
        logger.info(f"{'=' * 80}")
        
        start_time = time.time()
        
        try:
            # Get annotation for this clip
            annotation = self.annotations.get(clip_id)
            if not annotation:
                logger.warning(f"No annotation found for clip_id: {clip_id}")
                annotation = {
                    'clip_id': clip_id,
                    'move_label': 'unknown',
                    'difficulty': 'unknown',
                    'energy_level': 'medium',
                    'lead_follow_roles': 'both',
                    'estimated_tempo': 120,
                    'notes': ''
                }
            
            # Get video properties
            cap = cv2.VideoCapture(str(video_path))
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            # 1. Generate pose embeddings
            logger.info("Step 1/3: Detecting couple poses...")
            couple_poses = self.pose_detector.detect_couple_poses(
                video_path=str(video_path),
                target_fps=15
            )
            
            logger.info(f"Detected poses in {len(couple_poses)} frames")
            
            if len(couple_poses) == 0:
                raise ValueError("No poses detected in video")
            
            logger.info("Generating pose embeddings...")
            pose_embeddings = self.pose_embedding_generator.generate_embeddings(
                couple_poses=couple_poses,
                frame_width=frame_width,
                frame_height=frame_height
            )
            
            # Validate pose embeddings
            if not self.pose_embedding_generator.validate_embeddings(pose_embeddings):
                raise ValueError("Invalid pose embeddings generated")
            
            # 2. Generate audio embedding
            logger.info("Step 2/3: Analyzing audio...")
            
            # Find corresponding audio file (same name, different extension)
            audio_path = self._find_audio_file(video_path)
            
            if audio_path and audio_path.exists():
                logger.info(f"Using audio file: {audio_path.name}")
                music_features = self.music_analyzer.analyze_audio(str(audio_path))
                audio_embedding = np.array(music_features.audio_embedding, dtype=np.float32)
            else:
                logger.warning(f"No audio file found for {video_path.name}, extracting from video...")
                # Extract audio from video (fallback)
                music_features = self.music_analyzer.analyze_audio(str(video_path))
                audio_embedding = np.array(music_features.audio_embedding, dtype=np.float32)
            
            logger.info(f"Audio embedding generated: {audio_embedding.shape}")
            
            # 3. Generate text embedding
            logger.info("Step 3/3: Generating text embedding...")
            text_embedding = self.text_embedding_service.generate_embedding_from_annotation(
                annotation=annotation,
                normalize=True
            )
            
            logger.info(f"Text embedding generated: {text_embedding.shape}")
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Compile all embeddings and metadata
            embedding_document = {
                'clip_id': clip_id,
                'video_path': str(video_path.relative_to(self.video_dir.parent)),
                
                # Embeddings
                'audio_embedding': audio_embedding,
                'lead_embedding': pose_embeddings.lead_embedding,
                'follow_embedding': pose_embeddings.follow_embedding,
                'interaction_embedding': pose_embeddings.interaction_embedding,
                'text_embedding': text_embedding,
                
                # Metadata from annotation
                'move_label': annotation.get('move_label'),
                'difficulty': annotation.get('difficulty'),
                'energy_level': annotation.get('energy_level'),
                'lead_follow_roles': annotation.get('lead_follow_roles'),
                'estimated_tempo': annotation.get('estimated_tempo'),
                
                # Quality metadata
                'quality_score': pose_embeddings.quality_metadata['quality_score'],
                'detection_rate': pose_embeddings.quality_metadata['detection_rate'],
                'frame_count': pose_embeddings.quality_metadata['total_frames'],
                'processing_time': processing_time,
                'version': 'mmpose_v1',
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Validate all embeddings
            logger.info("Validating embeddings...")
            is_valid, errors = self.embedding_validator.validate_all_embeddings(
                embedding_document, check_normalized=True
            )
            
            if not is_valid:
                logger.error(f"Embedding validation failed for {clip_id}:")
                for error in errors:
                    logger.error(f"  - {error}")
                raise ValueError(f"Invalid embeddings: {', '.join(errors)}")
            
            logger.info(f"✓ Video processed successfully in {processing_time:.2f}s")
            logger.info(f"  Quality score: {embedding_document['quality_score']:.3f}")
            logger.info(f"  Detection rate: {embedding_document['detection_rate']:.3f}")
            logger.info(f"  All embeddings validated ✓")
            
            # Add quality metrics to report generator
            quality_metrics = QualityMetrics(
                quality_score=embedding_document['quality_score'],
                detection_rate=embedding_document['detection_rate'],
                avg_confidence=pose_embeddings.quality_metadata['avg_confidence'],
                total_frames=pose_embeddings.quality_metadata['total_frames'],
                frames_with_both_dancers=pose_embeddings.quality_metadata['frames_with_both_dancers'],
                lead_frame_count=pose_embeddings.quality_metadata['lead_frame_count'],
                follow_frame_count=pose_embeddings.quality_metadata['follow_frame_count'],
                interaction_frame_count=pose_embeddings.quality_metadata['interaction_frame_count'],
                video_path=str(video_path),
                clip_id=clip_id
            )
            self.quality_report_generator.add_metrics(quality_metrics)
            
            return embedding_document
            
        except Exception as e:
            logger.error(f"✗ Failed to process video: {e}", exc_info=True)
            return None
    
    def _find_audio_file(self, video_path: Path) -> Optional[Path]:
        """
        Find corresponding audio file for a video.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to audio file, or None if not found
        """
        # Look for audio file in data/songs directory
        songs_dir = self.video_dir.parent / 'songs'
        if not songs_dir.exists():
            return None
        
        # Try common audio extensions
        audio_extensions = ['.mp3', '.wav', '.m4a', '.MP3', '.WAV', '.M4A']
        
        for ext in audio_extensions:
            audio_path = songs_dir / f"{video_path.stem}{ext}"
            if audio_path.exists():
                return audio_path
        
        return None
    
    def process_all_videos(self) -> List[Dict]:
        """
        Process all videos and generate embeddings.
        
        Returns:
            List of embedding documents for successful videos
        """
        video_files = self.find_all_videos()
        self.stats['total_videos'] = len(video_files)
        
        if len(video_files) == 0:
            logger.error("No video files found!")
            return []
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"PROCESSING {len(video_files)} VIDEOS")
        logger.info(f"{'=' * 80}\n")
        
        embeddings = []
        
        # Process each video with progress bar
        for video_path in tqdm(video_files, desc="Processing videos", unit="video"):
            # Reset tracker for each video
            self.pose_detector.reset_tracker()
            
            # Process video
            embedding_doc = self.process_video(video_path)
            
            if embedding_doc:
                embeddings.append(embedding_doc)
                self.stats['successful'] += 1
                self.stats['quality_scores'].append(embedding_doc['quality_score'])
            else:
                self.stats['failed'] += 1
                self.stats['failed_videos'].append(str(video_path.name))
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"PROCESSING COMPLETE")
        logger.info(f"{'=' * 80}")
        logger.info(f"Total videos: {self.stats['total_videos']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        
        if self.stats['failed_videos']:
            logger.warning(f"Failed videos: {', '.join(self.stats['failed_videos'])}")
        
        return embeddings
    
    def index_embeddings(self, embeddings: List[Dict]):
        """
        Index all embeddings in Elasticsearch using bulk operations.
        
        Args:
            embeddings: List of embedding documents
        """
        if not embeddings:
            logger.warning("No embeddings to index")
            return
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"INDEXING {len(embeddings)} EMBEDDINGS IN ELASTICSEARCH")
        logger.info(f"{'=' * 80}")
        
        try:
            self.elasticsearch_service.bulk_index_embeddings(embeddings)
            
            # Verify indexing
            count = self.elasticsearch_service.count_documents()
            logger.info(f"✓ Successfully indexed {count} embeddings")
            
            if count != len(embeddings):
                logger.warning(
                    f"Expected {len(embeddings)} documents but found {count} in index"
                )
        
        except Exception as e:
            logger.error(f"✗ Failed to index embeddings: {e}", exc_info=True)
            raise
    
    def generate_report(self, embeddings: List[Dict]) -> Dict:
        """
        Generate processing report with summary statistics.
        
        Args:
            embeddings: List of embedding documents
            
        Returns:
            Report dictionary
        """
        logger.info(f"\n{'=' * 80}")
        logger.info("GENERATING PROCESSING REPORT")
        logger.info(f"{'=' * 80}")
        
        # Calculate statistics
        total_processing_time = sum(emb['processing_time'] for emb in embeddings)
        avg_processing_time = total_processing_time / len(embeddings) if embeddings else 0
        
        quality_scores = [emb['quality_score'] for emb in embeddings]
        detection_rates = [emb['detection_rate'] for emb in embeddings]
        
        report = {
            'summary': {
                'total_videos': self.stats['total_videos'],
                'successful': self.stats['successful'],
                'failed': self.stats['failed'],
                'success_rate': self.stats['successful'] / self.stats['total_videos'] if self.stats['total_videos'] > 0 else 0
            },
            'timing': {
                'total_processing_time_seconds': total_processing_time,
                'total_processing_time_minutes': total_processing_time / 60,
                'average_time_per_video_seconds': avg_processing_time
            },
            'quality_metrics': {
                'mean_quality_score': float(np.mean(quality_scores)) if quality_scores else 0,
                'median_quality_score': float(np.median(quality_scores)) if quality_scores else 0,
                'min_quality_score': float(np.min(quality_scores)) if quality_scores else 0,
                'max_quality_score': float(np.max(quality_scores)) if quality_scores else 0,
                'std_quality_score': float(np.std(quality_scores)) if quality_scores else 0,
                
                'mean_detection_rate': float(np.mean(detection_rates)) if detection_rates else 0,
                'median_detection_rate': float(np.median(detection_rates)) if detection_rates else 0,
                'min_detection_rate': float(np.min(detection_rates)) if detection_rates else 0,
                'max_detection_rate': float(np.max(detection_rates)) if detection_rates else 0
            },
            'failed_videos': self.stats['failed_videos'],
            'embeddings': [
                {
                    'clip_id': emb['clip_id'],
                    'video_path': emb['video_path'],
                    'quality_score': emb['quality_score'],
                    'detection_rate': emb['detection_rate'],
                    'processing_time': emb['processing_time'],
                    'move_label': emb['move_label'],
                    'difficulty': emb['difficulty']
                }
                for emb in embeddings
            ],
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Log summary
        logger.info(f"Total processing time: {report['timing']['total_processing_time_minutes']:.2f} minutes")
        logger.info(f"Average time per video: {report['timing']['average_time_per_video_seconds']:.2f} seconds")
        logger.info(f"Mean quality score: {report['quality_metrics']['mean_quality_score']:.3f}")
        logger.info(f"Mean detection rate: {report['quality_metrics']['mean_detection_rate']:.3f}")
        
        return report
    
    def save_report(self, report: Dict, output_path: str = "embedding_generation_report.json"):
        """
        Save processing report to JSON file.
        
        Args:
            report: Report dictionary
            output_path: Path to output file
        """
        output_file = Path(output_path)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✓ Report saved to: {output_file}")
    
    def run(self):
        """
        Run the complete embedding generation pipeline.
        
        This method:
        1. Processes all videos
        2. Generates all embeddings
        3. Indexes embeddings in Elasticsearch
        4. Generates and saves processing report
        """
        pipeline_start_time = time.time()
        
        try:
            # Process all videos
            embeddings = self.process_all_videos()
            
            if not embeddings:
                logger.error("No embeddings generated. Pipeline failed.")
                return
            
            # Index embeddings in Elasticsearch
            self.index_embeddings(embeddings)
            
            # Generate processing report
            report = self.generate_report(embeddings)
            
            # Save processing report
            self.save_report(report)
            
            # Generate quality report
            logger.info(f"\n{'=' * 80}")
            logger.info("GENERATING QUALITY REPORT")
            logger.info(f"{'=' * 80}")
            quality_report = self.quality_report_generator.generate_report(
                output_path="data/validation_reports/quality_report.json"
            )
            
            # Calculate total pipeline time
            pipeline_time = time.time() - pipeline_start_time
            
            logger.info(f"\n{'=' * 80}")
            logger.info("PIPELINE COMPLETE")
            logger.info(f"{'=' * 80}")
            logger.info(f"Total pipeline time: {pipeline_time / 60:.2f} minutes")
            logger.info(f"Successfully processed {self.stats['successful']}/{self.stats['total_videos']} videos")
            logger.info(f"All embeddings indexed in Elasticsearch")
            logger.info(f"Quality report saved to: data/validation_reports/quality_report.json")
            logger.info(f"{'=' * 80}\n")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise


def main():
    """Main entry point for embedding generation script."""
    parser = argparse.ArgumentParser(
        description="Generate multimodal embeddings for Bachata video clips"
    )
    
    parser.add_argument(
        '--video_dir',
        type=str,
        required=True,
        help='Directory containing video files (will search recursively)'
    )
    
    parser.add_argument(
        '--annotations',
        type=str,
        required=True,
        help='Path to bachata_annotations.json file'
    )
    
    parser.add_argument(
        '--environment',
        type=str,
        default='local',
        choices=['local', 'cloud'],
        help='Environment configuration (local or cloud)'
    )
    
    parser.add_argument(
        '--checkpoint_path',
        type=str,
        default=None,
        help='Optional path to MMPose model checkpoints (overrides config)'
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
        logger.debug("Debug logging enabled")
    
    # Set environment variable
    import os
    os.environ['ENVIRONMENT'] = args.environment
    
    # Create and run pipeline
    try:
        pipeline = EmbeddingGenerationPipeline(
            video_dir=args.video_dir,
            annotations_path=args.annotations,
            environment=args.environment,
            checkpoint_path=args.checkpoint_path
        )
        
        pipeline.run()
        
    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
