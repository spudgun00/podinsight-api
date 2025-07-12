# Search Fix Deployment Checklist

**Date**: 2025-01-12
**Sprint**: 5
**Fix**: Phase 1 - Get Search Working

## Pre-Deployment Checklist

### Code Changes
- [x] `lib/embedding_utils.py` - Made embed_query() async
- [x] `api/search_lightweight_768d.py` - Added await to embed_query call
- [x] `lib/embeddings_768d_modal.py` - Reduced timeout to 15s, added retry logic
- [x] `api/improved_hybrid_search.py` - Updated MongoDB lookups from guid to episode_id

### Testing
- [x] Local test passed - search completes in ~13s
- [x] No more infinite hanging
- [x] Results returned with proper scoring
- [x] Answer synthesis working

## Deployment Steps

1. **Commit Changes**
   ```bash
   git add -A
   git commit -m "fix: Resolve search hanging issue with async Modal embedding

   - Convert embed_query() to async to prevent event loop blocking
   - Reduce Modal timeout from 25s to 15s with retry logic
   - Fix MongoDB field alignment (guid -> episode_id)
   - Search now completes in ~13s instead of hanging infinitely

   Fixes the core search functionality for VC podcast insights"
   ```

2. **Push to GitHub**
   ```bash
   git push origin main
   ```

3. **Vercel Auto-Deploy**
   - Vercel will automatically deploy from main branch
   - Monitor at: https://vercel.com/dashboard

## Post-Deployment Verification

### Immediate (5-10 minutes)
1. **Check Vercel Deployment**
   - Go to Vercel dashboard
   - Verify deployment succeeded
   - Check function logs for errors

2. **Test Production Endpoint**
   ```bash
   curl -X POST https://podinsight-api.vercel.app/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "What are VCs saying about AI valuations?", "limit": 5}' \
     -w "\nTotal time: %{time_total}s\n"
   ```

3. **Monitor Logs**
   ```bash
   vercel logs --follow
   ```

### What to Look For
- ✅ Responses complete within 30s (Vercel limit)
- ✅ No more timeout errors from frontend
- ✅ Modal embedding completes within 15s
- ✅ Search returns actual results

### If Issues Arise
1. **Check Vercel Function Logs**
   - Look for Python errors
   - Check for environment variable issues
   - Verify Modal endpoint is accessible

2. **Quick Rollback**
   ```bash
   git revert HEAD
   git push origin main
   ```

3. **Debug Locally**
   - Pull latest logs
   - Reproduce issue locally
   - Fix and redeploy

## Expected Outcomes

### Success Metrics
- Response time: <20s (production may be slower than local)
- Success rate: >80%
- No infinite hangs
- Clear error messages on timeout

### Known Issues (Phase 2/3)
- MongoDB "ReplicaSetNoPrimary" warnings (auto-recovers)
- Context expansion disabled (N+1 query optimization needed)
- Cold starts still take 13-15s (caching needed)

## Next Steps After Successful Deploy

1. **Monitor for 24 hours**
   - Track success rate
   - Note any timeout patterns
   - Collect user feedback

2. **Begin Phase 2**
   - Add MongoDB connection resilience
   - Implement proper retry logic
   - Add request-level timeouts

3. **Plan Phase 3**
   - Batch context expansion
   - Add Redis caching
   - Implement streaming responses
