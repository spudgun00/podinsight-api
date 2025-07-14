# Frontend Search CORS Issue - Detailed Analysis

**Date**: 2025-01-14
**Status**: ACTIVE ISSUE
**Sprint**: 5

## Executive Summary

The search functionality appears to "hang" at "Warming up search engine..." but backend logs prove the search is working perfectly. This is a CORS (Cross-Origin Resource Sharing) issue preventing the frontend from reading the response.

## The Problem

### What Users See
- Search bar shows "Warming up search engine, this may take up to 20 seconds on first use..."
- This message never goes away
- No search results are displayed
- No error messages appear

### What's Actually Happening (From Backend Logs)

```
INFO:api.search_lightweight_768d:=== SEARCH HANDLER START === Query: 'What are VCs saying about AI valuations?'
...
INFO:api.search_lightweight_768d:[HYBRID_SEARCH] Final hybrid results: 25
INFO:api.search_lightweight_768d:Response has 10 results
INFO:api.search_lightweight_768d:Answer synthesis included with 3 citations
INFO:api.search_lightweight_768d:[TIMING] SEARCH HANDLER END - Total time: 27.034s
127.0.0.1 - - [14/Jul/2025 08:35:13] "POST /api/search HTTP/1.1" 200 -
```

**Key Evidence**: The backend returns `200 OK` with 10 results and synthesis. The search IS working!

## Root Cause: CORS Blocking the Response

When the frontend makes a direct request to `https://podinsight-api.vercel.app/api/search`, the browser blocks the response due to CORS policy. The request succeeds, but the frontend cannot read the data.

## How to Verify This Is CORS

1. Open Chrome DevTools (F12)
2. Go to the Console tab
3. Try a search
4. Look for an error like:

```
Access to fetch at 'https://podinsight-api.vercel.app/api/search' from origin 'https://your-frontend-domain.vercel.app'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## The Solution

The frontend needs to implement a proxy route for the search endpoint, following the same pattern as the prewarm endpoint (which works correctly).

### Step 1: Create the Proxy Route

Create a new file: `/app/api/search/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const response = await fetch('https://podinsight-api.vercel.app/api/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Search proxy error:', error)
    return NextResponse.json(
      { error: 'Search request failed' },
      { status: 500 }
    )
  }
}
```

### Step 2: Update the Frontend Component

Change the search component to use the local proxy instead of the direct backend URL:

```typescript
// OLD (causes CORS error):
const response = await fetch('https://podinsight-api.vercel.app/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: searchQuery, limit: 10 })
})

// NEW (no CORS issues):
const response = await fetch('/api/search', {  // Local path!
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: searchQuery, limit: 10 })
})
```

## Why This Works

- The browser makes a same-origin request to `/api/search` (no CORS)
- Next.js proxy forwards the request to the backend (server-to-server, no CORS)
- Next.js returns the response to the browser (same-origin, no CORS)

## Comparison with Working Endpoints

| Endpoint | Implementation | Status | Why It Works |
|----------|---------------|--------|--------------|
| `/api/prewarm` | Has proxy at `/app/api/prewarm/route.ts` | ✅ Working | No CORS issues |
| `/api/search` | Direct backend call | ❌ Broken | CORS blocks response |

## Additional Notes

### About the 27-second Response Time
The logs show the search takes 27 seconds during MongoDB replica elections. This is a separate issue we're addressing, but it's NOT causing the frontend hang. Even with a fast 4-second response, the frontend would still hang due to CORS.

### Testing the Fix
1. Implement the proxy route
2. Update the component to use `/api/search`
3. Test a search - you should see results appear
4. Check DevTools Console - no CORS errors should appear

## Questions?

If you need help implementing this or have questions about the proxy pattern, refer to:
- The working prewarm implementation at `/app/api/prewarm/route.ts`
- The CORS policy documentation at `/docs/sprint5/CORS_POLICY.md`
