# URGENT: Frontend Search CORS Fix Implementation Guide

**Date**: 2025-01-13
**Priority**: CRITICAL - Blocking demos next week
**Time to implement**: ~15 minutes
**Issue**: Search functionality completely broken due to CORS errors

## 🚨 The Problem

The frontend is making direct API calls to the backend, causing CORS errors:

```
Access to fetch at 'https://podinsight-api.vercel.app/api/search' from origin 'http://localhost:3002' has been blocked by CORS policy
```

This is blocking the core search functionality - VCs cannot search for podcast insights.

## ✅ The Solution

Create a frontend proxy endpoint (exactly like the existing prewarm proxy).

## 📝 Implementation Steps

### Step 1: Create the Search Proxy Endpoint

Create a new file: `/app/api/search/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    // Get the backend API URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://podinsight-api.vercel.app'

    // Get the request body
    const body = await request.json()

    console.log(`Forwarding search request to: ${apiUrl}/api/search`)

    // Forward the search request to the backend
    const response = await fetch(`${apiUrl}/api/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })

    // Return error if backend fails
    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend search failed:', response.status, errorText)
      return NextResponse.json({
        error: `Search failed: ${response.status}`,
        details: errorText
      }, { status: response.status })
    }

    // Return the backend response
    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('Error calling backend search:', error)
    return NextResponse.json({
      error: 'Search request failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 })
  }
}
```

### Step 2: Update the Search Component

In `/components/dashboard/ai-search-modal-enhanced.tsx`, find this function around line ~260:

```typescript
async function performSearchApi(searchQuery: string, signal: AbortSignal) {
  const response = await fetch('https://podinsight-api.vercel.app/api/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: searchQuery,
      limit: 10
    }),
    signal,
  })
```

Change it to:

```typescript
async function performSearchApi(searchQuery: string, signal: AbortSignal) {
  const response = await fetch('/api/search', {  // <-- CHANGED: Now uses local proxy
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: searchQuery,
      limit: 10
    }),
    signal,
  })
```

### Step 3: Test Locally

1. Start the frontend dev server: `npm run dev`
2. Open the search modal (usually Cmd+K or clicking search)
3. Type a query like "AI valuations"
4. Verify it returns results without CORS errors

## 🔍 Technical Context

### Why This Works
- Frontend makes request to its own origin (`/api/search`)
- Next.js proxy forwards to backend (`https://podinsight-api.vercel.app/api/search`)
- No CORS issues because it's same-origin from browser's perspective

### Existing Pattern
You already have this pattern working for prewarm:
- `/app/api/prewarm/route.ts` → `https://podinsight-api.vercel.app/api/prewarm`

### Backend Details
- **Backend URL**: `https://podinsight-api.vercel.app`
- **Search Endpoint**: `/api/search`
- **Method**: POST
- **Request Body**:
  ```json
  {
    "query": "search terms",
    "limit": 10
  }
  ```
- **Response**: Search results with AI-synthesized answer

## 🚀 Deployment

After implementing:
1. Commit with message: `fix(api): Add search proxy to resolve critical CORS issue`
2. Push to your branch
3. Create PR with description linking to this guide
4. Deploy to staging/production

## ⚠️ Other Issues to Note

While implementing this fix, be aware of these other issues that need attention:

1. **Dashboard API 500 errors**: `/api/intelligence/dashboard` is failing
2. **Topics API 500 errors**: `/api/topics?tags=...` is failing
3. **Prewarm 404**: Backend `/api/prewarm` returns 404 (but proxy handles gracefully)

These are separate backend issues that the backend team is investigating.

## 📞 Questions?

The search proxy fix is identical to the prewarm proxy pattern. If you have questions:
1. Check `/app/api/prewarm/route.ts` for reference
2. Review Sprint 5 documentation about CORS handling via proxies
3. Contact backend team for API specifics

## 🎯 Success Criteria

- [ ] Search queries work without CORS errors
- [ ] Results appear in the search modal
- [ ] No console errors about CORS
- [ ] Local development works
- [ ] Production deployment works

---

**Remember**: This is blocking critical VC demos next week. The backend search API is working perfectly - it just needs the proxy to handle CORS.
