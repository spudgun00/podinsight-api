# Dashboard API Fix Summary

**Date**: 2025-01-13
**Issue**: All dashboard APIs returning 500 errors after rollback to commit a541bbb

## Issues Found & Fixed

### 1. Prewarm Endpoint (404 → Fixed)
**Problem**: `prewarm.py` was creating its own FastAPI app instead of exporting a router
**Fix**: Changed to use APIRouter pattern consistent with other modules
```python
# Before:
app = FastAPI()
@app.post("/api/prewarm")

# After:
router = APIRouter(prefix="/api", tags=["prewarm"])
@router.post("/prewarm")
```

### 2. Import Path Issues
**Problem**: Absolute imports failing in Vercel environment
**Fix**: Changed to relative imports
```python
# Before:
from api.search_lightweight_768d import generate_embedding_768d_local

# After:
from .search_lightweight_768d import generate_embedding_768d_local
```

## Remaining Issues to Investigate

### Dashboard & Topics API 500 Errors
Likely causes based on Gemini's analysis:
1. **Environment Variables**: Check if `MONGODB_URI` and `MONGODB_DATABASE` are set in Vercel
2. **Database Connection**: MongoDB might be timing out or credentials changed
3. **Module Import Order**: The mounting order in `index.py` might be causing conflicts

## Immediate Actions Needed

1. **Check Vercel Environment Variables**:
   - Go to Vercel Dashboard → Project Settings → Environment Variables
   - Verify these are set:
     - `MONGODB_URI`
     - `MONGODB_DATABASE`
     - `OPENAI_API_KEY`
     - Any other API keys

2. **Deploy the Prewarm Fix**:
   ```bash
   git add api/prewarm.py
   git commit -m "fix: Convert prewarm to router pattern and fix imports"
   git push
   ```

3. **Monitor Vercel Logs**:
   - After deployment, check Function Logs in Vercel Dashboard
   - Look for specific Python stack traces for 500 errors
   - Common errors to look for:
     - `pymongo.errors.ServerSelectionTimeoutError`
     - `KeyError` for missing environment variables
     - Import errors

## Testing After Deployment

```bash
# Test prewarm endpoint
curl -X POST https://podinsight-api.vercel.app/api/prewarm

# Test dashboard endpoint
curl https://podinsight-api.vercel.app/api/intelligence/dashboard

# Test topics endpoint
curl "https://podinsight-api.vercel.app/api/topics?tags=AI"
```

## Frontend Status

✅ Search proxy created and working
✅ Frontend updated to use proxy instead of direct API calls
⏳ Waiting for backend fixes to be deployed

## Root Cause Analysis

The rollback to commit a541bbb likely worked initially but:
1. Environment variables might have changed since then
2. Database schema might have evolved
3. The prewarm endpoint was added after a541bbb but implemented incorrectly

## Next Steps

1. Deploy the prewarm fix
2. Check Vercel environment variables
3. Monitor logs for specific error messages
4. If MongoDB connection issues, may need to:
   - Update connection string
   - Check database access permissions
   - Verify replica set configuration
