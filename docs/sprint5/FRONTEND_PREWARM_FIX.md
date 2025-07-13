# Frontend Prewarm Fix Required - Sprint 5

**Date**: 2025-01-13
**Priority**: HIGH - Blocking 5-second search target
**Issue**: Prewarm endpoint returning 404, causing 10-second Modal cold starts

## Executive Summary

The search functionality is almost at our 5-second target, but Modal cold starts are adding 10 seconds to search time. The prewarm endpoint exists in the backend but the frontend is getting a 404 error when trying to call it.

## Current Situation

### Search Performance Breakdown
- **Modal embedding**: 9.88s (cold start) vs 0.36s (warm) ❌
- **MongoDB operations**: 2.5s (improved from 5.8s) ✅
- **Context expansion**: 0.16s ✅
- **OpenAI synthesis**: ~1.5s ✅
- **Total**: 14.3s (should be 4-5s with warm Modal)

### The Problem

When the search modal opens, it tries to prewarm Modal:
```
ai-search-modal-enhanced.tsx:204 Search modal opened. Pre-warming backend...
:3002/api/prewarm:1 Failed to load resource: the server responded with a status of 404 (Not Found)
app-index.js:33 Prewarm failed: 404
```

This 404 error means Modal isn't pre-warmed, resulting in a 9.88s cold start on every search.

## Root Cause

The frontend is calling `:3002/api/prewarm` which is trying to hit a local frontend route, but either:
1. The proxy file doesn't exist at `/app/api/prewarm/route.ts`
2. The proxy exists but isn't configured correctly

According to the CORS policy documentation, this proxy should already be implemented.

## Required Fix

### Option 1: If Proxy Already Exists
Verify the proxy file at `/app/api/prewarm/route.ts` matches this pattern:

```typescript
// /app/api/prewarm/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const response = await fetch('https://podinsight-api.vercel.app/api/prewarm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Prewarm proxy error:', error)
    return NextResponse.json(
      { status: 'error', message: 'Prewarm failed' },
      { status: 500 }
    )
  }
}
```

### Option 2: If Proxy Doesn't Exist
Create the file above at `/app/api/prewarm/route.ts`

### Verify Frontend is Calling Correct Path
Ensure the component is calling the local path:
```typescript
// Should be calling:
fetch('/api/prewarm', { method: 'POST' })

// NOT:
fetch('https://podinsight-api.vercel.app/api/prewarm', { method: 'POST' })
```

## Expected Impact

Once the prewarm proxy is working:
1. Modal will be pre-warmed when users open the search modal
2. Search embedding time will drop from 9.88s to 0.36s
3. Total search time will be ~4-5s (meeting our target!)

## Testing

1. Open the search modal
2. Check browser console - should see "Pre-warming backend..." without 404 errors
3. Run a search - should complete in ~4-5 seconds
4. Check backend logs for "Modal pre-warm successful" message

## Additional Context

- The backend prewarm endpoint exists and is working at `/api/prewarm`
- This follows the established CORS proxy pattern already used successfully
- The MongoDB performance improvements are already deployed and working (2.5s, down from 5.8s)
- This is the last blocker to achieving 5-second search performance

## Questions?

The backend team is available to help debug if needed. The prewarm endpoint is simple - it just sends a test embedding request to Modal to warm up the GPU instance.
