# Search API Deployment Checklist

## Pre-Deployment Verification

- [x] Search endpoint implemented in api/search.py
- [x] Integrated into main app (api/topic_velocity.py)
- [x] Dependencies updated in requirements.txt
- [x] Vercel config updated (1024MB memory, 30s timeout)
- [x] Environment variables documented

## Deployment Steps

### 1. Commit and Push Changes

```bash
git add -A
git commit -m "feat: Add search API endpoint with embeddings and caching"
git push origin main
```

### 2. Deploy to Vercel

```bash
vercel --prod
```

### 3. Verify Deployment

```bash
# Test health check
curl https://podinsight-api.vercel.app/

# Test search endpoint
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI agents and startup valuations",
    "limit": 5
  }'
```

## Expected Challenges

### 1. Large Dependencies
- sentence-transformers + torch = ~500MB
- Vercel has a 250MB deployment size limit
- **Solution**: May need to use Lambda Layers or external model hosting

### 2. Cold Start Time
- Model loading takes 1-2s
- First request will be slow
- **Solution**: Keep-warm strategy or accept the latency

### 3. Memory Usage
- Model requires ~500MB RAM
- Already configured 1024MB in vercel.json
- Monitor for OOM errors

## Post-Deployment Tests

### 1. Basic Search Test
```bash
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "blockchain DeFi", "limit": 3}'
```

### 2. Cache Test
```bash
# Run same query twice
for i in {1..2}; do
  echo "Request $i:"
  time curl -X POST https://podinsight-api.vercel.app/api/search \
    -H "Content-Type: application/json" \
    -d '{"query": "test caching", "limit": 1}'
  echo ""
done
```

### 3. Rate Limit Test
```bash
# Send 25 requests rapidly
for i in {1..25}; do
  curl -X POST https://podinsight-api.vercel.app/api/search \
    -H "Content-Type: application/json" \
    -d '{"query": "rate limit test", "limit": 1}' &
done
wait
```

### 4. Error Handling Test
```bash
# Invalid query length
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "'$(python3 -c "print('x'*501))'", "limit": 10}'
```

## Monitoring

- Check Vercel Function logs for errors
- Monitor cold start times
- Track memory usage
- Verify rate limiting is working

## Rollback Plan

If deployment fails:
1. `vercel rollback` to previous version
2. Remove sentence-transformers temporarily
3. Implement lightweight embedding API call instead