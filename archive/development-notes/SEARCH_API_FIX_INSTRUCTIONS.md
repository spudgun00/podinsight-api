# Search API Fix Instructions

## The Problem
The lightweight search API (`api/search_lightweight.py`) has a circular import on line 106:
```python
from .search import (
    check_query_cache,
    store_query_cache,
    search_episodes,
    SearchRequest,
    SearchResponse,
    SearchResult
)
```

This causes deployment to fail because it tries to import from `search.py` which has heavy dependencies (sentence-transformers).

## Quick Fix Steps

### Option A: Fix the Import (Recommended)
1. Edit `api/search_lightweight.py`
2. Remove lines 106-113 (the import from .search)
3. The file already has all the functions defined above, they just need to be used
4. Save and deploy

### Option B: Temporary Disable Search (Quick Workaround)
1. Edit `api/topic_velocity.py`
2. Comment out line 12:
   ```python
   # from .search_lightweight import search_handler_lightweight as search_handler, SearchRequest, SearchResponse
   ```
3. Comment out the search endpoint (lines 277-304):
   ```python
   # @app.post("/api/search", response_model=SearchResponse)
   # @limiter.limit("20/minute")
   # async def search_episodes_endpoint(
   #     request: Request,
   #     search_request: SearchRequest
   # ) -> SearchResponse:
   #     ...
   #     return await search_handler(search_request)
   ```
4. Deploy without search functionality

## Detailed Fix for Option A

In `api/search_lightweight.py`, the file already contains:
- ✅ Lines 1-50: All the Pydantic models (SearchRequest, SearchResponse, etc.)
- ✅ Lines 52-102: The `generate_embedding_api` function
- ❌ Line 106: Imports from search.py (REMOVE THIS)
- ❌ Lines 116-178: The handler that uses undefined functions

The issue is that the file needs these functions defined locally:
1. `check_query_cache` - Check if query exists in cache
2. `store_query_cache` - Store query in cache
3. `search_episodes` - Search using pgvector

## Complete Fix

Replace the entire `api/search_lightweight.py` with the self-contained version that includes all functions. The fixed version:
1. Defines all functions locally (no imports from search.py)
2. Uses the same Hugging Face API approach
3. Maintains all the same functionality

## How to Revert

### To Use Full Version (Local Development)
1. In `api/topic_velocity.py`, change line 11-12:
   ```python
   # Comment out:
   # from .search_lightweight import search_handler_lightweight as search_handler, SearchRequest, SearchResponse

   # Uncomment:
   from .search import search_handler, SearchRequest, SearchResponse
   ```
2. Install full dependencies: `pip install -r requirements.txt`

### To Use Lightweight Version (Vercel Deployment)
1. Keep line 12 in `api/topic_velocity.py` as is
2. Ensure `api/search_lightweight.py` has no imports from `search.py`
3. Use `requirements_vercel.txt` for deployment

## Testing After Fix

1. Test locally first:
   ```bash
   python -m pytest test_search_manual.py
   ```

2. Deploy to Vercel:
   ```bash
   git add api/search_lightweight.py
   git commit -m "fix: Remove circular import in lightweight search"
   git push
   vercel --prod
   ```

3. Test deployment:
   ```bash
   ./test_deployment.sh
   ```

## Key Points
- The lightweight version MUST be self-contained
- No imports from the heavy `search.py` file
- All functions must be defined within `search_lightweight.py`
- The API functionality remains exactly the same
