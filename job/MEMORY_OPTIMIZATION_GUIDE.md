# Memory Optimization Guide

## Quick Reference

This guide provides recommendations for maintaining low memory usage in the job container.

## Current Status

✅ **Memory usage: 28.89 MB peak (5.6% of 512 MB limit)**

## Best Practices

### 1. Keep Dependencies Minimal

**DO:**
- Only include dependencies needed for video assembly
- Use system packages (FFmpeg) instead of Python libraries when possible
- Rely on the API/backend for intelligence (AI, search, analysis)

**DON'T:**
- Add ML libraries (NumPy, SciPy, TensorFlow, PyTorch)
- Include web frameworks (Django, Flask)
- Add search engines (Elasticsearch)
- Include audio analysis libraries (Librosa)

### 2. Stream Data, Don't Buffer

**DO:**
- Use FFmpeg for video processing (minimal Python overhead)
- Process files in chunks when possible
- Clean up temporary files immediately after use

**DON'T:**
- Load entire videos into memory
- Keep large buffers in Python
- Cache processed data

### 3. Efficient File Handling

**DO:**
```python
# Use context managers for automatic cleanup
with open(file_path, 'rb') as f:
    process_file(f)

# Clean up temp files immediately
import shutil
shutil.rmtree(temp_dir)

# Use tempfile for automatic cleanup
import tempfile
with tempfile.TemporaryDirectory() as temp_dir:
    # Work with temp files
    pass  # Automatic cleanup
```

**DON'T:**
```python
# Don't keep file handles open
f = open(file_path, 'rb')
data = f.read()  # Entire file in memory
# ... forgot to close

# Don't accumulate temp files
for i in range(100):
    temp_file = f'/tmp/file_{i}.mp4'
    # ... never cleaned up
```

### 4. Parallel Operations

**DO:**
```python
# Limit concurrent operations
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=10) as executor:
    # Controlled parallelism
    results = executor.map(download_file, file_paths)
```

**DON'T:**
```python
# Unlimited parallelism
import threading

threads = []
for file_path in file_paths:  # Could be 1000s
    thread = threading.Thread(target=download_file, args=(file_path,))
    threads.append(thread)
    thread.start()
```

### 5. Garbage Collection

**DO:**
```python
import gc

# Force garbage collection after large operations
process_large_file()
gc.collect()

# Clear large data structures
large_list.clear()
large_dict.clear()
```

## Memory Monitoring

### During Development

```bash
# Run memory profiling test
uv run python job/test_memory_usage.py

# With detailed profiling
uv run python job/test_memory_usage.py --detailed
```

### In Production

Monitor Cloud Run Jobs metrics:
- Memory usage percentage
- Memory limit exceeded errors
- OOM (Out of Memory) kills

Set up alerts:
```yaml
# Alert if memory exceeds 400 MB (warning threshold)
condition:
  memory_usage > 400MB
```

## Troubleshooting High Memory Usage

### Symptom: Memory usage increasing over time

**Possible causes:**
1. Memory leak (objects not being garbage collected)
2. Temp files not being cleaned up
3. File handles not being closed

**Solutions:**
```python
# 1. Use weak references for caches
import weakref
cache = weakref.WeakValueDictionary()

# 2. Explicit cleanup
try:
    process_files()
finally:
    cleanup_temp_files()
    gc.collect()

# 3. Close file handles
with open(file_path) as f:
    data = f.read()
# Automatically closed
```

### Symptom: Memory spikes during video processing

**Possible causes:**
1. Loading entire video into memory
2. FFmpeg buffer size too large
3. Too many parallel operations

**Solutions:**
```python
# 1. Use FFmpeg streaming (already implemented)
# FFmpeg handles video in chunks

# 2. Reduce parallel downloads
MAX_PARALLEL_DOWNLOADS = 5  # Instead of 10

# 3. Process videos sequentially if needed
for video in videos:
    process_video(video)
    gc.collect()
```

### Symptom: OOM errors in production

**Immediate actions:**
1. Check Cloud Run Jobs logs for memory usage
2. Review recent code changes
3. Verify temp file cleanup is working

**Long-term solutions:**
1. Add memory profiling to CI/CD
2. Set up memory usage alerts
3. Review and optimize hot paths

## Memory Budget

Current allocation (512 MB total):

| Component | Memory | Percentage |
|-----------|--------|------------|
| Python runtime | ~20 MB | 4% |
| Service imports | ~7 MB | 1% |
| FFmpeg operations | ~50-100 MB | 10-20% |
| Temp files (disk) | N/A | 0% |
| **Buffer/Headroom** | **~380 MB** | **75%** |

## Testing Checklist

Before deploying changes:

- [ ] Run `test_memory_usage.py` and verify peak < 512 MB
- [ ] Check for memory leaks (stable across iterations)
- [ ] Review new dependencies (are they necessary?)
- [ ] Verify temp file cleanup
- [ ] Test with realistic video sizes
- [ ] Monitor memory in staging environment

## Related Files

- `test_memory_usage.py` - Memory profiling test
- `MEMORY_USAGE_VERIFICATION.md` - Verification results
- `src/main.py` - Main job entry point
- `src/services/video_assembler.py` - Video assembly logic
- `src/services/storage_service.py` - Storage operations

## References

- [Python Memory Management](https://docs.python.org/3/c-api/memory.html)
- [Cloud Run Jobs Memory Limits](https://cloud.google.com/run/docs/configuring/memory-limits)
- [FFmpeg Memory Usage](https://ffmpeg.org/ffmpeg.html#Main-options)
