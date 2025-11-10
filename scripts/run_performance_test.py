#!/usr/bin/env python
"""
Simple performance test runner that saves results incrementally.
"""

import sys
import os
import time
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django - Use backend API settings
import sys
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
import django
django.setup()

def test_imports():
    """Test import times."""
    results = {}
    
    modules = [
        "video_processing.services.video_generator",
        "video_processing.services.video_storage_service",
        "ai_services.services.elasticsearch_service",
        "ai_services.services.text_embedding_service",
        "common.config.environment_config",
    ]
    
    for module in modules:
        # Clear from cache
        if module in sys.modules:
            del sys.modules[module]
        
        start = time.perf_counter()
        __import__(module)
        end = time.perf_counter()
        
        results[module] = (end - start) * 1000  # ms
        print(f"✓ {module}: {results[module]:.3f}ms")
    
    return results

def test_initialization():
    """Test service initialization."""
    results = {}
    
    # VideoGenerator
    print("\nTesting VideoGenerator initialization...")
    from video_processing.services.video_generator import VideoGenerator
    from video_processing.models.video_models import VideoGenerationConfig
    
    start = time.perf_counter()
    config = VideoGenerationConfig(output_path="data/temp/test.mp4")
    generator = VideoGenerator(config)
    end = time.perf_counter()
    
    results["VideoGenerator"] = (end - start) * 1000
    print(f"✓ VideoGenerator: {results['VideoGenerator']:.3f}ms")
    
    return results

def main():
    """Run performance tests."""
    print("=" * 60)
    print("Performance Test - Core App Refactoring")
    print("=" * 60)
    
    all_results = {
        "imports": {},
        "initialization": {}
    }
    
    print("\n### Import Tests ###")
    all_results["imports"] = test_imports()
    
    print("\n### Initialization Tests ###")
    all_results["initialization"] = test_initialization()
    
    # Save results
    output_file = project_root / "performance_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    
    # Print summary
    print("\n### Summary ###")
    avg_import = sum(all_results["imports"].values()) / len(all_results["imports"])
    print(f"Average import time: {avg_import:.3f}ms")
    
    print("\n✓ All tests completed successfully")

if __name__ == "__main__":
    main()
