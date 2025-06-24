# Modal.com Operations Guide - Deployment & Management

> **📅 Created**: June 24, 2025  
> **🎯 Purpose**: Operational procedures for managing Modal.com integration  
> **⚡ Status**: Production deployment guide

## 🚀 QUICK REFERENCE

### Emergency Controls
```bash
# STOP Modal endpoint (immediate)
modal app stop podinsighthq--podinsight-embeddings-simple

# START Modal endpoint
modal deploy scripts/modal_web_endpoint_simple.py

# Check status
modal app list | grep podinsight
```

---

## 🔄 SWITCHING API ON/OFF

### 1. Disable Modal.com (Fallback to Basic Search)

**When to disable:**
- Cost concerns (exceeded budget)
- Performance issues with Modal
- Testing fallback mechanisms
- Emergency situations

**Steps to disable:**
```bash
# 1. Set environment variable in Vercel
vercel env add MODAL_ENABLED production
# Enter: false

# 2. Or update search handler to skip Modal
# In api/search_lightweight_768d.py, set:
USE_MODAL = False  # Line 15 (approx)

# 3. Redeploy Vercel
vercel --prod
```

**What happens:**
- Search falls back to MongoDB text search
- Quality drops to 60-70% relevance
- No semantic understanding
- Faster but less accurate

### 2. Enable Modal.com (Full AI Search)

**Steps to enable:**
```bash
# 1. Ensure Modal app is deployed
modal deploy scripts/modal_web_endpoint_simple.py

# 2. Set environment variable
vercel env add MODAL_ENABLED production
# Enter: true

# 3. Test endpoint
curl https://podinsighthq--podinsight-embeddings-simple-health-check.modal.run

# 4. Redeploy Vercel
vercel --prod
```

### 3. Gradual Rollout (A/B Testing)

**For safe deployment:**
```python
# In search handler, implement percentage routing:
import random

def should_use_modal():
    # Start with 10% traffic
    return random.random() < 0.10  # Increase gradually
```

---

## 📦 DEPLOYMENT PROCEDURES

### Modal.com Deployment

#### Initial Setup
```bash
# 1. Install Modal CLI
pip install modal

# 2. Authenticate
modal token new

# 3. Create app (first time only)
modal app create
```

#### Deploy/Update Endpoint
```bash
# 1. Test locally first
modal run scripts/modal_web_endpoint_simple.py

# 2. Deploy to production
modal deploy scripts/modal_web_endpoint_simple.py

# 3. Verify deployment
modal app list
# Should show: podinsighthq--podinsight-embeddings-simple

# 4. Test health endpoint
curl https://podinsighthq--podinsight-embeddings-simple-health-check.modal.run
```

#### Configuration Options
```python
# In modal_web_endpoint_simple.py

# Adjust scaling
@app.cls(
    gpu="A10G",  # or "T4" for cheaper
    min_containers=0,  # Set to 1 for always-warm ($15/mo)
    max_containers=10,  # Limit concurrent instances
    container_idle_timeout=600,  # 10 min before scale-down
)

# Adjust memory/CPU
@app.cls(
    cpu=2.0,  # 2 vCPUs
    memory=16384,  # 16GB RAM
)
```

### MongoDB Atlas Management

#### Connection String Update
```bash
# 1. Get new connection string from Atlas
# MongoDB Atlas > Database > Connect > Connect your application

# 2. Update Vercel environment
vercel env add MONGODB_URI production
# Paste new connection string

# 3. Test connection
python scripts/test_mongodb_connection.py
```

#### Index Management
```javascript
// In MongoDB Atlas UI or mongosh:

// Check index status
db.transcript_chunks_768d.getIndexes()

// Rebuild vector index if needed
db.transcript_chunks_768d.createIndex(
  { "embedding_768d": "vector" },
  {
    name: "vector_index",
    vectorOptions: {
      type: "hnsw",
      dimensions: 768,
      similarity: "cosine"
    }
  }
)
```

### Vercel Deployment

#### Standard Deploy
```bash
# 1. Test locally
vercel dev

# 2. Deploy to preview
vercel

# 3. Deploy to production
vercel --prod

# 4. Check logs
vercel logs --prod
```

#### Environment Variables
```bash
# List all env vars
vercel env ls

# Required variables:
MONGODB_URI          # MongoDB connection string
MONGODB_DB_NAME      # Database name (e.g., "production")
SUPABASE_URL         # Supabase project URL
SUPABASE_ANON_KEY    # Supabase anonymous key
MODAL_ENABLED        # "true" or "false"
MODAL_ENDPOINT       # Modal embedding endpoint URL
```

---

## 🛡️ BEST PRACTICES

### 1. Pre-Deployment Checklist
- [ ] Run all tests: `python scripts/test_modal_production.py`
- [ ] Check Modal credits: https://modal.com/billing
- [ ] Verify MongoDB connection: `python scripts/test_mongodb_connection.py`
- [ ] Test fallback search works
- [ ] Review recent error logs
- [ ] Notify team of deployment window

### 2. Monitoring During Deployment
```bash
# Watch Modal logs
modal logs -f

# Watch Vercel logs
vercel logs --prod -f

# Monitor health endpoint
while true; do 
  curl -s https://podinsighthq--podinsight-embeddings-simple-health-check.modal.run | jq .
  sleep 5
done
```

### 3. Rollback Procedures

**If Modal fails:**
```bash
# 1. Immediately disable Modal
vercel env add MODAL_ENABLED production
# Enter: false

# 2. Redeploy Vercel (takes ~30s)
vercel --prod

# 3. Investigate Modal issues
modal logs --tail 100
```

**If MongoDB fails:**
```bash
# System auto-falls back to Supabase pgvector
# No action needed, but investigate:
python scripts/test_mongodb_connection.py
```

### 4. Cost Management

**Monitor Modal usage:**
```python
# Add to health check endpoint:
import modal

@app.get("/usage")
def get_usage():
    # This would need Modal API integration
    return {
        "credits_used": get_modal_credits_used(),
        "credits_remaining": 5000 - get_modal_credits_used(),
        "estimated_days_remaining": calculate_burn_rate()
    }
```

**Set spending alerts:**
1. Modal Dashboard > Settings > Billing
2. Set alert at $100, $500, $1000
3. Email notifications to team

---

## ⚠️ WHEN TO TAKE ACTION

### Disable Modal When:
1. **Credits < $100** - Preserve for critical testing
2. **Error rate > 10%** - Something is wrong
3. **Response time > 30s** - Performance degraded
4. **Monthly cost projection > $50** - Budget concern

### Scale Up When:
1. **Queue depth > 50** - Users waiting
2. **Response time > 5s consistently** - Add containers
3. **Important demo/launch** - Set min_containers=1

### Emergency Contacts:
- **Modal Support**: support@modal.com
- **MongoDB Atlas**: Use in-app chat
- **Vercel Support**: support@vercel.com

---

## 📊 PERFORMANCE TUNING

### Optimize Cold Starts
```python
# Option 1: Keep warm ($15/month)
@app.cls(min_containers=1)

# Option 2: Smaller model (trade accuracy)
model = SentenceTransformer('all-MiniLM-L6-v2')  # 90MB vs 2.1GB

# Option 3: Pre-warm on schedule
@app.schedule(cron="0 9 * * 1-5")  # Weekdays 9am
def warmup():
    generate_embedding("warmup query")
```

### Optimize Costs
```python
# 1. Batch requests
@app.post("/batch-embed")
def batch_embed(queries: List[str]):
    return [embed(q) for q in queries]

# 2. Cache common queries
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_embed(query: str):
    return generate_embedding(query)

# 3. Use spot instances
@app.cls(gpu="T4", preemptible=True)  # 70% cheaper
```

---

## 🔍 TROUBLESHOOTING

### Common Issues

**"Modal endpoint timeout"**
```bash
# Check if app is running
modal app list

# Restart if needed
modal app stop podinsighthq--podinsight-embeddings-simple
modal deploy scripts/modal_web_endpoint_simple.py
```

**"MongoDB connection refused"**
```bash
# Check IP whitelist in Atlas
# Add current IP or use 0.0.0.0/0 for testing

# Test with mongosh
mongosh "mongodb+srv://cluster.mongodb.net/" --username your-username
```

**"Vercel function timeout"**
```javascript
// Increase timeout in vercel.json
{
  "functions": {
    "api/search.py": {
      "maxDuration": 30
    }
  }
}
```

---

## 📋 OPERATIONAL RUNBOOKS

### Daily Health Check
```bash
#!/bin/bash
# health_check.sh

echo "=== PodInsight Daily Health Check ==="
echo "Date: $(date)"

# 1. Check Modal
echo -n "Modal Health: "
curl -s https://podinsighthq--podinsight-embeddings-simple-health-check.modal.run | jq -r .status

# 2. Check API
echo -n "API Health: "
curl -s https://podinsight-api.vercel.app/api/health | jq -r .status

# 3. Test search
echo -n "Search Test: "
curl -s -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"test","limit":1}' | jq -r '.results[0].relevance_score'

# 4. Check MongoDB
echo -n "MongoDB Status: "
python scripts/test_mongodb_connection.py | grep "Connection"

echo "=== Check Complete ==="
```

### Weekly Maintenance
1. Review Modal usage and costs
2. Check MongoDB index performance
3. Analyze search query patterns
4. Update test queries based on user behavior
5. Review and rotate logs
6. Test fallback mechanisms

### Monthly Review
1. Analyze total costs vs budget
2. Review search quality metrics
3. Plan capacity for next month
4. Update documentation
5. Security patches and updates

---

## 🚦 DEPLOYMENT DECISION TREE

```
Start Deployment
    │
    ├─ Is this a critical fix?
    │   ├─ Yes → Deploy immediately with fallback ready
    │   └─ No → Continue
    │
    ├─ Are Modal credits < $500?
    │   ├─ Yes → Use conservative settings (scale-to-zero)
    │   └─ No → Continue
    │
    ├─ Is it peak hours (9am-5pm PST)?
    │   ├─ Yes → Deploy with gradual rollout (10% → 50% → 100%)
    │   └─ No → Full deployment OK
    │
    └─ Run deployment with monitoring
```

---

## 📚 ADDITIONAL RESOURCES

- **Modal Docs**: https://modal.com/docs
- **MongoDB Vector Search**: https://www.mongodb.com/docs/atlas/atlas-vector-search/
- **Vercel Deployment**: https://vercel.com/docs/deployments
- **System Architecture**: See MODAL_ARCHITECTURE_DIAGRAM.md
- **Testing Guide**: See SINGLE_SOURCE_USER_TESTING_CLI_AND_WEB.md

---

**Remember**: The system is designed to fail gracefully. If Modal fails, search still works (just with lower quality). If MongoDB fails, Supabase provides backup. Always test fallbacks!