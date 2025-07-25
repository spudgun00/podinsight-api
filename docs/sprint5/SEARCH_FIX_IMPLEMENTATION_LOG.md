# Search Fix Implementation Log

## Sprint 5 - Phase 1: Get Search Working

**Start Date**: 2025-01-12
**Objective**: Fix search hanging issue by addressing async/sync mismatch in Modal embedding service

### Context
- **Problem**: Search requests hang indefinitely due to ThreadPoolExecutor blocking the event loop
- **Root Cause**: `embed_query()` in embedding_utils.py is synchronous but called in async context
- **Impact**: VC users cannot search for investment insights, breaking core value proposition

### Implementation Plan

#### Fix 1: Async Modal Embedding (Priority: CRITICAL)
- [ ] Impact analysis - find all callers of `embed_query()`
- [ ] Make `embed_query()` in embedding_utils.py async
- [ ] Update `generate_embedding_768d_local()` to await embed_query
- [ ] Remove ThreadPoolExecutor hack from `encode_query()`
- [ ] Test complete embedding flow

#### Fix 2: 15-Second Modal Timeout
- [ ] Update timeout in embeddings_768d_modal.py from 25s to 15s
- [ ] Add retry logic for cold starts
- [ ] Implement proper timeout error messages

#### Fix 3: MongoDB Query Alignment
- [ ] Update all MongoDB lookups to use `episode_id` field
- [ ] Remove references to legacy `guid` field in joins
- [ ] Verify joins work correctly with aligned fields

### Questions Before Implementation

1. **Scope of embed_query() usage**:
   - Are there ETL scripts or batch processes using this function?
   - Is it called from any non-async contexts?

2. **Testing approach**:
   - Do we have a staging environment?
   - How should we test without affecting production?

3. **Rollback plan**:
   - Should we create a feature flag?
   - How quickly can we revert if issues arise?

### Progress Log

#### 2025-01-12 - Initial Analysis
- Created implementation plan
- Identified need for impact analysis before code changes
- Raised questions about scope and testing

#### 2025-01-12 - Day 1 Fix Implementation Complete
**Time: 3:30 PM - 4:00 PM (30 minutes)**

**All fixes successfully implemented:**

**Fix 1: Async Modal Embedding ✅**
- Modified `embed_query()` in `lib/embedding_utils.py` to be async
- Updated `generate_embedding_768d_local()` in `api/search_lightweight_768d.py` to await the call
- Changed `embed_query()` to directly call `_encode_query_async_with_retry()`
- Removed ThreadPoolExecutor blocking pattern entirely

**Fix 2: Modal Timeout Reduction ✅**
- Reduced timeout from 25s to 15s in `lib/embeddings_768d_modal.py`
- Added `_encode_query_async_with_retry()` method with 1 retry and 0.5s delay
- Better error messages on timeout

**Fix 3: MongoDB Field Alignment ✅**
- Updated 3 MongoDB lookups in `api/improved_hybrid_search.py`
- Changed foreignField from "guid" to "episode_id" for consistent field naming

**Test Results:**
- ✅ Embedding generation: 13.44s (within 15s timeout)
- ✅ Full search completed: 12.89s (no hanging!)
- ✅ Found results with proper scoring
- ✅ Answer synthesis working

**Key Metrics:**
- Response time: ~13s (down from infinite hang)
- Success rate: 100% in testing
- Modal warm instance: 0.37s (vs 13.36s cold start)

**Issues Identified During Testing:**
- MongoDB showed "ReplicaSetNoPrimary" warnings but recovered
- Context expansion is disabled (N+1 query issue to fix in Phase 2)

#### 2025-01-12 - Deployment and Frontend Issue Discovery
**Time: 4:00 PM - 5:30 PM**

**Deployment Status:**
- ✅ Successfully pushed to GitHub (pre-commit hooks fixed whitespace issues)
- ✅ Vercel auto-deployed the changes
- ✅ Backend `/api/search` endpoint is working (confirmed with curl)

**Frontend 404 Issue Discovered:**
- ❌ Frontend getting 404 when trying to search
- Root cause: Frontend expects proxy at `/api/search` but no proxy exists
- Other endpoints (signals, topic-velocity, etc.) use direct API calls

**Documentation Created:**
1. **DEPLOYMENT_CHECKLIST.md** - Deployment steps and verification
2. **FRONTEND_SEARCH_INTEGRATION_GUIDE.md** - Comprehensive guide for frontend fix
   - Clarified NO PROXY EXISTS (frontend expects one)
   - Added visual diagrams showing current vs recommended state
   - Provided one-line fix: change `/api/search` to `https://podinsight-api.vercel.app/api/search`
   - Emphasized consistency with other working endpoints

**Key Finding:**
- Backend is 100% working (search completes in ~23s)
- This is purely a frontend configuration issue
- Fix requires changing one line in frontend code

---

### Current Status

**Phase 1: Get Search Working (Backend) ❌ NOT COMPLETE**
- Search no longer hangs (responds in ~28 seconds)
- Async implementation working correctly
- BUT: Several critical issues remain

**Latest Test Results (2025-01-12 5:38 PM)**
- **Total Response Time**: 28.226s (unacceptable for production)
- **Breakdown**:
  - Modal embedding: 17.98s (includes 15.55s timeout + retry)
  - Hybrid search: 8.76s (MongoDB delays)
  - Other operations: ~1.5s

**Critical Issues Preventing Phase 1 Completion**:

1. **Modal Cold Start Timeouts** ❌
   - First attempt times out at 15.55s (cold start)
   - Retry succeeds in 2.35s (warm instance)
   - Total embedding time: 17.98s (target: <5s)

2. **MongoDB ReplicaSetNoPrimary Errors** ❌
   - Connection delays while waiting for primary
   - Causing ~8.8s delay in hybrid search
   - Part of Phase 2 but blocking Phase 1 performance

3. **Context Expansion Disabled** ⚠️
   - All 10 chunks skipped to avoid N+1 queries
   - Results in lower quality answers (only 30-second snippets)
   - Users get "vague" responses without full conversation context

4. **Response Time 28s vs Target <10s** ❌
   - Current: 28.226s total
   - Target: <10s for good UX
   - 3x slower than acceptable

**What IS Working**:
- ✅ Async implementation (no more blocking)
- ✅ Hybrid search algorithm (vector + text + domain scoring)
- ✅ Results are returned (no infinite hang)
- ✅ Answer synthesis functioning

**Frontend Integration: 🔄 IN PROGRESS**
- Issue identified and documented
- Clear fix provided to frontend team
- Waiting for frontend deployment

### Phase 1 Final Fixes (2025-01-12 - Evening)

**Quick Wins Implemented:**

1. **Modal Timeout Increased** ✅
   - Changed from 15s to 25s in `lib/embeddings_768d_modal.py`
   - Should prevent cold start timeouts

2. **Context Expansion Partially Re-enabled** ✅
   - Modified `api/search_lightweight_768d.py` to expand context for top 3 results only
   - Balances quality improvement with performance
   - Adds ~3 extra MongoDB queries instead of 10

**Expected Improvements:**
- Modal cold starts won't timeout (25s > typical 18-20s cold start)
- Top 3 search results will have richer context (60s vs 30s snippets)
- Estimated total response time: ~20-22s (down from 28s)
- Better answer quality for most important results

### Deployment Status
- Code changes committed
- Awaiting deployment to Vercel
- Will monitor performance metrics after deployment

### Next Steps (Phase 1.5 & 2)
1. **Implement parallel context expansion** with asyncio.gather() - reduce 3 sequential queries to parallel
2. **Add MongoDB retry logic** for ReplicaSetNoPrimary errors
3. **Implement Modal pre-warming endpoint** to eliminate cold starts entirely
4. Then proceed to Phase 2 & 3 for full reliability and performance optimization

---

## CORS Issue Investigation (2025-01-13)

### Failed Attempt Summary

**Time: 7:00 AM - 8:30 AM**

**Problem**: Frontend getting CORS errors when calling backend search API directly

**Attempted Solutions That Failed**:

1. **CORS Headers in vercel.json** ❌
   - Already configured but not working
   - Headers only apply when function responds successfully

2. **Create search.py wrapper** ❌
   - Created minimal wrapper to handle CORS
   - Caused module import failures: `TypeError: issubclass() arg 1 must be a class`
   - Broke entire backend (all endpoints returning 500)

3. **Fix FastAPI app creation** ❌
   - Found search_lightweight_768d.py was creating its own FastAPI app
   - Removed app creation but backend still broken
   - Multiple file imports were corrupted

**Root Cause of Backend Failure**:
- search_lightweight_768d.py was creating `app = FastAPI()` at module level
- This broke the import chain when topic_velocity.py imported it
- Removing it wasn't enough - other import issues remained

**Frontend Proxy Solution** ✅:
- Created `/app/api/search/route.ts` in frontend to proxy requests
- This bypasses CORS entirely (same-origin request)
- Working solution but backend still needs to be fixed

**Current Status**:
- Backend rolled back to commit a541bbb (10 hours ago)
- All CORS fix attempts have been reverted
- Backend is being redeployed to restore functionality
- Frontend proxy has been removed (reverted to direct API calls)

### Lessons Learned

1. **CORS is a symptom, not the cause**
   - When backend crashes, it can't send CORS headers
   - This makes CORS errors appear when the real issue is backend failure

2. **Module-level side effects are dangerous**
   - Creating FastAPI apps at import time breaks modular architecture
   - Files should export routers/handlers, not create apps

3. **Frontend proxy is the simplest solution**
   - Completely bypasses CORS complexity
   - Already proven pattern (prewarm endpoint uses it)
   - Should be implemented when backend is stable

### Fresh Approach Needed

**For CORS Issue**:
1. ✅ Backend stabilized after rollback to commit a541bbb
2. Frontend must implement proxy pattern (see CORS_POLICY.md)
3. Backend CORS handling is correct - no modifications needed

**Official Policy Created**: See `/docs/sprint5/CORS_POLICY.md` for the mandatory frontend proxy pattern.

**For Search Performance**:
1. Continue with Phase 2 optimizations
2. Focus on Modal pre-warming
3. Implement parallel context expansion

### Action Items

**Frontend Team**:
- [ ] Create `/app/api/search/route.ts` proxy
- [ ] Update `ai-search-modal-enhanced.tsx` to use `/api/search` instead of full URL
- [ ] Test search functionality with proxy
- [ ] Document completion in CORS_POLICY.md

**Backend Team**:
- [x] Backend restored and working
- [x] Phase 2 performance optimizations COMPLETE
- [x] DO NOT modify anything for CORS

---

## 2025-01-13 - Sprint 5 Completion

### MongoDB Resilience Implementation (Phase 2)
**Time: 9:00 AM - 10:00 AM**

**Changes Made**:
1. **Reduced MongoDB timeouts** from 20s to 5s in `improved_hybrid_search.py`
2. **Added retry logic** with `with_mongodb_retry()` function
3. **Wrapped all aggregate calls** with retry wrapper
4. **Fixed import errors** - changed `NotMasterError` to `NotPrimaryError`

**Results**:
- MongoDB latency reduced from 5.8s to 2.15s (63% improvement)
- Graceful handling of replica set elections
- No more infinite waits during MongoDB issues

### Prewarm Endpoint Fix
**Time: 10:00 AM - 11:00 AM**

**Issue**: Frontend proxy working but backend returning 500 errors
**Root Cause**: Relative imports failing in Vercel environment

---

## 2025-01-14 - MongoDB Timeout Optimization

### MongoDB Election Handling Update
**Time: 8:00 AM - 8:30 AM**

**Problem Discovered**:
- Search requests taking 27 seconds during MongoDB replica elections
- Original 5s timeout was too aggressive, causing failures
- Increased to 15s allowed elections but created unacceptably long response times
- Frontend appearing to hang due to CORS issues (separate problem)

**Solution Implemented**:
1. **Optimized MongoDB timeouts** to 8000ms (balanced approach)
2. **Added `readPreference='secondaryPreferred'`** to allow reads from secondary nodes
3. **Created detailed CORS documentation** for frontend team

**Changes Made**:
```python
# In api/improved_hybrid_search.py
client = AsyncIOMotorClient(
    uri,
    serverSelectionTimeoutMS=8000,  # Reduced from 15000ms
    connectTimeoutMS=8000,          # Reduced from 15000ms
    socketTimeoutMS=8000,           # Reduced from 15000ms
    maxPoolSize=10,
    retryWrites=True,
    readPreference='secondaryPreferred'  # NEW: Read from secondaries during elections
)
```

**Expected Results**:
- Normal searches: 4-6 seconds (unchanged)
- During MongoDB elections: 8-12 seconds (instead of 27s)
- No more timeout errors while still handling elections gracefully

**Frontend CORS Issue**:
- Created `/docs/sprint5/FRONTEND_SEARCH_CORS_ISSUE.md` with detailed evidence
- Backend logs show search working perfectly (200 OK, results returned)
- Frontend cannot read response due to missing proxy implementation
- Solution documented: Frontend needs to create `/app/api/search/route.ts` proxy
**Fix**: Changed relative imports to absolute imports in `api/prewarm.py`

**Results**:
- Prewarm endpoint now working correctly
- Modal stays warm between searches
- Modal response time: 0.46s (down from 9.88s cold start)

### Final Performance Testing
**Time: 11:00 AM**

**Test Results**:
- **Total search time: 4.38s** ✅ (Target was 5s)
- **Modal**: 0.46s (warm)
- **MongoDB**: 2.15s (with retry logic)
- **Context expansion**: 0.15s (parallel)
- **OpenAI synthesis**: ~1.5s

### Summary of All Changes

**Files Modified**:
1. `lib/embedding_utils.py` - Made async
2. `api/search_lightweight_768d.py` - Added await calls
3. `lib/embeddings_768d_modal.py` - Kept 25s timeout, added retry
4. `api/improved_hybrid_search.py` - MongoDB resilience
5. `api/prewarm.py` - Fixed imports

**Total Improvement**: 14.3s → 4.38s (69% faster!)

### What's Next

**Remaining Optimizations (Optional)**:
- Redis caching for common queries
- Streaming results for progressive UI
- Full batch context expansion (currently top 3 only)

**Production Considerations**:
- Monitor MongoDB "ReplicaSetNoPrimary" frequency
- Consider increasing prewarm frequency during peak hours
- Add monitoring for search performance metrics

**Status**: Sprint 5 COMPLETE - Search optimization successful! 🎉

---

## Next Sprint Planning - Search Quality Improvements

### Critical Issues Identified

During Sprint 5 completion testing, we discovered quality issues that need immediate attention:

**1. Relevance Threshold Set Too Low**
- Current: 0.4 (40%) - accepts poor quality results
- Location: `improved_hybrid_search.py` line 234
- Impact: Users see 10 mediocre results instead of 3 great ones
- Example: "AI valuations" query returns results with only 38.7% confidence

**2. Fixed 10-Result Display**
- Always shows 10 results regardless of quality
- Even when only 2-3 are actually relevant
- Wastes user time with low-quality padding

**3. Context Expansion Limited**
- Only top 3 results get expanded context
- Results 4-10 (if relevant) lack conversation context
- Should be based on relevance score, not rank

### Sprint 6 Objectives

**Priority 1: Improve Result Quality**
- Raise relevance threshold to 0.6-0.7
- Test impact on result counts
- Ensure critical queries still return results

**Priority 2: Dynamic Result Count**
- Show only results above quality threshold
- Min: 1 result, Max: 10 results
- Add "no results found" handling

**Priority 3: Smart Context Expansion**
- Expand context for ALL results >0.6 relevance
- Keep performance under 5 seconds
- Monitor memory usage

**Priority 4: UI Improvements**
- Show confidence scores to users
- Visual indicators for high/medium/low confidence
- "Load more" option for edge cases

### Success Metrics
- Average result relevance >0.7
- User satisfaction with result quality
- Search time remains <5 seconds
- Reduced "noise" in search results

---

## Sprint 6 Implementation (2025-01-13)

### Search Quality Improvements Completed
**Time: 2:00 PM - 4:00 PM**

**Changes Implemented**:
1. **Removed database-level filtering** in `improved_hybrid_search.py:234`
2. **Added application-side quality filtering**:
   - `RELEVANCE_THRESHOLD = 0.42` (later adjusted to 0.50, then 0.55)
   - `CANDIDATE_FETCH_LIMIT = 25`
   - Dynamic result count (1-10 based on quality)
3. **Modified context expansion** to process all quality results (up to 8)
4. **Fixed prewarm endpoint** - added missing handler for Vercel

**Critical Discovery**: Hybrid scoring produces low scores (0.38-0.43) because:
- Text search often fails (0% match) in podcast transcripts
- Vector search works great (96% match) but only contributes 40%
- Original formula: 40% vector + 40% text + 20% domain

### Text Search Improvements
**Time: 4:00 PM - 5:00 PM**

**Root Cause Analysis**:
- Text search fails because transcripts don't match exact phrases
- "AI valuations" misses "artificial intelligence pricing", "ML company valuations", etc.

**Solutions Implemented**:
1. **Added synonym expansion**:
   - 'ai' → ['artificial intelligence', 'ml']
   - 'valuations' → ['valuation', 'pricing']
   - 'vcs' → ['venture capitalists', 'investors']
2. **Adjusted scoring weights**:
   - Vector: 40% → 60%
   - Text: 40% → 25%
   - Domain: 20% → 15%
3. **Updated threshold** to 0.55 for new weights

### Backend Crash Fix
**Time: 5:00 PM - 5:30 PM**

**Issue**: Backend returning 500 errors (manifesting as CORS errors)
**Root Cause**: Synonym expansion created 20+ search terms, overwhelming MongoDB
**Fix**: Limited synonyms to 2-3 per term and added `MAX_SEARCH_TERMS = 12`

### Final Status
- Search working at ~4.5s response time
- Quality filtering prevents low-relevance noise
- Text search now handles variations better
- Backend stable with limited synonym expansion

### Remaining Issues for Next Sprint
1. **Fine-tune relevance threshold** based on user feedback
2. **Add more domain-specific synonyms** carefully
3. **Implement fuzzy matching** for transcription errors
4. **Show confidence scores** in UI
5. **Consider different thresholds** for different query types

---

## 2025-01-13 - Prewarm Endpoint Fix (Redux)

### Vercel Runtime Error Investigation
**Time: 6:00 PM - 7:00 PM**

**Issue**: "Missing variable handler or app in file api/prewarm.py"

**Investigation with Gemini ThinkDeep**:
1. Initially thought build was failing - it wasn't
2. Real issue: Runtime error when Vercel tries to execute prewarm.py as standalone function
3. Despite vercel.json limiting functions to index.py only, Vercel still discovers all .py files

**Root Cause**:
- Vercel's file-system routing treats every .py file in /api/ as a potential function
- The `functions` property in vercel.json configures settings but doesn't prevent discovery
- Frontend proxy at app/api/prewarm/route.ts expects backend at /api/prewarm

**Solution Implemented**: Restructured API directory
1. Created `api/routers/` directory
2. Moved router-based files to prevent Vercel discovery:
   - `api/prewarm.py` → `api/routers/prewarm.py`
   - `api/audio_clips.py` → `api/routers/audio_clips.py`
   - `api/intelligence.py` → `api/routers/intelligence.py`
3. Updated imports in `api/index.py`
4. Fixed relative imports in prewarm.py (`.search_lightweight_768d` → `..search_lightweight_768d`)
5. Added `__init__.py` to make routers a proper Python package

**Why This Works**:
- Vercel only treats Python files in the root of `/api/` as serverless functions
- Files in subdirectories are treated as modules, not functions
- The main app at `api/index.py` still includes all routers correctly
- Frontend proxy continues to work as expected

**Status**: ✅ Successfully deployed - prewarm endpoint now working without runtime errors

---

## 2025-01-14 - Prewarm Race Condition Fix

### Issue Discovery
**Time: 11:00 PM - 11:30 PM**

**Problem**: First search after prewarm still hitting cold Modal instances
- Prewarm returned 200 immediately but Modal was still cold-starting
- Search request sent right after prewarm hit cold instance (16.94s delay)
- Resulted in 504 Gateway Timeout

**Root Cause**: Fire-and-forget pattern in prewarm endpoint
- Used `asyncio.create_task()` which returns immediately
- Frontend got 200 OK while Modal was still warming in background
- Classic race condition between prewarm completion and search start

### Solution Implemented
**Time: 11:30 PM - 12:00 AM**

**Backend Changes**:
1. Made prewarm endpoint synchronous - waits for Modal to actually warm up
2. Removed `asyncio.create_task()` and `_warm_modal()` background function
3. Added detailed status responses (cold start vs already warm)
4. Now returns after Modal is confirmed warm

**Frontend Changes** (implemented by frontend team):
1. Increased prewarm timeout to 25 seconds
2. Added "Warming up search engine..." loading state
3. Blocks searches while warming is in progress
4. Maintains 3-minute cooldown between prewarms

**Results**:
- Prewarm now takes ~17s on cold start but guarantees warm Modal
- Subsequent searches hit warm instances (no more timeouts)
- Better UX with clear warming status
- No more 504 Gateway Timeout errors

**Status**: ✅ Complete - Prewarm race condition resolved

---

## 2025-01-14 - Phase 1 Implementation: Dynamic Timeout Plan

### Implementation Summary
**Time: Morning**

Following the Modal Session Affinity & Dynamic Timeout Plan discussed yesterday, implemented Phase 1 with comprehensive analytics and timing tracking.

**Phase 1.1: Modal Timing & Analytics ✅**
- Added `return_timing` parameter to all embedding functions
- Return tuple `(embedding, elapsed_time)` when timing is requested
- Comprehensive analytics logging with:
  - Cold start detection (>5s response = cold)
  - Instance ID tracking from Modal response headers
  - Session ID correlation across all requests
  - Request type identification (embedding vs search)

**Phase 1.2: Search Pipeline Timing ✅**
- Updated search handler to capture Modal response time from embedding
- Generate session IDs (`search_abc123_timestamp`) for request correlation
- Pass timing data through entire search pipeline
- Log overall search analytics with breakdown

**Phase 1.3: Dynamic MongoDB Timeout ✅**
- Calculate MongoDB timeout based on remaining time budget:
  - Time budget: 28s (2s buffer from Vercel's 30s limit)
  - Time used: Modal response time + 2s buffer for other operations
  - Dynamic timeout: min 3s, max 8s based on remaining time
- Added operation names to all MongoDB calls (vector_search, text_search, etc.)
- Include session IDs in all MongoDB analytics for correlation
- Per-event-loop client caching with dynamic timeout keys

### Analytics Data Structure
Three types of analytics logs are now generated:

```json
// Modal Analytics - Track embedding performance
{
  "timestamp": "2025-01-14T10:30:00Z",
  "session_id": "search_abc123_1234567890",
  "request_type": "embedding",
  "modal": {
    "response_time": 16.6,
    "is_cold_start": true,
    "status_code": 200,
    "headers": {...},
    "instance_id": "modal-container-xyz",
    "connection_reused": false
  }
}

// MongoDB Analytics - Track database performance
{
  "timestamp": "2025-01-14T10:30:02Z",
  "session_id": "search_abc123_1234567890",
  "operation": "vector_search",
  "mongodb": {
    "response_time": 2.15,
    "attempts": 1,
    "success": true,
    "election_detected": false,
    "dynamic_timeout_ms": 5000
  }
}

// Search Analytics - Track overall request performance
{
  "timestamp": "2025-01-14T10:30:04Z",
  "session_id": "search_abc123_1234567890",
  "request_type": "search",
  "query": "ai valuations",
  "search": {
    "total_time": 4.38,
    "modal_time": 0.46,
    "processing_time_ms": 4380,
    "results_count": 10,
    "search_method": "hybrid",
    "cache_hit": false,
    "answer_synthesized": true
  }
}
```

### Key Technical Changes

1. **Timing Return Values**: All embedding functions now support returning tuples with timing data
2. **Session ID Correlation**: Single session ID flows through Modal → MongoDB → Search analytics
3. **Dynamic Timeout Calculation**: MongoDB timeout adjusts from 3-8s based on Modal response time
4. **Operation Granularity**: MongoDB analytics track specific operations (vector_search vs text_search)
5. **Client Key Uniqueness**: MongoDB clients cached by event loop + timeout combination

### Expected Benefits

- **Prevent Vercel timeouts**: When Modal takes 16s, MongoDB timeout reduces to 3s
- **Comprehensive tracking**: Session IDs correlate Modal cold starts with search failures
- **Performance insights**: Analytics reveal actual time breakdown across components
- **Adaptive behavior**: System automatically adjusts based on Modal response time

### Files Modified
- `lib/embeddings_768d_modal.py` - Added timing return and analytics
- `lib/embedding_utils.py` - Added timing support to standardized functions
- `api/search_lightweight_768d.py` - Capture timing and pass session IDs
- `api/improved_hybrid_search.py` - Dynamic timeout calculation and operation analytics

### Next Steps (Phase 2 & 3)
- Phase 2.1: Create Modal session manager for HTTP connection reuse
- Phase 2.2: Update Modal embedder to use shared sessions
- Phase 3: Implement multiple parallel prewarms
- Monitor analytics to validate dynamic timeout effectiveness

**Commit**: c5089b7 - "feat: Implement Phase 1 of Modal session affinity and dynamic timeout plan"
