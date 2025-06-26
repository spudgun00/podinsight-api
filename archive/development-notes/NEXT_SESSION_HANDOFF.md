# Next Session Handoff - Modal Deployment & Testing

## 🎯 Primary Objective
Deploy the optimized Modal endpoint and verify search works with <1 second response times

## 📋 Current Status

### What Was Done This Session
1. **Root Cause Identified**: Modal running on CPU, no snapshots, 60s container lifetime
2. **Solution Created**: Optimized Modal deployment with GPU, snapshots, volume caching
3. **Documentation Complete**: Problem analysis, fix explanation, cost breakdown
4. **Code Ready**: All files created and pushed to GitHub

### What Needs to Be Done
1. Deploy optimized Modal endpoint
2. Update environment variables
3. Test search performance
4. Verify results quality

## 🚀 Step-by-Step Deployment Guide

### Step 1: Deploy to Modal
```bash
# Make sure you're in the project root
cd /Users/jamesgill/PodInsights/podinsight-api

# Run the deployment script
./scripts/deploy_modal_optimized.sh

# Expected output:
# - "Deployment complete!"
# - Modal dashboard URL
# - New endpoint URL (save this!)
```

### Step 2: Get Your Endpoint URL
1. Go to [Modal Dashboard](https://modal.com/apps)
2. Find "podinsight-embeddings-optimized"
3. Copy the endpoint URL (looks like: https://[workspace]--podinsight-embeddings-optimized-embedder-web-embed-single.modal.run)

### Step 3: Update Environment Variables
```bash
# Edit .env file
# Change MODAL_EMBEDDING_URL to your new endpoint URL
MODAL_EMBEDDING_URL=https://[your-new-modal-url]/embed
```

### Step 4: Test Modal Endpoint Directly
```bash
# Test health check
curl https://[your-modal-url]/health

# Test embedding generation (expect 7s first time)
time curl -X POST https://[your-modal-url]/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "venture capital"}' | jq

# Test again (expect <200ms)
time curl -X POST https://[your-modal-url]/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "artificial intelligence"}' | jq
```

### Step 5: Update Vercel Environment
```bash
# Update Vercel with new Modal URL
vercel env pull
# Edit .env.local with new MODAL_EMBEDDING_URL
vercel env add MODAL_EMBEDDING_URL
# Enter the new URL when prompted
```

### Step 6: Test Complete Search Pipeline
```bash
# First search - expect ~7-10 seconds total (Modal cold start)
time curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "artificial intelligence", "limit": 3}' | jq

# Second search - expect <1 second total (Modal warm)
time curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "venture capital funding", "limit": 5}' | jq

# Third search - test different queries
time curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "startup acquisitions", "limit": 3}' | jq
```

## 📊 Expected Results

### Performance Metrics
| Test | Expected Time | Status |
|------|--------------|--------|
| Modal Health Check | <500ms | Should show GPU available |
| First Embedding (cold) | ~7 seconds | Container starting up |
| Second Embedding (warm) | <200ms | Container already running |
| First Search (cold) | ~8-10 seconds | Modal cold + MongoDB |
| Subsequent Searches | <1 second | Everything warm |

### Response Quality
- Should return actual podcast excerpts
- Relevance scores between 0.6-0.95
- Results should match query semantics
- Metadata should include episode info

## 🧪 Comprehensive Testing Plan

### 1. Basic Functionality Tests
```bash
# Run from scripts directory
cd scripts

# Test 1: Verify Modal GPU
curl https://[modal-url]/health | jq '.gpu_available'
# Expected: true

# Test 2: Search quality
python3 <<EOF
import json
queries = [
    "AI and machine learning",
    "Series A funding",
    "crypto and blockchain",
    "SaaS metrics",
    "founder advice"
]
for q in queries:
    print(f"Testing: {q}")
    # Add search API call here
EOF
```

### 2. Performance Tests
```bash
# Cold start test (wait 10+ minutes first)
sleep 600 && time curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test cold start", "limit": 1}'

# Warm performance test (rapid fire)
for i in {1..10}; do
  time curl -X POST https://podinsight-api.vercel.app/api/search \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"test query $i\", \"limit\": 3}" \
    -o /dev/null -s
done
```

### 3. Filter Tests (if search is working)
```bash
# Test filter by podcast
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence",
    "limit": 5,
    "filter": {"feed_slug": "acquired"}
  }' | jq
```

## 🚨 Troubleshooting Guide

### If Modal deployment fails:
1. Check Modal CLI is authenticated: `modal token show`
2. Verify you have credits: Check Modal dashboard
3. Try deploying with T4 instead of A10G (edit the file)

### If search still times out:
1. Check Modal logs: `modal logs podinsight-embeddings-optimized`
2. Verify GPU is allocated: Check health endpoint
3. Check container is staying warm: Monitor Modal dashboard

### If results are empty:
1. MongoDB index should already be active
2. Check Modal is returning valid embeddings
3. Verify environment variables are updated

## 📈 Success Criteria

✅ **Deployment Success**:
- Modal endpoint deployed and accessible
- Health check shows GPU available
- First embedding takes ~7s, subsequent <200ms

✅ **Search Success**:
- First search takes <10 seconds
- Subsequent searches take <1 second
- Results contain relevant podcast excerpts
- No timeout errors

✅ **Quality Success**:
- Search results are semantically relevant
- Scores are in reasonable range (0.6-0.95)
- Different queries return different results

## 💰 Cost Monitoring

Check Modal dashboard for:
- GPU seconds used
- Number of cold starts
- Estimated monthly cost

Expected: <$10/month at current usage

## 📝 Notes for Next Session

1. The Modal fix addresses the root cause - no more 150s timeouts
2. Cold starts are acceptable at 7s with good UX
3. Monitor if cold starts become frequent → consider min_containers=1
4. All code is ready, just needs deployment
5. $5,000 Modal credits will last years at this rate

## 🎯 Quick Start Commands

```bash
# 1. Deploy
./scripts/deploy_modal_optimized.sh

# 2. Test
curl https://[modal-url]/health

# 3. Search
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI startups", "limit": 3}'
```

---

**Remember**: The fix is already coded and ready. You just need to deploy it and verify it works!
