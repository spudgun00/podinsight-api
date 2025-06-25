# PodInsight API Search Issue - Complete Technical Analysis with Code

## Executive Summary

The PodInsight API search endpoint is failing despite the Modal embedding service and MongoDB vector search working correctly. The issue appears to be in the API's request handling and query processing logic, not in the embedding or database layers.

## Test Results Summary

### Working:
- ✅ Modal endpoint generates correct 768D embeddings
- ✅ MongoDB has 823,763 properly indexed chunks
- ✅ Direct MongoDB vector searches return results
- ✅ API health endpoint responds

### Failing:
- ❌ API returns 0 results for most queries
- ❌ Only "openai" with `offset=0` works consistently
- ❌ Case sensitivity issues ("openai" vs "OpenAI")
- ❌ Inconsistent parameter handling

## Critical Code Analysis

### 1. Main Search Handler: `/api/search_lightweight_768d.py`

**Key Function: `search_handler_lightweight_768d` (lines 222-419)**

```python
async def search_handler_lightweight_768d(request: SearchRequest) -> SearchResponse:
    # Line 243: Generates embedding
    embedding_768d = await generate_embedding_768d_local(request.query)
    
    # Lines 258-263: Performs vector search
    vector_results = await vector_handler.vector_search(
        embedding_768d,
        limit=request.limit + request.offset,
        min_score=0.0  # Lowered threshold to debug - was 0.7
    )
```

**Identified Issues:**

1. **No Query Normalization**: The query is passed directly without normalization
   ```python
   # Line 243 - query used as-is
   embedding_768d = await generate_embedding_768d_local(request.query)
   ```

2. **Offset Logic**: The code adds offset to limit (line 261)
   ```python
   limit=request.limit + request.offset,
   ```
   This explains why `offset=0` works but other parameters don't.

3. **Logging Shows Issue**: Lines 258-264 have debug logging that would reveal the problem
   ```python
   logger.info(f"Vector search returned {len(vector_results)} results")
   ```

### 2. Embedding Service: `/api/embeddings_768d_modal.py`

**Key Function: `encode_query` (lines 23-43)**

```python
def encode_query(self, query: str) -> Optional[List[float]]:
    # Wraps async call
    return asyncio.run(self._encode_query_async(query))

async def _encode_query_async(self, query: str) -> Optional[List[float]]:
    # Line 62: Sends query to Modal
    payload = {"text": query}
    
    # Line 75: Extracts embedding
    embedding = data.get("embedding", data)
```

**Potential Issues:**

1. **No Text Preprocessing**: Query sent as-is to Modal
2. **Response Format Handling**: Line 75 tries to handle different formats but may fail

### 3. MongoDB Vector Search: `/api/mongodb_vector_search.py`

**Key Function: `vector_search` (lines 60-100)**

```python
pipeline = [
    {
        "$vectorSearch": {
            "index": "vector_index_768d",
            "path": "embedding_768d",
            "queryVector": embedding,
            "numCandidates": min(limit * 10, 1000),
            "limit": limit,
        }
    },
    {
        "$limit": limit  # Critical: Add $limit right after $vectorSearch
    }
]
```

**Configuration:**
- Index name: `vector_index_768d`
- Field path: `embedding_768d`
- Correctly limits candidates to prevent full scan

## Root Cause Analysis

### Primary Issue: Query Processing Bug

The evidence points to a query processing bug in the API:

1. **Case Sensitivity**: "openai" works but "OpenAI" doesn't
2. **Parameter Sensitivity**: Adding `offset=0` changes behavior
3. **Inconsistent Results**: Same query returns different results

### Specific Bug Location

In `search_lightweight_768d.py`, line 261:
```python
limit=request.limit + request.offset,
```

When offset=0:
- `limit = 10 + 0 = 10` ✅ Works
- MongoDB returns 10 results

When no offset provided (defaults to 0 internally):
- Something else is happening that breaks the query

### Secondary Issues

1. **No Query Normalization**: Queries should be normalized (lowercase, trim)
2. **Embedding Format**: Possible nested array issues
3. **Caching**: No caching implemented (commented out)

## Environment Variables Required

```bash
# MongoDB
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=podinsight

# Modal
MODAL_EMBEDDING_URL=https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run

# Supabase (for metadata)
SUPABASE_URL=...
SUPABASE_KEY=...
```

## Immediate Fix Recommendations

### 1. Add Query Normalization

In `search_lightweight_768d.py`, before line 243:
```python
# Normalize query
normalized_query = request.query.lower().strip()
embedding_768d = await generate_embedding_768d_local(normalized_query)
```

### 2. Fix Offset Logic

Change line 261 from:
```python
limit=request.limit + request.offset,
```
To:
```python
limit=request.limit * 2,  # Get extra results for quality
```

### 3. Add Debug Logging

Add before line 243:
```python
logger.info(f"Original query: '{request.query}'")
logger.info(f"Offset: {request.offset}, Limit: {request.limit}")
```

### 4. Verify Embedding Format

In `embeddings_768d_modal.py`, after line 75:
```python
# Ensure flat array
if isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
    embedding = embedding[0]
logger.info(f"Embedding shape: {len(embedding) if embedding else 0}")
```

## Testing Commands

```bash
# Test with curl
curl -X POST "https://podinsight-api.vercel.app/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "openai", "offset": 0}' \
  -s | jq '.results | length'

# Test Modal directly
curl -X POST "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run" \
  -H "Content-Type: application/json" \
  -d '{"text": "venture capital"}' \
  -s | jq '.dimension'
```

## Monitoring Script Created

`monitor_system_health.py` - Run regularly to detect issues:
```bash
python3 scripts/monitor_system_health.py
```

## Next Steps

1. **Check Vercel Logs**: Look for error messages in production
2. **Add Debug Endpoint**: Create `/api/debug` to inspect query processing
3. **Test Locally**: Run API locally with same environment variables
4. **Enable Verbose Logging**: Set log level to DEBUG in production temporarily

## Conclusion

The issue is almost certainly in the API's query handling logic, specifically around parameter processing and the offset calculation. The fix should be straightforward once the exact bug is identified through logging.