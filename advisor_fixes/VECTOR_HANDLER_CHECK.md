# Vector Handler Check - What to Look For

## What I Added

In `search_lightweight_768d.py`, just before the vector_search call:

```python
logger.info(
    "[VECTOR_HANDLER] about to call %s from module %s",
    vector_handler.__class__.__qualname__,
    vector_handler.__class__.__module__,
)
```

And after the await:
```python
logger.info("[VECTOR_LATENCY] %.1f ms", (time.time()-start)*1000)
```

## What to Check After Deployment

1. Trigger a search:
```bash
curl -s https://podinsight-api.vercel.app/api/search \
     -H 'content-type: application/json' \
     -d '{"query":"venture capital","limit":5}'
```

2. Check logs for these patterns:
```bash
vercel logs podinsight-api --since 5m --region all | grep -E "(BOOT-TOP|VECTOR_HANDLER|VECTOR_LATENCY|VECTOR_SEARCH_ERROR)" -A1
```

## Expected Outcomes

### If VECTOR_HANDLER shows the expected module:
- Shows: `[VECTOR_HANDLER] about to call MongoDBVectorSearch from module api.mongodb_vector_search`
- Means: We're calling the right handler, but it's failing before first log
- Next: Check if VECTOR_LATENCY appears (if yes, function returned; if no, it threw)

### If VECTOR_HANDLER shows a different module:
- Shows: Different module path like `src.mongodb_vector_search` or `podinsight.mongodb_search`
- Means: Shadow/duplicate file is being imported
- Next: Clean up duplicate or fix import path

### If no VECTOR_HANDLER appears:
- Means: Code never reaches the vector_search call
- Next: Look for early returns in the function

## Key Logs to Report Back
```
[BOOT-TOP] ...
[VECTOR_HANDLER] ...
[VECTOR_LATENCY] ...
[VECTOR_SEARCH_ERROR] ...
```