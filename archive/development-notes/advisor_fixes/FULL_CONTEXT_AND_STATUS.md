# Full Context and Status - PodInsight API Vector Search Issue

## The Core Problem

We have a MongoDB Atlas vector search that works perfectly locally but returns 0 results in production (Vercel). This has been ongoing for about a week.

### Environment Details
- **MongoDB Atlas**: M20 cluster (AWS London), version 8.0.10
- **Documents**: 823,763 in `transcript_chunks_768d` collection
- **Vector Index**: `vector_index_768d` (READY status)
- **Embedding Service**: Modal.com endpoint for 768D embeddings
- **Deployment**: Vercel serverless functions

### The Mystery
```
Local test: "venture capital" → 5 results ✅
Production API: "venture capital" → 0 results ❌
Same database, same index, same code
```

## Current Status (As of Latest Deployment)

### What's Working
1. **MongoDB Connection** ✅
   - `/api/diag/` returns correct count (823,763 documents)
   - Connection latency ~122ms

2. **Environment Variables** ✅
   ```
   MONGODB_URI = mongodb+srv://podinsight-api:***@podinsight-cluster.bgknvz.mongodb.net/?retryWrites=true&w=majority&appName=podinsight-cluster
   MONGODB_DATABASE = podinsight
   MODAL_EMBEDDING_URL = https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run
   DEBUG_MODE = true
   ```

3. **Text Search Fallback** ✅
   - Some queries work via text search (e.g., "openai")

### What's Not Working
1. **Vector Search Returns 0 Results** ❌
   - All queries fail vector search and fall back to text
   - "venture capital" specifically returns 0 results

2. **Diagnostic VC Endpoint** ❌
   - `/api/diag/vc` returns 404 (routing issue)
   - Would test isolated vector search pipeline

3. **Missing Debug Logs** ❌
   - Not seeing `[VECTOR_SEARCH]` or `[DEBUG] raw vector hits` logs
   - Suggests vector_search function might be failing before execution

## All Relevant Scripts and Code

### 1. Direct MongoDB Test Script (WORKS LOCALLY)
**File: `scripts/test_venture_capital_query.py`**
```python
#!/usr/bin/env python3
"""Test failing queries through all three paths"""

import os
import sys
import asyncio
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def test_modal_to_atlas(query="venture capital"):
    """Test 1: Modal → Atlas (proves embeddings + vector index work)"""
    print(f"\n1. Testing Modal → Atlas for '{query}'")
    print("=" * 60)

    # Get embedding from Modal
    modal_url = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"
    response = requests.post(modal_url, json={"text": query}, timeout=10)

    if response.status_code != 200:
        print(f"❌ Modal error: {response.status_code}")
        return False

    embedding = response.json()["embedding"]
    print(f"✅ Got embedding from Modal (dim: {len(embedding)})")

    # Search MongoDB Atlas
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client.podinsight

    # Vector search pipeline
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": embedding,
                "numCandidates": 100,
                "limit": 5
            }
        },
        {
            "$addFields": {
                "score": {"$meta": "vectorSearchScore"}
            }
        },
        {
            "$project": {
                "text": 1,
                "score": 1,
                "episode_title": 1
            }
        }
    ]

    cursor = db.transcript_chunks_768d.aggregate(pipeline)
    results = await cursor.to_list(None)

    print(f"✅ Vector search returned {len(results)} results")
    for i, result in enumerate(results[:3]):
        print(f"   {i+1}. Score: {result.get('score', 0):.4f}")
        print(f"      Text: {result.get('text', '')[:100]}...")

    client.close()
    return len(results) > 0

# Run with: python scripts/test_venture_capital_query.py
# Result: Returns 5 results for "venture capital"
```

### 2. Diagnostic Endpoint (PARTIALLY WORKING)
**File: `api/diag.py`**
```python
# api/diag.py
import os, time, traceback, logging, requests, math
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import APIRouter
from api.topic_velocity import app

router = APIRouter()

@router.get("/")
async def root():
    """Basic MongoDB connectivity check."""
    # This works! Returns count: 823763

@router.get("/vc")
async def venture_capital():
    """Full Modal->Atlas vector round-trip for 'venture capital'."""
    # This returns 404 - routing issue

app.include_router(router, prefix="/api/diag")
```

### 3. Main Search Handler with Debug Logging
**File: `api/search_lightweight_768d.py`** (key parts)
```python
# Added comprehensive logging
if vector_handler.db is not None:
    logger.info(f"Using MongoDB 768D vector search: {clean_query}")
    logger.info(f"Calling vector search with limit={num_to_fetch}, min_score=0.0")
    try:
        vector_results = await vector_handler.vector_search(
            embedding_768d,
            limit=num_to_fetch,
            min_score=0.0  # Lowered from 0.7 for debugging
        )
    except Exception as ve:
        logger.error(f"[VECTOR_SEARCH_ERROR] Exception during vector search: {str(ve)}")
        logger.error(f"[VECTOR_SEARCH_ERROR] Type: {type(ve).__name__}")
        logger.error(f"[VECTOR_SEARCH_ERROR] Traceback: {traceback.format_exc()}")
        vector_results = []

    # ALWAYS log first result for debugging
    if vector_results:
        logger.info(f"[ALWAYS_LOG] First result score: {first_result.get('score', 'NO_SCORE')}")
    else:
        logger.info(f"[ALWAYS_LOG] Vector search returned EMPTY results for '{clean_query}'")
```

### 4. MongoDB Vector Search Handler
**File: `api/mongodb_vector_search.py`** (key parts)
```python
async def vector_search(self, embedding: List[float], limit: int = 10, min_score: float = 0.7):
    logger.info(f"[VECTOR_SEARCH_START] Called with limit={limit}, min_score={min_score}")

    # MongoDB aggregation pipeline - SAME AS LOCAL TEST
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": embedding,
                "numCandidates": min(limit * 50, 2000),
                "limit": limit
            }
        },
        {"$limit": limit},
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
        {"$match": {"score": {"$gte": 0}}},  # Fixed from {"$exists": True, "$ne": None}
    ]

    cursor = self.collection.aggregate(pipeline)
    results = await cursor.to_list(None)
    logger.info(f"[VECTOR_SEARCH] Attempt {attempt+1} returned {len(results)} results")
    logger.info(f"[DEBUG] raw vector hits: {results[:3] if results else 'EMPTY'}")
```

## Latest Vercel Logs Analysis

```
Jun 25 23:35:39.60 - POST /api/search
INFO:api.search_lightweight_768d:[DEBUG] fallback_used: vector_768d

Jun 25 23:36:14.78 - POST /api/search
WARNING:api.search_lightweight_768d:Returning empty results instead of 503 for debugging
```

**Critical Finding**: Vector search IS being attempted but we're NOT seeing:
- `[VECTOR_SEARCH_START]` - Function entry log
- `[VECTOR_SEARCH]` - Results count log
- `[DEBUG] raw vector hits` - Actual results log
- `[ALWAYS_LOG]` - Empty results confirmation

This suggests the vector_search function is failing before it logs anything.

## Test Commands

```bash
# 1. Test MongoDB connection (WORKS)
curl -s https://podinsight-api.vercel.app/api/diag/ | jq

# 2. Test vector search in isolation (404)
curl -s https://podinsight-api.vercel.app/api/diag/vc | jq

# 3. Test regular search (Returns 0 results)
curl -s -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"venture capital","limit":5}' | jq

# 4. Check Vercel logs
vercel logs podinsight-api --since=5m -f | grep -E "(VECTOR_SEARCH|ALWAYS_LOG|ERROR)"
```

## What We've Tried (Chronologically)

### 1. Environment Variable Fixes ✅
- Added `MONGODB_DATABASE = podinsight`
- Added `MODAL_EMBEDDING_URL`
- Removed database name from MongoDB URI

### 2. Code Fixes (All Implemented) ✅
- Fixed MongoDB pipeline `$match` filter
- Added query normalization (lowercase)
- Increased `numCandidates` to `limit * 50`
- Added retry logic with exponential backoff
- Disabled 503 error for better visibility
- Added comprehensive debug logging

### 3. Diagnostic Endpoints (Partial Success) ⚠️
- `/api/diag/` works - confirms MongoDB connection
- `/api/diag/vc` returns 404 - routing issue prevents isolated test

### 4. Enhanced Logging (Awaiting Results) 🔄
- Added `[VECTOR_SEARCH_START]` at function entry
- Added `[VECTOR_SEARCH_ERROR]` exception handling
- Added `[DEBUG] raw vector hits` to see actual results

## Hypotheses (Ranked by Likelihood)

### 1. **Silent Exception in Vector Search** (Most Likely)
- Vector search function throws exception before logging
- Exception is caught somewhere and returns empty array
- Need to see `[VECTOR_SEARCH_ERROR]` logs

### 2. **MongoDB Aggregation Pipeline Difference**
- Something subtle differs between local and production
- Possibly related to connection pooling or timeout
- The "ReplicaSetNoPrimary" warning suggests connection instability

### 3. **Embedding Mismatch**
- Modal returns different embeddings in production
- Need to log and compare embedding values

### 4. **Index Access Permission**
- Lambda can read documents but not vector index
- Would explain why text search works but vector doesn't

## Next Immediate Steps

### 1. **Wait for Latest Deployment**
The new logging will show:
- If vector_search function is even called
- Any exceptions that occur
- The actual MongoDB response

### 2. **Fix the `/api/diag/vc` Endpoint**
This would allow isolated testing of:
- Modal embedding generation
- Direct MongoDB vector search
- Without the complexity of the main search handler

### 3. **If Still No Logs Appear**
Add logging even earlier in the chain:
- In `get_vector_search_handler()`
- At the very start of search handler
- In the MongoDB connection initialization

## Success Criteria

We'll know we've solved it when:
1. `/api/diag/vc` returns `hits > 0`
2. `/api/search?query=venture capital` returns 5 results
3. We see `[DEBUG] raw vector hits` with actual data

## For New Claude Session

If starting fresh, the key files to examine are:
1. This document: `/advisor_fixes/FULL_CONTEXT_AND_STATUS.md`
2. Test script that works: `/scripts/test_venture_capital_query.py`
3. Main search handler: `/api/search_lightweight_768d.py`
4. Vector search implementation: `/api/mongodb_vector_search.py`
5. Diagnostic endpoint: `/api/diag.py`

The core mystery remains: **Why does the exact same MongoDB query return 5 results locally but 0 in production?**
