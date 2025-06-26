# Sprint Log: MongoDB Vector Search Debugging Session
**Date**: June 26, 2025
**Duration**: ~2 hours
**Status**: ✅ RESOLVED - Vector search now working in production

## 📋 Executive Summary

**Problem**: MongoDB Atlas vector search was returning 0 results in production (Vercel) while working perfectly locally. This had been broken for about a week.

**Root Causes Found**:
1. Missing `time` module import causing NameError
2. MongoDB collection boolean check incompatibility
3. Logging at INFO level not visible in Vercel logs

**Result**: Vector search is now working! "venture capital" query returns 5 relevant results with high similarity scores (0.987-0.992).

## 🔍 The Problem

### Initial Symptoms
- Local test script: ✅ Returns 5 results for "venture capital"
- Production API: ❌ Returns 0 results (falls back to text search)
- Same database, same index, same code - different results

### Test Script That Worked Locally
```python
# scripts/test_venture_capital_query.py
async def test_modal_to_atlas(query="venture capital"):
    # Get embedding from Modal
    response = requests.post(modal_url, json={"text": query})
    embedding = response.json()["embedding"]

    # Search MongoDB Atlas directly
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": embedding,
                "numCandidates": 100,
                "limit": 5
            }
        }
    ]
    results = await db.transcript_chunks_768d.aggregate(pipeline).to_list(None)
    # This returned 5 results locally!
```

## 🛠️ Debugging Process

### Step 1: Enhanced Logging
Added comprehensive debug logging throughout the search pipeline:

**Files Modified**:
- `api/search_lightweight_768d.py` - Added query normalization, embedding validation, fallback tracking
- `api/mongodb_vector_search.py` - Added pipeline logging, raw results output, retry logic

Key additions:
```python
# Added in search_lightweight_768d.py
logger.info(f"[DEBUG] Original query: '{request.query}'")
logger.info(f"[DEBUG] Clean query: '{clean_query}'")
logger.info(f"[DEBUG] Embedding length: {len(embedding_768d)}")
logger.info(f"[DEBUG] First 5 values: {embedding_768d[:5]}")
logger.info(f"[DEBUG] Embedding norm: {norm:.4f}")

# Added in mongodb_vector_search.py
logger.info(f"[VECTOR_SEARCH_START] Called with limit={limit}, min_score={min_score}")
logger.info(f"[DEBUG] raw vector hits: {results[:3] if results else 'EMPTY'}")
```

### Step 2: Diagnostic Endpoints
Created diagnostic endpoints to test MongoDB connection and vector search in isolation:

**File Created**: `api/diag.py`
```python
@app.get("/diag")  # Test MongoDB connection
@app.get("/diag/vc")  # Test full vector search for "venture capital"
```

**Issue**: Vercel routing prevented these from working due to path rewriting in `vercel.json`.

### Step 3: The Advisor's Systematic Approach

The advisor suggested adding unmissable logging to verify code deployment:

1. **BOOT logs** to confirm new code is running:
```python
print(f"[BOOT-TOP] sha={os.getenv('VERCEL_GIT_COMMIT_SHA','local')} py={sys.version.split()[0]}  ts={int(time.time())}", flush=True)
```

2. **Handler identification** to verify correct module is called:
```python
logger.warning("[VECTOR_HANDLER] about to call %s from module %s",
               vector_handler.__class__.__qualname__,
               vector_handler.__class__.__module__)
```

3. **Function entry logs** with WARNING level to ensure visibility:
```python
logger.warning("[VECTOR_SEARCH_ENTER] path=%s idx=%s  len=%d",
               self.collection.full_name if self.collection is not None else "None",
               "vector_index_768d", len(embedding))
```

## 🐛 Root Causes Discovered

### Issue 1: Missing Import
```
ERROR: name 'time' is not defined. Did you forget to import 'time'
```
**Fix**: Added `import time` to `api/search_lightweight_768d.py`

### Issue 2: MongoDB Collection Boolean Check
```
ERROR: Collection objects do not implement truth value testing or bool()
```
**Cause**: PyMongo/Motor collections can't be used in boolean context
**Fix**: Changed `if self.collection` to `if self.collection is not None`

### Issue 3: Logging Visibility
- INFO level logs weren't showing in Vercel
- Changed critical logs to WARNING level
- This revealed the actual errors happening in production

## 📁 Files Modified

### 1. `api/search_lightweight_768d.py`
- Added query normalization: `clean_query = request.query.strip().lower()`
- Added comprehensive DEBUG logging
- Added missing `import time`
- Changed key logs to WARNING level

### 2. `api/mongodb_vector_search.py`
- Fixed collection boolean check
- Added VECTOR_SEARCH_ENTER warning log
- Added OperationFailure exception handling
- Enhanced retry logic with exponential backoff

### 3. `api/diag.py`
- Created diagnostic endpoints (though Vercel routing prevented access)
- Standalone FastAPI app for testing

### 4. `vercel.json`
- Attempted to fix routing for diagnostic endpoints
- Added rewrite rules (ultimately not needed)

## ✅ Final Working Solution

After all fixes were applied:

```bash
curl -s https://podinsight-api.vercel.app/api/search \
     -H 'content-type: application/json' \
     -d '{"query":"venture capital","limit":5}'
```

**Returns**:
```json
{
  "results": [
    {
      "episode_id": "869fe9e8-ca05-11ef-b801-fb878e3f311a",
      "podcast_name": "The Pitch",
      "episode_title": "#156 Barberino's: Italian Luxury Takes on the American Dream",
      "similarity_score": 0.9920226335525513,
      "excerpt": "...venture...",
      ...
    },
    // 4 more results
  ],
  "total_results": 5,
  "search_method": "vector_768d"  // ✅ Using vector search!
}
```

## 📊 Current Status

### What's Working ✅
- MongoDB Atlas vector search returns results
- High-quality similarity matching (scores 0.987-0.992)
- Modal.com embeddings working correctly (768D)
- Fallback to text search when needed
- Proper error handling and logging

### Known Issues ⚠️
- Some queries still timeout (>15s) - appears to be "Event loop is closed" errors
- Supabase UUID errors for non-UUID episode IDs (e.g., "substack:post:123")
- These don't affect vector search but cause fallback delays

### Performance Metrics
- Vector search (when working): 1-3 seconds
- Cold start with timeouts: 14-15 seconds
- Some queries timeout due to retry logic

## 🎯 Key Takeaways

1. **Logging is Critical**: The advisor's emphasis on WARNING-level logs was key to finding the issues
2. **Simple Bugs Can Hide**: Missing `import time` and boolean check caused complete failure
3. **Systematic Debugging Works**: Step-by-step verification from boot to execution
4. **Test in Production**: Local tests can miss production-specific issues

## 📚 References

- **Original Context**: `/advisor_fixes/FULL_CONTEXT_AND_STATUS.md`
- **Test Script**: `/scripts/test_venture_capital_query.py`
- **Implementation Checklist**: `/advisor_fixes/IMPLEMENTATION_CHECKLIST.md`
- **Modal Architecture**: `/MODAL_ARCHITECTURE_DIAGRAM.md`

## 🚀 Next Steps

1. Fix the "Event loop is closed" errors causing timeouts
2. Handle non-UUID episode IDs properly
3. Monitor performance over next 24 hours
4. Consider adding request-level logging for better observability

The vector search is now functional in production after a week of debugging! The issue was ultimately simple bugs that were hidden by insufficient logging.
