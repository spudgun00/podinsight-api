# Implementation Checklist - Advisor's Deep Debugging Fixes

## ✅ Fix 1: Get the diagnostic function building

### 1.1 Add missing dependencies ✅
**Action taken:**
- Added `requests==2.32.3` to requirements.txt
- `pymongo==4.7.2` and `motor==3.4.0` already present

### 1.2 Rename and restructure diagnostic file ✅
**Action taken:**
- Deleted old `api/diag.py`
- Created new `api/diag/index.py` directory structure
- This will deploy as `/api/diag` endpoint

### 1.3 Export proper ASGI app ✅
**Action taken:**
- Created router-based implementation using `APIRouter`
- Mounted on existing FastAPI app from `topic_velocity.py`
- No duplicate FastAPI instances

### 1.4 Complete diagnostic implementation ✅
**File created: `api/diag/index.py`**
```python
# Key features implemented:
- Async motor client (not sync pymongo)
- Proper error handling with traceback logging
- Timing measurements for each step
- Reuses existing embed_query function
- Returns detailed error info if any step fails
```

## ✅ Fix 2: Surface real stack traces

### 2.1 Enhanced logging ✅
**Actions taken:**
- Added `traceback.format_exc()` to all error handlers
- Added timing logs for each operation:
  - `⏱️ embed_query ok (X ms)`
  - `⏱️ mongo connect ok (X ms)`  
  - `⏱️ vector search ok (X ms)`
- Log embedding first 5 values for verification

### 2.2 Remove 503 gate ✅
**Already completed:**
- Modified `api/search_lightweight_768d.py` to return empty results instead of 503
- This allows us to see actual errors in logs

## ✅ Fix 3: Network reachability tests

### 3.1 Diagnostic routes test both services ✅
**Routes created:**
- `/api/diag` - Tests MongoDB connection only
- `/api/diag/vc` - Tests Modal embedding + MongoDB vector search

### 3.2 Error identification helpers ✅
**What each error means:**
- `ConnectTimeout` on embed_query → Vercel can't reach Modal
- `ServerSelectionTimeoutError` → Vercel can't reach MongoDB Atlas
- `OperationFailure: index not found` → Wrong database or index name
- Returns 0 hits but no error → Vector search executed but found nothing

## Files Changed Summary

1. **Created `api/diag/index.py`** - Proper diagnostic lambda with:
   - Async MongoDB operations
   - Full error tracebacks
   - Timing measurements
   - Network connectivity tests

2. **Created `api/diag/__init__.py`** - Makes it a proper Python package

3. **Updated `requirements.txt`** - Added `requests==2.32.3`

4. **Previously updated `api/search_lightweight_768d.py`**:
   - Disabled 503 error
   - Added raw vector hits logging
   - Returns empty results to see errors

## Expected Results After Deployment

### Test 1: Basic connectivity
```bash
curl https://podinsight-api.vercel.app/api/diag
```
Should return:
```json
{
  "db": "podinsight",
  "count": 823763,
  "env": {
    "MONGODB_URI": true,
    "MONGODB_DATABASE": true,
    "MODAL_EMBEDDING_URL": true
  }
}
```

### Test 2: Full vector search
```bash
curl https://podinsight-api.vercel.app/api/diag/vc
```
Should return:
```json
{
  "hits": 3,
  "top": [/* array of results with scores */]
}
```

### Test 3: Check logs for timing
```bash
vercel logs podinsight-api --since=10m --region all | grep -E "(⏱️|ERROR|diag)"
```

## If Still Failing - Check These

1. **MongoDB Atlas Network Access**
   - Needs `0.0.0.0/0` or Vercel IP ranges added
   
2. **Modal endpoint accessibility**
   - Check if Modal allows Vercel's egress IPs
   
3. **Exact error from logs**
   - The traceback will show exactly where it's failing

## Status: Ready to Deploy

All changes implemented per advisor's specifications. The diagnostic endpoints will now:
1. Actually deploy (proper structure)
2. Show real errors (traceback logging)
3. Test both MongoDB and Modal connectivity
4. Provide timing information for debugging