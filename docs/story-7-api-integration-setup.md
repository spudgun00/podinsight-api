# Story 7: API Integration Setup Guide

## Overview
This document guides you through integrating the Episode Intelligence dashboard components with the real API endpoints, replacing mock data with live data from the FastAPI backend.

## Architecture Summary

### Technology Stack
- **Frontend**: React with TypeScript
- **Data Fetching**: React Query (TanStack Query)
- **HTTP Client**: Axios with interceptors
- **Authentication**: Supabase JWT tokens
- **Error Handling**: Error boundaries + toast notifications
- **Caching**: React Query with 60s dashboard refresh

## Implementation Files Created

### 1. Core API Infrastructure
- `lib/api-client.ts` - Axios client with auth interceptors and token refresh
- `lib/auth-service.ts` - Supabase auth integration
- `providers/query-provider.tsx` - React Query setup with global error handling

### 2. Data Fetching Hooks
- `hooks/use-intelligence.ts` - Dashboard data with 60s polling
- `hooks/use-episode-brief.ts` - Episode brief lazy loading
- `hooks/use-share-episode.ts` - Share functionality with optimistic updates
- `hooks/use-network-status.ts` - Network connectivity monitoring

### 3. UI Components
- `components/dashboard/episode-intelligence-cards-api.tsx` - Main dashboard
- `components/dashboard/intelligence-brief-modal-api.tsx` - Brief modal
- `components/dashboard/loading-skeleton.tsx` - Loading states
- `components/dashboard/error-state.tsx` - Error handling UI
- `components/error-boundary.tsx` - React error boundary

## Setup Instructions

### 1. Install Dependencies
```bash
npm install @tanstack/react-query @tanstack/react-query-devtools axios react-hot-toast @supabase/supabase-js
```

### 2. Environment Variables
Add to `.env.local`:
```env
NEXT_PUBLIC_API_URL=https://your-api-url.vercel.app
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

### 3. App Setup
In your main app file (`app/layout.tsx` or `_app.tsx`):

```tsx
import { QueryProvider } from '@/providers/query-provider';
import { IntelligenceErrorBoundary } from '@/components/error-boundary';
import { Toaster } from 'react-hot-toast';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <QueryProvider>
          <IntelligenceErrorBoundary>
            {children}
          </IntelligenceErrorBoundary>
          <Toaster position="top-right" />
        </QueryProvider>
      </body>
    </html>
  );
}
```

### 4. Replace Mock Components
In your dashboard page, replace the mock component:

```tsx
// Before (mock data)
import { EpisodeIntelligenceCards } from '@/components/dashboard/episode-intelligence-cards';

// After (API integration)
import { EpisodeIntelligenceCards } from '@/components/dashboard/episode-intelligence-cards-api';
```

## Key Features Implemented

### 1. Authentication & Token Management
- Automatic token injection via Axios interceptors
- Token refresh with request queuing
- Auth state synchronization across tabs

### 2. Data Fetching
- 60-second auto-refresh for dashboard
- Lazy loading for episode briefs
- Prefetching on hover (optional)
- Stale-while-revalidate pattern

### 3. Error Handling
- Network failure detection
- Specific handling for 401, 404, 429, 500 errors
- Toast notifications for background refetch failures
- Error boundaries for catastrophic failures

### 4. Performance Optimizations
- Query caching (60s dashboard, 5min briefs)
- Background refetch disabled when tab inactive
- Optimistic updates for share actions
- Request deduplication

### 5. User Experience
- Loading skeletons during fetch
- Stale data indicator during refresh
- Graceful degradation on errors
- Offline mode detection

## API Response Formats

### Dashboard Response
```typescript
{
  episodes: EpisodeBrief[],
  total_episodes: number,
  generated_at: string
}
```

### Episode Brief
```typescript
{
  episode_id: string,
  title: string,
  podcast_name: string,
  published_at: string,
  duration_seconds: number,
  relevance_score: number,
  signals: Signal[],
  summary: string,
  key_insights: string[],
  audio_url?: string
}
```

### Signal
```typescript
{
  type: 'investable' | 'competitive' | 'portfolio' | 'sound_bite',
  content: string,
  confidence: number,
  timestamp?: string
}
```

## Testing Checklist

- [ ] Dashboard loads with real data
- [ ] 60-second auto-refresh works
- [ ] Brief modal opens with lazy-loaded data
- [ ] Share functionality sends to API
- [ ] Auth errors redirect to login
- [ ] Network errors show appropriate UI
- [ ] Offline mode displays correct message
- [ ] Token refresh handles concurrent requests
- [ ] React Query DevTools show correct cache state

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check JWT token in localStorage
   - Verify SUPABASE_JWT_SECRET in API
   - Ensure auth context provides token

2. **CORS Errors**
   - Verify API CORS configuration
   - Check API_BASE_URL matches deployment

3. **No Data Showing**
   - Check MongoDB connection in API
   - Verify episode_metadata collection has data
   - Check user preferences exist

4. **Polling Not Working**
   - Ensure tab is active (background refetch disabled)
   - Check React Query DevTools for errors
   - Verify refetchInterval configuration

## Next Steps

1. Add comprehensive error tracking (Sentry)
2. Implement request performance monitoring
3. Add unit tests with Mock Service Worker
4. Set up E2E tests for critical flows
5. Add analytics for share actions
6. Implement push notifications (future)
