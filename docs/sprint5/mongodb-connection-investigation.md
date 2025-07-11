# MongoDB Connection Investigation - Sprint 5

**Date**: July 11, 2025
**Issue**: Search quality degradation and MongoDB connection errors
**Status**: Partially resolved - reverted breaking changes, root cause identified

## Executive Summary

We investigated "ReplicaSetNoPrimary" errors that were causing search quality issues. After attempting to fix with a connection string change, we broke working functionality (topic velocity). We have now reverted the changes and identified the real root cause.

## Timeline of Events

### Initial State
- **Topic Velocity**: ✅ Working correctly
- **Search**: ❌ Hybrid search failing, degrading to vector-only mode
- **Error**: "ReplicaSetNoPrimary" with all nodes showing as "Unknown"

### After Connection String Change
- **Topic Velocity**: ❌ Broken (returning 0 mentions)
- **Search**: ❌ Still failing with "none_all_failed"
- **Database**: Shows as "connected" but clearly wrong cluster/database

### After Reverting (Current State)
- **Topic Velocity**: ✅ Working again
- **Search**: ❌ Still failing (but we haven't made it worse)
- **Next Steps**: Investigate the actual text search issue

## Key Findings

### 1. Misdiagnosed the Problem
- We saw "ReplicaSetNoPrimary" errors and assumed it was a connection string issue
- Reality: MongoDB connection was working fine (topic velocity proved this)
- The error was specific to the text search component of hybrid search

### 2. Connection String Formats
- **Original (working)**: `mongodb+srv://...@podinsight-cluster.bgknvz.mongodb.net/`
- **Changed to**: `mongodb://...@shard-00-00.bgknvz.mongodb.net:27017,.../`
- The change pointed to wrong cluster or had incompatible format

### 3. Real Root Cause
The text search component of hybrid search is failing, likely due to:
- Missing text index on `transcript_chunks_768d` collection
- Text search aggregation pipeline too complex for 10s timeout
- Async Motor client issues with parallel operations
- Race condition in `asyncio.gather()` for parallel searches

## Evidence

### MongoDB is Connected and Working
```bash
# Topic velocity returns data
GET /api/topic-velocity?weeks=4
# Returns: AI Agents with 8 mentions in week 24

# Health check shows connected
GET /api/health
# Shows: "database": "connected"
```

### Only Text Search Fails
From `improved_hybrid_search.py`:
```python
# These run in parallel
vector_task = self._vector_search(collection, query_vector, limit * 2)
text_task = self._text_search(collection, query_terms, limit * 2)
vector_results, text_results = await asyncio.gather(vector_task, text_task)
```

When text search fails after 10s timeout:
- Vector search succeeds (uses existing index)
- Text search returns empty results
- Hybrid search degrades to vector-only mode
- Results are semantically similar but lack keyword relevance

## Lessons Learned

1. **Don't fix what's not broken** - Verify the scope of issues before infrastructure changes
2. **Test impact thoroughly** - Check if other endpoints use the same connection
3. **Error messages can be misleading** - "ReplicaSetNoPrimary" was a symptom, not the cause
4. **Partial failures need targeted fixes** - Don't apply global solutions to local problems

## Recommended Next Steps

### Immediate Actions
1. ✅ Reverted MongoDB connection string (completed)
2. ✅ Verified topic velocity works again (completed)
3. Check for text index: `db.transcript_chunks_768d.getIndexes()`
4. Investigate text search pipeline complexity

### Short-term Fixes
1. **Increase timeout for text search**:
   ```python
   # In improved_hybrid_search.py
   serverSelectionTimeoutMS=20000,  # Increase from 10000
   ```

2. **Run searches sequentially instead of parallel**:
   ```python
   # Instead of asyncio.gather, run sequentially
   vector_results = await self._vector_search(...)
   text_results = await self._text_search(...)
   ```

3. **Add text index if missing**:
   ```javascript
   db.transcript_chunks_768d.createIndex(
     { text: "text" },
     { name: "text_search_index" }
   )
   ```

### Long-term Solutions
1. Use MongoDB Data API for stateless connections
2. Switch from async Motor to sync PyMongo for serverless
3. Implement proper connection pooling with retry logic
4. Add comprehensive error logging to identify exact failure point

## Configuration Reference

### Environment Variables
```bash
# Correct configuration (verified working)
MONGODB_URI=mongodb+srv://podinsight-api:***@podinsight-cluster.bgknvz.mongodb.net/?retryWrites=true&w=majority&appName=podinsight-cluster
MONGODB_DATABASE=podinsight
MODAL_EMBEDDING_URL=https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run/
```

### Related Files
- `/api/improved_hybrid_search.py` - Hybrid search implementation
- `/api/search_lightweight_768d.py` - Search endpoint handler
- `/api/topic_velocity.py` - Working MongoDB example
- `/docs/sprint5/sprint5-synthesis-improvements.md` - Previous search improvements

## 🔍 Root Cause Analysis - Text Search Failure

### The Real Problem
After thorough investigation, the text search component of hybrid search is failing specifically due to:

1. **Aggregation Pipeline Complexity**
   - The text search pipeline in `improved_hybrid_search.py:232-300` is too complex
   - It performs regex matching, array filtering, and $lookup joins
   - This exceeds the 10-second timeout in serverless environments

2. **Text Index Not Being Used**
   - The `text_search_index` exists on `transcript_chunks_768d` (confirmed in database_field_mapping_rosetta_stone.md:167)
   - However, the implementation uses regex search instead of the text index (line 246)
   - This is inefficient for 823,763 documents

3. **Parallel Execution Race Condition**
   - Vector and text searches run in parallel via `asyncio.gather()` (line 139)
   - When text search times out, it returns empty results
   - The hybrid search then degrades to vector-only mode

4. **MongoDB Field Mapping Complexity**
   - The $lookup join to `episode_metadata` adds overhead
   - Field paths like `metadata.raw_entry_original_feed.episode_title` are deeply nested
   - This requires complex projection in the aggregation pipeline

### Why Vector Search Works
- Uses the optimized `vector_index_768d` index
- Simple pipeline with direct score calculation
- No complex joins or regex operations
- Completes within the timeout window

### Evidence from Code Analysis
```python
# From improved_hybrid_search.py:245-246
# Text search falls back to regex, not using the text index properly
"$match": {
    "text": {"$regex": combined_pattern, "$options": "i"}
}
```

This explains why searches like "What are VCs saying about AI valuations?" return generic results - the text component that would match "valuations" times out, leaving only vector similarity.

## Key Documents Referenced

### Architecture & Infrastructure
- `/docs/master-architecture-infrastructure.md` - System overview showing Modal.com integration
- `/docs/master-api-reference.md` - API documentation with endpoint specifications
- `/docs/latest/database_field_mapping_rosetta_stone.md` - Critical field mapping guide

### Sprint Documentation
- `/docs/sprint5/sprint5-synthesis-improvements.md` - Previous hybrid search implementation
- `podinsight-business-canvas.md` - Business context and goals
- `sprint3-command-bar-playbook.md` - Command bar search requirements

## Conclusion

The MongoDB connection was never broken - only the text search component of hybrid search was failing. By changing the connection string, we broke working functionality while not fixing the actual issue. After reverting, we're back to the original state where most features work but search quality is degraded. The next step is to fix the text search component specifically without breaking other functionality.
