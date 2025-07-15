# MongoDB Quick Fix Guide - URGENT

## 🚨 IMMEDIATE ACTION REQUIRED

### Step 1: Upgrade MongoDB Tier NOW (5 minutes)

1. **Login to MongoDB Atlas**: https://cloud.mongodb.com
2. **Select**: podinsight-cluster
3. **Click**: Configuration → Edit Configuration
4. **Change Tier**:
   - From: M20 (4GB)
   - To: M30 (8GB) minimum or M40 (16GB) recommended
5. **Click**: Review Changes → Apply Changes
6. **Wait**: 5-10 minutes for rolling upgrade

**Cost Impact**:
- M20 → M30: ~$140/month → ~$370/month
- M20 → M40: ~$140/month → ~$700/month

### Step 2: Quick Code Fix (10 minutes)

Add this to your search queries immediately:

**File**: `api/improved_hybrid_search.py`

Find the text search query and add a limit:
```python
# Add this after line where text search is performed
text_results = await collection.find(
    {"$text": {"$search": search_string}}
).limit(5000).to_list(length=5000)  # Add limit!
```

### Step 3: Deploy the Code Fix

```bash
git add -A
git commit -m "fix: Add result limit to MongoDB text search to prevent timeouts"
git push origin main
```

### Step 4: Verify the Fix

1. **Check Atlas Metrics**: Memory usage should drop below 80%
2. **Test Search**: Should complete in <5 seconds
3. **Monitor**: No more timeout errors in logs

---

## 🔍 How to Monitor

### Atlas Dashboard
- Go to Metrics tab
- Watch "Memory Usage" - should be <80%
- Watch "Operation Execution Time" - should be <1s

### Test Search
```bash
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI valuations", "limit": 10}'
```

Should return in <5 seconds!

---

## ⚡ Why This Works

1. **More RAM** = MongoDB keeps data in memory instead of disk
2. **Result Limit** = Process 5,000 docs instead of 40,000
3. **Combined Effect** = 90% faster searches, no timeouts

---

## 📞 If Issues Persist

1. Check Atlas logs for new errors
2. Verify the tier upgrade completed
3. Confirm code changes are deployed
4. Contact MongoDB support through Atlas console

**Expected Timeline**:
- Tier upgrade: 5-10 minutes
- Performance improvement: Immediate
- Full stability: Within 1 hour
