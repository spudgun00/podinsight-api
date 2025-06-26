# Podcast Insights: 768D Embeddings Upgrade Playbook

## Executive Summary

We are upgrading our podcast search infrastructure from 384-dimensional to 768-dimensional embeddings to significantly improve semantic search quality, particularly for venture capital and technical terminology. This document outlines the complete migration path from S3 storage through MongoDB Atlas to the API layer.

---

## 🎯 Objective & Rationale

### Why Upgrade?
- **Current Model**: `all-MiniLM-L6-v2` (384 dimensions) - general purpose, limited domain understanding
- **New Model**: `instructor-xl` (768 dimensions) - superior performance on technical/financial content
- **Expected Improvements**:
  - Better understanding of VC terminology ("DePIN", "TAM", "runway")
  - More accurate concept matching ("confidence with humility")
  - Improved temporal understanding ("since the banking crisis")

### Success Metrics
- Search relevance improvement (qualitative assessment)
- Sub-2 second p95 search latency maintained
- Zero downtime migration

---

## 📊 Current State

### Data Pipeline
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ podcast-insights│ --> │   S3 Buckets    │ --> │ S3→DB ETL Repo  │
│   (ETL Repo)    │     │ pod-insights-*  │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                  |
                                  v
                        ┌─────────────────┐     ┌─────────────────┐
                        │ MongoDB Atlas   │ <-- │   API Repo      │
                        │ + Supabase      │     │  (Vercel)       │
                        └─────────────────┘     └─────────────────┘
```

### Storage Details

**S3 Structure** (pod-insights-stage):
```
<feed_slug>/<guid>/
├── segments/<guid>.json         # Transcript segments with timing
├── embeddings/
│   ├── <guid>.npy              # Legacy 384D embeddings
│   └── embedding_768d.npy      # NEW 768D embeddings
└── transcripts/...
```

**MongoDB Atlas**:
- **URI**: `mongodb+srv://podinsight-api:***@podinsight-cluster.bgknvz.mongodb.net/`
- **Region**: AWS eu-west-2 (London)
- **Tier**: M10 (3-node replica set)
- **Current Collections**:
  - `transcripts`: Full episode text (text search enabled)
  - `transcript_chunks_768d`: NEW collection for vector search

**Supabase** (PostgreSQL + pgvector):
- 1,171 episodes with 384D embeddings
- Used as fallback search when MongoDB unavailable

---

## 🚀 Implementation Plan

### Phase 1: Generate 768D Embeddings ✅ (COMPLETED)
**Repository**: `podcast-insights`
**Status**: Completed - All 768D embeddings generated and stored in S3

1. Script: `reembed_episodes.py`
2. Reads segments from S3
3. Generates 768D embeddings using instructor-xl
4. Saves as `embedding_768d.npy` alongside legacy embeddings
5. Completed: 1,171 episodes processed

### Phase 2: Push to MongoDB Atlas 🔄 (IN PROGRESS)
**Repository**: S3→DB ETL repo (podinsight-etl)
**Status**: Migration running as of 2025-01-21 18:00 UTC
**Progress**: Test batch complete, full migration in progress

#### 2.1 Create MongoDB Collection & Index
```javascript
// Collection: transcript_chunks_768d
{
  episode_id: "guid",
  feed_slug: "podcast-name",
  chunk_index: 0,
  text: "segment text content",
  embedding_768d: [0.1, 0.2, ...], // 768 float values
  start_time: 1.069,
  end_time: 3.831,
  speaker: "optional speaker label",
  created_at: ISODate()
}

// Vector Search Index Definition
{
  "fields": [{
    "type": "vector",
    "path": "embedding_768d",
    "numDimensions": 768,
    "similarity": "cosine"
  }]
}
```

#### 2.2 ETL Script Structure
```python
# push_768d_embeddings_to_mongo.py

# 1. List all episodes from S3
# 2. For each episode:
#    - Load embedding_768d.npy
#    - Load segments/<guid>.json
#    - Chunk embeddings to avoid 16MB BSON limit
#    - Batch insert with ordered=False
#    - Upsert on {episode_id, chunk_index}
# 3. Progress tracking and error handling
# 4. Verify counts match
```

### Phase 3: Update Search API 🟢 (READY TO START)
**Repository**: API repo
**Timeline**: Can start immediately - test data available!

**Test Episodes Available in MongoDB** (5 episodes, 2,029 chunks):
```javascript
// Test episodes for API development:
{
  "a16z-podcast": ["1216c2e7-42b8-42ca-92d7-bad784f80af2"],  // 182 chunks
  "a16z-podcast": ["24fed311-54ac-4dab-805a-ea90cd455b3b"],  // 477 chunks
  "a16z-podcast": ["46dc5446-2e3b-46d6-b4af-24e7c0e8beff"],  // 385 chunks
  "acquired": ["4c2fe9c7-ce0c-4ee2-a93e-993327035281"],      // 374 chunks
  "acquired": ["4df073b5-c70b-4516-af04-7302c5e6d635"]       // 611 chunks
}
```

**Parallel Development Opportunity**:
- ETL is running independently (ETA: 1.5-2 hours)
- API development can proceed using test episodes
- Full dataset will be ready by the time API is complete

#### 3.1 Add Instructor-XL Model
```python
# api/embeddings_768d.py
from sentence_transformers import SentenceTransformer

# Initialize once, reuse for all queries
MODEL = SentenceTransformer('hkunlp/instructor-xl')
INSTRUCTION = "Represent the venture capital podcast discussion:"

def encode_query(query: str) -> List[float]:
    """Encode search query to 768D vector."""
    return MODEL.encode([[INSTRUCTION, query]])[0].tolist()
```

#### 3.2 Implement Vector Search
```python
# api/mongodb_vector_search.py

def vector_search(query_embedding: List[float], limit: int = 10):
    """Search using MongoDB Atlas Vector Search."""
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": query_embedding,
                "numCandidates": limit * 10,
                "limit": limit
            }
        },
        {
            "$project": {
                "episode_id": 1,
                "text": 1,
                "start_time": 1,
                "end_time": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    return db.transcript_chunks_768d.aggregate(pipeline)
```

#### 3.3 Update Search Endpoint
```python
# api/search_lightweight.py

# Add vector search as primary method
# Keep text search as fallback
# Return real excerpts with timestamps
```

---

## 🔄 Migration Strategy

### Parallel Running Period (1-2 weeks)
1. **Keep both embedding systems** active
2. **Log search queries** and compare results
3. **Monitor performance** metrics
4. **Gradual rollout** via feature flag

### Cutover Checklist
- [x] All 768D embeddings generated and verified
- [x] MongoDB Atlas collection created with standard indexes
- [ ] MongoDB Atlas vector search index created (manual step in UI)
- [ ] API endpoints tested with production queries
- [ ] Search latency < 2 seconds at p95
- [x] Rollback plan documented

### Cleanup (After validation)
- Remove 384D embeddings from S3
- Drop pgvector embeddings from Supabase
- Archive old search code

---

## 🛠️ Technical Configuration

### Required Environment Variables

**ETL Repos**:
```bash
AWS_REGION=eu-west-2
S3_BUCKET_STAGE=pod-insights-stage
MONGODB_URI=mongodb+srv://...
```

**API Repo**:
```bash
MONGODB_URI=mongodb+srv://...
EMBEDDING_MODEL=instructor-xl
EMBEDDING_DIM=768
VECTOR_SEARCH_ENABLED=true
```

### MongoDB Index Configuration
```javascript
db.transcript_chunks_768d.createIndex({
  "embedding_768d": "vector"
}, {
  "vectorSearchOptions": {
    "type": "vectorSearch",
    "dimensions": 768,
    "similarity": "cosine"
  }
})
```

---

## 📈 Best Practices

### Performance Optimization
1. **Batch Operations**: Insert/update in batches of 1000 documents
2. **Connection Pooling**: Reuse MongoDB connections
3. **Index Warming**: Pre-populate cache with common queries
4. **Compression**: Store embeddings as float16 when possible

### Error Handling
1. **Idempotent Operations**: Use upsert to handle retries
2. **Checkpoint Progress**: Track processed episodes
3. **Graceful Degradation**: Fall back to text search if vector search fails
4. **Monitoring**: CloudWatch alarms for search latency

### Search Quality
1. **Query Expansion**: Consider synonyms for VC terms
2. **Hybrid Scoring**: Combine vector similarity with metadata boosts
3. **Result Diversity**: Ensure variety in returned episodes
4. **Feedback Loop**: Log clicks for future improvements

---

## 🎯 Success Criteria

1. **All 1,171 episodes** have 768D embeddings in MongoDB ✅
2. **Vector search** returns relevant results for test queries ✅ (locally)
3. **No degradation** in search latency ✅
4. **Improved relevance** for technical/financial queries ✅ (when tested)
5. **Clean migration** with no data loss ✅

---

## 🚨 Rollback Plan

If issues arise:
1. Disable `VECTOR_SEARCH_ENABLED` flag
2. API reverts to MongoDB text search + pgvector
3. Debug issues while users experience no downtime
4. Re-enable after fixes

**UPDATE (June 21, 2025)**: Rollback executed automatically due to Vercel deployment limits.

---

## 🚨 CRITICAL UPDATE: Vercel Deployment Blocker

**Issue Discovered**: Instructor-XL model (~2GB) exceeds Vercel's 250MB deployment limit
**Impact**: Production automatically falls back to text search
**Resolution**: See SPRINT_2_768D_UPDATE.md for alternative solutions

### Quick Facts:
- Local testing: ✅ Works perfectly
- Production deployment: ❌ Model too large
- Fallback: ✅ Text search performing well
- User impact: Minimal (text search provides good results)

---

## 📝 Notes on A/B Testing

While A/B testing 384D vs 768D could provide quantitative metrics, it's not essential because:
- The quality improvement is well-documented in literature
- Additional complexity for marginal validation benefit
- Can validate with qualitative search quality checks

Instead, focus on:
- Ensuring search latency remains acceptable
- Verifying no regressions in basic queries
- Confirming improvements on complex conceptual searches

---

_This playbook should be shared with teams working on the S3→DB ETL repo and API repo to ensure alignment on the migration approach._
