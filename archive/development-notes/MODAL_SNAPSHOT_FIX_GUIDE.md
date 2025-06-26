# Modal Memory Snapshot Fix Guide

## Current Issue
- **Problem**: 26.78s cold start (should be 4-6s)
- **Root Cause**: Memory snapshots not properly configured
- **Solution**: Implement proper snapshot-enabled model loading

## Quick Fix Steps

### 1. Deploy the Fixed Version

```bash
# Deploy the new optimized endpoint
modal deploy scripts/modal_web_endpoint_fixed.py

# Watch the logs during first deployment
# You should see: "Creating memory snapshot..."
```

### 2. Verify Snapshots Are Working

**First Deploy (Creating Snapshot):**
```
🔄 Loading model in snapshot context...
✅ Model loaded from cache
🖥️  Moving model to GPU: NVIDIA A10
✅ GPU warmup complete
✅ Model loaded and moved to GPU in X.XXs
📸 Creating memory snapshot...  ← LOOK FOR THIS
```

**Subsequent Cold Starts (Using Snapshot):**
```
Using memory snapshot...  ← LOOK FOR THIS
```

### 3. Test Cold Start Performance

```bash
# Wait 10+ minutes for container to scale down
# Then test cold start:
curl -X POST https://podinsighthq--podinsight-embeddings-fixed-embedding-model-generate-embedding.modal.run \
  -H "Content-Type: application/json" \
  -d '{"text": "test cold start with snapshots"}'
```

## Key Changes Made

### 1. Proper Class-Based Structure
```python
@app.cls(
    enable_memory_snapshot=True,  # ✅ Enabled
)
class EmbeddingModel:
    @modal.enter(snap=True)  # ✅ Critical flag
    def load_model(self):
        # Model loading and GPU setup here
```

### 2. Model Weights Baked into Image
```python
image = (
    modal.Image.debian_slim()
    .pip_install(...)
    .run_commands(
        "python -c \"from sentence_transformers import SentenceTransformer; "
        "model = SentenceTransformer('hkunlp/instructor-xl')\""
    )
)
```

### 3. Cold Start Telemetry
```python
is_cold = getattr(modal, 'is_cold_start', lambda: None)()
if is_cold is not None:
    logger.info(f"cold={is_cold}, dur={time.time()-start:.3f}s")
```

## Expected Performance After Fix

| Phase | Time | What Happens |
|-------|------|--------------|
| Container spin-up | ~1s | Modal starts container |
| Restore snapshot | 1-2s | CPU weights restored |
| Transfer to GPU | 2s | Weights → GPU memory |
| **Total Cold Start** | **4-6s** | Ready to serve |

## Monitoring Commands

```bash
# Check logs for snapshot messages
modal logs podinsight-embeddings-fixed

# Monitor cold start times
python scripts/test_modal_production.py

# Check container status
modal app list
```

## If Snapshots Still Don't Work

1. **Check GPU Memory Usage**
   - Snapshots skip if >8GB GPU memory used
   - Instructor-XL uses ~3GB, so should be fine

2. **Disable and Re-enable**
   ```python
   enable_memory_snapshot=False  # Deploy once
   enable_memory_snapshot=True   # Deploy again
   ```

3. **Contact Modal Support**
   - If cold start improvement <20%
   - Provide logs showing missing snapshot messages

## Cost Impact

- **Before**: 26s × $0.000306/s = $0.008 per cold start
- **After**: 5s × $0.000306/s = $0.0015 per cold start
- **Savings**: 80% reduction in cold start costs

## Next Steps

1. Deploy `modal_web_endpoint_fixed.py`
2. Monitor logs for "Creating memory snapshot..."
3. Test cold start after 10+ minute idle
4. Report new cold start time to advisor
5. Update board deck with confirmed 4-6s cold starts
