# Search API Implementation Guide

## Current Status (Updated 2025-01-12)
**Backend Status**: Partially working but not production-ready
- ✅ Search returns results (no longer hangs indefinitely)
- ❌ Response time: 28 seconds (target: <10s)
- ❌ Modal cold starts causing timeouts
- ❌ MongoDB replica issues causing delays
- ⚠️ Context expansion disabled (affecting answer quality)

**Frontend Status**: Waiting for configuration fix
- Frontend expects proxy at `/api/search` but needs direct API call
- One-line fix required: change to `https://podinsight-api.vercel.app/api/search`

## Original Issue Summary
The search functionality in the PodInsight dashboard is currently hanging when users submit queries. The user reports: "What are VCs saying about AI valuations? - and it just hangs...can't see anything in logs."

## Current Architecture

### Frontend Implementation (Working)
1. **Search Modal Component**: `/components/dashboard/ai-search-modal-enhanced.tsx`
   - Sends POST requests to local proxy route `/api/search`
   - Handles caching, timeout management, and UI feedback
   - Expects specific response format with AI-generated answers

2. **Local Proxy Route**: `/app/api/search/route.ts`
   - Forwards requests to `https://podinsight-api.vercel.app/api/search`
   - 45-second timeout to handle Modal.com cold starts
   - Graceful error handling

### Backend Implementation (Unknown Status)
The frontend is trying to call `POST https://podinsight-api.vercel.app/api/search` but the request hangs with no visible errors in the logs.

## API Specification

### Endpoint
```
POST /api/search
```

### Request Format
```json
{
  "query": "What are VCs saying about AI valuations?",
  "limit": 10,
  "offset": 0
}
```

### Expected Response Format
```json
{
  "answer": {
    "text": "Based on recent podcast discussions, VCs are expressing concerns about AI valuations...",
    "citations": [
      {
        "index": 0,
        "episode_id": "ep_123abc",
        "episode_title": "AI Valuations in 2024",
        "podcast_name": "The VC Podcast",
        "timestamp": "12:34",
        "start_seconds": 754,
        "chunk_index": 42
      }
    ]
  },
  "processing_time_ms": 2341,
  "total_results": 15,
  "search_method": "semantic"  // or "none_all_failed" if search fails
}
```

### Response Fields Explanation

#### `answer` Object (Required)
- **`text`** (string): AI-generated answer synthesizing information from podcast transcripts
- **`citations`** (array): Supporting evidence from specific podcast segments
  - **`index`** (number): Citation order (0-based)
  - **`episode_id`** (string): Unique episode identifier
  - **`episode_title`** (string): Human-readable episode title
  - **`podcast_name`** (string): Podcast series name
  - **`timestamp`** (string): Human-readable timestamp (format: "MM:SS" or "HH:MM:SS")
  - **`start_seconds`** (number): Exact start time in seconds for audio playback
  - **`chunk_index`** (number): Internal reference to transcript chunk

#### Optional Fields
- **`processing_time_ms`** (number): Backend processing duration
- **`total_results`** (number): Total matching episodes found
- **`search_method`** (string): Method used ("semantic", "keyword", "none_all_failed")

## Implementation Requirements

### 1. Search Pipeline
The backend should implement a search pipeline that:

1. **Accepts natural language queries** (e.g., "What are VCs saying about AI valuations?")
2. **Searches across podcast transcripts** using semantic search or keyword matching
3. **Synthesizes an AI-generated answer** from relevant transcript segments
4. **Returns citations** linking to specific podcast moments

### 2. Modal.com Integration
Based on the prewarming implementation, the backend likely uses Modal.com for:
- Embedding generation
- Semantic search
- AI response generation

**Important**: The search endpoint should handle Modal.com cold starts gracefully. The frontend expects responses within 45 seconds.

### 3. Error Handling
Return appropriate HTTP status codes:
- `200 OK`: Successful search with results
- `404 Not Found`: Endpoint not implemented (current issue)
- `500 Internal Server Error`: Search processing failure
- `504 Gateway Timeout`: If processing exceeds timeout

For errors, return:
```json
{
  "error": "Descriptive error message",
  "search_method": "none_all_failed"
}
```

### 4. Performance Considerations
- Implement caching for common queries
- Consider pagination using `limit` and `offset` parameters
- Pre-warm Modal.com services when possible (already implemented via `/api/prewarm`)

## Testing the Implementation

### 1. Basic Query Test
```bash
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are VCs saying about AI valuations?",
    "limit": 10,
    "offset": 0
  }'
```

### 2. Expected Successful Response
- Should return within 45 seconds
- Must include `answer.text` and `answer.citations`
- Citations should reference real podcast episodes

### 3. Frontend Integration Test
1. Open the PodInsight dashboard
2. Click the "Chat" button to open search modal
3. Type a query and press Enter
4. Should see AI-generated answer with podcast citations

## Observed Behavior

### Previous Behavior (Before Fix)
When users submit a search query (e.g., "What are VCs saying about AI valuations?"):
1. Frontend sends request to `/api/search` (local proxy)
2. Proxy forwards to `https://podinsight-api.vercel.app/api/search` with 40-second timeout
3. The request hangs with no visible errors in logs
4. No response is received within the timeout period

### Current Behavior (After Partial Fix - 2025-01-12)
1. Frontend sends request to `/api/search` (gets 404 - no proxy exists)
2. Backend API directly responds in ~28 seconds with:
   - ✅ AI-generated answer with citations
   - ✅ Hybrid search results (vector + text)
   - ❌ Modal embedding timeout on first attempt (15.55s)
   - ❌ MongoDB ReplicaSetNoPrimary warnings
   - ⚠️ Context expansion disabled (N+1 query issue)

### Test Results from Latest Run
```
Total Response Time: 28.226s
- Modal embedding: 17.98s (timeout + retry)
- Hybrid search: 8.76s (MongoDB delays)
- Synthesis & other: ~1.5s

Quality Issues:
- Context expansion disabled
- Only getting 30-second transcript chunks
- Results feel "vague" without surrounding context
```

## Possible Causes for Hanging

1. **Endpoint doesn't exist** - Returns 404 but proxy might not handle it properly
2. **Endpoint exists but timing out** - Processing takes longer than 40 seconds
3. **Endpoint exists but returns unexpected format** - Causing parsing issues
4. **Network/CORS issues** - Though proxy should handle CORS

## Recommended Debugging Steps

1. **Check if endpoint exists**:
   ```bash
   curl -X POST https://podinsight-api.vercel.app/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "limit": 10, "offset": 0}'
   ```

2. **Check backend logs** for any incoming requests to `/api/search`

3. **If endpoint needs to be implemented**:
   - Implement transcript search functionality
   - Integrate AI response generation
   - Format response according to the specification above
   - Ensure response time is under 40 seconds

## Prewarming Implementation Status

### What's Been Implemented
The frontend prewarming is **fully implemented and working**:

1. **Frontend Behavior**:
   - When user clicks "Chat" button, the search modal opens
   - Modal immediately sends POST request to `/api/prewarm`
   - Console log shows: `"Search modal opened. Pre-warming backend..."`
   - Prewarming has a 3-minute cooldown to prevent excessive requests

2. **Local Proxy Route** (`/app/api/prewarm/route.ts`):
   - Successfully forwards requests to backend
   - Gracefully handles 404 responses (backend endpoint optional)
   - Returns success even if backend doesn't have the endpoint

3. **What We See in Logs**:
   ```
   Search modal opened. Pre-warming backend...
   Attempting to prewarm backend at: https://podinsight-api.vercel.app/api/prewarm
   Backend prewarm endpoint not found - this is optional, search will still work
   ```

4. **Frontend Response Handling**:
   - Frontend gets `{"status": "skipped", "message": "Prewarm endpoint not available - search will work but may have initial delay"}`
   - This is expected behavior - prewarming is optional
   - Search should still work, just with cold start delays

### Why Prewarming Matters for Search
- Modal.com services have ~18-20 second cold start times
- Prewarming triggers when modal opens, not when user submits query
- Users typically take 3-5 seconds to type their query
- By the time they submit, Modal should be warm and ready
- Without prewarming: First search takes 20+ seconds
- With prewarming: First search should be fast

### Current Problem
Despite prewarming being implemented, search still hangs:
1. Prewarming attempts to warm the backend (gets 404 but handles gracefully)
2. When user submits a search query, it hangs with no errors
3. The request to `https://podinsight-api.vercel.app/api/search` doesn't return within 40 seconds

## Additional Context

### Related Files
- **Frontend Search Modal**: `/components/dashboard/ai-search-modal-enhanced.tsx`
- **Local Proxy Route**: `/app/api/search/route.ts`
- **Prewarming Endpoint**: `/app/api/prewarm/route.ts` (implemented, working)
- **Prewarming Test Guide**: `/docs/sprint5/PREWARMING_TEST_GUIDE.md`

### Audio Playback Integration
The frontend expects `episode_id` and `start_seconds` to enable audio playback via:
```
GET /api/v1/audio_clips/{episode_id}?start_time_ms={start_time_in_ms}
```

This allows users to listen to the exact podcast segment referenced in search results.

## Questions for Backend Team

1. **Is Modal.com being used for search/embeddings?** The prewarming suggests this.
2. **What transcript data is available?** Format, storage, indexing method.
3. **Which AI model for answer generation?** OpenAI, Anthropic, or other.
4. **Are there rate limits to consider?** For search or AI generation.

## Summary
The search feature is fully implemented on the frontend but requires the backend `/api/search` endpoint. Once implemented following this specification, the search functionality should work seamlessly, providing AI-powered insights from podcast transcripts with audio playback support.
