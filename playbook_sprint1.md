# PodInsightHQ: Sprint 1 Playbook - Intelligence Features

*This document is the single source of truth for implementing natural language search, entity tracking, and enhanced visualizations for PodInsightHQ. It follows the proven Genesis Sprint methodology with clinical precision.*

---

## Part 1: Sprint Definition & Product Decisions

### Sprint Goal (The Mission)
Transform our working Topic Velocity dashboard into an intelligent search and insights platform by adding natural language search across 1,171 episodes, entity tracking, sentiment analysis, and user authentication—proving we can deliver actionable intelligence beyond simple trend charts.

### Definition of Success (How We Know We've Won)
- ✅ **Search is Live**: Natural language queries return relevant transcript excerpts in <2 seconds
- ✅ **Entities are Trackable**: Users can search for any person/company across all episodes
- ✅ **Authentication Works**: Alpha users can create accounts and save searches
- ✅ **Sentiment Visible**: New heatmap shows market sentiment trends
- ✅ **UI Enhanced**: Missing v0 components integrated, animations polished
- ✅ **Audio Playable**: Click any quote to hear the original audio
- ✅ **Performance Maintained**: All features load in <2 seconds

### Core Product & Technical Decisions

| Theme | Question | Decision | Strategic Rationale |
|-------|----------|----------|-------------------|
| **Search Scope** | Full semantic search or keyword? | **Semantic search using embeddings.** | We already have embeddings for all episodes. Semantic search delivers "wow" factor. |
| **Search Results** | How many results per query? | **Top 10 with pagination.** | Balance between comprehensive and overwhelming. Users can load more if needed. |
| **Entity Display** | Show all 123k entities? | **No. Top 100 with search.** | Too many entities confuses. Focus on most mentioned people/companies. |
| **Authentication** | Build custom or use service? | **Supabase Auth (already have it).** | Leverage existing infrastructure. No need for separate auth system. |
| **User Accounts** | What can users save? | **Searches, tracked entities, topic sets.** | Start simple. These are the highest-value personalizations. |
| **Audio Playback** | Stream or download? | **Stream with pre-signed URLs.** | Better security, no storage costs, instant playback. |
| **Sentiment Analysis** | Real-time or pre-computed? | **Pre-computed during search.** | Can always optimize later. Start with working solution. |
| **Topic Customization** | Free text or predefined? | **Predefined + custom (max 8).** | Balance flexibility with performance. Too many topics clutters chart. |
| **Data Freshness** | When to add new episodes? | **Manual trigger for Sprint 1.** | Automation is Sprint 3. Focus on features first. |
| **Search Infrastructure** | Build or use service? | **pgvector in Supabase.** | We have embeddings + pgvector. No need for external service. |

### Environment Configuration Decisions

#### Step 1.0: Environment Key Separation
**What:** Separate API keys for staging vs production environments.

**Problem:** Staging tests can exhaust production OpenAI quota causing service outages.

**Solution:** Use distinct keys with clear prefixes:
```bash
# .env.staging
OPENAI_API_KEY_STAGING=sk-staging-xxx...
SUPABASE_URL_STAGING=https://staging-xxx.supabase.co

# .env.production  
OPENAI_API_KEY_PROD=sk-prod-xxx...
SUPABASE_URL_PROD=https://prod-xxx.supabase.co

# In code:
api_key = os.getenv(f'OPENAI_API_KEY_{ENV}')
```

**Monitoring:** Track OpenAI usage by key prefix in billing dashboard; set up alerts at 80% quota.

### Technical Architecture Decisions

| Component | Genesis Sprint | Sprint 1 Addition | Why This Approach |
|-----------|----------------|-------------------|-------------------|
| **Database** | 4 tables (episodes, topics, kpis, entities) | +2 tables (users, saved_searches) | Minimal schema changes |
| **API** | Single endpoint (/topic-velocity) | +3 endpoints (/search, /entities, /auth) | RESTful expansion |
| **Frontend** | Topic chart only | +Search UI, Entity explorer, User menu | Progressive enhancement |
| **Auth** | Basic auth (staging) | Supabase Auth (users) | Production-ready auth |
| **Search** | None | pgvector similarity search | Leverage existing embeddings |

---

## Part 2: Phase 1 - Search Infrastructure
*(Goal: Enable semantic search across all podcast transcripts)*

### 🎯 Critical Context
- We already have embeddings: 1,171 .npy files in S3 at ~140KB each
- pgvector is installed: Confirmed in Genesis Sprint (v0.8.0)
- Transcripts are stored: Full text in Supabase for display
- No external services needed: Everything runs in Supabase

### 🏠 Repository Setup

**Repository: Continue in existing repos**
- `podinsight-etl` - For search infrastructure setup
- `podinsight-api` - For new search endpoints
- `podinsight-dashboard` - For search UI components

### Step 1.1: Search Database Setup

**🏠 Repository: Work in `podinsight-etl` first**

**The Goal:** Add vector search capabilities to our existing database.

**The "Why":** pgvector enables similarity search - users ask "What are VCs saying about AI valuations?" and get semantically relevant results, not just keyword matches.

#### Database Migration

**Prompt for Claude Code:**
```
I need to add vector search capabilities to our existing PodInsightHQ database.

Current state:
- pgvector extension already installed (v0.8.0)
- We have embeddings stored in S3 as .npy files (path in s3_embeddings_path column)
- 1,171 episodes already loaded

Create migration files to add:

1. A new column to episodes table:
   - embedding vector(1536) - for storing OpenAI embeddings
   - Create index using ivfflat method for fast similarity search

2. New tables for user features:
   - users (id, email, created_at, subscription_tier)
   - saved_searches (id, user_id, query, created_at)
   - tracked_entities (id, user_id, entity_name, entity_type)

3. SQL functions for search:
   - similarity_search function using <-> operator
   - Function to format results with episode context

Generate:
- 002_vector_search.up.sql
- 002_vector_search.down.sql

Include comments explaining pgvector operators and why we use ivfflat indexing.
```

#### Step 1.1.1: Query-Embedding Cache Table

**What:** Supabase table that stores embeddings for previously seen queries to avoid re-computing.

**Problem:** Without caching, every identical search costs ~$0.0001 and adds ~300ms latency.

**Solution:** Add cache table and check before calling OpenAI:
```sql
-- In 002_vector_search.up.sql
CREATE TABLE query_cache (
    query_hash TEXT PRIMARY KEY,  -- SHA256 of lowercased query
    query_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP DEFAULT NOW(),
    use_count INTEGER DEFAULT 1
);

CREATE INDEX idx_query_cache_last_used ON query_cache(last_used DESC);

-- Cleanup old entries (>30 days unused)
CREATE OR REPLACE FUNCTION cleanup_old_queries() RETURNS void AS $$
BEGIN
    DELETE FROM query_cache WHERE last_used < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;
```

**Monitoring:** Track cache_hit_rate in API logs; target >80% for common queries.

#### Embeddings Loader Script

**🏠 Repository: Continue in `podinsight-etl`**

**Prompt for Claude Code:**
```
Create a Python script to load embeddings from S3 into our database.

Context:
- Embeddings are stored as .npy files in S3 (numpy arrays)
- Path to each embedding is in episodes.s3_embeddings_path
- Embeddings are 1536-dimensional vectors (OpenAI standard)
- We need to update the episodes table with these vectors

Create embeddings_loader.py that:

1. Queries all episodes with s3_embeddings_path
2. For each episode:
   - Downloads the .npy file from S3
   - Loads the numpy array
   - Converts to PostgreSQL vector format
   - Updates the episode record

3. Includes:
   - Progress bar (we have 1,171 embeddings)
   - Batch processing (50 at a time)
   - Error handling for missing files
   - Resume capability (skip already loaded)

4. Performance considerations:
   - Download files in parallel (max 10 concurrent)
   - Use UPDATE with prepared statements
   - Show progress: "Loading embedding 567/1171"

Note: Each .npy file is ~140KB, total ~164MB to download.
```

**Testing Checkpoints:**
1. **Migration test**: Run migration - should add embedding column without errors
2. **Sample load**: Load 10 embeddings - verify vectors stored correctly
3. **Query test**: `SELECT id FROM episodes WHERE embedding IS NOT NULL LIMIT 5` - should return 5 rows
4. **Similarity test**: Test pgvector similarity with sample query
5. **Performance test**: Measure load time for 100 embeddings (target: <30 seconds)
6. **Full load**: Run complete load of 1,171 embeddings

### Step 1.2: Search API Endpoints

**🏠 Repository: Switch to `podinsight-api`**

**The Goal:** Create API endpoints for semantic search and entity tracking.

**The "Why":** This exposes our rich transcript data through intelligent search, not just pre-defined topics.

#### Step 1.2.1: Rate Limiting Middleware

**What:** FastAPI middleware that limits requests per IP to prevent abuse.

**Problem:** Without limits, bots or testers can spam search endpoint, burning OpenAI credits.

**Solution:** Add slowapi rate limiter:
```python
# In api/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Create limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"]
)

# In main app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# On search endpoint
@app.post("/api/search")
@limiter.limit("20 per minute")
async def search(request: Request, query: SearchQuery):
    # ... search logic
```

**Monitoring:** Log 429 responses to track rate limit hits; alert if >10 per hour.

#### Search Endpoint Implementation

**Prompt for Claude Code:**
```
Add semantic search functionality to our FastAPI application.

Current state:
- We have /api/topic-velocity endpoint working
- Database has episodes with embeddings (vector(1536))
- Need to add search capabilities

Create a new endpoint: POST /api/search

Request body:
{
  "query": "What are VCs saying about AI valuations?",
  "limit": 10,
  "offset": 0
}

Implementation requirements:

1. Generate embedding for the query:
   - Use OpenAI API to create embedding
   - Cache query embeddings in memory (LRU cache)
   
2. Perform similarity search:
   - Use pgvector <-> operator
   - Include similarity score threshold (>0.7)
   - Order by similarity DESC

3. Return enriched results:
{
  "results": [
    {
      "episode_id": "uuid",
      "podcast_name": "The Twenty Minute VC",
      "episode_title": "AI Valuations in 2025",
      "published_at": "2025-04-15",
      "excerpt": "...the key insight about AI valuations is...",
      "similarity_score": 0.89,
      "timestamp_seconds": 1234,
      "s3_audio_path": "pod-insights-raw/..."
    }
  ],
  "total_results": 42,
  "query_embedding_cached": true
}

4. Extract relevant excerpt:
   - Find most relevant 200-word segment from transcript
   - Highlight query terms
   - Include surrounding context

Add to requirements.txt:
- openai>=1.0.0

Include proper error handling and query sanitization.
```

#### Step 1.2.2: Search Feature Flag

**What:** Environment variable to disable search endpoint during OpenAI outages or quota issues.

**Problem:** If OpenAI limits are hit, the entire search feature crashes the app.

**Solution:** Add graceful degradation:
```python
# In api/config.py
SEARCH_ENABLED = os.getenv('SEARCH_ENABLED', 'true').lower() == 'true'

# In search endpoint
@app.post("/api/search")
async def search(query: SearchQuery):
    if not SEARCH_ENABLED:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Search temporarily unavailable",
                "message": "Please try again later",
                "feature_disabled": True
            }
        )
    # ... normal search logic

# In frontend
if (response.status === 503 && response.data.feature_disabled) {
    showToast("Search is temporarily unavailable");
}
```

**Monitoring:** Log search_disabled events; send Slack alert when feature flag changes.

#### Entity Search Endpoint

**Prompt for Claude Code:**
```
Create an entity search endpoint to leverage our 123,948 extracted entities.

Create: GET /api/entities

Query parameters:
- search: Optional search term (e.g., "Sequoia")
- type: Filter by entity type (PERSON, ORG, GPE, MONEY)
- limit: Default 20, max 100
- timeframe: Optional (e.g., "30d", "90d")

Implementation:

1. If search term provided:
   - Search normalized_name field
   - Use PostgreSQL ILIKE for fuzzy matching
   - Include partial matches

2. Aggregate entity mentions:
   - Count total mentions
   - Count unique episodes
   - Track mention trend (weekly counts)
   - Include most recent mention date

3. Return format:
{
  "entities": [
    {
      "name": "Sequoia Capital",
      "type": "ORG",
      "mention_count": 47,
      "episode_count": 23,
      "trend": "up",  // up, down, stable
      "recent_mentions": [
        {
          "episode_title": "The Future of VC",
          "date": "2025-06-01",
          "context": "...Sequoia Capital announced..."
        }
      ],
      "weekly_mentions": {
        "W20": 5,
        "W21": 8,
        "W22": 12
      }
    }
  ],
  "total_entities": 156,
  "filter_applied": "ORG"
}

4. Performance optimization:
   - Create index on normalized_name
   - Use materialized view for counts
   - Cache popular entities (1 hour)
```

#### Step 1.2.3: Entity Weekly Mentions Materialized View

**What:** Pre-computed view that aggregates entity mentions by week to speed up queries.

**Problem:** Real-time GROUP BY on 123k entities causes >2 second response times.

**Solution:** Create materialized view refreshed nightly:
```sql
-- In 002_vector_search.up.sql
CREATE MATERIALIZED VIEW entity_weekly_mentions_mv AS
SELECT 
    e.normalized_name,
    e.entity_type,
    EXTRACT(WEEK FROM ep.published_at) as week_number,
    EXTRACT(YEAR FROM ep.published_at) as year,
    COUNT(*) as mention_count,
    COUNT(DISTINCT ep.id) as episode_count
FROM extracted_entities e
JOIN episodes ep ON e.episode_id = ep.id
GROUP BY e.normalized_name, e.entity_type, week_number, year;

CREATE INDEX idx_entity_weekly_name ON entity_weekly_mentions_mv(normalized_name);
CREATE INDEX idx_entity_weekly_type ON entity_weekly_mentions_mv(entity_type);

-- Refresh function
CREATE OR REPLACE FUNCTION refresh_entity_mentions() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY entity_weekly_mentions_mv;
END;
$$ LANGUAGE plpgsql;
```

**Monitoring:** Query latency should drop to <500ms; track refresh time in cron logs.

#### Step 1.2.4: Search Unit Test Seed

**What:** Basic pytest that validates search endpoint functionality to catch regressions early.

**Problem:** Schema or environment changes can break search without immediate detection.

**Solution:** Add test file that runs in CI:
```python
# tests/test_search.py
import pytest
from httpx import AsyncClient
import os

@pytest.mark.asyncio
async def test_search_endpoint():
    """Verify search returns results for known query"""
    async with AsyncClient(base_url=os.getenv('API_URL')) as client:
        response = await client.post("/api/search", json={
            "query": "AI agents",
            "limit": 5
        })
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['results']) > 0
        assert data['results'][0]['similarity_score'] > 0.7
        
@pytest.mark.asyncio  
async def test_search_feature_flag():
    """Verify search can be disabled via feature flag"""
    os.environ['SEARCH_ENABLED'] = 'false'
    async with AsyncClient(base_url=os.getenv('API_URL')) as client:
        response = await client.post("/api/search", json={"query": "test"})
        assert response.status_code == 503
```

**Monitoring:** CI pipeline fails if tests don't pass; green build required for deploy.

**Testing Checkpoints:**
1. **Search endpoint test**: POST query about "AI agents" - should return relevant episodes
2. **Embedding generation**: Verify OpenAI API creates 1536-dim vectors
3. **Similarity threshold**: Test that only relevant results returned (>0.7 similarity)
4. **Entity search**: Search "Sequoia" - should return Sequoia Capital with counts
5. **Performance**: Both endpoints respond in <500ms
6. **Error handling**: Test with malformed queries, missing API keys

---

## Part 3: Phase 2 - Authentication System
*(Goal: Enable user accounts for saved searches and personalization)*

### Step 2.1: Supabase Auth Setup

**🏠 Repository: Work in `podinsight-api` for backend auth**

**The Goal:** Implement user authentication using Supabase's built-in auth.

**The "Why":** Users need accounts to save searches, track entities, and get personalized insights. Supabase Auth gives us this without building from scratch.

#### Step 2.1.1: SendGrid SMTP for Auth Emails

**What:** Configure SendGrid as SMTP provider for Supabase Auth emails (signup, password reset).

**Problem:** Without SMTP, signup emails fail and users cannot verify accounts or reset passwords.

**Solution:** Set up SendGrid free tier with Supabase:
```bash
# 1. Get SendGrid API key (free tier = 100 emails/day)
# 2. In Supabase Dashboard > Auth > SMTP Settings:
SMTP Host: smtp.sendgrid.net
SMTP Port: 587
SMTP User: apikey
SMTP Pass: SG.xxxx... (your API key)
From Email: noreply@podinsighthq.com

# 3. Verify domain in SendGrid for better deliverability
# 4. Set email templates in Supabase Auth > Email Templates
```

**Monitoring:** SendGrid dashboard shows email stats; alert if bounce rate >5% or daily limit approaching.

#### Enable Auth in Supabase

**Prompt for Claude Code:**
```
Set up Supabase authentication for PodInsightHQ.

Current state:
- Using Supabase for database
- Need user authentication for alpha testers

Create authentication setup:

1. Update database schema (003_auth_tables.sql):
   - Modify users table to reference auth.users
   - Add RLS policies for user data access
   - Ensure users can only see their own saved searches

2. Create auth middleware for API (auth_middleware.py):
   - Verify Supabase JWT tokens
   - Extract user ID from token
   - Add @require_auth decorator

3. Add auth endpoints:
   - POST /api/auth/signup
   - POST /api/auth/login  
   - POST /api/auth/logout
   - GET /api/auth/me

4. Update existing endpoints to support auth:
   - /api/search - Save searches if authenticated
   - /api/entities - Track entities if authenticated

Return format for auth endpoints:
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "created_at": "2025-06-20T10:00:00Z"
  },
  "access_token": "jwt_token_here",
  "refresh_token": "refresh_token_here"
}

Security requirements:
- Use httpOnly cookies for tokens
- Implement CORS properly
- Rate limit auth endpoints
- Validate email format
```

### Step 2.2: Frontend Auth UI

**🏠 Repository: Switch to `podinsight-dashboard`**

**Prompt for Claude Code:**
```
Implement authentication UI using the existing v0 components.

I need to add:

1. Login/Signup modal:
   - Use existing v0 modal components
   - Email/password fields
   - Toggle between login and signup
   - Error handling with toast notifications

2. User menu in header:
   - Show user email when logged in
   - Dropdown with: My Searches, Tracked Entities, Logout
   - Use existing v0 dropdown components

3. Protected features:
   - Save Search button (appears after searching)
   - Track Entity button (on entity cards)
   - Personalized dashboard section

4. Auth context/hooks:
   - useAuth() hook for auth state
   - Automatic token refresh
   - Redirect to login when needed

5. Update API client:
   - Include auth headers
   - Handle 401 responses
   - Refresh token logic

The v0 components are already in the project. Find and use:
- Modal components for auth forms
- Form components with proper styling
- Toast notifications for feedback
- Dropdown menu components

Maintain the existing dark theme and glass morphism effects.
```

**Testing Checkpoints:**
1. **Signup flow**: Create new account - should receive welcome email
2. **Login flow**: Login with credentials - should see user menu
3. **Token persistence**: Refresh page - should remain logged in
4. **Protected routes**: Try saving search while logged out - should prompt login
5. **Logout**: Click logout - should clear session and redirect
6. **Error handling**: Wrong password - should show error toast

---

## Part 4: Phase 3 - Enhanced Visualizations
*(Goal: Add sentiment heatmap and complete v0 UI integration)*

### Step 3.1: Complete v0 Component Integration

**🏠 Repository: Continue in `podinsight-dashboard`**

**The Goal:** Use ALL the v0 components that were already created but not integrated.

**The "Why":** You paid for beautiful UI through v0 - let's use every component to match the original design.

#### Find and Integrate Missing Components

**Prompt for Claude Code:**
```
The v0 components were integrated but not all are being used. Find and integrate:

1. SIGNAL Bar Component:
   - Search for components with "signal", "alert", or "notification"
   - Should have purple gradient background
   - Contains "⚡ SIGNAL:" text
   - Shows correlation insights between topics

2. Statistics Row:
   - Search for stats or metrics components
   - Shows: Total Mentions, Avg Weekly Growth, Most Active Week, Trending Topic
   - Should be 4 cards in a row below the chart

3. Enhanced Legend:
   - Current legend missing growth percentages and arrows
   - Search for legend components with indicators
   - Should show: "AI Agents ↑6% w/w" with colored arrows

4. Update the main dashboard to include ALL v0 components found.

For the SIGNAL bar, calculate real insights from the data:
- Find which topics are discussed together most often
- Calculate correlation percentages
- Rotate through multiple signals

For statistics, calculate from real data:
- Total Mentions: Sum across all topics
- Weekly Growth: Compare to previous week
- Most Active: Week with highest total
- Trending: Highest growth rate

Don't create new components - find and use what v0 already built.
```

#### Step 3.1.1: Nightly Signal Pre-computation Service

**What:** Python ETL job that pre-calculates topic correlations and insights for the SIGNAL bar.

**Problem:** Real-time correlation calculations across 1,171 episodes cause UI freezes and slow loads.

**Solution:** Compute signals nightly and store results:
```python
# signal_service.py
import asyncio
from datetime import datetime
import json

async def calculate_topic_correlations():
    """Pre-compute which topics appear together"""
    
    # Query episodes with multiple topic mentions
    query = """
    SELECT 
        t1.topic_name as topic_a,
        t2.topic_name as topic_b,
        COUNT(DISTINCT t1.episode_id) as co_occurrences,
        COUNT(DISTINCT t1.episode_id) * 100.0 / 
            (SELECT COUNT(*) FROM episodes) as percentage
    FROM topic_mentions t1
    JOIN topic_mentions t2 ON t1.episode_id = t2.episode_id
    WHERE t1.topic_name < t2.topic_name
    GROUP BY t1.topic_name, t2.topic_name
    HAVING COUNT(DISTINCT t1.episode_id) > 10
    ORDER BY co_occurrences DESC
    """
    
    results = await db.fetch(query)
    
    # Store in signals table
    await db.execute("""
        INSERT INTO topic_signals (
            signal_type, signal_data, calculated_at
        ) VALUES ('correlation', $1, $2)
    """, json.dumps(results), datetime.now())
    
# Run via cron: 0 2 * * * python signal_service.py
```

**Monitoring:** Cron success logged to signals.log; Slack alert if job fails or takes >10 minutes.

### Step 3.2: Sentiment Heatmap

**Prompt for Claude Code:**
```
Create a sentiment heatmap visualization using the v0 design system.

Requirements:

1. New component: SentimentHeatmap
   - Grid layout: Topics (Y-axis) vs Weeks (X-axis)
   - Color intensity: Sentiment score (-1 to +1)
   - Color scheme: Red (negative) → Yellow (neutral) → Green (positive)

2. Data structure:
   - For now, use mock sentiment data
   - Structure: {topic: {week: sentiment_score}}
   - Add tooltip showing exact sentiment value

3. Visual design matching v0:
   - Glass morphism container
   - Smooth color gradients
   - Hover effects on cells
   - Animation on load

4. Integration:
   - Add tab toggle: "Velocity" | "Sentiment"
   - Share same topic selection
   - Maintain time range filter

Mock data example:
{
  "AI Agents": {
    "W20": 0.72,  // Positive
    "W21": 0.45,  // Slightly positive
    "W22": -0.23  // Slightly negative
  }
}

Note: Real sentiment analysis will come from Phase 4.
Use Recharts or create custom grid component.
```

---

## Part 5: Phase 4 - Audio Integration & Polish
*(Goal: Enable audio playback and complete UI enhancements)*

### Step 4.1: Audio Streaming

**🏠 Repository: Work in `podinsight-api` first**

**The Goal:** Enable secure audio streaming from S3.

**The "Why":** Users want to hear the actual conversation, not just read excerpts. This brings the content to life.

#### Step 4.1.1: S3 CORS Policy Configuration

**What:** Configure S3 bucket CORS to allow browser-based audio streaming with range requests.

**Problem:** Without proper CORS headers, browsers block audio playback and seeking fails.

**Solution:** Add CORS configuration to S3 bucket:
```json
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedOrigins": [
        "http://localhost:3000",
        "https://podinsighthq.vercel.app"
      ],
      "ExposeHeaders": [
        "Accept-Ranges",
        "Content-Range",
        "Content-Length",
        "Content-Type"
      ],
      "MaxAgeSeconds": 3600
    }
  ]
}
```

**Monitoring:** CloudWatch alarm if 4xx errors >5% on audio bucket; check CORS headers in browser DevTools.

#### Pre-signed URL Endpoint

**Prompt for Claude Code:**
```
Create audio streaming functionality using S3 pre-signed URLs.

Create: GET /api/audio/stream/{episode_id}

Implementation:

1. Validate episode exists and user has access
2. Generate pre-signed URL:
   - 1-hour expiration
   - Read-only access
   - Use episode's s3_audio_path

3. Return response:
{
  "stream_url": "https://s3.amazonaws.com/...",
  "expires_at": "2025-06-20T11:00:00Z",
  "duration_seconds": 3600,
  "format": "audio/mpeg"
}

4. Security:
   - Rate limit: Max 10 requests per minute
   - Log streaming requests
   - Validate episode_id format

5. Add seek parameter support:
   - ?start=120 (start at 2 minutes)
   - Return partial content headers

Update requirements.txt if needed for S3 pre-signed URLs.
```

### Step 4.2: Audio Player UI

**🏠 Repository: Switch to `podinsight-dashboard`**

**Prompt for Claude Code:**
```
Add audio playback to search results and entity mentions.

Requirements:

1. Mini audio player component:
   - Appears when clicking "Play" on any excerpt
   - Minimal design: Play/pause, progress bar, time
   - Stays at bottom of screen
   - Uses v0 styling (glass morphism)

2. Integration points:
   - Search results: Add play button to each result
   - Entity mentions: Play button on context snippets
   - Click → Fetch pre-signed URL → Start playback

3. Player features:
   - Start at specific timestamp
   - Show episode info while playing
   - Keyboard shortcuts (space = play/pause)
   - Continue playing while browsing

4. Implementation:
   - Use HTML5 audio element
   - Store player state in React context
   - Handle URL expiration (re-fetch if needed)

The player should feel premium but not intrusive.
Use existing v0 components for buttons and progress bars.
```

---

## Part 6: Testing & Validation Checkpoints

### Phase 1 (Search) Success Criteria
- [ ] Embeddings loaded for all 1,171 episodes
- [ ] Search query "AI agents" returns relevant results in <2 seconds
- [ ] Similarity scores make sense (>0.7 for relevant content)
- [ ] Entity search for "OpenAI" shows mention counts and trends
- [ ] Search results include accurate excerpts with context
- [ ] API endpoints handle errors gracefully
- [ ] No memory leaks during embedding operations
- [ ] Query cache hit rate >80% for common searches
- [ ] Rate limiting prevents abuse (20 req/min enforced)
- [ ] Unit tests pass in CI pipeline

### Phase 2 (Auth) Success Criteria
- [ ] Users can create accounts with email/password
- [ ] Login persists across page refreshes
- [ ] Saved searches appear in user profile
- [ ] Tracked entities show notification badges
- [ ] RLS policies prevent cross-user data access
- [ ] Auth tokens refresh automatically
- [ ] SendGrid delivers signup emails <30 seconds
- [ ] Password reset flow works end-to-end

### Phase 3 (Visualizations) Success Criteria
- [ ] ALL v0 components integrated and working
- [ ] SIGNAL bar shows real data insights
- [ ] Statistics row calculates from actual data
- [ ] Sentiment heatmap renders with smooth gradients
- [ ] Tab switching maintains state
- [ ] Animations feel premium, not janky
- [ ] Signal service runs nightly without errors
- [ ] Pre-computed signals load instantly

### Phase 4 (Audio) Success Criteria
- [ ] Click excerpt → Audio plays within 2 seconds
- [ ] Player shows correct timestamp
- [ ] Pre-signed URLs expire and refresh properly
- [ ] Player persists while navigating site
- [ ] Keyboard shortcuts work
- [ ] No CORS issues with S3
- [ ] Audio seeking works smoothly
- [ ] Range requests supported

### Performance Benchmarks

| Feature | Target | Measurement Method |
|---------|--------|-------------------|
| Search query | <2s | Time from submit to results |
| Entity lookup | <500ms | API response time |
| Audio start | <2s | Click to first sound |
| Page load | <3s | All components rendered |
| Embedding load | <30s per 100 | ETL script timing |
| Cache hit rate | >80% | Daily metric in logs |
| Signal computation | <10min | Nightly job duration |

---

## Part 7: Sprint Review & Demo Script

### Demo Flow (10 minutes)

1. **Show Topic Velocity Baseline (1 min)**
   - "Last sprint we proved we could visualize trends"
   - Show current dashboard briefly

2. **Reveal Natural Language Search (3 min)**
   - Type: "What are VCs saying about AI agent valuations?"
   - Show relevant results appearing instantly
   - Click one result → Play audio excerpt
   - "From 1,000 hours to specific insights in seconds"

3. **Demonstrate Entity Tracking (2 min)**
   - Search: "Sequoia Capital"
   - Show 47 mentions across 23 episodes
   - Display trend chart: "Mentions up 300% this quarter"
   - Click "Track Entity" → Saves to profile

4. **Show Enhanced UI (2 min)**
   - SIGNAL bar: "AI Agents and DePIN discussed together in 67% of episodes"
   - Statistics row with real calculations
   - Tab to Sentiment Heatmap
   - "See market sentiment at a glance"

5. **Highlight Personal Features (2 min)**
   - Login as demo user
   - Show saved searches
   - Show tracked entities with alerts
   - "Your personal intelligence dashboard"

### Key Talking Points
- "We've gone from showing what's trending to understanding WHY"
- "Every insight links back to the actual conversation"
- "This is just 1,171 episodes - imagine 10,000"
- "Each feature multiplies the value of our data foundation"

---

## Appendix A: Troubleshooting Guide

### Common Issues & Solutions

| Problem | Likely Cause | Solution |
|---------|--------------|----------|
| Embeddings won't load | numpy version mismatch | Use numpy<2.0 for compatibility |
| Search returns nothing | Similarity threshold too high | Lower to 0.5 for testing |
| Auth tokens expire quickly | Clock skew | Sync server time with NTP |
| Audio won't play | CORS policy | Check S3 bucket CORS configuration |
| Sentiment heatmap blank | Missing data | Use mock data generator first |
| v0 components not found | Wrong import paths | Check components/ui/ directory |
| pgvector similarity slow | Missing index | Run CREATE INDEX with ivfflat |
| Entity counts wrong | Not aggregating properly | Use GROUP BY with COUNT(DISTINCT) |
| Query cache misses | Hash function issue | Ensure lowercase + trim whitespace |
| SendGrid emails fail | Domain not verified | Complete domain auth in SendGrid |
| Signal service timeout | Too much data | Add LIMIT to correlation query |

### Emergency Procedures
1. **Search index corrupted**: Rebuild embeddings from backup
2. **Auth system down**: Temporarily disable auth checks
3. **S3 access denied**: Check IAM roles and bucket policies
4. **Database overwhelmed**: Enable connection pooling
5. **OpenAI quota hit**: Enable SEARCH_ENABLED=false flag

---

## Appendix B: Cost Tracking

### Additional Monthly Costs (Sprint 1)
- **OpenAI API**: ~$50 (for search query embeddings, reduced by caching)
- **Increased Supabase usage**: +$0 (still within free tier)
- **S3 bandwidth**: ~$10 (pre-signed URLs for audio)
- **SendGrid**: $0 (free tier = 100 emails/day)
- **Total additional**: ~$60/month

### Initial One-Time Costs
- **Embeddings loader S3 egress**: ~$0.20 (164MB at $0.0012/GB)
- **Total one-time**: ~$0.20

### Cost Optimization Strategies
- Query cache reduces OpenAI costs by ~80%
- Materialized views prevent database upgrade need
- Rate limiting caps maximum API spend
- Pre-computed signals avoid real-time computation

### Upgrade Triggers Documentation

| Service | Free Tier Limit | Upgrade Trigger | Action |
|---------|----------------|-----------------|---------|
| Supabase | 2GB transfer | Monitor at 1.5GB | Enable pooling first |
| Vercel | 100GB bandwidth | Alert at 80GB | Review caching strategy |
| OpenAI | N/A | $40/month spend | Review cache hit rate |
| SendGrid | 100 emails/day | 80 emails/day | Upgrade to Essentials |

**Monitoring:** Weekly Slack digest of usage across all services; alerts at 80% of any limit.

---

## Appendix C: Working with Claude Code - Sprint 1 Context

### Repository Context Files

Update each repository's PROJECT.md:

**For `podinsight-etl/PROJECT.md` additions:**
```markdown
## Sprint 1 Additions

### Embeddings Loader
- Script: embeddings_loader.py
- Purpose: Load .npy embeddings from S3 into pgvector
- Status: 1,171 embeddings ready for similarity search

### Database Migrations
- 002_vector_search.sql - Added vector column and search functions
- 003_auth_tables.sql - User account infrastructure

### Query Cache
- Table: query_cache for embedding reuse
- Hit rate target: >80%

### Signal Service
- Script: signal_service.py
- Runs nightly via cron
- Pre-computes topic correlations
```

**For `podinsight-api/PROJECT.md` additions:**
```markdown
## Sprint 1 Endpoints

### Search Endpoints
- POST /api/search - Natural language search
- GET /api/entities - Entity tracking and trends
- GET /api/audio/stream/{id} - Pre-signed URLs

### Auth Endpoints  
- POST /api/auth/signup
- POST /api/auth/login
- GET /api/auth/me

### Performance Features
- Query embedding cache
- Rate limiting (20/min)
- Feature flags (SEARCH_ENABLED)
- Materialized views for entities
```

**For `podinsight-dashboard/PROJECT.md` additions:**
```markdown
## Sprint 1 Features

### New Components
- SearchInterface - Natural language search UI
- EntityExplorer - Browse and track entities
- SentimentHeatmap - Market sentiment visualization
- AudioPlayer - Streaming audio playback
- AuthModal - Login/signup forms

### Enhanced Components
- SIGNAL bar integration
- Statistics row with real data
- Complete v0 component usage

### Infrastructure
- SendGrid email configuration
- S3 CORS for audio streaming
- Nightly signal pre-computation
```

### Claude Code Best Practices for Sprint 1

1. **When Adding to Existing Code:**
   ```
   @existing-file.py
   @project.md
   
   I need to add vector search to our existing API. The current structure is documented in project.md.
   Please add the new /api/search endpoint following the same patterns as /api/topic-velocity.
   ```

2. **For Complex Features:**
   ```
   Let's implement embeddings loading step by step:
   1. First, show me how to read one .npy file from S3
   2. Then, how to convert numpy array to pgvector format
   3. Finally, create the full batched loading script
   ```

3. **For UI Integration:**
   ```
   @components/dashboard/
   
   Find the existing v0 components that match:
   - Purple notification bar (SIGNAL bar)
   - Statistics cards row
   - Legend with growth indicators
   
   Show me which files contain these components.
   ```

### Testing Checklist Template

After EVERY feature addition:
```markdown
## Feature: [Feature Name]
Date: [Date]
Status: [ ] In Progress [ ] Complete

### Implementation Checklist
- [ ] Code written and saved
- [ ] Dependencies added to requirements.txt / package.json
- [ ] Environment variables documented
- [ ] Error handling implemented

### Testing Checklist  
- [ ] Unit test written (if applicable)
- [ ] Manual test passed
- [ ] Edge cases tested
- [ ] Performance measured
- [ ] No console errors

### Git Checklist
- [ ] Changes committed with clear message
- [ ] Pushed to repository
- [ ] No sensitive data in commit

### Documentation Checklist
- [ ] PROJECT.md updated
- [ ] README.md updated if needed
- [ ] API endpoints documented
- [ ] Environment variables listed
```

---

## Appendix D: Sprint 1 Quick Reference Card

Save this for easy copy-paste:
```
=== PODINSIGHTHQ SPRINT 1 CONTEXT ===
Goal: Add search, auth, sentiment, and audio to working dashboard
Stack: pgvector + Supabase Auth + OpenAI embeddings
Repos: podinsight-etl, podinsight-api, podinsight-dashboard
Key Features: Natural language search, Entity tracking, User accounts
Data: 1,171 episodes, 123k entities, embeddings ready in S3
Performance: All features <2 second response time
Budget: ≤$75/month (use caching, rate limits)
CRITICAL: Use existing v0 components, don't recreate
===================================
```

### Development Order (Recommended)

1. **Week 1: Search Infrastructure**
   - Day 1-2: Database setup and embeddings loading
   - Day 3-4: Search API endpoints
   - Day 5: Search UI integration

2. **Week 2: Auth & Enhancement**
   - Day 1-2: Authentication system
   - Day 3: Complete v0 integration (SIGNAL bar, stats)
   - Day 4: Sentiment heatmap
   - Day 5: Audio playback

### Key Commands Quick Reference
```bash
# ETL Repository
cd podinsight-etl
source venv/bin/activate
python embeddings_loader.py --limit 10  # Test with 10 first

# API Repository  
cd podinsight-api
source venv/bin/activate
uvicorn api.topic_velocity:app --reload

# Dashboard Repository
cd podinsight-dashboard
npm run dev

# Deployment
git add . && git commit -m "feat: add search functionality"
git push origin main
vercel --prod

# Run tests
pytest tests/test_search.py -v
```

---

*This playbook builds on Genesis Sprint's foundation with cost-conscious, reliable features. Every component includes monitoring and fallback strategies. Follow the testing checklists religiously - they prevent cascading issues and ensure predictable costs.*

*Remember: You're not building features, you're building intelligence tools that make 1,000 hours of content instantly accessible - within budget.*