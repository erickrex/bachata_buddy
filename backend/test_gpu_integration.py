#!/usr/bin/env python
"""
Quick integration test for GPU functionality.
Tests that GPU code works in both GPU and CPU modes.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

def test_gpu_utils():
    """Test GPU utilities module."""
    print("Testing GPU utilities...")
    
    from services.gpu_utils import GPUConfig, get_gpu_info, check_cuda_available
    
    # Test config loading
    config = GPUConfig()
    print(f"  ✓ GPUConfig loaded: enabled={config.enabled}")
    
    # Test GPU info
    info = get_gpu_info()
    print(f"  ✓ GPU info retrieved: {len(info)} keys")
    print(f"    - CUDA available: {info.get('cuda_available', False)}")
    print(f"    - FAISS GPU available: {info.get('faiss_gpu_available', False)}")
    print(f"    - NVENC available: {info.get('nvenc_available', False)}")
    
    return True


def test_vector_search_service():
    """Test VectorSearchService with GPU support."""
    print("\nTesting VectorSearchService...")
    
    from services.vector_search_service import VectorSearchService, get_vector_search_service
    
    # Test direct instantiation (CPU mode)
    service_cpu = VectorSearchService(use_gpu=False)
    print(f"  ✓ VectorSearchService created (CPU mode)")
    print(f"    - GPU enabled: {service_cpu.use_gpu}")
    print(f"    - FAISS available: {service_cpu.use_faiss}")
    
    # Test factory function (auto-detect)
    service_auto = get_vector_search_service()
    print(f"  ✓ VectorSearchService via factory (auto-detect)")
    print(f"    - GPU enabled: {service_auto.use_gpu}")
    
    # Test cache info
    cache_info = service_cpu.get_cache_info()
    print(f"  ✓ Cache info retrieved: {cache_info.get('cached', False)}")
    
    # Test GPU info method
    if hasattr(service_cpu, 'get_gpu_info'):
        gpu_info = service_cpu.get_gpu_info()
        print(f"  ✓ GPU info method works: {gpu_info.get('gpu_enabled', False)}")
    
    return True


def test_settings_integration():
    """Test Django settings GPU configuration."""
    print("\nTesting Django settings...")
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
    import django
    django.setup()
    
    from django.conf import settings
    
    # Check GPU settings exist
    assert hasattr(settings, 'USE_GPU'), "USE_GPU not in settings"
    assert hasattr(settings, 'FAISS_USE_GPU'), "FAISS_USE_GPU not in settings"
    assert hasattr(settings, 'GPU_MEMORY_FRACTION'), "GPU_MEMORY_FRACTION not in settings"
    
    print(f"  ✓ GPU settings loaded")
    print(f"    - USE_GPU: {settings.USE_GPU}")
    print(f"    - FAISS_USE_GPU: {settings.FAISS_USE_GPU}")
    print(f"    - GPU_MEMORY_FRACTION: {settings.GPU_MEMORY_FRACTION}")
    
    return True


def test_backward_compatibility():
    """Test that existing code still works."""
    print("\nTesting backward compatibility...")
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
    import django
    django.setup()
    
    from services.vector_search_service import get_vector_search_service
    
    # Test that we can get a service without GPU
    service = get_vector_search_service(use_gpu=False)
    print(f"  ✓ Service works in CPU mode")
    
    # Test that combine_embeddings_weighted still works
    import numpy as np
    from services.vector_search_service import VectorSearchService
    
    pose_emb = np.random.randn(512).astype(np.float32)
    audio_emb = np.random.randn(128).astype(np.float32)
    text_emb = np.random.randn(384).astype(np.float32)
    
    combined = VectorSearchService.combine_embeddings_weighted(
        pose_emb, audio_emb, text_emb
    )
    
    expected_dim = 512 + 128 + 384
    assert combined.shape[0] == expected_dim, f"Expected {expected_dim}, got {combined.shape[0]}"
    print(f"  ✓ combine_embeddings_weighted works: {combined.shape}")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("GPU Integration Tests")
    print("=" * 60)
    
    tests = [
        ("GPU Utilities", test_gpu_utils),
        ("VectorSearchService", test_vector_search_service),
        ("Django Settings", test_settings_integration),
        ("Backward Compatibility", test_backward_compatibility),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✓ {name} PASSED")
        except Exception as e:
            failed += 1
            print(f"\n✗ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
