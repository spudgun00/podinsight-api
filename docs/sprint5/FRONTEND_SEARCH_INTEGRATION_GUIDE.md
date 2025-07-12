# Frontend Search Integration Guide

**Date**: 2025-01-12
**Sprint**: 5
**Status**: Backend search is working - Frontend needs configuration update

## Executive Summary

The search backend is fully functional at `https://podinsight-api.vercel.app/api/search`. The frontend is getting a 404 because it's trying to use a proxy that doesn't exist. This guide provides complete context and solutions.

## 🚨 CRITICAL CLARIFICATION 🚨

**What's Actually Happening:**
1. **The frontend code is TRYING to use a proxy** for search (`/api/search`)
2. **But NO PROXY EXISTS** - there is no proxy configuration for search
3. **ALL OTHER endpoints use DIRECT calls** - no proxy needed
4. **This inconsistency is causing the 404 error**

**In Simple Terms:**
- Search: Frontend → Proxy (doesn't exist) → 404 ❌
- Everything else: Frontend → Backend directly → Works ✅

## 📊 Visual Diagram: Current State vs Fix

### Current State (BROKEN):
```
┌─────────────┐      ┌─────────────────┐     ┌────────────────┐
│   Frontend  │ ---> │ /api/search     │ --> │      ???       │
│   Search    │      │ (local proxy)   │     │   404 ERROR    │
└─────────────┘      └─────────────────┘     └────────────────┘
                           ↑
                     NO PROXY EXISTS!
```

### How Other Endpoints Work (WORKING):
```
┌─────────────┐      ┌────────────────────────────────────────┐
│   Frontend  │ ---> │ https://podinsight-api.vercel.app/api │
│   Features  │      │ /signals, /topic-velocity, etc.       │
└─────────────┘      └────────────────────────────────────────┘
                           ↑
                     DIRECT CALLS WORK!
```

### Recommended Fix:
```
┌─────────────┐      ┌────────────────────────────────────────┐
│   Frontend  │ ---> │ https://podinsight-api.vercel.app/api │
│   Search    │      │ /search                                │
└─────────────┘      └────────────────────────────────────────┘
                           ↑
                     MAKE SEARCH DIRECT TOO!

## Current Situation

### What's Working ✅
- Backend search endpoint is live and responding
- Search completes in ~23 seconds (within Vercel's 30s limit)
- Returns results with AI-generated answers and citations

### What's Not Working ❌
- Frontend gets 404 when trying to search
- Frontend code is calling `/api/search` expecting a proxy to forward the request
- **BUT NO PROXY EXISTS** - the proxy was never set up
- Other API endpoints work because they bypass proxies and call the backend directly

## API Communication Pattern Analysis

### Current Frontend API Calls

Looking at the Vercel logs, here's how the frontend currently calls APIs:

| Endpoint | How It's Called | Status |
|----------|-----------------|---------|
| `/api/signals` | Direct to `podinsight-api.vercel.app` | ✅ Working |
| `/api/topic-velocity` | Direct to `podinsight-api.vercel.app` | ✅ Working |
| `/api/sentiment_analysis_v2` | Direct to `podinsight-api.vercel.app` | ✅ Working |
| `/api/intelligence/dashboard` | Direct to `podinsight-api.vercel.app` | ✅ Working |
| `/api/search` | Via proxy (doesn't exist) | ❌ 404 Error |

## Proxy vs Direct API Calls

### Pros of Using a Proxy

1. **CORS Handling**: Next.js handles CORS automatically
2. **Security**: Backend URL not exposed in browser
3. **Middleware**: Can add frontend-specific auth/logging
4. **Consistency**: Unified API path structure

### Cons of Using a Proxy

1. **Latency**: Extra hop adds delay (critical for search's 23s response time)
2. **Complexity**: Another point of failure
3. **Maintenance**: Need to maintain proxy configuration
4. **Timeout Risk**: With 23s backend + proxy overhead, might exceed 30s Vercel limit

## Why This Confusion Exists

The search implementation guide (SEARCH_API_IMPLEMENTATION_GUIDE.md) described a proxy setup:
- It showed `/app/api/search/route.ts` as a local proxy
- It assumed this proxy would forward to the backend
- BUT: This proxy was never actually created
- Other endpoints were implemented differently (direct calls)

This created an inconsistency where search expects a proxy that doesn't exist.

## Recommended Solution

### Option 1: Direct API Call (RECOMMENDED - Consistency with Other Endpoints) ⭐

Update the search modal to call the backend directly, consistent with other endpoints.

**Implementation:**

```typescript
// In ai-search-modal-enhanced.tsx or wherever the search is implemented

// CURRENT (Not Working):
const response = await fetch('/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query, limit: 10 })
});

// CHANGE TO (Recommended):
const response = await fetch('https://podinsight-api.vercel.app/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query, limit: 10 })
});
```

**Benefits:**
- Consistent with other API calls
- No proxy overhead (important for 23s response time)
- Already proven to work (tested with curl)
- No additional configuration needed

### Option 2: Add Proxy Configuration (NOT RECOMMENDED ⚠️)

If you prefer to use a proxy for consistency, add this to your Next.js configuration:

**In `next.config.js`:**

```javascript
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/search',
        destination: 'https://podinsight-api.vercel.app/api/search',
      },
    ];
  },
};
```

**Or in `app/api/search/route.ts` (App Router):**

```typescript
export async function POST(request: Request) {
  const body = await request.json();

  const response = await fetch('https://podinsight-api.vercel.app/api/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  return Response.json(data);
}
```

**Concerns:**
- Adds latency to already slow search
- Risk of exceeding 30s total timeout
- More complex error handling

## Testing the Fix

Once implemented, test with:

```bash
# Test query that should return results
"What are VCs saying about AI valuations?"

# Expected response time: 15-25 seconds
# Expected results: 5 results with AI answer
```

## Important Context

### Why Search is Slow

1. **Modal Cold Start**: Embedding generation takes 18-20s on cold start
2. **MongoDB Operations**: ~10s for hybrid search
3. **OpenAI Synthesis**: 2-3s for answer generation

This is being addressed in Phase 2/3 of the search fix, but for now, the goal is to get it working.

### API Response Format

The search endpoint returns:

```typescript
interface SearchResponse {
  answer: {
    text: string;
    citations: Citation[];
    confidence?: number;
  } | null;
  results: SearchResult[];
  total_results: number;
  cache_hit: boolean;
  search_id: string;
  query: string;
  limit: number;
  offset: number;
  search_method: string;
  processing_time_ms: number;
}
```

### Error Handling

The backend will return appropriate HTTP status codes:
- 200: Success
- 422: Invalid request (query too long, etc.)
- 504: Timeout (if exceeds limits)
- 500: Server error

## Environment Variables

No additional environment variables needed for the frontend. The backend URL is hardcoded since it's public.

## Summary

**Immediate Action Required:**
1. **DO NOT set up a proxy** - this would add unnecessary complexity and latency
2. **DO update the search API call** to use direct backend URL: `https://podinsight-api.vercel.app/api/search`
3. **DO follow the pattern** of other working API calls (signals, topic-velocity, etc.)

**One-Line Fix:**
```typescript
// Change this:
const response = await fetch('/api/search', ...)
// To this:
const response = await fetch('https://podinsight-api.vercel.app/api/search', ...)
```

**Why This is the Right Solution:**
- ✅ Consistency: Matches all other working endpoints
- ✅ Performance: No proxy overhead (critical for 23s search)
- ✅ Simplicity: No additional configuration needed
- ✅ Proven: Already tested and working with curl

**The backend is working correctly** - this is purely a frontend configuration issue that can be fixed in minutes by changing one line of code.
