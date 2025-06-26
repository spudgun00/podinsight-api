# Deployment Workaround Documentation

## Issue
The search API deployment to Vercel fails due to size constraints:
- The full `sentence-transformers` library with dependencies exceeds Vercel's 250MB limit
- Created a lightweight version using Hugging Face API instead of local model

## Current Workaround

### 1. Lightweight Search Implementation
- **File**: `api/search_lightweight.py`
- **Change**: Uses Hugging Face Inference API instead of local sentence-transformers
- **API Key**: See `.env` file for the key

### 2. Import Strategy
- **Issue**: Circular import between `search.py` and `search_lightweight.py`
- **Fix**: Make `search_lightweight.py` completely self-contained
- **Note**: DO NOT import anything from `search.py` in the lightweight version

### 3. Deployment Configuration
- **File**: `api/topic_velocity.py`
- **Line 12**: Uses lightweight search handler for Vercel deployment
```python
from .search_lightweight import search_handler_lightweight as search_handler
```

## Reverting to Full Version (Local Development)

To use the full version with local model:
1. In `api/topic_velocity.py`, change line 11-12:
```python
# Comment out lightweight version
# from .search_lightweight import search_handler_lightweight as search_handler
# Uncomment full version
from .search import search_handler, SearchRequest, SearchResponse
```

2. Install full dependencies:
```bash
pip install -r requirements.txt  # Full version with sentence-transformers
```

## Permanent Solutions (Future)

1. **Option A**: Use a different deployment platform without size limits
2. **Option B**: Create a separate microservice for embeddings
3. **Option C**: Use edge functions for embedding generation
4. **Option D**: Optimize dependencies to reduce size

## Environment Variables

### Required for Vercel:
- `HUGGINGFACE_API_KEY`: For embedding API calls
- `SUPABASE_URL`: Database connection
- `SUPABASE_KEY`: Database authentication

### Commands to Add:
```bash
vercel env add HUGGINGFACE_API_KEY production
vercel env add SUPABASE_URL production
vercel env add SUPABASE_KEY production
```

## Testing

### Local Testing (Full Version):
```bash
python test_search_manual.py
```

### Production Testing (Lightweight):
```bash
./test_deployment.sh
```

## Notes
- The lightweight version has slightly slower response times due to API calls
- Caching helps mitigate the performance impact
- All functionality remains the same between versions
