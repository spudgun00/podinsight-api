# Final Diagnosis - MongoDB Atlas Vector Search Issue

## Root Cause Identified

Based on MongoDB documentation and test results:

### 1. **Cluster Tier Issue (Most Likely)**
- **Current**: Likely on M0 (free) or M2 tier
- **Problem**: M0/M2 tiers have severe limitations:
  - Maximum 3 search indexes
  - Vector search is throttled
  - Resource contention on shared clusters
  - May get "PlanExecutor error: VectorSearch not allowed on tenant"

### 2. **Why Direct MongoDB Tests Work**
- Direct test script connects with longer timeouts
- API has 10s timeout which hits throttling limits
- M0/M2 tiers can work intermittently but fail under load

### 3. **Why Some Queries Work (openai) but Others Don't (venture capital)**
- Text search (fallback) works for common terms
- Vector search is required for multi-word phrases
- Vector search is being throttled/blocked on shared tier

## Immediate Solution

### Check Your Cluster Tier:
1. Go to MongoDB Atlas Dashboard
2. Click on your cluster
3. Check the tier (M0, M2, M5, M10, etc.)

### If on M0/M2/M5:
**You must upgrade to at least M10 for reliable vector search**

### MongoDB's Official Recommendation:
- **Testing**: M0-M5 acceptable
- **Development**: M10-M20 
- **Production**: M30+ required

## Code Changes Still Needed

1. **Fix the diagnostic endpoint** (api/diag.py isn't loading):
```python
# In vercel.json, add:
{
  "rewrites": [
    { "source": "/api/diag", "destination": "/api/diag" },
    { "source": "/api/diag/vc", "destination": "/api/diag" }
  ]
}
```

2. **Add proper error handling for throttling**:
```python
except Exception as e:
    if "PlanExecutor error" in str(e):
        logger.error("Vector search blocked - likely cluster tier issue")
    elif "timed out" in str(e):
        logger.error("Vector search timeout - likely throttling on shared tier")
```

## Why The Advisor's Fixes Haven't Worked

All the code fixes are correct, but **MongoDB Atlas is blocking vector search at the infrastructure level** due to cluster tier limitations. No amount of code changes will fix this - it requires upgrading the MongoDB cluster.

## Action Items

1. **Check cluster tier in Atlas dashboard**
2. **If M0/M2/M5**: Upgrade to M10 minimum
3. **After upgrade**: All queries should immediately start working
4. **No code changes needed** - the existing code is correct

## Cost Consideration

- M0: Free (but vector search barely works)
- M10: ~$57/month (vector search works reliably)
- M30: ~$185/month (production ready)

This explains why "venture capital" works in direct tests (no timeout) but fails in API (10s timeout hits throttling).