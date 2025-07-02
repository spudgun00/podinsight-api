# Search Timeout Improvements - Modal.com Cold Start Solutions

**Date**: June 30, 2025
**Issue**: Modal.com embedding service takes 25+ seconds on cold start, causing Vercel 30-second timeouts
**Impact**: Search requests randomly fail, poor user experience

## Quick Summary

The search API times out because generating embeddings through Modal.com can take 25+ seconds on cold start. Since always-on Modal is too expensive, we need smart workarounds.

---

## Solution 1: Query Embedding Cache 🎯 (RECOMMENDED - Start Here)

### What It Is
Cache the embedding vectors for common search queries in MongoDB or Redis.

### Why It's Good
- **80/20 Rule**: Most searches are repeated - "venture capital", "AI", "crypto" etc.
- **Instant Results**: Cache hits return in <50ms
- **Zero Additional Cost**: Uses existing infrastructure

### Implementation
```python
# In search_lightweight_768d.py
cache_key = f"embed:{hashlib.sha256(query.encode()).hexdigest()}"
cached_embedding = mongodb.embeddings_cache.find_one({"_id": cache_key})
if cached_embedding:
    return cached_embedding["vector"]  # Instant!
```

### Complexity: ⭐⭐ (Low)
### Time: 2-4 hours
### Cost: $0

---

## Solution 2: Budget Modal Pre-warming ⏰

### What It Is
Ping Modal during business hours only (9am-5pm) to keep containers warm.

### Why It's Good
- **Smart Timing**: Only warm when users are active
- **80% Reduction**: Cold starts drop from 25s to 2-3s
- **Budget Friendly**: Much cheaper than always-on

### Implementation
```python
# Vercel cron job - runs every 10 minutes during business hours
# vercel.json
{
  "crons": [{
    "path": "/api/warm-modal",
    "schedule": "*/10 9-17 * * MON-FRI"
  }]
}
```

### Complexity: ⭐⭐ (Low)
### Time: 2-3 hours
### Cost: ~$5-10/month

---

## Solution 3: Hybrid Search with Fallback 🔄

### What It Is
Try embedding search for 5 seconds, then fallback to MongoDB text search.

### Why It's Good
- **Never Fails**: Users always get results
- **Best Effort**: Semantic search when possible, text search as backup
- **No Frontend Changes**: Drop-in replacement

### Implementation
```python
async def search_with_fallback(query):
    try:
        # Try embedding search with timeout
        embedding = await asyncio.wait_for(
            get_embedding(query),
            timeout=5.0
        )
        return vector_search(embedding)
    except asyncio.TimeoutError:
        # Fallback to text search
        logger.warning(f"Embedding timeout, using text search: {query}")
        return text_search(query)
```

### Complexity: ⭐⭐⭐ (Medium)
### Time: 1-2 days
### Cost: $0

---

## Solution 4: Local Embeddings 🏠

### What It Is
Run a smaller embedding model directly in the Vercel function.

### Why It's Good
- **No External Calls**: Everything runs locally
- **No Cold Starts**: Model loads with function
- **Predictable**: Consistent 200-300ms performance

### Trade-offs
- **Lower Quality**: all-MiniLM-L6-v2 is good but not as good as instructor-xl
- **Memory Usage**: ~100MB model in memory
- **Different Embeddings**: Would need to re-embed all 800k documents

### Implementation
```python
from sentence_transformers import SentenceTransformer

# Load once at module level
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text):
    return model.encode(text).tolist()  # ~200ms
```

### Complexity: ⭐⭐⭐ (Medium)
### Time: 1-2 days + migration time
### Cost: $0 (but need to re-embed everything)

---

## Solution 5: Async Search Pattern 🔀

### What It Is
Return a job ID immediately, process embedding in background, frontend polls for results.

### Why It's Good
- **Never Timeouts**: Completely eliminates the timeout problem
- **Better UX**: Can show progress, estimated time
- **Future Proof**: Handles any long-running operation

### Implementation
```python
@app.post("/api/search")
async def search(query: str, background_tasks: BackgroundTasks):
    job_id = str(uuid4())
    cache.set(job_id, {"status": "processing"})
    background_tasks.add_task(process_search, query, job_id)
    return {"job_id": job_id}

@app.get("/api/search/{job_id}")
async def get_results(job_id: str):
    return cache.get(job_id)
```

### Complexity: ⭐⭐⭐⭐ (High - needs frontend changes)
### Time: 3-5 days
### Cost: $0

---

## Solution 6: Progressive Enhancement 📈

### What It Is
Return text search immediately, enhance with semantic search when ready.

### Why It's Good
- **Instant Results**: Users see something immediately
- **Progressive**: Results improve as embeddings complete
- **Best UX**: Fast initial response + accurate final results

### Implementation
- Return text search results with flag `enhanced: false`
- Process embeddings in background
- Update results via WebSocket/SSE when ready
- Frontend shows "Enhancing results..." indicator

### Complexity: ⭐⭐⭐⭐ (High - needs real-time updates)
### Time: 2-3 days
### Cost: $0

---

## Recommended Implementation Order

### Phase 1: Quick Wins (This Week)
1. **Query Caching** - 4 hours, huge impact
2. **Budget Pre-warming** - 3 hours, reduces most timeouts

### Phase 2: Reliability (Next Week)
3. **Hybrid Fallback** - 2 days, ensures no failures

### Phase 3: Long-term (If Needed)
4. Choose between:
   - **Async Pattern** (if you want perfect reliability)
   - **Local Embeddings** (if you want to drop Modal entirely)
   - **Progressive Enhancement** (if you want best UX)

---

## Decision Matrix

| Solution | Dev Time | Complexity | Cost/Month | User Experience | Reliability |
|----------|----------|------------|------------|-----------------|-------------|
| Cache | 4 hours | Low | $0 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Pre-warm | 3 hours | Low | $5-10 | ⭐⭐⭐ | ⭐⭐⭐ |
| Hybrid | 2 days | Medium | $0 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Local | 2 days | Medium | $0 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Async | 5 days | High | $0 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Progressive | 3 days | High | $0 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Next Steps

1. Start with **Query Caching** - biggest bang for buck
2. Add **Budget Pre-warming** for peak hours
3. Implement **Hybrid Fallback** for reliability
4. Evaluate if further improvements needed based on user feedback

The combination of caching + pre-warming + fallback should eliminate 95%+ of timeout issues without breaking the bank.
