# AI Services

## Purpose

The `ai_services` app provides AI and machine learning capabilities for the Bachata Buddy choreography generation system. It handles natural language processing, embedding generation and storage, similarity search, move analysis, and recommendation scoring.

This app is the intelligence layer that powers:
- Natural language query understanding
- Semantic search across dance moves
- Multi-modal similarity matching (audio, pose, text)
- Move quality assessment
- Choreography recommendations

## Architecture

The AI services layer sits between the video processing pipeline and the user-facing choreography generation:

```
User Query → Gemini NLP → Recommendation Engine → Elasticsearch → Video Processing
                ↓                    ↓                    ↓
         Text Embeddings    Move Analysis      Stored Embeddings
```

## Services

### Core AI Services

#### 1. **GeminiService** (`gemini_service.py`)

Natural language processing using Google's Gemini API for choreography parameter extraction.

**Features:**
- Parses natural language queries into structured choreography parameters
- Generates AI explanations for move selections
- Provides smart search suggestions when no results found
- Rate limiting (60 requests/minute for free tier)
- Error handling with fallback strategies

**Usage:**
```python
from ai_services.services.gemini_service import GeminiService, ChoreographyParameters

service = GeminiService()

# Parse natural language query
params = service.parse_choreography_request(
    "I want a romantic, slow dance for beginners"
)
# Returns: ChoreographyParameters(
#     difficulty='beginner',
#     energy_level='low',
#     style='romantic',
#     tempo='slow'
# )

# Generate explanation
explanation = service.generate_move_explanation(
    selected_moves=['basic_step', 'cross_body_lead'],
    user_query="romantic dance"
)
```

**Dependencies:**
- `google-generativeai>=0.3.0`
- `common.config.environment_config`

---

#### 2. **ElasticsearchService** (`elasticsearch_service.py`)

Manages storage and retrieval of multimodal embeddings using Elasticsearch.

**Features:**
- Bulk indexing for efficient batch operations
- kNN vector similarity search across 5 embedding types
- Metadata filtering (difficulty, energy, tempo, etc.)
- Connection pooling and retry logic with exponential backoff
- Sub-10ms query latency

**Embedding Structure:**
```
Total: 1792D (stored as separate embeddings)
├── audio_embedding: 128D (music features)
├── lead_embedding: 512D (lead dancer pose)
├── follow_embedding: 512D (follow dancer pose)
├── interaction_embedding: 256D (couple dynamics)
└── text_embedding: 384D (semantic annotations)
```

**Usage:**
```python
from ai_services.services.elasticsearch_service import ElasticsearchService
from common.config.environment_config import EnvironmentConfig

config = EnvironmentConfig.load()
es_service = ElasticsearchService(config.elasticsearch)

# Index embeddings
es_service.index_embeddings(
    clip_id="basic_step_1",
    embeddings={
        'audio_embedding': audio_emb,
        'lead_embedding': lead_emb,
        'follow_embedding': follow_emb,
        'interaction_embedding': interaction_emb,
        'text_embedding': text_emb
    },
    metadata={
        'move_label': 'basic_step',
        'difficulty': 'beginner',
        'energy_level': 'medium'
    }
)

# Search by similarity
results = es_service.search_similar(
    query_embeddings={
        'audio_embedding': query_audio,
        'text_embedding': query_text
    },
    filters={'difficulty': 'beginner'},
    top_k=10
)
```

**Dependencies:**
- `elasticsearch>=8.11.0`
- `common.config.environment_config`

**See Also:** [README_ELASTICSEARCH.md](./README_ELASTICSEARCH.md) for detailed Elasticsearch integration documentation.

---

#### 3. **TextEmbeddingService** (`text_embedding_service.py`)

Generates semantic text embeddings from move annotations using sentence-transformers.

**Features:**
- Loads annotations from `bachata_annotations.json`
- Generates natural language descriptions from structured data
- Creates 384D embeddings using `all-MiniLM-L6-v2` model
- Caches model instance for reuse
- Handles missing/incomplete annotations gracefully

**Usage:**
```python
from ai_services.services.text_embedding_service import TextEmbeddingService

service = TextEmbeddingService(model_name='all-MiniLM-L6-v2')

# Load annotations
annotations = service.load_annotations('data/bachata_annotations.json')

# Generate embedding for a clip
embedding = service.generate_embedding(
    clip_id="basic_step_1",
    annotations=annotations
)
# Returns: 384D numpy array
```

**Dependencies:**
- `sentence-transformers>=2.0.0`
- `numpy>=1.21.0`

---

#### 4. **RecommendationEngine** (`recommendation_engine.py`)

Multi-factor scoring system for choreography generation using weighted multimodal similarity.

**Features:**
- Weighted similarity computation across 5 modalities
- Metadata filtering (difficulty, energy, tempo)
- Diversity enforcement to avoid repetitive moves
- Configurable modality weights

**Modality Weights:**
- Text semantic: 35%
- Audio: 35%
- Lead pose: 10%
- Follow pose: 10%
- Interaction: 10%

**Usage:**
```python
from ai_services.services.recommendation_engine import RecommendationEngine
from common.config.environment_config import EnvironmentConfig

config = EnvironmentConfig.load()
engine = RecommendationEngine(config)

# Get recommendations
recommendations = engine.recommend_moves(
    query_embeddings={
        'audio_embedding': song_audio_emb,
        'text_embedding': query_text_emb
    },
    filters={
        'difficulty': 'intermediate',
        'energy_level': 'high'
    },
    num_moves=8,
    diversity_threshold=0.7
)

# Each recommendation includes:
# - move_candidate: MoveCandidate with all embeddings
# - overall_score: Weighted similarity score
# - modality_scores: Individual similarity scores
```

**Dependencies:**
- `ai_services.services.elasticsearch_service`
- `common.config.environment_config`
- `numpy>=1.21.0`

---

#### 5. **MoveAnalyzer** (`move_analyzer.py`)

Analyzes Bachata move clips using MediaPipe for pose detection and feature extraction.

**Features:**
- Pose landmark detection (33 keypoints per person)
- Hand landmark detection (21 keypoints per hand)
- Joint angle computation
- Movement dynamics analysis (velocity, acceleration, rhythm)
- Energy level estimation
- Complexity scoring

**Usage:**
```python
from ai_services.services.move_analyzer import MoveAnalyzer

analyzer = MoveAnalyzer()

# Analyze a video clip
result = analyzer.analyze_move(
    video_path="data/Bachata_steps/basic_steps/basic_step_1.mp4"
)

# Access features
print(f"Energy level: {result.movement_dynamics.energy_level}")
print(f"Complexity: {result.movement_dynamics.complexity_score}")
print(f"Dominant direction: {result.movement_dynamics.dominant_movement_direction}")
```

**Dependencies:**
- `mediapipe`
- `opencv-python>=4.5.0`
- `numpy>=1.21.0`

---

### ML Utilities

#### 6. **FeatureFusion** (`feature_fusion.py`)

Combines audio and pose features into unified multimodal embeddings.

**Features:**
- Fuses audio (128D) and pose (384D) into combined 512D embeddings
- Weighted fusion strategies
- Similarity scoring across modalities

**Usage:**
```python
from ai_services.services.feature_fusion import FeatureFusion, MultiModalEmbedding

fusion = FeatureFusion()

# Combine features
combined = fusion.fuse_features(
    audio_features=music_features,
    pose_features=move_analysis_result
)
# Returns: MultiModalEmbedding with combined_embedding, audio_embedding, pose_embedding

# Compute similarity
similarity = fusion.compute_similarity(
    embedding1=combined1,
    embedding2=combined2,
    weights={'audio': 0.5, 'pose': 0.5}
)
```

---

#### 7. **QualityMetrics** (`quality_metrics.py`)

Calculates quality metrics for pose embeddings and video analysis.

**Metrics:**
- Quality score: `0.6 * detection_rate + 0.4 * avg_confidence`
- Detection rate: Percentage of frames with both dancers detected
- Average confidence: Mean confidence across all keypoints
- Frame statistics

**Usage:**
```python
from ai_services.services.quality_metrics import QualityMetrics

metrics = QualityMetrics.calculate(
    couple_poses=detected_poses,
    temporal_sequences=pose_sequences
)

print(f"Quality score: {metrics.quality_score:.2f}")
print(f"Detection rate: {metrics.detection_rate:.2%}")
print(f"Frames with both dancers: {metrics.frames_with_both_dancers}/{metrics.total_frames}")
```

---

#### 8. **EmbeddingValidator** (`embedding_validator.py`)

Validates embeddings for quality and correctness.

**Checks:**
- NaN values
- Inf values
- Correct dimensionality
- Value ranges

**Expected Dimensions:**
- `lead_embedding`: 512D
- `follow_embedding`: 512D
- `interaction_embedding`: 256D
- `text_embedding`: 384D
- `audio_embedding`: 128D

**Usage:**
```python
from ai_services.services.embedding_validator import EmbeddingValidator

validator = EmbeddingValidator()

# Validate single embedding
is_valid, errors = validator.validate_embedding(
    embedding=lead_embedding,
    embedding_type='lead_embedding'
)

# Validate all embeddings for a clip
is_valid, errors = validator.validate_all_embeddings({
    'lead_embedding': lead_emb,
    'follow_embedding': follow_emb,
    'interaction_embedding': interaction_emb,
    'text_embedding': text_emb,
    'audio_embedding': audio_emb
})
```

---

### Planned Services (Stubs)

The following services are planned but not yet fully implemented:

#### 9. **HyperparameterOptimizer** (`hyperparameter_optimizer.py`)
- Optimizes modality weights for recommendation engine
- Grid search and Bayesian optimization
- Cross-validation support

#### 10. **ModelValidationFramework** (`model_validation.py`)
- Cross-validation for recommendation quality
- A/B testing framework
- Performance benchmarking

#### 11. **TrainingDataValidator** (`training_data_validator.py`)
- Validates training data quality and structure
- Checks for data consistency

#### 12. **TrainingDatasetBuilder** (`training_dataset_builder.py`)
- Builds training datasets from annotations
- Creates similarity pairs and ground truth matrices

---

## Dependencies

### Required Python Packages

```toml
# AI/ML Core
google-generativeai>=0.3.0      # Gemini API for NLP
sentence-transformers>=2.0.0    # Text embeddings
numpy>=1.21.0                   # Numerical operations
scipy>=1.11.0                   # Scientific computing
torch>=2.0.0                    # PyTorch (for sentence-transformers)

# Search & Storage
elasticsearch>=8.11.0           # Vector similarity search

# Video/Pose Analysis
opencv-python>=4.5.0            # Video processing
mediapipe                       # Pose detection (via move_analyzer)

# Utilities
tqdm>=4.62.0                    # Progress bars
```

### Internal Dependencies

```python
# From common app
from common.config.environment_config import EnvironmentConfig, ElasticsearchConfig
from common.exceptions import ValidationError, ServiceError

# From video_processing app (for move_analyzer)
from video_processing.services.music_analyzer import MusicFeatures
from video_processing.services.yolov8_couple_detector import CouplePose
from video_processing.services.pose_feature_extractor import TemporalPoseSequence
from video_processing.services.couple_interaction_analyzer import TemporalInteractionSequence
```

---

## Configuration

AI services are configured through environment variables and the `EnvironmentConfig` class:

```python
# .env file
GEMINI_API_KEY=your_api_key_here
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=bachata_embeddings
```

```python
# Usage in code
from common.config.environment_config import EnvironmentConfig

config = EnvironmentConfig.load()

# Access AI service configs
gemini_key = config.gemini_api_key
es_config = config.elasticsearch
```

---

## Testing

Tests for AI services are located in `tests/services/`:

```bash
# Run all AI service tests
uv run pytest tests/services/

# Run specific service tests
uv run pytest tests/services/test_gemini_service.py
uv run pytest tests/services/test_elasticsearch_service.py
uv run pytest tests/services/test_recommendation_engine.py
```

**Key Test Files:**
- `test_gemini_service.py` - NLP and parameter extraction tests
- `test_elasticsearch_service.py` - Embedding storage and retrieval tests
- `test_elasticsearch_serverless.py` - Serverless Elasticsearch tests
- `test_text_embedding_service.py` - Text embedding generation tests
- `test_recommendation_engine.py` - Recommendation scoring tests
- `test_hybrid_search.py` - Multi-modal search tests

---

## Common Usage Patterns

### 1. End-to-End Choreography Generation

```python
from ai_services.services.gemini_service import GeminiService
from ai_services.services.recommendation_engine import RecommendationEngine
from ai_services.services.text_embedding_service import TextEmbeddingService
from common.config.environment_config import EnvironmentConfig

# Initialize services
config = EnvironmentConfig.load()
gemini = GeminiService()
text_embedder = TextEmbeddingService()
recommender = RecommendationEngine(config)

# 1. Parse user query
user_query = "I want a romantic, slow dance for beginners"
params = gemini.parse_choreography_request(user_query)

# 2. Generate text embedding from query
query_text_emb = text_embedder.generate_embedding_from_text(user_query)

# 3. Get recommendations
recommendations = recommender.recommend_moves(
    query_embeddings={
        'text_embedding': query_text_emb,
        'audio_embedding': song_audio_emb  # from video_processing
    },
    filters={
        'difficulty': params.difficulty,
        'energy_level': params.energy_level
    },
    num_moves=8
)

# 4. Generate explanation
explanation = gemini.generate_move_explanation(
    selected_moves=[r.move_candidate.move_label for r in recommendations],
    user_query=user_query
)
```

### 2. Indexing New Move Clips

```python
from ai_services.services.elasticsearch_service import ElasticsearchService
from ai_services.services.text_embedding_service import TextEmbeddingService
from ai_services.services.embedding_validator import EmbeddingValidator
from video_processing.services.pose_embedding_generator import PoseEmbeddingGenerator
from video_processing.services.music_analyzer import MusicAnalyzer

# Initialize services
es_service = ElasticsearchService(config.elasticsearch)
text_embedder = TextEmbeddingService()
validator = EmbeddingValidator()
pose_generator = PoseEmbeddingGenerator()
music_analyzer = MusicAnalyzer()

# Process video clip
video_path = "data/Bachata_steps/basic_steps/basic_step_1.mp4"

# Generate embeddings
pose_embeddings = pose_generator.generate_embeddings(video_path)
audio_embedding = music_analyzer.extract_features(video_path)
text_embedding = text_embedder.generate_embedding(
    clip_id="basic_step_1",
    annotations=annotations
)

# Validate embeddings
embeddings = {
    'lead_embedding': pose_embeddings.lead_embedding,
    'follow_embedding': pose_embeddings.follow_embedding,
    'interaction_embedding': pose_embeddings.interaction_embedding,
    'text_embedding': text_embedding,
    'audio_embedding': audio_embedding
}

is_valid, errors = validator.validate_all_embeddings(embeddings)
if not is_valid:
    raise ValueError(f"Invalid embeddings: {errors}")

# Index in Elasticsearch
es_service.index_embeddings(
    clip_id="basic_step_1",
    embeddings=embeddings,
    metadata={
        'move_label': 'basic_step',
        'difficulty': 'beginner',
        'energy_level': 'medium',
        'video_path': video_path
    }
)
```

### 3. Quality Assessment

```python
from ai_services.services.quality_metrics import QualityMetrics
from video_processing.services.yolov8_couple_detector import YOLOv8CoupleDetector
from video_processing.services.pose_feature_extractor import PoseFeatureExtractor

# Detect poses
detector = YOLOv8CoupleDetector()
extractor = PoseFeatureExtractor()

couple_poses = detector.detect_couple(video_path)
temporal_sequences = extractor.extract_temporal_features(couple_poses)

# Calculate quality metrics
metrics = QualityMetrics.calculate(
    couple_poses=couple_poses,
    temporal_sequences=temporal_sequences
)

# Use metrics for filtering
if metrics.quality_score < 0.5:
    print(f"Low quality video: {metrics.quality_score:.2f}")
    print(f"Detection rate: {metrics.detection_rate:.2%}")
```

---

## Performance Considerations

### Elasticsearch Query Optimization

- **Bulk Indexing**: Use `bulk_index_embeddings()` for batch operations
- **Connection Pooling**: Reuse ElasticsearchService instances
- **Metadata Filtering**: Apply filters before kNN search to reduce search space
- **Index Refresh**: Bulk operations use single refresh for better performance

### Embedding Generation

- **Model Caching**: TextEmbeddingService caches the sentence-transformers model
- **Batch Processing**: Generate embeddings in batches when possible
- **GPU Acceleration**: Use CUDA-enabled PyTorch for faster embedding generation

### Rate Limiting

- **Gemini API**: 60 requests/minute (free tier)
- **Implement Caching**: Cache parsed parameters and explanations
- **Fallback Strategies**: Use default parameters when API is unavailable

---

## Troubleshooting

### Common Issues

#### 1. Elasticsearch Connection Errors

```python
# Check Elasticsearch is running
curl http://localhost:9200

# Verify configuration
from common.config.environment_config import EnvironmentConfig
config = EnvironmentConfig.load()
print(config.elasticsearch.host)
```

#### 2. Gemini API Rate Limiting

```python
# The service includes automatic rate limiting
# If you hit limits, responses will be delayed automatically
# For production, consider upgrading to paid tier
```

#### 3. Embedding Dimension Mismatches

```python
# Use EmbeddingValidator to catch dimension errors
from ai_services.services.embedding_validator import EmbeddingValidator

validator = EmbeddingValidator()
is_valid, errors = validator.validate_embedding(embedding, 'lead_embedding')
if not is_valid:
    print(f"Validation errors: {errors}")
```

#### 4. Low Quality Scores

```python
# Check detection rates and confidence
metrics = QualityMetrics.calculate(couple_poses, temporal_sequences)
print(f"Detection rate: {metrics.detection_rate:.2%}")
print(f"Avg confidence: {metrics.avg_confidence:.2f}")

# Low scores may indicate:
# - Poor lighting in video
# - Dancers out of frame
# - Occlusions
# - Low resolution video
```

---

## Migration Guide

If you're migrating from the old `core.services` structure:

### Old Import Paths
```python
from core.services.gemini_service import GeminiService
from core.services.elasticsearch_service import ElasticsearchService
from core.services.recommendation_engine import RecommendationEngine
```

### New Import Paths
```python
from ai_services.services.gemini_service import GeminiService
from ai_services.services.elasticsearch_service import ElasticsearchService
from ai_services.services.recommendation_engine import RecommendationEngine
```

All functionality remains the same - only import paths have changed.

---

## Contributing

When adding new AI services:

1. Place service files in `ai_services/services/`
2. Add comprehensive docstrings with features and usage examples
3. Include type hints for all function parameters and returns
4. Add tests in `tests/services/test_<service_name>.py`
5. Update this README with service documentation
6. Validate embeddings using `EmbeddingValidator`
7. Follow the existing service patterns for consistency

---

## Related Documentation

- [Elasticsearch Integration](./README_ELASTICSEARCH.md) - Detailed Elasticsearch setup and usage
- [Common App README](../common/README.md) - Shared utilities and configuration
- [Video Processing README](../video_processing/README.md) - Video and pose processing services
- [Architecture Diagrams](../../ARCHITECTURE_DIAGRAMS.md) - System architecture overview

---

## License

See [LICENSE](../../LICENSE) file in the project root.
