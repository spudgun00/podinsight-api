# Quick Search Troubleshooting Guide

## If Search Returns 0 Results

### 1. Check Index Status
- Go to MongoDB Atlas Dashboard
- Navigate to your cluster → Collections → transcript_chunks_768d
- Click "Search Indexes" tab
- Verify `vector_index_768d` shows "ACTIVE" status

### 2. Verify API is Using Correct Index
Check `api/mongodb_vector_search.py` line 85:
```python
"index": "vector_index_768d",  # Should match your index name
```

### 3. Check Vercel Logs
- Go to https://vercel.com/dashboard
- Select podinsight-api project
- Click "Functions" tab
- Check logs for errors

### 4. Test Modal.com Embedding Generation
```bash
curl -X POST https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "test query"}'
```
Should return 768-dimensional array.

### 5. Common Issues & Fixes

**Issue**: 500 Error from API
**Fix**: Redeploy to Vercel - sometimes needed after index creation

**Issue**: Wrong number of dimensions
**Fix**: Ensure Modal is returning 768D vectors (not 384D or 1536D)

**Issue**: No results but no errors
**Fix**: Check if embedding field name matches: `embedding_768d`

**Issue**: Timeout errors
**Fix**: Reduce numCandidates in search query (try 100 instead of 200)

## Quick Test Commands

### Test Search Endpoint
```bash
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI", "limit": 1}'
```

### Test 768D Endpoint Directly
```bash
curl -X POST https://podinsight-api.vercel.app/api/search_lightweight_768d \
  -H "Content-Type: application/json" \
  -d '{"query": "startup", "limit": 1}'
```

### Test Entity Search (Should Still Work)
```bash
curl "https://podinsight-api.vercel.app/api/entities?search=OpenAI&limit=1"
```

## If All Else Fails

1. Check MongoDB connection string in Vercel environment variables
2. Ensure Modal.com endpoint is accessible
3. Verify Supabase connection for metadata
4. Try local testing with proper .env file