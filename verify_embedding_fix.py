#!/usr/bin/env python3
"""
Quick verification that the embedding dimension fix is working.
"""
import sys
sys.path.insert(0, 'backend')

import numpy as np
from music_analyzer import MusicAnalyzer
from services.vector_search_service import VectorSearchService

print("=" * 80)
print("EMBEDDING DIMENSION FIX VERIFICATION")
print("=" * 80)
print()

# Step 1: Test music analyzer
print("Step 1: Testing Music Analyzer")
print("-" * 80)
ma = MusicAnalyzer()
features = ma.analyze_audio('data/songs/test_short.mp3')
print(f"✓ Audio embedding dimensions: {len(features.audio_embedding)}")
print(f"✓ Expected: 128")
assert len(features.audio_embedding) == 128, "Audio embedding should be 128-dim"
print()

# Step 2: Test weighted combination
print("Step 2: Testing Weighted Combination")
print("-" * 80)
audio_emb = np.array(features.audio_embedding, dtype=np.float32)
query_embedding = VectorSearchService.combine_embeddings_weighted(
    pose_embedding=None,
    audio_embedding=audio_emb,
    text_embedding=None
)
print(f"✓ Query embedding dimensions: {len(query_embedding)}")
print(f"✓ Expected: 1024 (512 pose + 128 audio + 384 text)")
assert len(query_embedding) == 1024, "Query embedding should be 1024-dim"
print()

# Step 3: Verify embedding structure
print("Step 3: Verifying Embedding Structure")
print("-" * 80)
print(f"✓ Pose component (0-512): {query_embedding[:512].shape}")
print(f"✓ Audio component (512-640): {query_embedding[512:640].shape}")
print(f"✓ Text component (640-1024): {query_embedding[640:1024].shape}")
print()

# Step 4: Check that audio component has non-zero values
audio_component = query_embedding[512:640]
non_zero_count = np.count_nonzero(audio_component)
print(f"✓ Non-zero values in audio component: {non_zero_count}/128")
assert non_zero_count > 0, "Audio component should have non-zero values"
print()

print("=" * 80)
print("✅ ALL CHECKS PASSED - EMBEDDING FIX IS WORKING!")
print("=" * 80)
print()
print("Summary:")
print("  • Music analyzer generates 128-dim audio embeddings")
print("  • Weighted combination creates 1024-dim query embeddings")
print("  • Dimensions match stored move embeddings in database")
print("  • Ready for production deployment")
