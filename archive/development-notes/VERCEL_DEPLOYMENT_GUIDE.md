# Vercel Deployment Guide for Search API

## Problem: Deployment Size Limit

Vercel has a 250MB deployment size limit. Our dependencies:
- sentence-transformers + torch = ~500MB ❌
- This exceeds Vercel's limit

## Solution: Lightweight Deployment

We've created a lightweight version that:
1. Uses external embedding API (Hugging Face)
2. Removes heavy ML dependencies
3. Maintains same functionality

## Deployment Steps

### 1. Use Lightweight Requirements

```bash
# Temporarily use lightweight requirements for Vercel
cp requirements_vercel.txt requirements.txt
```

### 2. Optional: Get Hugging Face API Key

For better performance, get a free API key:
1. Sign up at https://huggingface.co/
2. Get API key from https://huggingface.co/settings/tokens
3. Add to Vercel environment variables:
   ```
   HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxxx
   ```

Note: The API will work without this key (uses mock embeddings) but results will be random.

### 3. Deploy to Vercel

```bash
# Ensure you're logged in
vercel login

# Deploy to production
vercel --prod
```

### 4. Test Deployment

```bash
# Test search endpoint
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI agents and startup valuations",
    "limit": 5
  }' | python -m json.tool
```

## Environment Variables

Add these in Vercel Dashboard:
- `SUPABASE_URL` (required)
- `SUPABASE_KEY` (required)
- `HUGGINGFACE_API_KEY` (optional but recommended)
- `PYTHON_VERSION=3.12`

## Performance Notes

- First request may be slower (API model loading)
- Subsequent requests will be fast (cached)
- Rate limiting still applies (20/minute)

## Local Development

For local development with full model:
```bash
# Use full requirements
cp requirements_full.txt requirements.txt
pip install -r requirements.txt

# Import full search handler
# In api/topic_velocity.py, change:
# from .search_lightweight import search_handler_lightweight as search_handler
# to:
# from .search import search_handler
```

## Monitoring

Check Vercel Function logs:
```bash
vercel logs --prod
```

## Rollback

If issues arise:
```bash
vercel rollback
```
