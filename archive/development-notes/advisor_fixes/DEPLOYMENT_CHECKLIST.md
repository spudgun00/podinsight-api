# Deployment Checklist for Advisor's Last-Mile Fixes

## Files Changed:

1. **Created `api/__diag.py`** - New diagnostic lambda
   - Access at: `/api/__diag` and `/api/__diag/vc`

2. **Modified `api/search_lightweight_768d.py`**
   - Disabled 503 error (returns empty results instead)
   - Added raw vector hits debug logging

## What to Check After Deployment:

### Step 1: Basic Diagnostic
```bash
curl https://podinsight-api.vercel.app/api/__diag
```
Expected:
- `count`: ~823,763
- `db`: "podinsight"
- All env vars: true

### Step 2: Venture Capital Pipeline Test
```bash
curl https://podinsight-api.vercel.app/api/__diag/vc
```
Expected:
- `hits`: 3-5
- `top`: Array with actual results

### Step 3: Check Vercel Logs
1. Go to Vercel Dashboard → Logs → Realtime
2. Run: `curl -X POST https://podinsight-api.vercel.app/api/search -H "Content-Type: application/json" -d '{"query":"venture capital","limit":5}'`
3. Look for:
   - `[DEBUG] raw vector hits:` log line
   - Any error messages about index/permission/timeout

## Next Steps Based on Results:

**If `/api/__diag/vc` returns hits:**
- Bug is in pagination/post-filter code
- Check the raw vector hits log

**If `/api/__diag/vc` returns 0 or errors:**
- Check Atlas Network Access (0.0.0.0/0 or Vercel IPs)
- Verify cluster tier (M0/M2/M5 may throttle)
- Check exact error message in logs
