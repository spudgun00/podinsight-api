# MongoDB Performance Investigation Report
**Date**: 2025-01-14
**Issue**: Search queries timing out after 20-30 seconds
**Root Cause**: Memory exhaustion - 8.4GB database running on 4GB RAM tier

---

## 🚨 CRITICAL FINDINGS

### 1. Memory Crisis
- **Database Size**: 8.4GB (uncompressed)
- **Available RAM**: 4GB (M20 tier)
- **Memory Usage**: 97.75% (3.91GB of 4GB)
- **Result**: Constant disk paging causing severe performance degradation

### 2. Text Search Performance Issues
- **Query Execution Time**: 17.8 - 21 seconds
- **Documents Returned**: 39,938 (way too many!)
- **Documents Examined**: 39,938
- **Time Spent Fetching from Disk**: 17.7 seconds (99% of query time)

### 3. Not a Modal Problem
- **Modal Response Times**: 0.46s - 0.51s (warm instances)
- **Modal Cold Start**: 16.6s (but not happening during searches)
- **Conclusion**: Modal is performing well, MongoDB is the bottleneck

---

## 📊 DATABASE DETAILS

### Cluster Information
- **Provider**: MongoDB Atlas
- **Tier**: M20 (General)
- **Replica Set**: atlas-12vjb5-shard-0
- **Members**: 3 (1 primary, 2 secondaries)
- **Connection String**: `mongodb+srv://podinsight-api:[PASSWORD]@podinsight-cluster.bgknvz.mongodb.net/podinsight?retryWrites=true&w=majority&appName=podinsight-cluster`

### Database Statistics
```
Database: podinsight
Collections: 11
Total Objects: 826,879
Average Object Size: 10.25KB
Data Size: 8.48GB
Storage Size (compressed): 4.99GB
Total Indexes: 37
Index Size: 240MB
File System Usage: 16GB of 20GB (80% full)
```

### Collections
1. `transcript_chunks_768d` - Main search collection (823,763 docs, 8.4GB)
2. `episode_transcripts` - Full episode transcripts
3. `episode_metadata` - Episode information
4. `podcast_authority` - Podcast ranking data
5. `episode_intelligence`
6. `episode_processing_status`
7. `share_history`
8. `user_intelligence_prefs`
9. `sentiment_results`
10. `user_preferences`
11. `signal_duplicates`

### transcript_chunks_768d Collection Details
- **Document Count**: 823,763
- **Total Size**: 8.4GB
- **Average Document Size**: 10.2KB
- **Indexes**:
  - `_id_`: 22.8MB
  - `text_search_index`: 154.4MB ✓ (EXISTS and WORKING)
  - `episode_chunk_unique`: 20.9MB
  - `feed_slug_1`: 16.3MB
  - `created_at_-1`: 20MB
  - `episode_id_1`: 3.9MB

### Document Structure
```javascript
{
  _id: ObjectId('...'),
  chunk_index: 0,
  episode_id: 'uuid',
  created_at: ISODate('...'),
  embedding_768d: [768 float values], // ~6KB per embedding
  end_time: 3.831,
  feed_slug: 'a16z-podcast',
  speaker: null,
  start_time: 1.069,
  text: "transcript text chunk",
  updated_at: ISODate('...')
}
```

---

## 🔍 PERFORMANCE ANALYSIS

### Text Search Query Analysis
```javascript
db.transcript_chunks_768d.find({
  $text: { $search: "vcs venture capitalists investors ai artificial intelligence ml valuations valuation pricing" }
}).explain("executionStats")
```

**Results**:
- Execution Time: 17,853ms
- Documents Returned: 39,938
- Keys Examined: 41,605
- Index Used: `text_search_index`
- Stage Breakdown:
  - INDEX scan: 204ms (fast!)
  - FETCH documents: 17,742ms (99% of time - disk I/O)

**Why It's Slow**:
1. Query contains 10 search terms
2. MongoDB creates 10 separate index scans (OR operation)
3. Returns 39,938 documents that need scoring
4. With only 4GB RAM, most documents are read from disk
5. Each document is ~10KB, so ~400MB of data to process

### Replica Set Health
- **Status**: All members healthy
- **Last Election**: 2025-07-11 16:15:46 UTC (3 days ago)
- **Current Primary**: shard-00-01
- **Replication**: All members in sync
- **Note**: Election coincided with timeout issues but hasn't recurred

### MongoDB Metrics Analysis
1. **Memory Jump**: 1.95GB → 3.91GB during high load
2. **CPU Spikes**: Up to 30% system, 6% process
3. **Query Load**: 1K/s query executor, 3K/s query targeting
4. **Periodic Pattern**: Spikes every ~10 minutes
5. **Operation Execution Time**: Spiked to 200ms+ during issues

---

## 💡 RECOMMENDATIONS

### 1. IMMEDIATE ACTION - Upgrade MongoDB Tier (TODAY!)

**Current**: M20 (4GB RAM)
**Minimum Required**: M30 (8GB RAM)
**Recommended**: M40 (16GB RAM)

**How to Upgrade**:
1. Log into MongoDB Atlas
2. Select your cluster
3. Click "Configuration" → "Edit"
4. Change tier to M30 or M40
5. Click "Review Changes" → "Apply Changes"
6. Wait ~5-10 minutes for rolling upgrade

**Expected Impact**:
- 90% reduction in query times
- Elimination of disk paging
- Stable performance under load

### 2. Query Optimization (This Week)

**Current Problem**: Text search returns 39,938 documents

**Solution 1 - Add Filters**:
```javascript
// Before (slow):
db.transcript_chunks_768d.find({
  $text: { $search: "search terms" }
})

// After (fast):
db.transcript_chunks_768d.find({
  created_at: { $gte: new Date(Date.now() - 90*24*60*60*1000) }, // Last 90 days
  $text: { $search: "search terms" }
}).limit(1000)
```

**Solution 2 - Use Aggregation Pipeline**:
```javascript
db.transcript_chunks_768d.aggregate([
  { $match: { $text: { $search: "search terms" } } },
  { $limit: 1000 }, // Limit early in pipeline
  { $sort: { score: { $meta: "textScore" } } }
])
```

**Solution 3 - Add Compound Index**:
```javascript
// Create compound index for common filters
db.transcript_chunks_768d.createIndex({
  created_at: -1,
  text: "text"
})
```

### 3. Code Optimizations

**In `api/improved_hybrid_search.py`**:
- Add result limiting before processing
- Implement pagination for large result sets
- Consider caching frequent searches

**MongoDB Connection Optimization**:
```python
# Current timeout might be too high
client = AsyncIOMotorClient(
    uri,
    serverSelectionTimeoutMS=5000,  # Reduce from 10000
    maxPoolSize=50,  # Increase from 10
    minPoolSize=10   # Maintain warm connections
)
```

### 4. Monitoring Setup

**Key Metrics to Monitor**:
1. Memory usage (alert at 80%)
2. Page faults per second
3. Query execution time
4. Disk IOPS
5. Replication lag

**Atlas Alerts to Configure**:
- Memory usage > 80%
- Query execution time > 5s
- Replica set elections
- Disk queue depth > 100

### 5. Long-term Optimizations

1. **Data Archival**: Move old transcripts to cold storage
2. **Sharding**: Consider sharding if data grows beyond 50GB
3. **Search Infrastructure**: Evaluate dedicated search solutions (Elasticsearch, Algolia)
4. **Caching Layer**: Implement Redis for frequent queries

---

## 📈 EXPECTED OUTCOMES

### After M30/M40 Upgrade:
- Text search: 17-21s → 2-3s
- Memory usage: 97.75% → 50-60%
- Timeouts: Eliminated
- User experience: Significantly improved

### After Query Optimization:
- Documents processed: 39,938 → <1,000
- Query time: 2-3s → <1s
- Resource usage: Dramatically reduced

---

## 🔧 VERIFICATION STEPS

After implementing fixes:

1. **Check Memory Usage**:
```javascript
db.serverStatus().mem
```

2. **Re-run Text Search Explain**:
```javascript
db.transcript_chunks_768d.find({
  $text: { $search: "test query" }
}).explain("executionStats")
```

3. **Monitor Page Faults**:
```javascript
db.serverStatus().extra_info.page_faults
```

4. **Test Search API**:
```bash
curl -X POST https://your-api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI valuations"}'
```

---

## 📞 SUPPORT CONTACTS

- **MongoDB Atlas Support**: Available through Atlas console
- **Escalation**: If issues persist after upgrade, open Atlas support ticket
- **Documentation**: https://docs.mongodb.com/manual/core/read-preference/

---

## ✅ SUMMARY

**The Problem**: 8.4GB database running on 4GB RAM causing disk paging
**The Solution**: Upgrade to M30/M40 tier + optimize queries
**Timeline**: Upgrade TODAY, optimize this week
**Expected Result**: 90% performance improvement, no more timeouts
