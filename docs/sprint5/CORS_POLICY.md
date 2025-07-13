# CORS Policy - Frontend Proxy Pattern

**Date**: 2025-01-13
**Status**: OFFICIAL POLICY
**Sprint**: 5

## Executive Summary

All Cross-Origin Resource Sharing (CORS) issues must be handled via frontend proxies. Backend services should NOT be modified to handle CORS.

## The Policy

### ✅ DO: Use Frontend Proxies

Create Next.js API routes that proxy requests to the backend:

```typescript
// Frontend: /app/api/search/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  const body = await request.json()

  const response = await fetch('https://podinsight-api.vercel.app/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })

  const data = await response.json()
  return NextResponse.json(data)
}
```

Then update components to use the local proxy:
```typescript
// Component
const response = await fetch('/api/search', {  // Local path, no CORS
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'AI valuations' })
})
```

### ❌ DON'T: Modify Backend for CORS

Never:
- Add CORS middleware to FastAPI apps
- Create wrapper endpoints for CORS
- Modify vercel.json CORS headers (they're already correct)
- Create FastAPI apps at module level

## Why This Policy Exists

1. **Proven Pattern**: The prewarm endpoint already uses this successfully
2. **Reliability**: Frontend proxies always work, backend CORS is fragile
3. **Separation of Concerns**: Backend focuses on API logic, frontend handles routing
4. **Safety**: Modifying backend for CORS has broken the entire system before

## Current Implementation Status

| Endpoint | Proxy Status | Path |
|----------|-------------|------|
| /api/prewarm | ✅ Implemented | /app/api/prewarm/route.ts |
| /api/search | ❌ Needs Implementation | /app/api/search/route.ts |
| Other endpoints | Direct calls (working) | N/A |

## Implementation Guide

1. **Identify** endpoints that need CORS handling (called from frontend)
2. **Create** a proxy route in `/app/api/[endpoint]/route.ts`
3. **Update** frontend components to use the local path
4. **Test** to ensure the proxy works correctly
5. **Document** the new proxy in this table

## Historical Context

On 2025-01-13, attempts to fix CORS in the backend resulted in:
- Complete backend failure (all endpoints returning 500)
- 1.5 hours of downtime
- Emergency rollback required

This policy prevents such incidents from recurring.

## Questions?

Contact the architecture team before deviating from this policy.
