# Elasticsearch Integration

This document describes the Elasticsearch integration for storing and retrieving multimodal embeddings in the Bachata Buddy choreography generation system.

## Overview

The Elasticsearch service provides:
- **Storage**: Efficient storage of 1792-dimensional multimodal embeddings (audio, lead, follow, interaction, text)
- **Retrieval**: Fast retrieval of embeddings with <10ms latency
- **Filtering**: Metadata-based filtering (difficulty, energy_level, move_label, etc.)
- **Bulk Operations**: Efficient batch indexing with single refresh
- **Retry Logic**: Automatic retry with exponential backoff for resilience

## Architecture

### Embedding Storage

Each video clip is stored as a document with 5 separate embeddings:

```
Total: 1792D (stored as individual embeddings, no compression)
├── audio_embedding: 128D (music features)
├── lead_embedding: 512D (lead dancer pose)
├── follow_embedding: 512D (follow dancer pose)
├── interaction_embedding: 256D (couple dynamics)
└── text_embedding: 384D (semantic annotations)
```

### Metadata Fields

Each document includes metadata for filtering and quality tracking:
- `clip_id`: Unique identifier
- `move_label`: Dance move type (e.g., "basic_step", "cross_body_lead")
- `difficulty`: beginner, intermediate, advanced
- `energy_level`: low, medium, high
- `lead_follow_roles`: lead_focus, follow_focus, both
- `estimated_tempo`: BPM (80-160 for Bachata)
- `video_path`: Path to source video
- `quality_score`: 0-1 (0.6 * detection_rate + 0.4 * avg_confidence)
- `detection_rate`: Percentage of frames with both dancers detected
- `frame_count`: Number of frames processed
- `processing_time`: Seconds to process video
- `version`: "mmpose_v1"

## Setup

### Local Development

1. **Start Elasticsearch using Docker:**

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:9.1.0
```

2. **Configure environment variables in `.env`:**

```bash
ENVIRONMENT=local
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=bachata_move_embeddings
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=
ELASTICSEARCH_USE_SSL=false
```

3. **Install dependencies:**

```bash
uv sync
```

4. **Test the connection:**

```bash
uv run python test_elasticsearch_service.py
```

### Google Cloud Production

1. **Set up Elasticsearch on Google Cloud:**

Option A: Use Elastic Cloud (Managed)
- Go to https://cloud.elastic.co/
- Create deployment on Google Cloud Platform
- Choose same region as your Cloud Run service
- Get connection details (host, port, username, password)

Option B: Self-managed on GCE
- Deploy Elasticsearch 9.1 on Compute Engine VM
- Configure security and networking

2. **Store credentials in Secret Manager:**

```bash
# Set your project ID
export GCP_PROJECT_ID=your-project-id

# Create secrets
echo -n "your-es-host.es.gcp.cloud.es.io" | \
    gcloud secrets create elasticsearch-host --data-file=-

echo -n "9243" | \
    gcloud secrets create elasticsearch-port --data-file=-

echo -n "elastic" | \
    gcloud secrets create elasticsearch-username --data-file=-

echo -n "your-password" | \
    gcloud secrets create elasticsearch-password --data-file=-

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding elasticsearch-host \
    --member="serviceAccount:your-project@appspot.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Repeat for other secrets...
```

3. **Set environment variables:**

```bash
export ENVIRONMENT=cloud
export GCP_PROJECT_ID=your-project-id
```

## Usage

### Initialize Service

```python
from core.config.environment_config import EnvironmentConfig
from core.services.elasticsearch_service import ElasticsearchService

# Load configuration
config = EnvironmentConfig()

# Initialize service
es_service = ElasticsearchService(config.elasticsearch)
```

### Create Index

```python
# Create index with mappings (only needed once)
es_service.create_index()
```

### Index Embeddings

```python
import numpy as np
from datetime import datetime

# Prepare embedding document
embedding = {
    "clip_id": "basic_step_1",
    "audio_embedding": np.random.randn(128).astype(np.float32),
    "lead_embedding": np.random.randn(512).astype(np.float32),
    "follow_embedding": np.random.randn(512).astype(np.float32),
    "interaction_embedding": np.random.randn(256).astype(np.float32),
    "text_embedding": np.random.randn(384).astype(np.float32),
    "move_label": "basic_step",
    "difficulty": "beginner",
    "energy_level": "medium",
    "lead_follow_roles": "both",
    "estimated_tempo": 110.0,
    "video_path": "Bachata_steps/basic_steps/basic_step_1.mp4",
    "quality_score": 0.87,
    "detection_rate": 0.92,
    "frame_count": 450,
    "processing_time": 180.5,
    "version": "mmpose_v1",
    "created_at": datetime.now().isoformat()
}

# Bulk index multiple embeddings
embeddings = [embedding]  # Add more embeddings
es_service.bulk_index_embeddings(embeddings)
```

### Retrieve Embeddings

```python
# Get all embeddings
all_embeddings = es_service.get_all_embeddings()

# Filter by metadata
beginner_moves = es_service.get_all_embeddings(
    filters={"difficulty": "beginner"}
)

# Get single embedding by ID
embedding = es_service.get_embedding_by_id("basic_step_1")
```

### Compute Similarity

```python
def compute_weighted_similarity(query_emb, candidate_emb):
    """
    Compute weighted similarity across all modalities.
    
    Weights: text (35%), audio (35%), lead (10%), follow (10%), interaction (10%)
    """
    # Compute individual cosine similarities
    text_sim = cosine_similarity(
        query_emb['text_embedding'],
        candidate_emb['text_embedding']
    )
    audio_sim = cosine_similarity(
        query_emb['audio_embedding'],
        candidate_emb['audio_embedding']
    )
    lead_sim = cosine_similarity(
        query_emb['lead_embedding'],
        candidate_emb['lead_embedding']
    )
    follow_sim = cosine_similarity(
        query_emb['follow_embedding'],
        candidate_emb['follow_embedding']
    )
    interaction_sim = cosine_similarity(
        query_emb['interaction_embedding'],
        candidate_emb['interaction_embedding']
    )
    
    # Apply weights
    overall_similarity = (
        0.35 * text_sim +
        0.35 * audio_sim +
        0.10 * lead_sim +
        0.10 * follow_sim +
        0.10 * interaction_sim
    )
    
    return overall_similarity

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 > 0 and norm2 > 0:
        return dot_product / (norm1 * norm2)
    return 0.0
```

## Performance

### Benchmarks

With 38 video embeddings:
- **Index creation**: <1 second
- **Bulk indexing**: <1 second (38 documents)
- **Single retrieval**: <10ms
- **Retrieve all**: <50ms
- **Filtered retrieval**: <50ms

### Storage

- **Per document**: ~7 KB (1792D embeddings + metadata)
- **38 documents**: ~270 KB total
- **Index overhead**: ~1-2 MB

## Error Handling

The service includes robust error handling:

### Connection Errors

```python
try:
    es_service = ElasticsearchService(config.elasticsearch)
except ConnectionError as e:
    print(f"Cannot connect to Elasticsearch: {e}")
    # Check if Elasticsearch is running
    # Verify host/port configuration
```

### Retry Logic

All retrieval operations automatically retry up to 3 times with exponential backoff:
- Attempt 1: Immediate
- Attempt 2: Wait 1 second
- Attempt 3: Wait 2 seconds
- Attempt 4: Wait 4 seconds

### Validation

The service validates:
- Configuration parameters (host, port, index name)
- Embedding dimensions (128D, 512D, 512D, 256D, 384D)
- Connection on initialization

## Monitoring

### Check Index Status

```python
# Check if index exists
exists = es_service.index_exists()

# Count documents
count = es_service.count_documents()

# Get index info
info = es_service.client.indices.get(index=es_service.index_name)
```

### Logging

The service logs at different levels:
- **INFO**: Connection status, indexing progress, retrieval counts
- **WARNING**: Retry attempts, missing documents
- **ERROR**: Connection failures, indexing errors

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Troubleshooting

### Cannot connect to Elasticsearch

**Problem**: `ConnectionError: Cannot connect to Elasticsearch at localhost:9200`

**Solutions**:
1. Check if Elasticsearch is running:
   ```bash
   curl http://localhost:9200
   ```
2. Verify Docker container is running:
   ```bash
   docker ps | grep elasticsearch
   ```
3. Start Elasticsearch:
   ```bash
   docker start elasticsearch
   ```

### Index already exists

**Problem**: Index creation fails because index already exists

**Solution**: Delete and recreate:
```python
es_service.delete_index()
es_service.create_index()
```

### Slow queries

**Problem**: Queries take longer than expected

**Solutions**:
1. Check Elasticsearch health:
   ```bash
   curl http://localhost:9200/_cluster/health
   ```
2. Increase connection pool size in `.env`:
   ```
   ELASTICSEARCH_MAX_CONNECTIONS=20
   ```
3. Optimize index settings (production only)

### Memory issues

**Problem**: Elasticsearch runs out of memory

**Solutions**:
1. Increase Docker memory limit:
   ```bash
   docker run -m 4g ...
   ```
2. Reduce number of shards (for small datasets)
3. Use Elastic Cloud for production

## Best Practices

### Development

1. **Use Docker**: Simplest way to run Elasticsearch locally
2. **Test connection**: Always verify connection before indexing
3. **Clean up**: Delete test indices after testing
4. **Version control**: Never commit `.env` files

### Production

1. **Use managed service**: Elastic Cloud or equivalent
2. **Enable SSL**: Always use SSL in production
3. **Secure credentials**: Store in Secret Manager, never in code
4. **Monitor performance**: Track query latency and error rates
5. **Backup data**: Regular snapshots of indices
6. **Scale horizontally**: Add nodes as data grows

## API Reference

### ElasticsearchService

#### `__init__(config: ElasticsearchConfig)`
Initialize service with configuration.

#### `create_index()`
Create index with dense_vector mappings.

#### `bulk_index_embeddings(embeddings: List[Dict])`
Bulk index embeddings with single refresh.

#### `get_all_embeddings(filters: Optional[Dict] = None) -> List[Dict]`
Retrieve all embeddings, optionally filtered by metadata.

#### `get_embedding_by_id(clip_id: str) -> Optional[Dict]`
Retrieve single embedding by clip_id.

#### `index_exists() -> bool`
Check if index exists.

#### `delete_index()`
Delete index (warning: deletes all data).

#### `count_documents() -> int`
Count documents in index.

#### `close()`
Close Elasticsearch connection.

## Related Documentation

- [Environment Configuration](../config/README.md)
- [MMPose Integration](./README_MMPOSE.md)
- [Embedding Generation](./README_EMBEDDINGS.md)
- [Recommendation Engine](./README_RECOMMENDATIONS.md)

## Support

For issues or questions:
1. Check this documentation
2. Review error logs
3. Test with `test_elasticsearch_service.py`
4. Check Elasticsearch documentation: https://www.elastic.co/guide/
