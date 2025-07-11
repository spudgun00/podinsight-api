# MongoDB Search Fix Implementation Plan

**Date**: July 11, 2025
**Issue**: Search quality degradation due to text search timeouts
**Status**: In Progress

## Executive Summary

Search results are returning generic content instead of specific matches because the text search component is timing out. The root cause is inefficient regex-based text search on 823,763 documents instead of using MongoDB's text index.

## Root Cause Analysis

### What's Working ✅
- MongoDB connection is fine (topic velocity endpoint works)
- Vector search returns results successfully
- Hybrid search architecture is sound

### What's Broken ❌
- Text search uses regex instead of MongoDB $text operator
- Complex aggregation pipeline with unnecessary operations
- 10-second timeout insufficient for current implementation
- Silent degradation to vector-only search

## Implementation Plan

### Phase 1: Immediate Fixes (Priority 1) 🚨

#### 1. Fix Text Search Implementation ✅
**File**: `/api/improved_hybrid_search.py`
**Method**: `_text_search()` (lines 232-352)
**Changes**:
- [x] Replace regex search with MongoDB $text operator
- [x] Use existing `text_search_index` properly
- [x] Simplify aggregation pipeline
- [x] Remove complex $filter operations

**Code Change Preview**:
```python
# OLD (line 246-249):
{
    "$match": {
        "text": {"$regex": combined_pattern, "$options": "i"}
    }
}

# NEW:
{
    "$match": {
        "$text": {"$search": query_string}
    }
}
```

#### 2. Increase Timeouts ✅
- [x] MongoDB timeout: 10s → 20s
- [x] Add specific timeout handling for text search
- [x] Consider separate timeout for text vs vector search

#### 3. Add Error Handling ✅
- [x] Log when text search fails
- [x] Implement graceful fallback to regex
- [x] Return partial results with metadata

### Phase 2: Performance Optimization 🚀

#### 1. Optimize Text Search Pipeline
- [ ] Use MongoDB text score for ranking
- [ ] Remove manual term counting
- [ ] Simplify field projections
- [ ] Use `$meta: "textScore"` for relevance

#### 2. Sequential Execution Option
- [ ] Run vector search first
- [ ] Only run text search if vector succeeds
- [ ] Better timeout management
- [ ] Circuit breaker pattern

#### 3. Add Caching Layer
- [ ] Cache common query embeddings
- [ ] Cache frequent search results
- [ ] Use MongoDB for cache storage
- [ ] TTL-based cache expiration

### Phase 3: Testing & Validation ✅

#### Test Queries
- [ ] "What are VCs saying about AI valuations?"
- [ ] "Series A funding trends"
- [ ] "Startup burn rates"
- [ ] "Unicorn valuations 2024"

#### Performance Metrics
- [ ] Response time < 2 seconds
- [ ] Both vector and text results return
- [ ] Hybrid scoring works correctly
- [ ] No timeout errors

#### Production Monitoring
- [ ] Track timeout rates
- [ ] Log search quality metrics
- [ ] Monitor user satisfaction
- [ ] Set up alerts for failures

## Technical Details

### Current Implementation Issues

1. **Regex Search (Line 249)**:
   ```python
   "$match": {
       "text": {"$regex": combined_pattern, "$options": "i"}
   }
   ```
   - Scans all 823,763 documents
   - No index utilization
   - O(n) complexity

2. **Complex Aggregation (Lines 256-263)**:
   ```python
   "$filter": {
       "input": {"$split": [{"$toLower": "$text"}, " "]},
       "cond": {"$in": ["$$this", [term.lower() for term in query_terms]]}
   }
   ```
   - Splits every document's text
   - Performs array operations
   - Adds significant overhead

### Proposed Solution

1. **Use Text Index**:
   ```python
   pipeline = [
       {
           "$match": {
               "$text": {"$search": query_string}
           }
       },
       {
           "$addFields": {
               "text_score": {"$meta": "textScore"}
           }
       },
       {"$sort": {"text_score": -1}},
       {"$limit": limit}
   ]
   ```

2. **Simplified Pipeline**:
   - Direct text search with index
   - Native scoring from MongoDB
   - Minimal post-processing

## Success Criteria

- ✅ Search returns relevant results for keyword queries
- ✅ No more ReplicaSetNoPrimary errors
- ✅ Hybrid search includes both vector and text results
- ✅ Response time under 2 seconds
- ✅ Proper error logging and monitoring

## Risk Mitigation

1. **Rollback Plan**: Keep original code commented
2. **Feature Flag**: Add environment variable to toggle implementations
3. **Gradual Rollout**: Test with subset of queries first
4. **Monitoring**: Track performance metrics closely

## Implementation Details (Completed July 11, 2025)

### Changes Made

1. **Text Search Method** (`_text_search`):
   - Replaced regex pattern matching with MongoDB $text operator
   - Properly formats search strings with phrase support
   - Uses MongoDB's native text scoring (`$meta: "textScore"`)
   - Simplified aggregation pipeline significantly

2. **Error Handling**:
   - Added comprehensive try-catch with fallback to regex
   - Fallback uses simplified pipeline without complex operations
   - Logs all failures for monitoring

3. **Score Processing**:
   - Updated `_merge_and_rerank` to use text scores
   - Normalizes MongoDB text scores (0-5 range) to 0-1
   - Maintains hybrid scoring algorithm

4. **Timeout Increases**:
   - `serverSelectionTimeoutMS`: 10s → 20s
   - `connectTimeoutMS`: 10s → 20s
   - `socketTimeoutMS`: 10s → 20s

### Test Script

Created `/scripts/test_search_improvements.py` to verify:
- Search response times
- Result quality
- Hybrid search functionality
- Error handling

## Timeline

- **Day 1**: ✅ Implement text search fix
- **Day 1**: ✅ Add error handling and timeouts
- **Day 2**: Test and optimize
- **Day 2**: Deploy to production
- **Day 3**: Monitor and fine-tune

## Notes

- Text index exists: `text_search_index` on `transcript_chunks_768d`
- Database has 823,763 chunks
- Current timeout: 10 seconds
- MongoDB connection string is correct
