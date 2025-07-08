# Episode Intelligence API Integration Guide

## Overview

This guide documents the new MongoDB collections created for Episode Intelligence and the API endpoints needed for dashboard integration.

## MongoDB Collections

### 1. `episode_intelligence`
Stores extracted signals and intelligence data for each episode.

**Schema:**
```javascript
{
  episode_id: String,       // Maps to Supabase episodes.guid
  signals: {
    investable: [{
      chunk_id: String,
      signal_text: String,
      confidence: Number,
      entities: [String],
      keywords: [String]
    }],
    competitive: [...],     // Same structure
    portfolio: [...],       // Same structure
    soundbites: [...]       // Same structure
  },
  chunk_refs: [String],     // References to transcript_chunks_768d
  relevance_score: Number,  // 0-100 from Story 2
  last_updated: Date
}
```

**Indexes:**
- `episode_id` (unique)
- `relevance_score` (descending)
- `last_updated` (descending)

### 2. `user_intelligence_prefs`
Stores user preferences for intelligence features.

**Schema:**
```javascript
{
  user_id: String,          // Maps to Supabase auth.users.id
  preferences: {
    topics: [String],       // Interested topics
    keywords: [String],     // Custom keywords
    notification_threshold: Number  // Min relevance score
  },
  last_updated: Date
}
```

**Indexes:**
- `user_id` (unique)

### 3. `podcast_authority`
Stores podcast tier rankings for authority scoring.

**Schema:**
```javascript
{
  feed_slug: String,        // Unique identifier
  podcast_name: String,     // Display name
  tier: Number,            // 1-5 (1 = highest)
  authority_score: Number,  // 0-100
  last_updated: Date
}
```

**Indexes:**
- `feed_slug` (unique)
- `podcast_name` (text index)

## API Endpoints Needed

### 1. Episode Intelligence Endpoints

#### GET `/api/episodes/{episode_guid}/intelligence`
Returns intelligence data for a single episode.

**Response:**
```json
{
  "episode_id": "guid",
  "signals": {
    "investable": [...],
    "competitive": [...],
    "portfolio": [...],
    "soundbites": [...]
  },
  "relevance_score": 85.5,
  "metadata": {
    "podcast_name": "All-In Podcast",
    "episode_title": "...",
    "published_at": "2025-01-07T..."
  }
}
```

#### GET `/api/episodes/intelligence`
Returns intelligence data for multiple episodes with filtering.

**Query Parameters:**
- `limit` (default: 20)
- `offset` (default: 0)
- `min_score` (default: 0)
- `signal_type` (optional: investable|competitive|portfolio|soundbites)
- `podcast_slug` (optional)
- `days` (default: 30)

**Response:**
```json
{
  "episodes": [...],
  "total": 150,
  "has_more": true
}
```

### 2. Dashboard Intelligence Card Endpoints

#### GET `/api/dashboard/intelligence/summary`
Returns summary data for the dashboard intelligence cards.

**Response:**
```json
{
  "top_episodes": [
    {
      "episode_id": "guid",
      "podcast_name": "All-In Podcast",
      "episode_title": "...",
      "relevance_score": 92.5,
      "signal_counts": {
        "investable": 3,
        "competitive": 2,
        "portfolio": 1,
        "soundbites": 5
      },
      "preview_bullets": [
        "Sequoia raising $8B for new fund",
        "OpenAI revenue hits $300M MRR"
      ]
    }
  ],
  "stats": {
    "total_episodes_processed": 50,
    "episodes_last_7_days": 12,
    "high_value_signals": 45
  }
}
```

#### GET `/api/dashboard/intelligence/feed`
Returns personalized intelligence feed for the user.

**Headers:**
- `Authorization: Bearer {token}`

**Response:**
```json
{
  "personalized_episodes": [...],
  "recommended_topics": ["AI", "B2B SaaS", "Crypto"],
  "trending_signals": [...]
}
```

### 3. Intelligence Brief Modal Endpoints

#### GET `/api/episodes/{episode_guid}/brief`
Returns detailed intelligence brief for modal display.

**Response:**
```json
{
  "episode": {
    "guid": "...",
    "title": "...",
    "podcast": "...",
    "published_at": "...",
    "audio_url": "..."
  },
  "intelligence": {
    "key_signals": [...],
    "entities_mentioned": {
      "companies": ["OpenAI", "Anthropic"],
      "people": ["Sam Altman", "Dario Amodei"],
      "investors": ["Sequoia", "a16z"]
    },
    "timestamps": [
      {
        "time": "00:15:30",
        "signal": "Discussion about AI agents market"
      }
    ],
    "related_episodes": [...]
  }
}
```

### 4. User Preference Endpoints

#### GET `/api/user/intelligence/preferences`
Get user's intelligence preferences.

#### PUT `/api/user/intelligence/preferences`
Update user's intelligence preferences.

**Request Body:**
```json
{
  "topics": ["AI", "Fintech"],
  "keywords": ["series A", "YC"],
  "notification_threshold": 70
}
```

## Dashboard Component Integration

### 1. Intelligence Dashboard Card
Located: `components/intelligence/IntelligenceDashboardCard.tsx`

**Data Source:**
- Primary: `GET /api/dashboard/intelligence/summary`
- Refresh: Every 5 minutes or on user action

**Features:**
- Top 5 episodes by relevance score
- Signal type badges with counts
- Click to open Intelligence Brief modal
- "View All" link to dedicated intelligence page

### 2. Intelligence Brief Modal
Located: `components/intelligence/IntelligenceBriefModal.tsx`

**Data Source:**
- Primary: `GET /api/episodes/{guid}/brief`
- Loaded on modal open

**Features:**
- Full signal list by category
- Entity extraction display
- Audio timestamps with player integration
- Related episodes suggestions

### 3. Episode Card Enhancement
Located: `components/episodes/EpisodeCard.tsx`

**Changes Needed:**
- Add relevance score badge (if score > 70)
- Add signal count indicators
- Add "View Intelligence" button
- Highlight high-value episodes

## Implementation Priority

### Phase 1 (Story 5B - API Endpoints)
1. Create MongoDB connection service
2. Implement episode intelligence endpoints
3. Add authentication middleware
4. Create response DTOs

### Phase 2 (Story 3 - Dashboard Cards)
1. Create IntelligenceDashboardCard component
2. Integrate with API endpoints
3. Add loading/error states
4. Implement auto-refresh

### Phase 3 (Story 4 - Intelligence Brief)
1. Create IntelligenceBriefModal component
2. Integrate with episode brief endpoint
3. Add entity highlighting
4. Connect audio player timestamps

## Performance Considerations

1. **Caching Strategy:**
   - Cache intelligence summaries for 5 minutes
   - Cache individual episode briefs for 1 hour
   - Invalidate on new signal extraction

2. **Query Optimization:**
   - Use MongoDB aggregation for summary stats
   - Limit initial loads to 20 episodes
   - Implement cursor-based pagination

3. **Real-time Updates:**
   - WebSocket for live signal updates (future)
   - Polling for dashboard summary (current)

## Security Notes

1. **Authentication Required:**
   - All intelligence endpoints require auth
   - User preferences are user-scoped
   - Rate limiting: 100 requests/minute

2. **Data Access:**
   - Users only see processed episodes
   - No access to raw extraction data
   - Personalization based on user_id

## Testing Checklist

- [ ] API endpoints return correct data structure
- [ ] Dashboard cards load within 2 seconds
- [ ] Modal opens without lag
- [ ] Relevance scores display correctly
- [ ] Signal counts are accurate
- [ ] Authentication works properly
- [ ] Error states handle gracefully
- [ ] Mobile responsive design works

## Migration Notes

No changes to existing Supabase tables. MongoDB collections are additive.

Key field mapping:
- MongoDB `episode_id` = Supabase `episodes.guid`
- MongoDB `user_id` = Supabase `auth.users.id`
- MongoDB `feed_slug` = Supabase `podcasts.feed_slug`
