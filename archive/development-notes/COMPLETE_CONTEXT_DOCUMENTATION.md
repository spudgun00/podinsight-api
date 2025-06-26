# Complete Context Documentation: MongoDB Vector Search Fix
**Created**: June 26, 2025
**Purpose**: Full documentation for next session - leave no stone unturned

## 🎯 Executive Summary

**What Was Broken**: MongoDB Atlas vector search was returning 0 results in production (Vercel) while working perfectly locally. This had been broken for about a week.

**What We Fixed**:
1. Missing `import time` in search handler
2. MongoDB collection boolean check incompatibility
3. Logging visibility issues (INFO vs WARNING level)

**Current Status**: ✅ Vector search is now working! "venture capital" returns 5 results with high similarity scores (0.987-0.992).

**Remaining Issues**:
- Some queries timeout due to "Event loop is closed" errors
- Supabase UUID validation errors for non-UUID episode IDs

## 📁 Critical Files & Their Purpose

### 1. Core Search Implementation
```
api/search_lightweight_768d.py
```
- **Purpose**: Main search handler that orchestrates vector, text, and fallback search
- **Key Functions**:
  - `search_handler_lightweight_768d()` - Main entry point
  - Normalizes queries to lowercase
  - Generates 768D embeddings via Modal
  - Falls back through vector → text → pgvector
- **Recent Changes**:
  - Added `import time` (was missing!)
  - Added comprehensive DEBUG logging
  - Changed critical logs to WARNING level

### 2. MongoDB Vector Search Handler
```
api/mongodb_vector_search.py
```
- **Purpose**: Handles vector search queries to MongoDB Atlas
- **Key Functions**:
  - `vector_search()` - Executes $vectorSearch aggregation
  - `_enrich_with_metadata()` - Adds episode data from Supabase
- **Recent Changes**:
  - Fixed `if self.collection` → `if self.collection is not None`
  - Added VECTOR_SEARCH_ENTER warning log
  - Added OperationFailure exception handling

### 3. Test Scripts

#### Local Test That Works
```
scripts/test_venture_capital_query.py
```
- **Purpose**: Proves that Modal→MongoDB pipeline works
- **Usage**: `python3 scripts/test_venture_capital_query.py`
- **What it does**:
  1. Gets embedding from Modal for "venture capital"
  2. Queries MongoDB directly with $vectorSearch
  3. Returns 5 results (works locally!)

#### E2E Production Test
```
scripts/test_e2e_production.py
```
- **Purpose**: Comprehensive production testing
- **Usage**: `python3 scripts/test_e2e_production.py`
- **Tests**:
  - Health endpoint
  - Cold start timing
  - VC-specific queries
  - Bad input handling
  - Unicode support
  - Concurrent requests

### 4. Diagnostic Endpoints
```
api/diag.py
```
- **Purpose**: Test MongoDB and Modal connections in isolation
- **Endpoints**:
  - `/api/diag` - Basic MongoDB connection test
  - `/api/diag/vc` - Full vector search for "venture capital"
- **Note**: Currently not accessible due to Vercel routing issues

### 5. Configuration Files
```
vercel.json
```
- Contains routing rules that redirect all `/api/*` to `/api/index`
- This prevented diagnostic endpoints from working

```
.env (Vercel Environment Variables)
```
- `MONGODB_URI` - Connection string to Atlas
- `MONGODB_DATABASE` - Should be "podinsight"
- `MODAL_EMBEDDING_URL` - Modal.com endpoint for embeddings

## 🔍 The Debugging Journey

### Step 1: Problem Identification
- **Symptom**: Vector search returns 0 results in production
- **Evidence**:
  ```
  Local: "venture capital" → 5 results ✅
  Production: "venture capital" → 0 results ❌
  ```

### Step 2: Enhanced Logging Added
```python
# In search_lightweight_768d.py
logger.info(f"[DEBUG] Original query: '{request.query}'")
logger.info(f"[DEBUG] Clean query: '{clean_query}'")
logger.info(f"[DEBUG] Embedding length: {len(embedding_768d)}")
logger.info(f"[DEBUG] First 5 values: {embedding_768d[:5]}")

# In mongodb_vector_search.py
logger.info(f"[VECTOR_SEARCH_START] Called with limit={limit}")
logger.info(f"[DEBUG] raw vector hits: {results[:3]}")
```

### Step 3: Advisor's Systematic Approach
The advisor suggested unmissable logging:

1. **BOOT logs** - Verify new code is deployed
2. **Handler identification** - Confirm correct module is called
3. **Function entry logs** - Use WARNING level for visibility

### Step 4: Root Causes Found

#### Issue 1: Missing Import
```python
# Error: name 'time' is not defined
start = time.time()  # Failed because time wasn't imported!
```

#### Issue 2: MongoDB Collection Check
```python
# Error: Collection objects do not implement truth value testing
if self.collection:  # Wrong!
if self.collection is not None:  # Correct!
```

#### Issue 3: Logging Level
- INFO logs weren't visible in Vercel
- Changed to WARNING for critical debug messages

## 📊 Current Test Results

### Working Queries ✅
```bash
# These return results
"AI startup valuations" → 5 results
"venture capital" → 5 results
"OpenAI" → Multiple results
"artificial intelligence" → 10 results
```

### Problematic Queries ⚠️
```bash
# These timeout or return 0 results
"founder burnout mental health" → Timeout
"product market fit indicators" → Timeout
"Series A metrics benchmarks" → 0 results
```

### Error Patterns
1. **"Event loop is closed"** - Causes retries and timeouts
2. **UUID validation errors** - Non-UUID episode IDs like "substack:post:123"
3. **Fallback cascade** - Vector → Text → pgvector adds latency

## 🧪 How to Test

### 1. Quick API Test
```bash
# Test vector search
curl -s https://podinsight-api.vercel.app/api/search \
     -H 'content-type: application/json' \
     -d '{"query":"venture capital","limit":5}' | jq

# Expected: 5 results with search_method: "vector_768d"
```

### 2. Website Testing
Yes, you can test using `test-podinsight-combined.html`!

**How to use**:
1. Open the file in a browser
2. Tab 1: Transcript Search
   - Try queries like "AI startup valuations"
   - Watch for relevance scores and response times
3. Tab 2: Entity Search
   - Search for "OpenAI" or "Sequoia Capital"
   - Shows mention counts and trends

**What to look for**:
- First search: ~14s (cold start)
- Subsequent searches: <1s (warm)
- Relevance scores: 85-95% for good matches

### 3. Comprehensive E2E Test
```bash
# Full test suite (includes waits)
python3 scripts/test_e2e_production.py

# Quick VC test (5 minutes)
python3 scripts/quick_e2e_test.py
```

## 🚨 Current Issues to Address

### 1. Event Loop Closed Errors
```
WARNING:api.mongodb_vector_search:Vector search attempt 1 failed, retrying in 2s: Event loop is closed
```
- Causes unnecessary retries
- Adds 6+ seconds to response time
- Needs investigation of async connection handling

### 2. Supabase UUID Errors
```
ERROR: invalid input syntax for type uuid: "substack:post:163244751"
```
- Non-UUID episode IDs from Substack
- Causes text search fallback to fail
- Need to handle mixed ID formats

### 3. Timeout Issues
- Some queries take >15 seconds
- Likely due to retry logic + fallback cascade
- Consider reducing retry attempts

## 📈 Next Steps

### Immediate Actions
1. **Fix "Event loop is closed" errors**
   - Check MongoDB connection pooling
   - Verify async context management
   - Consider connection warmup

2. **Handle non-UUID episode IDs**
   - Filter out non-UUID IDs before Supabase query
   - Or migrate away from Supabase enrichment

3. **Add request-level logging**
   - Track full request lifecycle
   - Identify bottlenecks in fallback chain

### Testing Checklist
- [ ] Test all example queries in website
- [ ] Monitor for "Event loop" errors in logs
- [ ] Check cold start times (<15s expected)
- [ ] Verify warm request times (<1s expected)
- [ ] Test concurrent requests don't cause issues

## 🔧 How to Debug Further

### 1. Check Logs
```bash
# View recent logs
vercel logs https://podinsight-api.vercel.app --output raw | tail -100

# Search for specific patterns
vercel logs https://podinsight-api.vercel.app | grep -E "(VECTOR_SEARCH|ERROR|WARNING)"
```

### 2. Key Log Patterns
- `[BOOT-TOP]` - Confirms new code deployment
- `[VECTOR_HANDLER]` - Shows which handler is called
- `[VECTOR_SEARCH_ENTER]` - Vector search started
- `[VECTOR_LATENCY]` - How long vector search took
- `Event loop is closed` - Connection issue

### 3. MongoDB Atlas Checks
- Verify index name: `vector_index_768d`
- Check index status (should be READY)
- Confirm database: `podinsight`
- Collection: `transcript_chunks_768d`

## 📚 Supporting Documentation

### In This Repository
- `/advisor_fixes/FULL_CONTEXT_AND_STATUS.md` - Original problem description
- `/advisor_fixes/IMPLEMENTATION_CHECKLIST.md` - What was implemented
- `/SPRINT_LOG_VECTOR_SEARCH_DEBUG.md` - Today's debugging session
- `/MODAL_ARCHITECTURE_DIAGRAM.md` - System architecture

### Key Code Sections
- Query normalization: `search_lightweight_768d.py:262`
- Vector search call: `search_lightweight_768d.py:299-304`
- MongoDB aggregation: `mongodb_vector_search.py:111-147`
- Error handling: Throughout both files

## ✅ Victory Conditions

The system will be fully operational when:
1. All example queries return results in <5s (warm)
2. No "Event loop is closed" errors
3. UUID errors don't break search flow
4. Diagnostic endpoints are accessible
5. 95%+ queries use vector search (not fallback)

## 🎯 Testing Script for Next Session

```python
# Save as test_current_status.py
import requests
import time

queries = [
    "venture capital",
    "AI startup valuations",
    "product market fit",
    "founder burnout",
    "Series A metrics"
]

for query in queries:
    start = time.time()
    try:
        resp = requests.post(
            "https://podinsight-api.vercel.app/api/search",
            json={"query": query, "limit": 3},
            timeout=20
        )
        data = resp.json()
        elapsed = time.time() - start

        print(f"\n{query}:")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Results: {len(data.get('results', []))}")
        print(f"  Method: {data.get('search_method', 'unknown')}")

    except Exception as e:
        print(f"\n{query}: ERROR - {e}")
```

This document contains everything needed to understand the current state and continue debugging in the next session.
