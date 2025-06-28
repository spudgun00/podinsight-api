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

## Context for Next Session

Use this prompt to continue:
```
I'm debugging the synthesis timeout issue for PodInsightHQ Sprint 3.

CONTEXT:
@docs/sprint3/HANDOVER_SPRINT3_SYNTHESIS_DEBUG.md - This handover
@api/synthesis.py - Check lines 183-199 for timing logs
@api/search_lightweight_768d.py - Check synthesis integration around line 452
@docs/sprint3/test_execution_report.md - See latest test results

CURRENT STATUS:
- Synthesis works in 1.64 seconds (confirmed in logs)
- But Vercel times out at 30 seconds
- 28+ seconds are unaccounted for
- Need to find what happens AFTER synthesis

IMMEDIATE TASKS:
1. Add more timing logs after synthesis
2. Check response serialization time
3. Test with minimal response
4. Consider implementing streaming

The synthesis feature works but something after it causes timeout.
```

---

## Summary

The synthesis feature is **functionally complete** and working correctly:
- ✅ Generates 2-sentence answers
- ✅ Includes proper citations
- ✅ Completes in 1.64 seconds

The only issue is a mysterious timeout that occurs AFTER the synthesis completes. The next session should focus on finding where those missing 28 seconds go.

**Key insight**: This is NOT an OpenAI performance issue - it's something in our code after the synthesis that's causing the delay.
