# Vector Search Performance Issue

## Current Status
After fixing text search (24.64s → 3.72s), vector search has become the new bottleneck at 8.94s.

## Root Cause Analysis

The vector search is taking 8.94s (was 0.67s previously). Possible causes:

1. **Missing vector index** - Most likely cause
2. **Index not optimized for the embedding dimensions (768D)**
3. **Connection pool exhaustion during parallel operations**

## Diagnostic Steps

### 1. Check Vector Index Configuration

```javascript
// In MongoDB Atlas Console
db.transcript_chunks_768d.getIndexes()

// Look for an index with:
{
  "embedding_768d": "cosmosSearch"  // or similar vector index
}
```

### 2. Create/Optimize Vector Index

If missing or misconfigured:

```javascript
db.transcript_chunks_768d.createIndex(
  { "embedding_768d": "cosmosSearch" },
  {
    "cosmosSearchOptions": {
      "kind": "vector-ivf",
      "numLists": 100,
      "similarity": "COS",
      "dimensions": 768
    }
  }
)
```

Or using Atlas Search:

```json
{
  "mappings": {
    "fields": {
      "embedding_768d": {
        "type": "knnVector",
        "dimensions": 768,
        "similarity": "cosine"
      }
    }
  }
}
```

## Connection Pool Optimization

The "remainingTimeMS: 9" warnings suggest connection pool stress:

1. **Increase pool size further**:
```python
maxPoolSize=200,  # From 100
minPoolSize=20,   # From 10
```

2. **Add connection retry logic**:
```python
retryWrites=True,
retryReads=True,
```

3. **Use connection pooling for parallel operations**:
- Share MongoDB client across context expansion operations
- Don't create new clients for each parallel task

## Quick Fixes

### 1. Limit Vector Search Results
```python
# In improved_hybrid_search.py
vector_pipeline = [
    {
        "$search": {
            "index": "vector_index",
            "knnBeta": {
                "vector": query_embedding,
                "path": "embedding_768d",
                "filter": {},
                "k": limit * 2,  # Reduce from limit * 4
                "numCandidates": limit * 10  # Add candidate limit
            }
        }
    }
]
```

### 2. Add Vector Search Timeout
```python
# Add specific timeout for vector search
vector_results = await collection.aggregate(
    vector_pipeline,
    maxTimeMS=5000  # 5 second timeout
).to_list(limit)
```

### 3. Pre-warm Vector Index
Add to the warming function:
```python
# Warm vector search with a simple query
dummy_embedding = [0.1] * 768
await collection.find_one({"embedding_768d": {"$exists": True}})
```

## Expected Results After Fix

- Vector search: <1s (down from 8.94s)
- Total search time: <5s (down from 8.96s)
- No "remainingTimeMS: 9" warnings
- Consistent sub-10s total response time

## Monitoring

Watch for:
```
[VECTOR_SEARCH] Execution time: X.XXs
```

Should be <1s after index optimization.
