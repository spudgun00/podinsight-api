# Urgent Text Search Performance Fix

## Current Issues
1. Text search taking 7-14 seconds (highly variable)
2. Gateway timeouts (504) occurring
3. "remainingTimeMS: 9" warnings persist
4. Duplicate log entries suggest parallel execution issues

## Immediate Actions Needed

### 1. Reduce Retry Attempts
Change `max_retries=2` to `max_retries=1` to avoid tripling execution time:
```python
async def with_mongodb_retry(func, max_retries=1, ...)
```

### 2. Increase Connection Pool Further
```python
maxPoolSize=200,  # From 100
minPoolSize=20,   # From 10
```

### 3. Add Operation Timeout
Add explicit timeout to prevent hanging:
```python
# In text/vector search operations
await collection.aggregate(pipeline, maxTimeMS=10000).to_list(limit)
```

### 4. Consider Reducing Search Terms Further
Current: 6 terms max
Suggested: 4 terms max for better performance

## Root Cause Analysis
The text search performance degradation (3.72s → 7-14s) suggests:
1. MongoDB replica set instability ("remainingTimeMS: 9")
2. Connection pool exhaustion under load
3. Possible index fragmentation or resource constraints

## Long-term Solutions
1. **Denormalize data** to eliminate $lookup entirely
2. **Use MongoDB Atlas Search** instead of text indexes
3. **Implement caching layer** for frequent queries
4. **Consider read replicas** for search operations