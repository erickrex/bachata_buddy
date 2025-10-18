# Offline Embedding Generation Pipeline

This script processes all Bachata video clips and generates multimodal embeddings for storage in Elasticsearch.

## Overview

The embedding generation pipeline:
1. **Processes all videos** recursively from a specified directory
2. **Generates pose embeddings** (lead 512D, follow 512D, interaction 256D) using MMPose
3. **Generates audio embeddings** (128D) using Librosa
4. **Generates text embeddings** (384D) from annotations using sentence-transformers
5. **Indexes all embeddings** in Elasticsearch using bulk operations
6. **Generates a processing report** with quality metrics and statistics

**Total embedding dimensions: 1792D** (stored as 5 separate embeddings)

## Requirements

- Python 3.11+
- UV package manager
- MMPose models downloaded (see `MMPOSE_SETUP.md`)
- Elasticsearch 9.1 running locally or in cloud
- Video files and annotations

## Usage

### Basic Usage (Local Development)

```bash
uv run python scripts/generate_embeddings.py \
  --video_dir data/Bachata_steps \
  --annotations data/bachata_annotations.json \
  --environment local
```

### With Custom Checkpoint Path

```bash
uv run python scripts/generate_embeddings.py \
  --video_dir data/Bachata_steps \
  --annotations data/bachata_annotations.json \
  --environment local \
  --checkpoint_path ./checkpoints
```

### With Debug Logging

```bash
uv run python scripts/generate_embeddings.py \
  --video_dir data/Bachata_steps \
  --annotations data/bachata_annotations.json \
  --environment local \
  --debug
```

### Cloud Environment

```bash
uv run python scripts/generate_embeddings.py \
  --video_dir data/Bachata_steps \
  --annotations data/bachata_annotations.json \
  --environment cloud
```

## Command-Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--video_dir` | Yes | Directory containing video files (searches recursively) |
| `--annotations` | Yes | Path to `bachata_annotations.json` file |
| `--environment` | No | Environment configuration: `local` or `cloud` (default: `local`) |
| `--checkpoint_path` | No | Path to MMPose model checkpoints (overrides config) |
| `--debug` | No | Enable debug logging |

## Configuration

The script uses environment-specific configuration:

### Local Development (.env file)

Create a `.env` file in the project root:

```env
ENVIRONMENT=local
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=bachata_move_embeddings
MMPOSE_CHECKPOINT_PATH=./checkpoints
```

### Cloud Production (Google Cloud Secret Manager)

Set environment variable:
```bash
export ENVIRONMENT=cloud
export GCP_PROJECT_ID=your-project-id
```

Secrets are loaded from Google Cloud Secret Manager:
- `elasticsearch-host`
- `elasticsearch-port`
- `elasticsearch-username`
- `elasticsearch-password`
- `mmpose-checkpoint-path`

## Output

### Processing Report

The script generates `embedding_generation_report.json` with:

```json
{
  "summary": {
    "total_videos": 38,
    "successful": 38,
    "failed": 0,
    "success_rate": 1.0
  },
  "timing": {
    "total_processing_time_seconds": 7200.0,
    "total_processing_time_minutes": 120.0,
    "average_time_per_video_seconds": 189.47
  },
  "quality_metrics": {
    "mean_quality_score": 0.85,
    "median_quality_score": 0.87,
    "min_quality_score": 0.65,
    "max_quality_score": 0.95,
    "mean_detection_rate": 0.92
  },
  "failed_videos": [],
  "embeddings": [...]
}
```

### Log File

Processing logs are saved to `embedding_generation.log`.

### Elasticsearch Index

All embeddings are indexed in Elasticsearch with the following structure:

```json
{
  "clip_id": "basic_step_1",
  "video_path": "data/Bachata_steps/basic_steps/basic_step_1.mp4",
  
  "audio_embedding": [...],      // 128D
  "lead_embedding": [...],       // 512D
  "follow_embedding": [...],     // 512D
  "interaction_embedding": [...], // 256D
  "text_embedding": [...],       // 384D
  
  "move_label": "basic_step",
  "difficulty": "beginner",
  "energy_level": "medium",
  "lead_follow_roles": "both",
  "estimated_tempo": 110.0,
  
  "quality_score": 0.87,
  "detection_rate": 0.92,
  "frame_count": 450,
  "processing_time": 180.5,
  "version": "mmpose_v1",
  "created_at": "2025-10-18T12:00:00Z"
}
```

## Processing Pipeline

For each video, the pipeline:

1. **Loads annotation** from `bachata_annotations.json`
2. **Detects couple poses** using MMPose (15 FPS sampling)
   - Detects both dancers (lead and follow)
   - Tracks person IDs across frames using IoU
   - Extracts 17 COCO body keypoints per person
   - Optionally detects 21 hand keypoints per hand
3. **Generates pose embeddings**
   - Lead embedding (512D) from lead dancer's pose sequence
   - Follow embedding (512D) from follow dancer's pose sequence
   - Interaction embedding (256D) from couple dynamics
4. **Analyzes audio** using Librosa
   - Extracts MFCC, chroma, spectral features
   - Analyzes tempo, beat, rhythm patterns
   - Generates 128D audio embedding
5. **Generates text embedding** from annotation
   - Creates natural language description
   - Uses sentence-transformers (all-MiniLM-L6-v2)
   - Generates 384D text embedding
6. **Validates embeddings** for NaN/Inf values
7. **Calculates quality metrics**
   - Quality score = 0.6 * detection_rate + 0.4 * avg_confidence
   - Detection rate = frames with both dancers / total frames

## Performance

### Expected Processing Time

- **Per video**: ~3-4 minutes on CPU (10-20 second videos)
- **All 38 videos**: ~2 hours on CPU
- **One-time processing**: Embeddings are pre-computed and stored

### Hardware Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 16GB+ recommended
- **Storage**: 2GB for model checkpoints, ~2MB for embeddings
- **No GPU required**: CPU-only processing

## Error Handling

The pipeline handles errors gracefully:

- **Video processing failures**: Logs error, skips video, continues with remaining videos
- **Missing annotations**: Uses fallback values
- **Elasticsearch failures**: Retries with exponential backoff (3 attempts)
- **Invalid embeddings**: Validates for NaN/Inf, rejects if invalid

Failed videos are listed in the processing report.

## Quality Filtering

Videos with quality scores below 0.5 should be reviewed:

```bash
# Check quality scores in report
cat embedding_generation_report.json | jq '.embeddings[] | select(.quality_score < 0.5)'
```

## Verification

Verify the pipeline is working correctly:

```bash
uv run python verify_embedding_pipeline.py
```

## Troubleshooting

### MMPose Models Not Found

```
FileNotFoundError: Checkpoint directory not found
```

**Solution**: Download MMPose models:
```bash
uv run python scripts/download_mmpose_models.py
```

### Elasticsearch Connection Failed

```
ConnectionError: Cannot connect to Elasticsearch
```

**Solution**: Start Elasticsearch:
```bash
docker run -p 9200:9200 -e "discovery.type=single-node" elasticsearch:9.1.0
```

### Out of Memory

```
MemoryError: Cannot allocate memory
```

**Solution**: Process videos in smaller batches or increase RAM.

### Low Quality Scores

If quality scores are consistently low (<0.5):
- Check video quality (minimum 480p recommended)
- Ensure both dancers are visible in >50% of frames
- Verify lighting conditions are adequate
- Consider re-recording problematic videos

## Integration with Recommendation Engine

After running this pipeline, embeddings are available for fast retrieval:

```python
from core.services.elasticsearch_service import ElasticsearchService
from core.config.environment_config import EnvironmentConfig

config = EnvironmentConfig()
es_service = ElasticsearchService(config.elasticsearch)

# Retrieve all embeddings
embeddings = es_service.get_all_embeddings()

# Get specific embedding
embedding = es_service.get_embedding_by_id("basic_step_1")
```

## Related Documentation

- `MMPOSE_SETUP.md` - MMPose installation and model download
- `ELASTICSEARCH_IMPLEMENTATION.md` - Elasticsearch setup and configuration
- `core/services/README_ELASTICSEARCH.md` - Elasticsearch service documentation
- `.kiro/specs/mmpose-embedding-enhancement/design.md` - System design

## Requirements Coverage

This script implements the following requirements:

- **Requirement 7.1-7.11**: Offline embedding generation pipeline
- **Requirement 5.1-5.11**: Text embedding generation
- **Requirement 6.1-6.12**: Elasticsearch storage
- **Requirement 10.1-10.4**: Quality metrics and validation
