"""
Quality Metrics Calculator

Calculates and logs quality metrics for pose embeddings.

Metrics:
- Quality score: 0.6 * detection_rate + 0.4 * avg_confidence
- Detection rate: percentage of frames with both dancers
- Average confidence: mean confidence across all keypoints
- Frame counts and statistics
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import logging
import json
from pathlib import Path

from video_processing.services.yolov8_couple_detector import CouplePose
from video_processing.services.pose_feature_extractor import TemporalPoseSequence
from video_processing.services.couple_interaction_analyzer import TemporalInteractionSequence

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """
    Quality metrics for a video's pose embeddings.
    
    Attributes:
        quality_score: Overall quality score (0-1)
        detection_rate: Percentage of frames with both dancers (0-1)
        avg_confidence: Average keypoint confidence (0-1)
        total_frames: Total number of frames processed
        frames_with_both_dancers: Number of frames with both dancers detected
        lead_frame_count: Number of frames with lead dancer detected
        follow_frame_count: Number of frames with follow dancer detected
        interaction_frame_count: Number of frames with valid interaction
        video_path: Path to video file
        clip_id: Unique identifier for the clip
    """
    quality_score: float
    detection_rate: float
    avg_confidence: float
    total_frames: int
    frames_with_both_dancers: int
    lead_frame_count: int
    follow_frame_count: int
    interaction_frame_count: int
    video_path: Optional[str] = None
    clip_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'quality_score': self.quality_score,
            'detection_rate': self.detection_rate,
            'avg_confidence': self.avg_confidence,
            'total_frames': self.total_frames,
            'frames_with_both_dancers': self.frames_with_both_dancers,
            'lead_frame_count': self.lead_frame_count,
            'follow_frame_count': self.follow_frame_count,
            'interaction_frame_count': self.interaction_frame_count,
            'video_path': self.video_path,
            'clip_id': self.clip_id,
        }
    
    def is_high_quality(self, threshold: float = 0.7) -> bool:
        """
        Check if quality score meets threshold.
        
        Args:
            threshold: Minimum quality score (default: 0.7)
        
        Returns:
            True if quality_score >= threshold
        """
        return self.quality_score >= threshold
    
    def needs_review(self, detection_threshold: float = 0.5) -> bool:
        """
        Check if video needs manual review due to low detection rate.
        
        Args:
            detection_threshold: Minimum detection rate (default: 0.5)
        
        Returns:
            True if detection_rate < threshold
        """
        return self.detection_rate < detection_threshold


class QualityMetricsCalculator:
    """
    Calculates quality metrics for pose embeddings.
    
    Formula: quality_score = 0.6 * detection_rate + 0.4 * avg_confidence
    """
    
    def __init__(self):
        """Initialize quality metrics calculator."""
        logger.info("QualityMetricsCalculator initialized")
    
    def calculate(self, couple_poses: List[CouplePose],
                 lead_sequence: TemporalPoseSequence,
                 follow_sequence: TemporalPoseSequence,
                 interaction_sequence: TemporalInteractionSequence,
                 video_path: Optional[str] = None,
                 clip_id: Optional[str] = None) -> QualityMetrics:
        """
        Calculate quality metrics from pose data.
        
        Args:
            couple_poses: List of CouplePose objects
            lead_sequence: Lead dancer's temporal sequence
            follow_sequence: Follow dancer's temporal sequence
            interaction_sequence: Interaction temporal sequence
            video_path: Optional path to video file
            clip_id: Optional clip identifier
        
        Returns:
            QualityMetrics object
        """
        total_frames = len(couple_poses)
        
        # Calculate detection rate (frames with both dancers)
        frames_with_both = sum(1 for cp in couple_poses if cp.has_both_dancers)
        detection_rate = frames_with_both / total_frames if total_frames > 0 else 0.0
        
        # Calculate average confidence
        all_confidences = []
        
        # Collect confidences from lead sequence
        for feat in lead_sequence.features:
            if feat is not None:
                all_confidences.extend(feat.keypoint_confidences)
        
        # Collect confidences from follow sequence
        for feat in follow_sequence.features:
            if feat is not None:
                all_confidences.extend(feat.keypoint_confidences)
        
        # Filter out zero confidences (invalid keypoints)
        valid_confidences = [c for c in all_confidences if c > 0]
        avg_confidence = float(np.mean(valid_confidences)) if valid_confidences else 0.0
        
        # Calculate quality score
        # Formula: quality = 0.6 * detection_rate + 0.4 * avg_confidence
        quality_score = 0.6 * detection_rate + 0.4 * avg_confidence
        
        # Create QualityMetrics object
        metrics = QualityMetrics(
            quality_score=float(quality_score),
            detection_rate=float(detection_rate),
            avg_confidence=avg_confidence,
            total_frames=total_frames,
            frames_with_both_dancers=frames_with_both,
            lead_frame_count=lead_sequence.frame_count,
            follow_frame_count=follow_sequence.frame_count,
            interaction_frame_count=interaction_sequence.frame_count,
            video_path=video_path,
            clip_id=clip_id,
        )
        
        # Log metrics
        self._log_metrics(metrics)
        
        return metrics
    
    def _log_metrics(self, metrics: QualityMetrics):
        """
        Log quality metrics with appropriate level.
        
        Args:
            metrics: QualityMetrics object
        """
        log_msg = (
            f"Quality Metrics for {metrics.clip_id or 'video'}:\n"
            f"  Quality Score: {metrics.quality_score:.3f}\n"
            f"  Detection Rate: {metrics.detection_rate:.3f} "
            f"({metrics.frames_with_both_dancers}/{metrics.total_frames} frames)\n"
            f"  Avg Confidence: {metrics.avg_confidence:.3f}\n"
            f"  Lead Frames: {metrics.lead_frame_count}\n"
            f"  Follow Frames: {metrics.follow_frame_count}\n"
            f"  Interaction Frames: {metrics.interaction_frame_count}"
        )
        
        # Log with appropriate level based on quality
        if metrics.quality_score >= 0.8:
            logger.info(f"✓ High quality - {log_msg}")
        elif metrics.quality_score >= 0.6:
            logger.info(f"○ Medium quality - {log_msg}")
        else:
            logger.warning(f"⚠ Low quality - {log_msg}")
        
        # Additional warning for low detection rate
        if metrics.needs_review():
            logger.warning(
                f"⚠️  Video flagged for quality review: "
                f"detection rate ({metrics.detection_rate:.1%}) below 50%"
            )
    
    def log_error(self, video_path: str, error: Exception):
        """
        Log detailed error information when embedding generation fails.
        
        Args:
            video_path: Path to video file that failed
            error: Exception that occurred
        """
        logger.error(
            f"❌ Embedding generation failed for {video_path}:\n"
            f"  Error Type: {type(error).__name__}\n"
            f"  Error Message: {str(error)}\n"
            f"  Video will be skipped"
        )


class QualityReportGenerator:
    """
    Generates quality reports for multiple videos.
    """
    
    def __init__(self):
        """Initialize quality report generator."""
        self.metrics_list: List[QualityMetrics] = []
        logger.info("QualityReportGenerator initialized")
    
    def add_metrics(self, metrics: QualityMetrics):
        """
        Add metrics to report.
        
        Args:
            metrics: QualityMetrics object
        """
        self.metrics_list.append(metrics)
    
    def generate_report(self, output_path: Optional[str] = None) -> dict:
        """
        Generate quality report with statistics.
        
        Args:
            output_path: Optional path to save report as JSON
        
        Returns:
            Dictionary containing report data
        """
        if not self.metrics_list:
            logger.warning("No metrics to generate report")
            return {}
        
        # Calculate statistics
        quality_scores = [m.quality_score for m in self.metrics_list]
        detection_rates = [m.detection_rate for m in self.metrics_list]
        avg_confidences = [m.avg_confidence for m in self.metrics_list]
        
        report = {
            'summary': {
                'total_videos': len(self.metrics_list),
                'high_quality_count': sum(1 for m in self.metrics_list if m.is_high_quality(0.7)),
                'needs_review_count': sum(1 for m in self.metrics_list if m.needs_review()),
                'mean_quality_score': float(np.mean(quality_scores)),
                'std_quality_score': float(np.std(quality_scores)),
                'min_quality_score': float(np.min(quality_scores)),
                'max_quality_score': float(np.max(quality_scores)),
                'mean_detection_rate': float(np.mean(detection_rates)),
                'mean_avg_confidence': float(np.mean(avg_confidences)),
            },
            'distribution': {
                'quality_score_bins': self._create_histogram(quality_scores, bins=10),
                'detection_rate_bins': self._create_histogram(detection_rates, bins=10),
            },
            'videos': [m.to_dict() for m in self.metrics_list],
            'flagged_for_review': [
                m.to_dict() for m in self.metrics_list if m.needs_review()
            ],
        }
        
        # Log summary
        logger.info(
            f"\n{'='*60}\n"
            f"Quality Report Summary:\n"
            f"  Total Videos: {report['summary']['total_videos']}\n"
            f"  High Quality (≥0.7): {report['summary']['high_quality_count']}\n"
            f"  Needs Review (<0.5 detection): {report['summary']['needs_review_count']}\n"
            f"  Mean Quality Score: {report['summary']['mean_quality_score']:.3f} "
            f"± {report['summary']['std_quality_score']:.3f}\n"
            f"  Quality Range: [{report['summary']['min_quality_score']:.3f}, "
            f"{report['summary']['max_quality_score']:.3f}]\n"
            f"  Mean Detection Rate: {report['summary']['mean_detection_rate']:.3f}\n"
            f"  Mean Avg Confidence: {report['summary']['mean_avg_confidence']:.3f}\n"
            f"{'='*60}"
        )
        
        # Save to file if path provided
        if output_path:
            self._save_report(report, output_path)
        
        return report
    
    def _create_histogram(self, values: List[float], bins: int = 10) -> dict:
        """
        Create histogram of values.
        
        Args:
            values: List of values
            bins: Number of bins
        
        Returns:
            Dictionary with bin edges and counts
        """
        counts, bin_edges = np.histogram(values, bins=bins, range=(0, 1))
        
        return {
            'bin_edges': bin_edges.tolist(),
            'counts': counts.tolist(),
        }
    
    def _save_report(self, report: dict, output_path: str):
        """
        Save report to JSON file.
        
        Args:
            report: Report dictionary
            output_path: Path to save file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✓ Quality report saved to {output_path}")
    
    def clear(self):
        """Clear all metrics from report."""
        self.metrics_list.clear()
        logger.debug("Quality report cleared")
