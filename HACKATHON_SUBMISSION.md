# Bachata Buddy - Your AI Dance Teacher
## Cloud Run GPU Hackathon Submission

**Live Demo:** https://bachata-buddy-gpu.web.app  
**Category:** GPU Acceleration  
**Tech Stack:** NVIDIA L4 GPU, Cloud Run, Multimodal Embeddings (FAISS), FFmpeg NVENC

---

## 💡 The Problem I'm Solving

I love dancing bachata. But learning is hard—instructors teach at their pace, not mine. As a beginner, I needed slower breakdowns. As I improved, I craved more complex patterns. Generic YouTube tutorials don't adapt to your level.

**What I needed:** A personal instructor who understands my skill level and creates custom routines just for me.

**The technical challenge:** Generating personalized dance videos requires:
1. **Multimodal embeddings** - matching dance moves to music beats, energy, and difficulty
2. **Heavy video processing** - assembling 50+ clips into seamless choreography

On CPU, this takes 150 seconds. Too slow to feel like a real learning tool.

---

## 🎯 The Solution

Describe your dream routine in plain English: *"I want a romantic bachata with lots of turns for beginners"*

Get a custom video in **25 seconds** (6x faster than CPU).

**How it works:**
1. AI understands your skill level and preferences
2. Multimodal embeddings match dance moves to music
3. GPU-accelerated video assembly creates your personalized routine
4. Practice with loop controls and variable speed playback

---

## 🛠️ The Tech: Why NVIDIA L4 GPUs Changed Everything

### The Two GPU Workloads

**1. Multimodal Embeddings with FAISS GPU (11x faster)**

The core challenge: match dance moves to music based on:
- Audio features (beats, energy, tempo)
- Move difficulty (beginner vs advanced)
- Style preferences (romantic vs energetic)
- Semantic meaning ("lots of turns", "body rolls")

I embed 10,000+ dance moves into a vector space where similar moves cluster together. Finding the right 50 moves for your routine requires searching this massive space.

```python
# CPU: 500ms per search → Too slow for real-time
# GPU: 45ms per search → Fast enough!

gpu_resources = faiss.StandardGpuResources()
gpu_index = faiss.index_cpu_to_gpu(gpu_resources, 0, cpu_index)
distances, indices = gpu_index.search(query_embedding, k=50)
```

**Why L4 matters:** FAISS GPU leverages tensor cores for parallel similarity computations. What took half a second on CPU now takes 45ms—enabling instant choreography matching.

**2. FFmpeg NVENC for Heavy Video Workloads (6.7x faster)**

The brutal reality: assembling 50+ video clips into a seamless routine is computationally expensive.

- Normalize frame rates across clips
- Concatenate without visible seams
- Mix audio tracks
- Encode final output

CPU encoding with libx264: **120 seconds**  
GPU encoding with NVENC: **18 seconds**

```python
ffmpeg_cmd = [
    'ffmpeg',
    '-hwaccel', 'cuda',                    # GPU decode
    '-hwaccel_output_format', 'cuda',      # Keep frames on GPU
    '-i', video_file,
    '-c:v', 'h264_nvenc',                  # Hardware encode
    '-preset', 'p4',                       # Speed/quality balance
    output_file
]
```

**Why NVENC matters:** Dedicated hardware encoder on L4 GPU handles video encoding without touching the CPU. Frames stay in GPU memory—no expensive CPU↔GPU transfers.

### The Pipeline

```
User Query → AI Parse → FAISS GPU Search (45ms) → Blueprint
                                ↓
                        FFmpeg NVENC Assembly (18s)
                                ↓
                        Custom Video (25s total)
```

**Stack:**
- Cloud Run + NVIDIA L4 GPU (serverless, scales to zero)
- FAISS GPU 1.7.4 (multimodal embeddings)
- FFmpeg with NVENC (hardware video encoding)
- CUDA 12.2 runtime

---

## 🚧 Challenges

**1. NVENC Quality vs Speed**  
Fast presets (p7) created blocky artifacts in dance videos. Found the sweet spot: preset p4 maintains visual quality (PSNR > 40dB) while achieving 6.7x speedup.

**2. GPU Memory Management**  
FAISS index + FFmpeg buffers = OOM errors. Solution: `StandardGpuResources` for shared memory allocation and aggressive cleanup after operations.

**3. FAISS Index Transfer Overhead**  
Transferring 10,000 embeddings to GPU took 2 seconds. Solution: pre-build GPU index at container startup, keep in memory across requests.

**4. Video Sync Issues**  
Audio/video drift when concatenating GPU-encoded clips. Solution: normalize to 30fps with `-vsync cfr` and `-af aresample=async=1` for audio sync.

---

## 🏆 Results

**Performance:**
| Component | CPU | GPU (L4) | Speedup |
|-----------|-----|----------|---------|
| Multimodal Search (FAISS) | 500ms | 45ms | **11x** |
| Video Assembly (NVENC) | 120s | 18s | **6.7x** |
| **End-to-End** | **150s** | **25s** | **6x** |

**Impact:**
- 150s → 25s makes this feel like a real-time tool, not a batch job
- GPU cost: +2% per request ($0.00005) for 6x speedup = 300% ROI
- Serverless GPU on Cloud Run = zero infrastructure management

**What I Built:**
- Natural language interface (no dance terminology needed)
- Smart video player with loop controls for practice
- Production-ready with CPU fallback and error handling

---

## 📚 What I Learned

**GPU Programming:**
- Memory management is everything—pre-load FAISS index, minimize CPU↔GPU transfers
- NVENC preset matters more than I expected—p4 is the sweet spot for quality vs speed
- Serverless GPU on Cloud Run eliminates infrastructure headaches (no Kubernetes, no driver management)

**Product:**
- 150s → 25s isn't just faster, it's a different product. Users experiment more when results feel instant.
- Dancers care more about loop controls than I expected—practicing specific sections is the killer feature.
- Natural language beats technical parameters every time.

---

## 🚀 What's Next

**More dance styles:** Salsa, Merengue, Kizomba with 50,000+ move database

**AI form feedback:** Use phone camera + GPU-accelerated pose estimation for real-time technique analysis

**Music integration:** Generate choreography for any Spotify song with automatic beat detection

---

## 🎬 Try It

**Live Demo:** https://bachata-buddy-gpu.web.app

1. Click "Describe Choreo"
2. Type: *"I want a romantic bachata with lots of turns for beginners"*
3. Watch your custom video generate in 25 seconds

---

## 🏅 Why This Matters

**Real-world impact:** Personalized dance instruction used to cost $200+ per session. Now anyone with a phone can learn at their own pace.

**Technical innovation:** Novel application of multimodal embeddings + heavy FFmpeg workloads on NVIDIA L4 GPUs. Production-ready with CPU fallback and comprehensive testing.

**Business viability:** 2% cost increase for 6x speedup = 300% ROI. Serverless GPU makes this sustainable and scalable.

---

**Built with ❤️ for dancers, powered by 💪 NVIDIA L4 GPUs on Google Cloud Run**

#CloudRunHackathon #GPUAcceleration #AIChoreography
