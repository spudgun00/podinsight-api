# Search API Hanging - Root Cause Analysis & Fix Guide

## Executive Summary

### Current State
The PodInsight command bar search functionality is **completely broken** - search requests hang indefinitely when users submit queries like "What are VCs saying about AI valuations?" with no visible errors in logs. The frontend times out after 45 seconds but receives no response from the backend.

### Root Causes Identified
1. **Blocking asyncio Event Loop** - Synchronous functions called with `await` freeze the entire event loop
2. **Missing Network Timeouts** - Modal service (18-20s cold start) and MongoDB operations can hang indefinitely
3. **N+1 Database Queries** - Multiple sequential queries multiply timeout risks
4. **MongoDB Connection Issues** - Persistent "ReplicaSetNoPrimary" errors causing queries to hang
5. **Insufficient Error Handling** - Exceptions leave requests in limbo with no visibility

### Solution Overview
Implement comprehensive timeouts, fix async patterns, optimize database queries, and add proper error handling to ensure requests fail fast with meaningful errors rather than hanging mysteriously.

## Issue Timeline & Discovery

### Sprint 3 (Command Bar Implementation)
- **Goal**: "Ask, listen, decide" - Perplexity for podcasts
- **What Was Built**:
  - MongoDB Atlas vector search with 768D embeddings
  - Modal.com GPU infrastructure (Instructor-XL model)
  - `/api/search` endpoint returning chunks
  - Answer synthesis with OpenAI
- **Documentation**: `/docs/sprint3-command-bar-playbookv2.md`

### Sprint 5 (Search Quality Improvements)
- **Problem**: "Bad output" from pure vector search
- **What Was Implemented**:
  - Hybrid search: 40% vector + 40% text + 20% domain boost
  - VC-specific term weighting (valuation: 2.0x, series: 1.5x)
  - Fixed duplicate embedding generation
  - Enhanced synthesis with confidence scoring
  - Created prewarming endpoint
- **Issues Encountered**:
  - MongoDB "ReplicaSetNoPrimary" errors
  - Modal cold starts taking 18-20 seconds
  - Search returning generic results
- **Documentation**:
  - `/docs/sprint5/sprint5-synthesis-improvements.md`
  - `/docs/sprint5/search-fix-implementation-plan.md`
  - `/docs/sprint5/fix-cold-start-and-no-results.md`

### Current State (Search Hanging)
- **Symptom**: Requests hang with no response or errors
- **Frontend**: Properly configured with 45-second timeout
- **Backend**: Endpoint exists but hangs during processing
- **Documentation**: `/docs/sprint5/SEARCH_API_IMPLEMENTATION_GUIDE.md`

## Technical Deep Dive

### 1. Blocking asyncio Event Loop

**The Problem:**
```python
# In api/improved_hybrid_search.py
async def hybrid_search(query, query_embedding):
    # WRONG: Awaiting synchronous functions blocks the event loop
    vector_results, text_results = await asyncio.gather(
        vector_search(query_embedding),  # This is a regular def function
        text_search(query)               # This is also synchronous
    )
```

**Why It Hangs:**
- Synchronous MongoDB operations block the entire event loop
- Other coroutines can't execute while waiting for database
- In serverless environment, this causes the function to freeze

**Evidence:**
- No timeout errors, just hanging = classic event loop blocking
- Sprint 5 implemented these as sync functions

### 2. Missing Network Timeouts

**Modal Service (Embedding Generation):**
```python
# Current implementation has no timeout
embedding = modal_client.remote(text)  # Can hang indefinitely
```

**Why It Matters:**
- Modal cold start: 18-20 seconds (documented)
- No timeout means infinite wait if service hangs
- Frontend timeout (45s) vs potential Modal hang (∞)

**MongoDB Operations:**
```python
# Current: No timeout configuration
client = MongoClient(MONGO_URI)

# No maxTimeMS on queries
results = list(db.collection.aggregate(pipeline))
```

**Sprint 5 Evidence:**
- "Modal embedding service taking 18+ seconds for initial request"
- "MongoDB ReplicaSetNoPrimary errors persist"
- Increased timeouts from 5s to 10s but not everywhere

### 3. N+1 Query Problem

**Current Implementation:**
```python
# In get_context_chunks - executes query for EACH result
for result in results[:limit]:
    transcript_segment_id = result["_id"]
    pipeline = [...]  # Build pipeline
    chunk = list(db[EMBEDDINGS_COLLECTION].aggregate(pipeline))
    if chunk:
        context_chunks.append(chunk[0])
```

**Performance Impact:**
- 5 results = 5 separate database queries
- Each query: 10-50ms network latency
- Total: 50-250ms extra latency
- Each query can independently timeout

### 4. MongoDB Connection Issues

**From Sprint 5 Handover:**
- "ReplicaSetNoPrimary" errors indicate cluster issues
- Connection may be waiting for primary election
- Queries hang while MongoDB finds healthy node

**Evidence:**
```
# From sprint5-synthesis-improvements.md
"MongoDB connection issues persist (ReplicaSetNoPrimary)"
"Check MongoDB Atlas cluster health"
```

### 5. Insufficient Error Handling

**Current Pattern:**
```python
try:
    # All operations
except Exception as e:
    # Too broad - hides specific failures
    logger.error(f"Error: {e}")
```

**Problems:**
- Can't distinguish Modal timeout from MongoDB failure
- Async exceptions may leave requests hanging
- No service-specific error codes

## Complete Fix Implementation

### Phase 1: Add Timeouts (Immediate Fix)

**1.1 MongoDB Client Configuration:**
```python
# In search handlers initialization
from lib.env_loader import load_env_with_override
load_env_with_override()

mongo_client = pymongo.MongoClient(
    os.getenv('MONGODB_URI'),
    connectTimeoutMS=10000,    # 10 second connection timeout
    socketTimeoutMS=10000,     # 10 second socket timeout
    serverSelectionTimeoutMS=10000  # 10 second server selection
)
```

**1.2 Query Timeouts:**
```python
# Add to all aggregate calls
results = list(db[EMBEDDINGS_COLLECTION].aggregate(
    pipeline,
    maxTimeMS=15000  # 15 second query timeout
))
```

**1.3 Modal Service Timeout:**
```python
import asyncio

async def get_embedding_with_timeout(text: str, timeout: float = 15.0):
    """Get embedding with timeout handling"""
    try:
        # Check if Modal client has async method
        if hasattr(modal_client.remote, 'aio'):
            embedding_future = modal_client.remote.aio(text)
        else:
            # Fallback: run sync call in thread
            embedding_future = asyncio.to_thread(modal_client.remote, text)

        embedding = await asyncio.wait_for(embedding_future, timeout=timeout)
        return embedding
    except asyncio.TimeoutError:
        logger.error(f"Modal embedding timeout after {timeout}s")
        raise HTTPException(504, "Embedding service timeout")
```

### Phase 2: Fix Async Implementation

**2.1 Hybrid Search Fix:**
```python
# In api/improved_hybrid_search.py
async def search(self, query: str, limit: int = 50, query_embedding: Optional[List[float]] = None):
    """Fixed async implementation"""

    # Generate embedding if not provided
    if query_embedding is None:
        query_embedding = await get_embedding_with_timeout(query)

    # Run blocking operations in threads
    vector_task = asyncio.to_thread(
        self._run_vector_search, query_embedding, limit
    )
    text_task = asyncio.to_thread(
        self._run_text_search, query, limit
    )

    # Execute in parallel
    vector_results, text_results = await asyncio.gather(
        vector_task, text_task
    )

    # Merge results...
```

**2.2 Search Handler Update:**
```python
# In api/search_lightweight_768d.py
async def search_handler_lightweight_768d(request: SearchRequest) -> SearchResponse:
    """Main search handler with proper async"""
    start_time = time.time()

    try:
        # Get embedding with timeout
        embedding_768d = await get_embedding_with_timeout(
            request.query,
            timeout=15.0
        )

        # Use hybrid search
        hybrid_handler = await get_hybrid_search_handler()
        vector_results = await hybrid_handler.search(
            request.query,
            limit=request.limit,
            query_embedding=embedding_768d
        )

        # Synthesize with timeout...
    except asyncio.TimeoutError:
        return SearchResponse(
            results=[],
            answer=None,
            processing_time_ms=int((time.time() - start_time) * 1000),
            error="Search timeout"
        )
```

### Phase 3: Optimize Database Queries

**3.1 Batch Context Loading:**
```python
async def get_context_chunks_batch(results: List[dict], limit: int = 10) -> List[dict]:
    """Load all context chunks in single query"""
    if not results:
        return []

    # Extract all segment IDs
    segment_ids = [r["_id"] for r in results[:limit]]

    # Single query with $in operator
    pipeline = [
        {"$match": {"_id": {"$in": segment_ids}}},
        {
            "$lookup": {
                "from": "episode_metadata",
                "localField": "episode_id",
                "foreignField": "guid",
                "as": "metadata"
            }
        },
        {"$unwind": {"path": "$metadata", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "text": 1,
                "episode_id": 1,
                "chunk_index": 1,
                "start_time": "$start_time_seconds",
                "score": 1,
                "podcast_name": "$metadata.podcast_title",
                "episode_title": "$metadata.raw_entry_original_feed.episode_title",
                "published": "$metadata.raw_entry_original_feed.published_date_iso"
            }
        }
    ]

    # Execute with timeout
    chunks_map = {}
    async for chunk in db[EMBEDDINGS_COLLECTION].aggregate(
        pipeline,
        maxTimeMS=15000
    ):
        chunks_map[str(chunk["_id"])] = chunk

    # Preserve original order
    return [chunks_map.get(str(sid)) for sid in segment_ids if str(sid) in chunks_map]
```

### Phase 4: Comprehensive Error Handling

**4.1 Service-Specific Exceptions:**
```python
class ModalTimeoutError(Exception):
    """Modal service timeout"""
    pass

class MongoDBTimeoutError(Exception):
    """MongoDB operation timeout"""
    pass

class SearchTimeoutError(Exception):
    """Overall search timeout"""
    pass
```

**4.2 Handler with Proper Error Handling:**
```python
async def search_handler_with_monitoring(request: SearchRequest) -> SearchResponse:
    """Search with comprehensive error handling"""
    start_time = time.time()
    operation_times = {}

    try:
        # Embedding generation
        embed_start = time.time()
        try:
            embedding = await get_embedding_with_timeout(request.query, 15.0)
            operation_times['embedding_ms'] = int((time.time() - embed_start) * 1000)
        except asyncio.TimeoutError:
            logger.error(f"Modal timeout for query: {request.query}")
            raise ModalTimeoutError("Embedding service unavailable")

        # Search execution
        search_start = time.time()
        try:
            results = await hybrid_search_with_timeout(request.query, embedding)
            operation_times['search_ms'] = int((time.time() - search_start) * 1000)
        except pymongo.errors.ExecutionTimeout:
            logger.error("MongoDB query timeout")
            raise MongoDBTimeoutError("Database query timeout")
        except pymongo.errors.ServerSelectionTimeoutError:
            logger.error("MongoDB connection timeout")
            raise MongoDBTimeoutError("Database connection failed")

        # Synthesis
        if results:
            synth_start = time.time()
            answer = await synthesize_with_timeout(request.query, results)
            operation_times['synthesis_ms'] = int((time.time() - synth_start) * 1000)
        else:
            answer = None

        # Log successful request
        total_time = int((time.time() - start_time) * 1000)
        logger.info(f"Search completed in {total_time}ms", extra={
            'query': request.query,
            'operation_times': operation_times,
            'result_count': len(results)
        })

        return SearchResponse(
            results=results,
            answer=answer,
            processing_time_ms=total_time,
            operation_times=operation_times
        )

    except ModalTimeoutError:
        return SearchResponse(
            results=[],
            answer=None,
            processing_time_ms=int((time.time() - start_time) * 1000),
            error="Embedding service timeout - please try again"
        )
    except MongoDBTimeoutError as e:
        return SearchResponse(
            results=[],
            answer=None,
            processing_time_ms=int((time.time() - start_time) * 1000),
            error=f"Database timeout: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected search error: {e}", exc_info=True)
        return SearchResponse(
            results=[],
            answer=None,
            processing_time_ms=int((time.time() - start_time) * 1000),
            error="Search failed - please try again"
        )
```

### Phase 5: Configuration & Deployment

**5.1 Environment Variables:**
```bash
# Vercel environment variables
MONGODB_URI=mongodb+srv://...
MODAL_EMBEDDING_URL=https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run
OPENAI_API_KEY=sk-...

# Timeout configurations
MODAL_TIMEOUT_SECONDS=15
MONGODB_TIMEOUT_SECONDS=10
SEARCH_TIMEOUT_SECONDS=40
```

**5.2 Vercel Function Configuration:**
```json
// vercel.json
{
  "functions": {
    "api/index.py": {
      "maxDuration": 60  // Increase from default 10s
    }
  }
}
```

## Architecture Context

### System Components
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   API Proxy     │────▶│  Backend API    │
│  (Next.js)      │     │  (/api/search)  │     │ (Vercel Python) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                        ┌─────────────────────────────────┼─────────────┐
                        │                                 │             │
                 ┌──────▼──────┐              ┌──────────▼────┐  ┌─────▼─────┐
                 │   Modal.com  │              │  MongoDB Atlas │  │  OpenAI   │
                 │  Embeddings  │              │ Vector+Text    │  │ Synthesis │
                 └──────────────┘              └────────────────┘  └───────────┘
```

### Data Flow
1. User enters query in command bar
2. Frontend sends POST to `/api/search` proxy
3. Proxy forwards to `https://podinsight-api.vercel.app/api/search`
4. Backend:
   - Generates embedding via Modal (15s timeout)
   - Runs hybrid search on MongoDB (15s timeout)
   - Synthesizes answer with OpenAI (10s timeout)
5. Returns structured response with citations

### Key Files
- **Search Handler**: `/api/search_lightweight_768d.py`
- **Hybrid Search**: `/api/improved_hybrid_search.py`
- **Synthesis**: `/api/synthesis.py`
- **Environment Loader**: `/lib/env_loader.py`
- **API Router**: `/api/index.py`

## Related Documentation Index

### Sprint 3 - Command Bar Implementation
- `/docs/sprint3-command-bar-playbookv2.md` - Complete implementation guide
- `/docs/sprint3/README.md` - Sprint overview
- `/docs/sprint3/implementation_log.md` - Daily progress
- `/docs/sprint3/architecture_updates.md` - System changes

### Sprint 5 - Search Improvements
- `/docs/sprint5/sprint5-synthesis-improvements.md` - Synthesis enhancements
- `/docs/sprint5/search-fix-implementation-plan.md` - Hybrid search implementation
- `/docs/sprint5/fix-cold-start-and-no-results.md` - Timeout fixes
- `/docs/sprint5/MONGODB_AUTH_FIX.md` - Connection fixes

### API Specifications
- `/docs/sprint5/SEARCH_API_IMPLEMENTATION_GUIDE.md` - Frontend expectations
- `/docs/latest/database_field_mapping_rosetta_stone.md` - MongoDB schema

### Business Context
- `/podinsight-business-canvas.md` - Product overview
- `/PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md` - System architecture

## Monitoring & Success Metrics

### Immediate Verification
```bash
# Test endpoint directly
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What are VCs saying about AI valuations?", "limit": 10}' \
  -w "\nTotal time: %{time_total}s\n"
```

### Expected Improvements
| Metric | Before | After |
|--------|--------|-------|
| Response Time (p95) | Timeout (>45s) | <20s |
| Success Rate | 0% (hangs) | >95% |
| Error Visibility | None | Full stack traces |
| Modal Cold Start | Blocks everything | 15s timeout |
| MongoDB Queries | Sequential | Parallel + batch |

### Success Criteria
1. **No More Hanging**: All requests complete or timeout with error
2. **Clear Error Messages**: Users see "Service timeout" not infinite loading
3. **Performance**: 95% of searches complete in <20 seconds
4. **Observability**: Logs show exactly where time is spent

### Monitoring Implementation
```python
# Add to search handler
logger.info("Search metrics", extra={
    "query": request.query,
    "embedding_time_ms": operation_times.get('embedding_ms'),
    "search_time_ms": operation_times.get('search_ms'),
    "synthesis_time_ms": operation_times.get('synthesis_ms'),
    "total_time_ms": total_time,
    "result_count": len(results),
    "success": answer is not None
})
```

### Debugging Commands
```bash
# Check Vercel function logs
vercel logs --follow

# Test Modal endpoint directly
curl -X POST $MODAL_EMBEDDING_URL \
  -H "Content-Type: application/json" \
  -d '{"text": "test query"}' \
  -w "\nTime: %{time_total}s\n"

# Test MongoDB connection
python -c "
from pymongo import MongoClient
import os
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=5000)
print(client.server_info()['version'])
"
```

## Implementation Priority

1. **Critical (Do First)**:
   - Add MongoDB timeouts (prevents hanging)
   - Add Modal timeout wrapper
   - Fix asyncio event loop blocking

2. **High Priority**:
   - Implement batch context loading
   - Add comprehensive error handling
   - Deploy with increased Vercel timeout

3. **Medium Priority**:
   - Add detailed performance logging
   - Implement retry logic for transient failures
   - Set up monitoring alerts

## Summary

The search hanging issue is caused by a perfect storm of missing timeouts, incorrect async patterns, and insufficient error handling. The fixes ensure that every network operation has a timeout, async operations don't block the event loop, and errors are properly caught and reported. This transforms the system from mysteriously hanging to failing fast with actionable error messages, enabling rapid debugging and a much better user experience.

The key insight: **It's better to fail fast with a clear error than to hang forever with no feedback.**
