# IMMEDIATE FIX NEEDED

## The Problem Line
In `api/search_lightweight.py`, lines 106-113 are causing the deployment failure:

```python
# Import other functions from original search.py
from .search import (
    check_query_cache,
    store_query_cache,
    search_episodes,
    SearchRequest,
    SearchResponse,
    SearchResult
)
```

## Quick Fix Option 1: Comment Out Search (5 seconds)

Edit `api/topic_velocity.py` line 12:
```python
# CHANGE THIS:
from .search_lightweight import search_handler_lightweight as search_handler, SearchRequest, SearchResponse

# TO THIS:
# from .search_lightweight import search_handler_lightweight as search_handler, SearchRequest, SearchResponse
```

Then comment out the search endpoint (lines 277-304).

## Quick Fix Option 2: Remove the Bad Import (10 seconds)

Edit `api/search_lightweight.py` and delete lines 105-113:
- Line 105: `# Import other functions from original search.py`
- Lines 106-113: The entire import block

## After Either Fix:

```bash
git add -A
git commit -m "fix: Remove circular import for Vercel deployment"
git push
vercel --prod
```

## Why This Happened
The lightweight version was supposed to be self-contained but someone added an import from the heavy version, creating a circular dependency that pulls in sentence-transformers (250MB+).
