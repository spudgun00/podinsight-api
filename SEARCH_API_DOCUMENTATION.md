# Search API Documentation

## Overview

The PodInsightHQ Search API provides semantic search capabilities across 1,171 podcast episodes using natural language queries. It uses the same embedding model (`sentence-transformers/all-MiniLM-L6-v2`) that was used to process the podcast transcripts, ensuring compatibility and high-quality search results.

## Endpoint

### POST /api/search

Search for podcast episodes using natural language queries.

**Rate Limit:** 20 requests per minute per IP address

**Request Body:**
```json
{
  "query": "AI agents and startup valuations",
  "limit": 10,
  "offset": 0
}
```

**Parameters:**
- `query` (string, required): Natural language search query. Max 500 characters.
- `limit` (integer, optional): Number of results to return. Default: 10, Max: 50
- `offset` (integer, optional): Offset for pagination. Default: 0

**Response:**
```json
{
  "results": [
    {
      "episode_id": "550e8400-e29b-41d4-a716-446655440000",
      "podcast_name": "The AI Podcast",
      "episode_title": "Building Autonomous AI Agents",
      "published_at": "2025-03-15T10:30:00Z",
      "similarity_score": 0.89,
      "excerpt": "...discussing how AI agents are transforming startup valuations...",
      "word_count": 12500,
      "duration_seconds": 3600,
      "topics": ["AI Agents", "B2B SaaS"],
      "s3_audio_path": "raw/podcast/episode/audio.mp3"
    }
  ],
  "total_results": 42,
  "cache_hit": true,
  "search_id": "search_a1b2c3d4_1234567890",
  "query": "AI agents and startup valuations",
  "limit": 10,
  "offset": 0
}
```

## Implementation Details

### Embedding Model
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Same model used for indexing all podcast transcripts**

### Search Algorithm
- Uses pgvector's `similarity_search_ranked` function
- Employs ranked search (not threshold-based) due to high baseline similarity
- Returns results ordered by cosine similarity

### Query Caching
- SHA256 hash of queries stored in `query_cache` table
- Cached embeddings reused for identical queries
- Significantly improves response time for repeated searches

### Performance
- First query: ~500-800ms (includes embedding generation)
- Cached query: ~50-200ms
- Connection pooling prevents database overload

## Example Usage

### Basic Search
```bash
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence and machine learning",
    "limit": 5
  }'
```

### Paginated Search
```bash
# Page 1
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "blockchain technology",
    "limit": 10,
    "offset": 0
  }'

# Page 2
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "blockchain technology",
    "limit": 10,
    "offset": 10
  }'
```

### Search with Topics
```bash
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "DePIN infrastructure projects",
    "limit": 20
  }'
```

## Testing

### Unit Tests
```bash
python -m pytest tests/test_search_api.py -v
```

### Manual Testing
```bash
python test_search_manual.py
```

## Error Handling

### Rate Limiting
```json
{
  "detail": "Rate limit exceeded: 20 per 1 minute"
}
```
**Status Code**: 429
**Retry-After** header indicates when to retry

### Invalid Query
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "ensure this value has at most 500 characters",
      "type": "value_error.any_str.max_length"
    }
  ]
}
```
**Status Code**: 422

### Server Error
```json
{
  "detail": "Failed to generate embedding: [error details]"
}
```
**Status Code**: 500

## Known Limitations

1. **High Similarity Baseline**: Due to averaging segment embeddings and domain-specific content, all episodes show 90-97% similarity. The API uses ranked search to return the most relevant results despite this.

2. **Excerpt Generation**: Currently returns a placeholder excerpt. Full transcript segment search will be implemented in a future update.

3. **Model Loading**: First request after a cold start may take longer (1-2 seconds) as the model loads into memory.

## Future Enhancements

1. **Segment-Level Search**: Search within episode segments for more precise results
2. **Hybrid Search**: Combine semantic search with keyword matching
3. **Search Filters**: Filter by podcast, date range, or topics
4. **Relevance Feedback**: Learn from user interactions to improve ranking
5. **Query Expansion**: Automatically expand queries with related terms