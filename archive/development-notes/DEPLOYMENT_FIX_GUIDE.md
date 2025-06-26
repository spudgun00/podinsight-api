# Deployment Fix Guide

## Issue Found
The Vercel deployment was failing with:
```
ModuleNotFoundError: No module named 'api.test_search'
```

## Root Cause
- The `api/topic_velocity.py` file was importing a test module that doesn't exist in production
- CLI tests were running locally, not against the deployed endpoints

## Fix Applied
1. Commented out the test endpoint import in `api/topic_velocity.py` (lines 743-748)
2. This removes the `/api/test-search` endpoint from production

## Deploy the Fix

```bash
# 1. Commit the fix
git add api/topic_velocity.py
git commit -m "fix: Remove test endpoint import causing production deployment error"

# 2. Push to trigger deployment
git push

# 3. Or manually deploy
vercel --prod
```

## Test the Fix

### Quick Test (2 minutes)
```bash
# Test health endpoint
curl https://podinsight-api.vercel.app/api/health

# Test search endpoint
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI startups", "limit": 5}'
```

### Full E2E Test Suite (30 minutes)
```bash
# Run comprehensive production tests
python scripts/test_e2e_production.py
```

This will test:
1. Health endpoint
2. Cold start performance (~14s expected)
3. Warm requests (<1s expected)
4. Bad input handling
5. Unicode/emoji support
6. Concurrent requests
7. Snapshot verification

## Using the Test HTML

The `test-podinsight-advanced.html` now includes:
- Auto-logging of all requests
- Session history tracking
- Downloadable test reports (JSON + TXT)
- Keyboard shortcuts (Ctrl+S to save logs)

```bash
# Open test interface
open test-podinsight-advanced.html
```

## Important Notes

1. **Always test against production endpoints**, not local scripts
2. **Monitor Modal dashboard** during tests for container scaling
3. **Check Vercel logs** for any Lambda errors
4. **Cold starts are expected** to be ~14s (first request) then ~6s (with snapshots)

## Success Criteria

✅ Health endpoint returns 200
✅ Search endpoint returns results
✅ No 500 errors in logs
✅ Warm requests <1s
✅ Cold start <20s
✅ Unicode queries work
✅ 95%+ success rate on concurrent requests
