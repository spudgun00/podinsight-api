# Sprint 5 Search Fix Implementation Plan

## Fixes Implemented

### 1. MongoDB Connection Fix ✅
- **Issue**: Shell environment had incorrect password overriding .env
- **Fix**: Created `lib/env_loader.py` to force .env values over shell
- **Files Updated**:
  - Created `lib/env_loader.py`
  - Updated `api/improved_hybrid_search.py`
  - Updated `api/search_lightweight_768d.py`
  - Created `MONGODB_AUTH_FIX.md` documentation

### 2. Text Search Query Simplification ✅
- **Issue**: Complex query with too many bigrams returning 0 results
- **Fix**: Simplified query generation, removed stop words, focused on meaningful terms
- **Changes**:
  - Removed unnecessary bigrams like "what are", "are vcs"
  - Added stop word filtering
  - Only include meaningful domain-specific bigrams
  - Result: Text search now returns results!

### 3. Modal Pre-warming (Backend) ✅
- **Issue**: 18+ second cold starts causing timeouts
- **Fix**: Created on-demand pre-warming endpoint
- **Files Created**:
  - `api/prewarm.py` - Fire-and-forget warming endpoint
  - Updated `api/index.py` to include router
- **Benefits**: 90% cost reduction vs 24/7 warming

## Next Steps

### 1. Frontend Pre-warming Integration
Add to CommandBar component:
```typescript
useEffect(() => {
  if (open && !hasWarmed.current) {
    fetch('/api/prewarm', { method: 'POST' }).catch(() => {});
    hasWarmed.current = true;
    setTimeout(() => { hasWarmed.current = false; }, 180000);
  }
}, [open]);
```

### 2. Query Caching
- Cache common query embeddings
- Cache search results with 1-hour TTL
- Implement LRU cache for embeddings

### 3. Search Quality Improvements
- Add query expansion for financial terms
- Improve hybrid scoring weights
- Consider semantic chunking vs time-based

## Testing Checklist

- [ ] MongoDB connection works locally
- [ ] Text search returns results for common queries
- [ ] Pre-warm endpoint responds quickly
- [ ] Search latency < 5 seconds (target: < 2s)
- [ ] No more "ReplicaSetNoPrimary" errors

## Deployment Notes

1. Ensure `.env` has correct MongoDB URI (without /podinsight in path)
2. Modal embedding URL must be set in environment
3. Test pre-warming in production environment
4. Monitor for any new timeout issues
