# Sprint 3 Synthesis Debugging Handover Document

## Session Summary - December 28, 2024 (Evening - Part 2)

### Latest Update - December 29, 2024 (Debugging with Gemini)

#### What We Did
1. ✅ Brought in Gemini as "Watson" to help investigate the mysterious 28-second gap
2. ✅ Identified Vercel's 5MB response payload limit as prime suspect
3. ✅ Added manual serialization with detailed timing and size logs
4. ✅ Deployed changes (commit: 1364659)
5. ✅ Fixed 500 error by removing FastAPI Response (commit: a0ad64c)
6. ✅ Brought in second Claude who identified DEBUG_MODE issue

#### Critical Discovery
- **Line 485**: `raw_chunks=chunks_for_synthesis if DEBUG_MODE else None`
- If DEBUG_MODE is enabled in production, ALL raw chunks are included in response
- This could make the payload MASSIVE (10+ chunks × full text = potential MB of data)

### What We Accomplished
1. ✅ Identified that the OpenAI API key only has access to `gpt-4o` models
2. ✅ Fixed the model access error by switching to `gpt-4o-mini`
3. ✅ Added timing logs to diagnose performance
4. ✅ Disabled retries to avoid timeout multiplication
5. ✅ Confirmed synthesis is working (generates answers in 1.64 seconds)
6. ❌ Still experiencing Vercel timeout despite fast synthesis

---

## Current Status: Synthesis Works But Times Out

### The Mystery
- OpenAI synthesis completes in 1.64 seconds
- Total processing time is 1.845 seconds
- BUT: Vercel function times out at 30 seconds
- Something is happening AFTER synthesis that causes the timeout

### Latest Code State (Commit: 11857ab)
```python
# api/synthesis.py - Current configuration
model: str = "gpt-4o-mini"  # Changed from gpt-3.5-turbo
max_retries: int = 0  # Reduced from 2 to avoid timeout issues

# Added timing logs:
logger.info(f"OpenAI API call completed in {openai_end - openai_start:.2f} seconds")
```

### Verified Working
From Vercel logs at 19:06:
```
INFO: OpenAI API call completed in 1.64 seconds
INFO: Raw answer from OpenAI: AI valuations are heavily influenced by...
INFO: Synthesis successful: 1 citations
INFO: [DEBUG] synthesis_time_ms: 1654
INFO: [DEBUG] total_time_ms: 1845
```

---

## Critical Files to Review

### 1. Core Implementation Files
- `api/synthesis.py` - Contains the OpenAI integration (line 147: model set to gpt-4o-mini)
- `api/search_lightweight_768d.py` - Main search endpoint (line 452: calls synthesize_with_retry)
- `vercel.json` - Shows maxDuration: 30 seconds limit

### 2. Test Files
- `tests/test_synthesis.py` - Unit tests (all passing)
- `scripts/verify_staging_synthesis.py` - Integration test script

### 3. Documentation
- `docs/sprint3/test_execution_report.md` - Updated with latest findings
- `docs/sprint3/HANDOVER_SPRINT3_PHASE1B_TESTING.md` - Previous debugging session
- `docs/sprint3-command-bar-playbookv2.md` - Original sprint requirements

---

## Key Discoveries

### 1. Available OpenAI Models
Run this to check available models:
```python
# check_models_with_env.py
client = OpenAI(api_key=api_key)
models = client.models.list()
# Result: Only gpt-4o, gpt-4o-2024-05-13, gpt-4o-mini available
```

### 2. Timeout Pattern
- Cold start: ~5-10 seconds
- OpenAI call: ~1.64 seconds
- Total logged time: 1.845 seconds
- Vercel timeout: 30 seconds
- **Missing: 28+ seconds unaccounted for**

---

## PARTIAL SUCCESS! 🎯

### What's Fixed
✅ ObjectId serialization error resolved (commit: a434796)
✅ Synthesis is working successfully
✅ Response size is reasonable (12.3 KB for 10 results)
✅ DEBUG_MODE confirmed disabled

### What's Still Happening - NOT PRODUCTION READY
⚠️ Response times are still slow (21+ seconds) - UNACCEPTABLE
⚠️ Some requests still timeout intermittently
⚠️ Simple queries sometimes timeout while complex ones work

### Performance Breakdown (from logs)
- MongoDB vector search: ~150ms ✅
- OpenAI synthesis: ~2.1s ✅
- **Missing: ~19 seconds somewhere else** ❌

### The ObjectId Fix

The issue was MongoDB ObjectId objects in the response that couldn't be serialized to JSON.

### Root Cause
```
ERROR: Unable to serialize unknown type: <class 'bson.objectid.ObjectId'>
```

When DEBUG_MODE was enabled, `raw_chunks` included MongoDB documents with `_id` fields containing ObjectId objects. Pydantic/FastAPI couldn't serialize these to JSON, causing the timeout.

### The Fix (commit: a434796)
Convert ObjectIds to strings before including chunks in the response:
```python
if "_id" in clean_chunk:
    clean_chunk["_id"] = str(clean_chunk["_id"])
```

### Timeline
1. OpenAI synthesis: 1.64 seconds ✅
2. Response object creation: instant ✅
3. Serialization attempt: FAILED due to ObjectId
4. Error handling and retry attempts: ~28 seconds ⏱️
5. Final timeout: 30 seconds ❌

## SOLUTION FOUND! 🎯

### Root Cause: N+1 Query Problem in expand_chunk_context

With help from Gemini ("Dr. Watson"), we identified the performance bottleneck:

**The Problem:**
- `expand_chunk_context` is called for EACH search result (line 367)
- Each call creates a new MongoDB connection via `get_vector_search_handler()`
- Each call executes a separate MongoDB query
- For 10 results: 10 × ~2 seconds = 20 seconds of delay

**The Evidence:**
```python
# In search_lightweight_768d.py line 367:
for result in paginated_results:
    expanded_text = await expand_chunk_context(result, context_seconds=20.0)

# In expand_chunk_context line 214:
vector_handler = await get_vector_search_handler()  # New connection!
```

### Immediate Fix (Commit: a4546ac)
Temporarily disabled context expansion to restore acceptable performance:
- Commented out the expand_chunk_context call
- Using original chunk text instead
- Added timing logs to confirm the bottleneck
- Expected improvement: 21s → ~3s response time

### Permanent Solution (To Implement)
Replace N+1 queries with batch fetching:

```python
# Instead of calling expand_chunk_context for each result:
# 1. Collect all episode_ids and time windows
time_windows = []
for result in paginated_results:
    time_windows.append({
        "episode_id": result["episode_id"],
        "start": result["start_time"] - 20,
        "end": result["end_time"] + 20
    })

# 2. Single batch query using $or operator
expanded_chunks = await collection.find({
    "$or": [
        {
            "episode_id": tw["episode_id"],
            "start_time": {"$gte": tw["start"], "$lte": tw["end"]}
        }
        for tw in time_windows
    ]
}).to_list(None)

# 3. Group by episode_id and merge texts
# 4. Map back to original results
```

### Additional Optimizations
1. **Connection Pooling**: Reuse MongoDB connections instead of creating new ones
2. **Caching**: Cache expanded contexts for frequently accessed chunks
3. **Async Batching**: Process expansions concurrently if needed

## SOLUTION FOUND!

The issue is almost certainly that **DEBUG_MODE is enabled in production Vercel**, causing `raw_chunks` to be included in the response (line 485).

### Immediate Fix
Remove DEBUG_MODE=true from Vercel environment variables. This will:
- Stop including raw_chunks in responses
- Reduce payload size by 90%+
- Fix the timeout issue

### How to Fix
1. Go to Vercel Dashboard → Settings → Environment Variables
2. Find DEBUG_MODE and set it to "false" or remove it entirely
3. Redeploy

## Next Debugging Steps

### 1. Find the Missing Time
Add more timing logs AFTER synthesis:
```python
# In search_lightweight_768d.py after line 455
logger.info(f"About to create SearchResponse object")
# After creating response
logger.info(f"SearchResponse created, about to return")
```

### 2. Check Response Serialization
The SearchResponse might be too large or have serialization issues:
```python
# Add before return
logger.info(f"Response size estimate: {len(str(response_dict))} chars")
```

### 3. Test Minimal Response
Try returning immediately after synthesis to isolate the issue:
```python
# Temporarily in search endpoint
if synthesis_result:
    return {"answer": synthesis_result.text, "test": "minimal"}
```

### 4. Gemini's Streaming Solution
As suggested by Gemini, implement streaming to avoid timeout:
```python
# Change to streaming response
response = await client.chat.completions.create(
    model=model,
    messages=messages,
    stream=True  # Add this
)
```

---

## Environment Status

### Vercel Environment Variables ✅
- `OPENAI_API_KEY` = Set correctly (sk-proj-...)
- `ANSWER_SYNTHESIS_ENABLED` = "true"

### Vercel Configuration
- Region: lhr1 (London)
- Memory: 1024 MB
- Max Duration: 30 seconds
- Python: 3.12.11

---

## Quick Test Commands

### 1. Test Synthesis
```bash
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI valuations", "limit": 6}' \
  -w "\nStatus: %{http_code}\nTime: %{time_total}s\n"
```

### 2. Check Logs
Watch Vercel logs for timing information:
- Look for: "OpenAI API call completed in X seconds"
- Check what happens after "Synthesis successful"

### 3. Run Verification Script
```bash
source venv/bin/activate
python scripts/verify_staging_synthesis.py
```

---

## Theories to Investigate

### 1. Response Object Issue
The SearchResponse pydantic model might be taking too long to serialize

### 2. Async/Await Issue
There might be an await hanging somewhere after synthesis

### 3. MongoDB Connection
Maybe the connection is timing out after synthesis

### 4. Memory Issue
Large response object causing memory pressure

---

## Next Session Priority - Fix 21+ Second Response Time

### Suspects for the Remaining Slowness
1. **Cold starts** - Vercel function initialization
2. **MongoDB connection pooling** - Maybe recreating connections
3. **Import time** - Heavy imports at module level
4. **Metadata lookups** - Episode/podcast metadata joins
5. **Chunk expansion** - The expand_chunk_context function

### What to Investigate Next
1. Add timing logs around MongoDB connection initialization
2. Check if connection pooling is working properly
3. Time the metadata lookups and joins
4. Profile the entire request path
5. Consider caching strategies

### Quick Test to Run
```bash
# Test if it's consistent or just cold starts
for i in {1..5}; do
    time curl -X POST https://podinsight-api.vercel.app/api/search \
        -H "Content-Type: application/json" \
        -d '{"query": "AI", "limit": 1}' \
        -w "\nTime: %{time_total}s\n"
    sleep 2
done
```

## Context for Next Session

Use this prompt to continue:
```
I'm debugging the synthesis timeout issue for PodInsightHQ Sprint 3.

CONTEXT:
@docs/sprint3/HANDOVER_SPRINT3_SYNTHESIS_DEBUG.md - This handover
@api/synthesis.py - Synthesis takes 2.1s (working fine)
@api/search_lightweight_768d.py - Main search handler
@scripts/test_synthesis_debug.py - Test script showing 21+ second responses

CURRENT STATUS - December 29, 2024:
- ✅ Fixed ObjectId serialization error (was causing timeouts)
- ✅ Synthesis now works successfully
- ❌ Response times are 21+ seconds (NOT PRODUCTION READY)
- ❌ Missing ~19 seconds somewhere in the request path

PERFORMANCE BREAKDOWN:
- MongoDB search: ~150ms ✅
- OpenAI synthesis: ~2.1s ✅
- Unknown delay: ~19s ❌

IMMEDIATE TASKS:
1. Add timing logs around MongoDB connection init
2. Check if connection pooling is working
3. Time metadata lookups and joins
4. Profile cold start vs warm requests
5. Find where the 19 seconds are going

The synthesis feature works but is way too slow for production use.
```

---

## Summary

The synthesis feature is **functionally complete** and working correctly:
- ✅ Generates 2-sentence answers
- ✅ Includes proper citations
- ✅ Completes in 1.64 seconds

The only issue is a mysterious timeout that occurs AFTER the synthesis completes. The next session should focus on finding where those missing 28 seconds go.

**Key insight**: This is NOT an OpenAI performance issue - it's something in our code after the synthesis that's causing the delay.
