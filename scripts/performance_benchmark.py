#!/usr/bin/env python
"""
Performance Benchmark Script for Core App Refactoring

This script benchmarks key operations to ensure the refactoring
from core.services to new app structure doesn't degrade performance.

Tests:
1. Import time for key services
2. Service initialization time
3. Key operation execution time
4. Memory usage during operations

Requirements: Non-functional requirement 3 (no performance degradation)
"""

import sys
import os
import time
import json
import tracemalloc
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
import statistics

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


class PerformanceBenchmark:
    """Benchmark runner for performance testing."""
    
    def __init__(self, output_file: str = "performance_benchmark_results.json"):
        self.output_file = output_file
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": {},
            "summary": {}
        }
    
    def measure_import_time(self, module_path: str, iterations: int = 10) -> Dict[str, float]:
        """
        Measure time to import a module.
        
        Args:
            module_path: Full module path (e.g., 'video_processing.services.video_generator')
            iterations: Number of times to measure
            
        Returns:
            Dict with timing statistics
        """
        times = []
        
        for _ in range(iterations):
            # Clear module from cache
            if module_path in sys.modules:
                del sys.modules[module_path]
            
            start = time.perf_counter()
            __import__(module_path)
            end = time.perf_counter()
            
            times.append((end - start) * 1000)  # Convert to ms
        
        return {
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def measure_initialization_time(
        self, 
        factory: Callable, 
        iterations: int = 10
    ) -> Dict[str, float]:
        """
        Measure time to initialize a service.
        
        Args:
            factory: Callable that creates the service instance
            iterations: Number of times to measure
            
        Returns:
            Dict with timing statistics
        """
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                instance = factory()
                end = time.perf_counter()
                times.append((end - start) * 1000)  # Convert to ms
            except Exception as e:
                print(f"Warning: Initialization failed: {e}")
                continue
        
        if not times:
            return {"error": "All initialization attempts failed"}
        
        return {
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def measure_operation_time(
        self, 
        operation: Callable, 
        iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Measure time and memory for an operation.
        
        Args:
            operation: Callable that performs the operation
            iterations: Number of times to measure
            
        Returns:
            Dict with timing and memory statistics
        """
        times = []
        memory_peaks = []
        
        for _ in range(iterations):
            tracemalloc.start()
            
            start = time.perf_counter()
            try:
                result = operation()
                end = time.perf_counter()
                
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                times.append((end - start) * 1000)  # Convert to ms
                memory_peaks.append(peak / 1024 / 1024)  # Convert to MB
            except Exception as e:
                tracemalloc.stop()
                print(f"Warning: Operation failed: {e}")
                continue
        
        if not times:
            return {"error": "All operation attempts failed"}
        
        return {
            "time": {
                "mean_ms": statistics.mean(times),
                "median_ms": statistics.median(times),
                "min_ms": min(times),
                "max_ms": max(times),
                "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0
            },
            "memory": {
                "mean_mb": statistics.mean(memory_peaks),
                "median_mb": statistics.median(memory_peaks),
                "max_mb": max(memory_peaks)
            }
        }
    
    def run_import_benchmarks(self):
        """Benchmark import times for key modules."""
        print("\n=== Import Time Benchmarks ===")
        
        modules = [
            "video_processing.services.video_generator",
            "video_processing.services.video_storage_service",
            "ai_services.services.elasticsearch_service",
            "ai_services.services.text_embedding_service",
            "ai_services.services.gemini_service",
            "common.config.environment_config",
            "common.exceptions",
        ]
        
        for module in modules:
            print(f"Benchmarking import: {module}")
            try:
                result = self.measure_import_time(module)
                self.results["benchmarks"][f"import_{module}"] = result
                print(f"  Mean: {result['mean_ms']:.3f}ms, Median: {result['median_ms']:.3f}ms")
            except Exception as e:
                print(f"  Error: {e}")
                self.results["benchmarks"][f"import_{module}"] = {"error": str(e)}
    
    def run_initialization_benchmarks(self):
        """Benchmark service initialization times."""
        print("\n=== Service Initialization Benchmarks ===")
        
        # Video Generator
        print("Benchmarking VideoGenerator initialization")
        try:
            from video_processing.services.video_generator import VideoGenerator
            from video_processing.models.video_models import VideoGenerationConfig
            
            def create_video_generator():
                config = VideoGenerationConfig(output_path="data/temp/benchmark_test.mp4")
                return VideoGenerator(config)
            
            result = self.measure_initialization_time(create_video_generator)
            self.results["benchmarks"]["init_video_generator"] = result
            print(f"  Mean: {result.get('mean_ms', 'N/A'):.3f}ms")
        except Exception as e:
            print(f"  Error: {e}")
            self.results["benchmarks"]["init_video_generator"] = {"error": str(e)}
        
        # Text Embedding Service
        print("Benchmarking TextEmbeddingService initialization")
        try:
            from ai_services.services.text_embedding_service import TextEmbeddingService
            
            def create_text_embedding_service():
                return TextEmbeddingService()
            
            result = self.measure_initialization_time(create_text_embedding_service, iterations=3)
            self.results["benchmarks"]["init_text_embedding_service"] = result
            print(f"  Mean: {result.get('mean_ms', 'N/A'):.3f}ms")
        except Exception as e:
            print(f"  Error: {e}")
            self.results["benchmarks"]["init_text_embedding_service"] = {"error": str(e)}
    
    def run_operation_benchmarks(self):
        """Benchmark key operations."""
        print("\n=== Operation Benchmarks ===")
        
        # Test text embedding generation
        print("Benchmarking text embedding generation")
        try:
            from ai_services.services.text_embedding_service import TextEmbeddingService
            
            service = TextEmbeddingService()
            
            def generate_embedding():
                text = "Basic step with hip movement and arm styling"
                return service.generate_embedding(text)
            
            result = self.measure_operation_time(generate_embedding)
            self.results["benchmarks"]["op_text_embedding"] = result
            if "time" in result:
                print(f"  Mean: {result['time']['mean_ms']:.3f}ms, Memory: {result['memory']['mean_mb']:.2f}MB")
        except Exception as e:
            print(f"  Error: {e}")
            self.results["benchmarks"]["op_text_embedding"] = {"error": str(e)}
        
        # Test environment config loading
        print("Benchmarking environment config loading")
        try:
            from common.config.environment_config import EnvironmentConfig
            
            def load_config():
                return EnvironmentConfig()
            
            result = self.measure_operation_time(load_config, iterations=10)
            self.results["benchmarks"]["op_env_config_load"] = result
            if "time" in result:
                print(f"  Mean: {result['time']['mean_ms']:.3f}ms")
        except Exception as e:
            print(f"  Error: {e}")
            self.results["benchmarks"]["op_env_config_load"] = {"error": str(e)}
    
    def generate_summary(self):
        """Generate summary statistics."""
        print("\n=== Generating Summary ===")
        
        # Count successful vs failed benchmarks
        total = len(self.results["benchmarks"])
        failed = sum(1 for v in self.results["benchmarks"].values() if "error" in v)
        successful = total - failed
        
        self.results["summary"] = {
            "total_benchmarks": total,
            "successful": successful,
            "failed": failed,
            "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%"
        }
        
        # Calculate average import time
        import_times = [
            v["mean_ms"] for k, v in self.results["benchmarks"].items()
            if k.startswith("import_") and "mean_ms" in v
        ]
        if import_times:
            self.results["summary"]["avg_import_time_ms"] = statistics.mean(import_times)
        
        # Calculate average initialization time
        init_times = [
            v["mean_ms"] for k, v in self.results["benchmarks"].items()
            if k.startswith("init_") and "mean_ms" in v
        ]
        if init_times:
            self.results["summary"]["avg_init_time_ms"] = statistics.mean(init_times)
        
        print(f"Total benchmarks: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {self.results['summary']['success_rate']}")
    
    def save_results(self):
        """Save results to JSON file."""
        try:
            output_path = project_root / self.output_file
            with open(output_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n=== Results saved to {output_path} ===")
        except Exception as e:
            print(f"\n=== Error saving results: {e} ===")
            # Try to save to a backup location
            try:
                backup_path = Path("/tmp") / self.output_file
                with open(backup_path, 'w') as f:
                    json.dump(self.results, f, indent=2)
                print(f"Results saved to backup location: {backup_path}")
            except Exception as e2:
                print(f"Failed to save to backup: {e2}")
    
    def compare_with_baseline(self, baseline_file: str):
        """
        Compare current results with baseline.
        
        Args:
            baseline_file: Path to baseline results JSON
        """
        baseline_path = project_root / baseline_file
        if not baseline_path.exists():
            print(f"\nNo baseline file found at {baseline_path}")
            print("Current results will serve as baseline for future comparisons")
            return
        
        print("\n=== Comparing with Baseline ===")
        
        with open(baseline_path, 'r') as f:
            baseline = json.load(f)
        
        comparisons = []
        
        for key, current in self.results["benchmarks"].items():
            if key not in baseline["benchmarks"]:
                continue
            
            baseline_val = baseline["benchmarks"][key]
            
            # Compare mean times
            if "mean_ms" in current and "mean_ms" in baseline_val:
                current_time = current["mean_ms"]
                baseline_time = baseline_val["mean_ms"]
                diff_pct = ((current_time - baseline_time) / baseline_time) * 100
                
                status = "✓" if diff_pct <= 5 else "⚠" if diff_pct <= 10 else "✗"
                
                comparisons.append({
                    "benchmark": key,
                    "baseline_ms": baseline_time,
                    "current_ms": current_time,
                    "diff_pct": diff_pct,
                    "status": status
                })
                
                print(f"{status} {key}: {current_time:.3f}ms (baseline: {baseline_time:.3f}ms, {diff_pct:+.1f}%)")
        
        # Add comparison summary
        if comparisons:
            degraded = sum(1 for c in comparisons if c["diff_pct"] > 10)
            warning = sum(1 for c in comparisons if 5 < c["diff_pct"] <= 10)
            good = sum(1 for c in comparisons if c["diff_pct"] <= 5)
            
            self.results["comparison"] = {
                "baseline_file": baseline_file,
                "total_compared": len(comparisons),
                "good": good,
                "warning": warning,
                "degraded": degraded,
                "comparisons": comparisons
            }
            
            print(f"\nComparison Summary:")
            print(f"  Good (≤5% change): {good}")
            print(f"  Warning (5-10% slower): {warning}")
            print(f"  Degraded (>10% slower): {degraded}")
            
            if degraded > 0:
                print("\n⚠ WARNING: Performance degradation detected!")
                return False
            elif warning > 0:
                print("\n⚠ Some benchmarks show minor slowdown")
                return True
            else:
                print("\n✓ No performance degradation detected")
                return True
        
        return True
    
    def run_all(self, baseline_file: Optional[str] = None):
        """Run all benchmarks."""
        print("=" * 60)
        print("Performance Benchmark Suite")
        print("Core App Refactoring - Performance Verification")
        print("=" * 60)
        
        try:
            self.run_import_benchmarks()
            self.run_initialization_benchmarks()
            self.run_operation_benchmarks()
            self.generate_summary()
            self.save_results()
            
            if baseline_file:
                return self.compare_with_baseline(baseline_file)
            
            return True
        except Exception as e:
            print(f"\n=== Error during benchmark execution: {e} ===")
            import traceback
            traceback.print_exc()
            # Try to save partial results
            self.save_results()
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run performance benchmarks")
    parser.add_argument(
        "--baseline",
        help="Baseline results file to compare against",
        default=None
    )
    parser.add_argument(
        "--output",
        help="Output file for results",
        default="performance_benchmark_results.json"
    )
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(output_file=args.output)
    success = benchmark.run_all(baseline_file=args.baseline)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
