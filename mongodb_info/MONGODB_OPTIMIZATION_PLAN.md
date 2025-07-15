# MongoDB Optimization Plan - Next Steps

## Phase 1: Immediate Fixes (Day 1)
✅ **Status**: Investigation Complete

- [x] Identify root cause: Memory exhaustion
- [x] Find slow queries: Text search returning 40K docs
- [x] Verify indexes exist: text_search_index present
- [ ] **ACTION**: Upgrade to M30/M40 tier
- [ ] **ACTION**: Deploy query limit fix

## Phase 2: Query Optimization (Week 1)

### 1. Optimize Text Search Query
```python
# In api/improved_hybrid_search.py

# Current (slow):
text_results = await collection.find({
    "$text": {"$search": search_string}
}).to_list(length=None)

# Optimized (fast):
# Add date filter and limit
ninety_days_ago = datetime.now() - timedelta(days=90)
text_results = await collection.find({
    "created_at": {"$gte": ninety_days_ago},
    "$text": {"$search": search_string}
}).limit(2000).to_list(length=2000)
```

### 2. Add Compound Indexes
```javascript
// For filtered text searches
db.transcript_chunks_768d.createIndex({
  created_at: -1,
  text: "text"
})

// For feed-specific searches
db.transcript_chunks_768d.createIndex({
  feed_slug: 1,
  created_at: -1
})
```

### 3. Implement Result Ranking
```python
# Score and filter results in application
def filter_results(results, min_score=0.7):
    scored_results = []
    for result in results:
        score = result.get('score', 0)
        if score >= min_score:
            scored_results.append(result)

    # Sort by score descending
    return sorted(scored_results,
                  key=lambda x: x['score'],
                  reverse=True)[:100]
```

## Phase 3: Architecture Improvements (Week 2-3)

### 1. Implement Caching Layer
```python
# Add Redis caching for popular searches
import redis
import hashlib
import json

redis_client = redis.Redis()

def get_cached_search(query):
    cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    return None

def cache_search_results(query, results):
    cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}"
    redis_client.setex(cache_key, 3600, json.dumps(results))  # 1 hour TTL
```

### 2. Pagination Implementation
```python
async def search_with_pagination(query, page=1, per_page=20):
    skip = (page - 1) * per_page

    results = await collection.find({
        "$text": {"$search": query}
    }).skip(skip).limit(per_page).to_list(length=per_page)

    total_count = await collection.count_documents({
        "$text": {"$search": query}
    })

    return {
        "results": results,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_count,
            "pages": (total_count + per_page - 1) // per_page
        }
    }
```

### 3. Connection Pool Optimization
```python
# In mongodb_vector_search.py
client = AsyncIOMotorClient(
    uri,
    maxPoolSize=100,        # Increase from 10
    minPoolSize=20,         # Keep connections warm
    maxIdleTimeMS=30000,    # 30 seconds idle timeout
    serverSelectionTimeoutMS=5000,  # Fail fast
    connectTimeoutMS=5000,
    socketTimeoutMS=5000,
    retryWrites=True,
    retryReads=True,
    readPreference='primaryPreferred',  # Change from secondaryPreferred
    readConcernLevel='local',
    w='majority',
    wtimeout=5000
)
```

## Phase 4: Monitoring & Alerting (Week 3-4)

### 1. Custom Metrics Collection
```python
# Add performance metrics
import time
from prometheus_client import Histogram, Counter

search_duration = Histogram('mongodb_search_duration_seconds',
                          'Time spent in MongoDB search')
search_results_count = Histogram('mongodb_search_results_count',
                               'Number of results returned')
search_errors = Counter('mongodb_search_errors_total',
                      'Total MongoDB search errors')

@search_duration.time()
async def monitored_search(query):
    try:
        results = await perform_search(query)
        search_results_count.observe(len(results))
        return results
    except Exception as e:
        search_errors.inc()
        raise
```

### 2. Atlas Alerts Configuration
- Memory Usage > 80%
- CPU Usage > 80%
- Query Execution Time > 5 seconds
- Page Faults > 100/second
- Replication Lag > 10 seconds

### 3. Application-Level Monitoring
```python
# Log slow queries
async def search_with_timing(query):
    start_time = time.time()
    results = await perform_search(query)
    duration = time.time() - start_time

    if duration > 5.0:
        logger.warning(f"Slow query detected: {duration:.2f}s for query: {query}")

    return results
```

## Phase 5: Long-term Strategy (Month 2+)

### 1. Data Archival Strategy
```javascript
// Archive old data to separate collection
db.transcript_chunks_768d.aggregate([
  { $match: { created_at: { $lt: ISODate("2024-01-01") } } },
  { $out: "transcript_chunks_archive" }
])

// Then remove from main collection
db.transcript_chunks_768d.deleteMany({
  created_at: { $lt: ISODate("2024-01-01") }
})
```

### 2. Consider Alternative Search Solutions
- **Elasticsearch**: Better full-text search capabilities
- **Algolia**: Managed search with instant results
- **Atlas Search**: MongoDB's native Lucene-based search

### 3. Implement Search Analytics
```python
# Track what users search for
async def track_search(query, results_count, duration):
    await analytics_collection.insert_one({
        "query": query,
        "results_count": results_count,
        "duration": duration,
        "timestamp": datetime.utcnow(),
        "user_satisfied": results_count > 0
    })
```

## Success Metrics

### Week 1 Goals
- [ ] Average search time < 3 seconds
- [ ] Zero timeout errors
- [ ] Memory usage < 80%

### Month 1 Goals
- [ ] Average search time < 1 second
- [ ] 99.9% uptime
- [ ] Implement caching (30% cache hit rate)

### Month 3 Goals
- [ ] Average search time < 500ms
- [ ] 50% cache hit rate
- [ ] Data archival in place
- [ ] Alternative search solution evaluated

## Cost-Benefit Analysis

### Current State (M20)
- Cost: ~$140/month
- Performance: 20+ second searches
- User Experience: Poor
- Business Impact: User churn

### After M30 Upgrade
- Cost: ~$370/month (+$230)
- Performance: 2-3 second searches
- User Experience: Acceptable
- ROI: Immediate user satisfaction

### After Full Optimization
- Cost: ~$500/month (including Redis)
- Performance: <1 second searches
- User Experience: Excellent
- ROI: Competitive advantage
