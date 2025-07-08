# Story 4: Dashboard API Integration - Single Source of Truth

## Story Overview

**Title**: STORY 4: API Integration for Episode Intelligence Component  
**Repository**: Dashboard (Frontend)  
**Purpose**: Connect the Episode Intelligence dashboard components to the existing API endpoints from Story 5B  
**Status**: Not Started (was confused with creating new API endpoints)

## What Story 4 Actually Is

Story 4 is a **frontend integration story** that connects the dashboard components to the **already-built API endpoints from Story 5B**.

### Story 5B Already Provided These Endpoints

All endpoints are in `api/intelligence.py` and require authentication:

1. **GET /api/intelligence/dashboard**
   - Returns top 6-8 episodes by relevance score
   - Includes signals, summaries, and metadata
   - Response format matches dashboard card needs

2. **GET /api/intelligence/brief/{episode_id}**
   - Returns full episode details for modal view
   - Includes all signals, insights, and audio URL
   - Used when user clicks on an episode card

3. **POST /api/intelligence/share**
   - Handles sharing via email or Slack
   - Accepts episode_id, method, recipient
   - Returns success confirmation

4. **PUT /api/intelligence/preferences**
   - Updates user preferences
   - Portfolio companies, interests, notifications
   - Affects relevance scoring

## What Needs to Be Done (Dashboard Repository)

### 1. Environment Setup
```env
# .env.local
NEXT_PUBLIC_API_URL=https://podinsight-api.vercel.app
```

### 2. Create API Client
```typescript
// lib/api-client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Note: Auth tokens will be added when authentication is implemented
```

### 3. Create React Query Hooks

#### useIntelligenceDashboard Hook
```typescript
// hooks/use-intelligence-dashboard.ts
export const useIntelligenceDashboard = () => {
  return useQuery({
    queryKey: ['intelligence', 'dashboard'],
    queryFn: () => apiClient.get('/api/intelligence/dashboard'),
    refetchInterval: 60000, // 60 seconds
    staleTime: 30000,
  });
};
```

#### useEpisodeBrief Hook
```typescript
// hooks/use-episode-brief.ts
export const useEpisodeBrief = (episodeId: string, enabled: boolean) => {
  return useQuery({
    queryKey: ['intelligence', 'brief', episodeId],
    queryFn: () => apiClient.get(`/api/intelligence/brief/${episodeId}`),
    enabled, // Only fetch when modal is open
  });
};
```

### 4. Update Dashboard Component

Replace mock data in `components/dashboard/actionable-intelligence-cards.tsx`:

```typescript
const { data, isLoading, error } = useIntelligenceDashboard();

if (isLoading) return <LoadingCards />;
if (error) return <ErrorState />;

// Map API response to component props
const episodes = data.episodes.map(episode => ({
  id: episode.episode_id,
  title: episode.title,
  podcast: episode.podcast_name,
  signals: episode.signals,
  urgency: determineUrgency(episode.signals),
  // ... other mappings
}));
```

### 5. Implement Share Functionality

```typescript
const { mutate: shareEpisode } = useMutation({
  mutationFn: (params) => apiClient.post('/api/intelligence/share', params),
  onSuccess: () => toast.success('Episode shared successfully'),
});
```

## Important Notes

### Authentication Status
- **Current**: No authentication implemented (despite Story 5B requiring it)
- **Temporary**: Endpoints may work without auth during development
- **Future**: Will need to add auth tokens to API client

### Response Mapping
The API returns different field names than the mock data. Key mappings:
- `episode_id` → `id`
- `podcast_name` → `podcast`
- `relevance_score` → Used for sorting
- `signals` → Map to card categories

### Error Handling
- Network errors: Show retry button
- 401/403: Will occur when auth is implemented
- 404: Episode not found
- 500: Server error - show generic message

## Subtasks Breakdown

1. **Set up API client and authentication** ⏳
   - Create axios client (auth to be added later)
   
2. **Create useIntelligence hook** ⏳
   - Fetches from `/api/intelligence/dashboard`
   
3. **Create useEpisodeBrief hook** ⏳
   - Fetches from `/api/intelligence/brief/{id}`
   
4. **Integrate API hooks with components** ⏳
   - Replace mock data in dashboard component
   
5. **Implement error handling UI** ⏳
   - Loading states, error boundaries
   
6. **Add real-time updates** ⏳
   - 60-second polling already in hook
   
7. **Optimize performance** ⏳
   - React Query handles caching
   
8. **Integration testing** ⏳
   - Test with real API data

## Testing the Integration

1. **Check API is working**:
   ```bash
   curl https://podinsight-api.vercel.app/api/intelligence/dashboard
   ```

2. **Expected Response Structure**:
   ```json
   {
     "episodes": [...],
     "total_episodes": 8,
     "generated_at": "2024-01-08T10:00:00Z"
   }
   ```

3. **Verify in Dashboard**:
   - Episodes load automatically
   - Click episode → modal opens with details
   - Share button → triggers share API
   - 60-second refresh works

## Common Pitfalls to Avoid

1. **Don't create new API endpoints** - Use Story 5B endpoints
2. **Don't implement auth yet** - It's not ready
3. **Don't cache on frontend** - React Query handles it
4. **Don't poll too frequently** - 60 seconds minimum

## Success Criteria

- ✅ Dashboard shows real episodes from API
- ✅ Modal loads episode details on demand
- ✅ Share functionality works (simulated)
- ✅ Updates every 60 seconds
- ✅ Graceful error handling
- ✅ Loading states during fetch

---

**Remember**: Story 4 is about connecting the dashboard to existing API endpoints, NOT creating new ones!