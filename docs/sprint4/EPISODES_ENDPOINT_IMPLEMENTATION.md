# Episode Intelligence - Episodes Endpoint Implementation

**Date:** 10 July 2025
**Status:** ✅ **IMPLEMENTED & READY**
**Endpoint:** `/api/intelligence/episodes`

## Summary

A dedicated episodes endpoint has been implemented to fix the frontend workaround where they were using the dashboard endpoint (which only returns 8 episodes) for the "All Episodes" modal. This new endpoint returns ALL 50 episodes with intelligence data and supports pagination, search, and sorting.

## The Problem: Frontend Workaround

### What Was Happening
- Frontend needed to show ALL episodes with intelligence data in the "All Episodes" modal
- Dashboard endpoint (`/api/intelligence/dashboard`) only returns top 8 episodes
- Frontend was using dashboard endpoint as a temporary workaround
- This meant users could only see 8 episodes instead of all 50

### Why It Was Problematic
1. **Limited Data**: Only showing 8 of 50 episodes (84% of content hidden)
2. **Semantic Mismatch**: Dashboard endpoint is for summary view, not full listing
3. **No Pagination**: Can't handle future scaling when we have 500+ episodes
4. **No Search**: Users can't find specific episodes
5. **Performance**: Loading all episodes at once would be inefficient at scale

## The Solution: Dedicated Episodes Endpoint

### Endpoint Details

**URL:** `GET /api/intelligence/episodes`

**Query Parameters:**
| Parameter | Type | Description | Default | Constraints |
|-----------|------|-------------|---------|-------------|
| `page` | integer | Page number | 1 | Min: 1 |
| `limit` | integer | Items per page | 10 | Min: 1, Max: 100 |
| `search` | string | Search in title/podcast | null | Case-insensitive |
| `sort` | string | Sort field:direction | "relevance_score:desc" | Fields: relevance_score, published_at |

### Response Format

```json
{
  "data": [
    {
      "episode_id": "685ba731e4f9ec2f07562307",
      "title": "949. News: Kraken buys NinjaTrader...",
      "podcast_name": "Fintech Insider Podcast by 11:FS",
      "published_at": "2025-03-31T05:00:00",
      "duration_seconds": 0,
      "relevance_score": 1.0,
      "signals": [
        {
          "type": "investable",
          "content": "Lumber has raised $15.5 million...",
          "confidence": 0.9,
          "timestamp": "19:26"
        }
        // ... more signals
      ],
      "summary": "Episode discusses major fintech...",
      "key_insights": ["Kraken's expansion..."],
      "audio_url": "https://s3.amazonaws.com/..."
    }
    // ... more episodes
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "limit": 10,
      "total_items": 50,
      "total_pages": 5
    }
  }
}
```

## Frontend Integration Guide

### Update the API Hook

Replace the temporary dashboard endpoint with the proper episodes endpoint:

```javascript
// OLD (temporary workaround)
const response = await fetch('/api/intelligence/dashboard');

// NEW (proper implementation)
const response = await fetch(
  `/api/intelligence/episodes?page=${page}&limit=${limit}&search=${search}&sort=${sort}`
);
```

### Example Implementation

```javascript
// useAllEpisodesAPI.ts
export const useAllEpisodesAPI = (page = 1, limit = 10, search = '', sort = 'relevance_score:desc') => {
  return useQuery({
    queryKey: ['episodes', page, limit, search, sort],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
        ...(search && { search }),
        sort
      });

      const response = await fetch(`/api/intelligence/episodes?${params}`);
      if (!response.ok) throw new Error('Failed to fetch episodes');

      return response.json();
    }
  });
};
```

### Key Differences from Dashboard

1. **Returns ALL Episodes**: 50 episodes instead of just top 8
2. **Pagination Support**: Use `page` and `limit` for efficient loading
3. **Search Capability**: Filter by title or podcast name
4. **Sorting Options**: Sort by relevance score or publication date
5. **Proper Response Format**: Includes pagination metadata

## Usage Examples

### Get First Page (Default)
```
GET /api/intelligence/episodes
```

### Get Second Page with 20 Items
```
GET /api/intelligence/episodes?page=2&limit=20
```

### Search for "AI" Episodes
```
GET /api/intelligence/episodes?search=AI
```

### Sort by Newest First
```
GET /api/intelligence/episodes?sort=published_at:desc
```

### Combined: Search + Sort + Pagination
```
GET /api/intelligence/episodes?search=crypto&sort=relevance_score:desc&page=1&limit=15
```

## Performance Considerations

- The endpoint loads all 50 episodes into memory for filtering/sorting
- This is acceptable for MVP scale (50 episodes)
- When scaling to 1000+ episodes, we'll optimize with:
  - Database-level search using indexes
  - Cursor-based pagination
  - Caching layer

## Testing the Endpoint

```bash
# Test basic request
curl https://podinsight-api.vercel.app/api/intelligence/episodes

# Test with pagination
curl "https://podinsight-api.vercel.app/api/intelligence/episodes?page=2&limit=20"

# Test search
curl "https://podinsight-api.vercel.app/api/intelligence/episodes?search=fintech"

# Test sorting
curl "https://podinsight-api.vercel.app/api/intelligence/episodes?sort=published_at:asc"
```

## Migration Steps for Frontend

1. **Update API Hook**: Change endpoint from `/dashboard` to `/episodes`
2. **Handle Response Format**: Use `data` array and `meta.pagination`
3. **Implement Pagination**: Use total_pages for pagination controls
4. **Add Search**: Connect search input to `search` parameter
5. **Add Sorting**: Allow users to sort by date or relevance

## Benefits Over Workaround

| Aspect | Workaround (Dashboard) | Proper Solution (Episodes) |
|--------|------------------------|---------------------------|
| Episodes Shown | 8 only | All 50 |
| Pagination | ❌ None | ✅ Full support |
| Search | ❌ None | ✅ Title & podcast |
| Sorting | ❌ Fixed | ✅ Configurable |
| Scalability | ❌ Poor | ✅ Ready for growth |
| API Semantics | ❌ Wrong endpoint | ✅ Correct endpoint |

## Next Steps

### Frontend Team
1. Update `useAllEpisodesAPI` hook to use new endpoint
2. Implement pagination controls using `meta.pagination`
3. Connect search input to API search parameter
4. Add sort dropdown for relevance/date options
5. Remove workaround comments from code

### Backend (Future)
1. Add more sort options (duration, signal count)
2. Implement advanced search (by signal type, date range)
3. Add filters (by podcast, signal type)
4. Optimize for 1000+ episodes with DB-level operations

---

**Status: The episodes endpoint is now live and ready for integration. No more workarounds needed!**
