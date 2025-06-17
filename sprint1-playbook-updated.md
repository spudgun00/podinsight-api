# PodInsightHQ: Sprint 1 Playbook - Intelligence Features (UPDATED)

*This playbook incorporates all learnings from Sprint 0 and includes critical technical debt resolution. It is the single source of truth for implementing natural language search, entity tracking, and enhanced visualizations for PodInsightHQ.*

**Last Updated:** June 17, 2025  
**Sprint Duration:** 2 weeks  
**Critical Context:** Must complete Phase 0 (Technical Debt) BEFORE starting new features

---

## ⚠️ CRITICAL SPRINT 0 LEARNINGS - READ FIRST

### Exact Naming Requirements
```python
# These MUST match EXACTLY - no variations!
EXACT_TOPIC_NAMES = [
    "AI Agents",
    "Capital Efficiency", 
    "DePIN",
    "B2B SaaS",
    "Crypto/Web3"  # NO SPACES around the slash!
]
```

### Known Data Structure Quirks
1. **KPI Data:** Direct array `[]`, NOT wrapped in `{"kpis": []}`
2. **Entity Type:** Use `label` field, NOT `type` field
3. **Dates:** Get from raw bucket, NOT metadata
4. **Foreign Keys:** Use `episode_id` (UUID), NOT `episode_guid`

### Current Performance Baseline
- API response: ~50ms (excellent)
- Bundle size: 235KB (acceptable, focus on functionality)
- Database connections: Approaching 20 limit
- Data volume: 1,171 episodes, 123k entities, 50k KPIs

---

## Part 1: Sprint Definition & Product Decisions

### Sprint Goal (The Mission)
Transform our working Topic Velocity dashboard into an intelligent search and insights platform by adding natural language search across 1,171 episodes, entity tracking, sentiment analysis, and user authentication—proving we can deliver actionable intelligence beyond simple trend charts.

### Definition of Success (How We Know We've Won)
- ✅ **Technical Debt Cleared**: TypeScript errors fixed, 6 broken components removed, connection pooling added
- ✅ **Search is Live**: Natural language queries return relevant transcript excerpts in <2 seconds
- ✅ **Entities are Trackable**: Users can search for any person/company across all episodes
- ✅ **Authentication Works**: Alpha users can create accounts and save searches
- ✅ **Sentiment Visible**: New heatmap shows market sentiment trends
- ✅ **UI Enhanced**: ALL v0 components integrated, animations polished
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

#### Environment Key Separation
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

---

## Part 2: Phase 0 - Technical Debt Resolution (NEW - MANDATORY)
*(Goal: Fix Sprint 0 issues before adding new features - SMART CLEANUP APPROACH)*

### 🏠 Repository: podinsight-dashboard

### Step 0.1: Smart Component Cleanup (Minimal Approach)

**Time Required:** 1-2 hours  
**Impact:** Fix TypeScript errors, remove only broken components, keep Sprint 1 flexibility

#### Strategic Component Removal

**Prompt for Claude Code:**
```
@components/ui/
@package.json

I need to do MINIMAL cleanup - only removing components with @ts-nocheck errors.

Smart cleanup approach:
1. Delete ONLY these 6 broken component files:
   - components/ui/calendar.tsx (has @ts-nocheck)
   - components/ui/carousel.tsx (has @ts-nocheck)
   - components/ui/drawer.tsx (has @ts-nocheck)
   - components/ui/input-otp.tsx (has @ts-nocheck)
   - components/ui/resizable.tsx (has @ts-nocheck)
   - components/ui/sonner.tsx (has @ts-nocheck)

2. Check if any files import these 6 components:
   - Search all .tsx and .ts files
   - Show me any import references

3. Remove ONLY packages specific to those 6 components:
   - react-day-picker (for calendar)
   - input-otp (for input-otp)
   - sonner (for sonner)
   - embla-carousel-react (for carousel)
   - vaul (for drawer)
   - react-resizable-panels (for resizable)

4. KEEP all @radix-ui packages - we need them for Sprint 1 features:
   - Auth modals will use @radix-ui/react-dialog
   - User menu will use @radix-ui/react-dropdown-menu
   - Tabs for sentiment view will use @radix-ui/react-tabs
   - Audio player will use @radix-ui/react-slider

5. Create a removal tracking document (removed-components.md) listing:
   - What was removed and why
   - What packages were uninstalled
   - How to restore if needed

Show the commands and verify build still works.
```

**Why Minimal Approach:**
- Sprint 1 needs UI components for search, auth, audio player
- Bundle at 235KB is acceptable (many apps are 500KB+)
- Aggressive removal risks breaking upcoming features
- Can optimize further in dedicated performance sprint

### Step 0.2: Fix TypeScript Import Issues

**Prompt for Claude Code:**
```
@lib/v0-types.ts
@components/ui/use-mobile.tsx
@components/ui/use-toast.ts

Fix the import path issues from Sprint 0:

1. Rename v0-types.ts to types.ts
2. Update all imports from 'v0-types' to 'types'
3. Create /hooks directory
4. Move use-mobile.tsx and use-toast.ts to /hooks
5. Update all imports to use @/hooks/

Show me all files that need import updates and the sed commands to fix them.
```

### 🏠 Repository: podinsight-api

### Step 0.3: Database Connection Pooling

**Critical:** Must complete BEFORE adding search features!

**Prompt for Claude Code:**
```
@api/topic_velocity.py
@requirements.txt

I need to implement connection pooling before adding search features.

Current situation:
- Supabase free tier limit: 20 concurrent connections
- We're approaching this limit
- Search features will exceed it

Create a connection pool manager:

1. Create api/database.py with:
   - SupabasePool class using asyncio
   - Max 10 connections per worker
   - Connection reuse logic
   - Automatic retry on connection failure

2. Update existing endpoint to use pool:
   - Modify topic_velocity.py to use pool
   - Add proper connection cleanup

3. Add monitoring:
   - Log active connections
   - Alert when >15 connections

Include error handling for connection exhaustion.
```

### Step 0.4: Performance Baseline Tests

**🏠 Repository: podinsight-api**

**Prompt for Claude Code:**
```
Create tests/test_performance_baseline.py that verifies our Sprint 0 performance:

1. Test API response time:
   - /api/topic-velocity should respond in <100ms
   - Test with default parameters

2. Test exact topic names:
   - Verify "Crypto/Web3" returns data (no spaces)
   - Verify all 5 topics return non-zero mentions

3. Test data integrity:
   - Verify 1,171 episodes in database
   - Verify topic_mentions uses correct foreign keys

These tests ensure Sprint 1 changes don't break Sprint 0 functionality.
```

**Testing Checkpoint:**
- [ ] All 6 broken components removed
- [ ] Only 6 specific packages uninstalled (not @radix-ui)
- [ ] TypeScript builds without errors
- [ ] No import errors
- [ ] Connection pool working
- [ ] All baseline tests pass
- [ ] Removal tracking document created

---

## Part 3: Phase 1 - Search Infrastructure
*(Goal: Enable semantic search across all podcast transcripts)*

### 🎯 Critical Context from Sprint 0
- We have embeddings: 1,171 .npy files in S3 at ~140KB each
- pgvector installed: v0.8.0 confirmed
- Entity field is `label` NOT `type`
- Use exact topic names (especially "Crypto/Web3" with no spaces)

### 🏠 Repository: podinsight-etl

### Step 1.1: Search Database Setup

**The Goal:** Add vector search capabilities to our existing database.

#### Database Migration with Sprint 0 Context

**Prompt for Claude Code:**
```
@001_initial_schema.up.sql

I need to add vector search to our PodInsightHQ database, incorporating Sprint 0 learnings.

Current state:
- pgvector v0.8.0 already installed
- 1,171 episodes loaded
- Foreign keys use episode.id (UUID), NOT episode.guid
- Entity type field is 'label' not 'type'

Create migration files:

1. 002_vector_search.up.sql with:
   - ADD COLUMN embedding vector(1536) to episodes table
   - Create ivfflat index for fast similarity search
   - Query cache table (include SHA256 hash example)
   - User tables: users, saved_searches, tracked_entities
   - Materialized view for entity weekly mentions

2. Important Sprint 0 context to include:
   - Comment that entity queries must use 'label' field
   - Note that topic names must match exactly (list all 5)
   - Include example of "Crypto/Web3" with NO spaces

3. SQL functions:
   - similarity_search function with cosine distance
   - Function to extract relevant excerpt from transcript

Include detailed comments about pgvector operators and performance tips.
```

### 🏠 Repository: podinsight-etl

### Step 1.2: Embeddings Loader Script

**Prompt for Claude Code:**
```
@main.py
@modules/s3_reader.py

Create embeddings_loader.py based on our existing ETL patterns.

Context from Sprint 0:
- S3 paths are in episodes.s3_embeddings_path column
- Each .npy file is ~140KB (numpy array)
- Use same progress bar pattern as main.py
- Connection handling like in supabase_loader.py

Requirements:

1. Query episodes WHERE embedding IS NULL
2. For each episode:
   - Read s3_embeddings_path
   - Download .npy file using boto3
   - Load with numpy (pin numpy<2.0 for compatibility)
   - Convert to PostgreSQL vector format
   - UPDATE episode with embedding

3. Performance features:
   - Batch processing (50 episodes)
   - Parallel S3 downloads (max 10)
   - Progress bar showing "Loading embedding 567/1171"
   - Resume capability

4. Error handling:
   - Missing .npy files (log and continue)
   - Corrupt arrays (skip with warning)
   - S3 timeouts (retry 3 times)

Total: ~164MB to download for all embeddings.
```

**Testing Checkpoints:**
- [ ] Test with --limit 10 first
- [ ] Verify vectors stored correctly
- [ ] Check vector dimensions (must be 1536)
- [ ] Test similarity search manually
- [ ] Full run completes in <30 minutes

### 🏠 Repository: podinsight-api

### Step 1.3: Search API Endpoints

#### Search Endpoint with Sprint 0 Learnings

**Prompt for Claude Code:**
```
@api/topic_velocity.py
@api/database.py (from Phase 0)

Add semantic search endpoint using our connection pool.

CRITICAL Sprint 0 context:
- Database has 'label' field for entities, not 'type'
- Topics must match exactly: ["AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS", "Crypto/Web3"]
- Use parser.parse() for dates, not fromisoformat()

Create POST /api/search endpoint:

1. Request validation:
   - query: string (required, max 500 chars)
   - limit: int (default 10, max 50)
   - offset: int (default 0)

2. Implementation with caching:
   - Check query_cache table first (SHA256 hash)
   - If miss, call OpenAI for embedding
   - Store in cache for future
   - Use connection pool for all queries

3. Search logic:
   - pgvector similarity search (cosine distance)
   - Threshold: similarity > 0.7
   - Extract 200-word excerpt around most relevant section
   - Include episode metadata

4. Response format:
   {
     "results": [...],
     "total_results": 42,
     "cache_hit": true,
     "search_id": "uuid-for-saving"
   }

5. Rate limiting:
   - Use slowapi: 20 requests/minute per IP
   - Return 429 with retry-after header

Include OpenAI error handling and fallback.
```

### 🏠 Repository: podinsight-api

### Step 1.4: Entity Search Endpoint

**Prompt for Claude Code:**
```
@api/topic_velocity.py

Create entity search endpoint using Sprint 0 knowledge.

CRITICAL: In our database, entity type is stored in 'label' field, NOT 'type' field!

Create GET /api/entities endpoint:

1. Query parameters:
   - search: optional (fuzzy match on entity_name)
   - type: filter by PERSON, ORG, GPE, MONEY
   - limit: 20 default, max 100

2. Use the materialized view from migration:
   - entity_weekly_mentions_mv for fast aggregation
   - JOIN with extracted_entities for details

3. Aggregation logic:
   - Count total mentions
   - Count unique episodes  
   - Calculate trend (compare last 4 weeks to previous 4)
   - Get sample contexts

4. IMPORTANT - correct query:
   ```sql
   SELECT * FROM extracted_entities 
   WHERE label = 'ORG'  -- NOT 'type' = 'ORG'
   ```

5. Performance:
   - Use connection pool
   - Cache popular entities (1 hour)
   - Target <500ms response

Include examples showing "Sequoia Capital" search.
```

**Testing Checkpoints:**
- [ ] Search "AI agents" returns relevant results
- [ ] Cache hit on repeated queries
- [ ] Entity search for "OpenAI" works
- [ ] Rate limiting blocks at 21st request
- [ ] Response times <500ms

---

## Part 4: Phase 2 - Authentication System
*(Goal: Enable user accounts for saved searches and personalization)*

### 🏠 Repository: podinsight-api

### Step 2.1: Supabase Auth Setup

**Prompt for Claude Code:**
```
@api/topic_velocity.py
@requirements.txt

Set up Supabase Auth with Sprint 0 patterns.

Current setup:
- Already using Supabase for database
- Have connection pool from Phase 0
- Need auth for alpha users (5 people)

Create auth system:

1. Migration 003_auth_setup.sql:
   - Link users table to auth.users(id)
   - Add RLS policies for user data
   - saved_searches table with user_id
   - tracked_entities table

2. Auth middleware (api/auth.py):
   - Verify Supabase JWT tokens
   - Extract user_id from token
   - @require_auth decorator
   - Use connection pool

3. Auth endpoints:
   - POST /api/auth/signup (rate limit: 5/hour)
   - POST /api/auth/login (rate limit: 10/minute)
   - POST /api/auth/logout
   - GET /api/auth/me

4. Update search endpoint:
   - If authenticated, save search to saved_searches
   - Include user's saved status in response

Use httpOnly cookies for tokens. Include CORS setup.
```

### 🏠 Repository: podinsight-dashboard

### Step 2.2: Frontend Auth UI

**Prompt for Claude Code:**
```
@components/ui/
@components/dashboard/

Add authentication UI using existing v0 components.

Sprint 0 context:
- We have many unused v0 components - use them!
- Dark theme with glass morphism effects
- Don't create new components

Find and integrate:

1. Auth modal:
   - Look for Modal or Dialog components
   - Create login/signup forms
   - Use existing form components
   - Add to main layout

2. User menu:
   - Find Dropdown or Menu components  
   - Show user email when logged in
   - Options: My Searches, Tracked Entities, Logout

3. Auth context (lib/auth-context.tsx):
   - useAuth() hook
   - Automatic token refresh
   - Handle 401 responses

4. Protected UI elements:
   - "Save Search" button (after searching)
   - "Track Entity" star icon
   - "My Dashboard" section

5. Update API client:
   - Include credentials: 'include'
   - Handle auth errors
   - Refresh token logic

Use existing v0 components - don't create new ones!
```

**Testing Checkpoints:**
- [ ] Can create account
- [ ] Login persists on refresh
- [ ] Saved searches appear in profile
- [ ] 401 errors trigger re-login
- [ ] Logout clears session

---

## Part 5: Phase 3 - Enhanced Visualizations
*(Goal: Add sentiment heatmap and complete v0 UI integration)*

### 🏠 Repository: podinsight-dashboard

### Step 3.1: Complete v0 Component Integration

**Critical:** You already have these components - FIND and USE them!

**Prompt for Claude Code:**
```
@components/ui/
@components/dashboard/topic-velocity-chart-full-v0.tsx

The v0 components exist but aren't all being used. Find and integrate ALL of them.

From Sprint 0, we know these components exist:
1. SIGNAL bar (purple gradient notification)
2. Statistics row (4 metric cards)
3. Enhanced legend with percentages
4. Metric cards with sparklines
5. Notable Performer card

Tasks:

1. Search components/ for:
   - Files with "signal", "notification", "alert"
   - Files with "stat", "metric", "card"
   - Files with "legend", "growth"
   - Show me what you find

2. For SIGNAL bar:
   - Must show real correlations from data
   - Calculate which topics appear together
   - Use the signal service data (will create next)

3. For statistics:
   - Total mentions (sum all topics)
   - Weekly growth (compare to last week)
   - Most active week (highest total)
   - Trending topic (highest growth %)

4. Update TopicVelocityChartFullV0:
   - Include ALL found components
   - Use real calculations, not mock data
   - Maintain glass morphism styling

Don't create new components - they already exist!
```

### 🏠 Repository: podinsight-etl

### Step 3.2: Signal Pre-computation Service

**Prompt for Claude Code:**
```
@main.py
@modules/supabase_loader.py

Create signal_service.py for nightly correlation computation.

Using Sprint 0 patterns:
- Database connection like main.py
- Progress logging like ETL
- Use exact topic names (especially "Crypto/Web3")

Create script that:

1. Calculates topic correlations:
   - Which topics appear together in episodes
   - Percentage of co-occurrence
   - Week-over-week changes

2. Query structure:
   ```sql
   -- Find episodes with multiple topics
   -- Remember: exactly 5 topics to check
   -- "Crypto/Web3" has no spaces!
   ```

3. Store results in topic_signals table:
   - signal_type: 'correlation'
   - signal_data: JSON with percentages
   - calculated_at: timestamp

4. Also calculate:
   - Fastest growing topic combinations
   - Unusual spikes in mentions
   - Entity + topic correlations

5. Performance:
   - Should complete in <10 minutes
   - Log progress and timing

Set up for cron: 0 2 * * *
```

### 🏠 Repository: podinsight-dashboard

### Step 3.3: Sentiment Heatmap

**Prompt for Claude Code:**
```
@components/dashboard/
@lib/types.ts

Create sentiment heatmap using v0 design system.

Requirements:

1. Component: SentimentHeatmap.tsx
   - Grid: Topics (Y) vs Weeks (X)
   - Colors: Red (-1) → Yellow (0) → Green (+1)
   - Use v0's glass morphism style

2. For Sprint 1, use mock data:
   - Generate realistic sentiment scores
   - All 5 topics (include "Crypto/Web3")
   - Last 12 weeks

3. Visual features:
   - Hover tooltip with exact score
   - Smooth color gradients
   - Animation on load
   - Click cell for details

4. Integration:
   - Add tabs: "Velocity" | "Sentiment"
   - Share topic selection state
   - Use same time range filter

5. Mock data generator:
   - Realistic patterns (not random)
   - Some topics correlate
   - Trending sentiment over time

Note: Real sentiment analysis comes in Sprint 2.
```

**Testing Checkpoints:**
- [ ] ALL v0 components found and integrated
- [ ] SIGNAL bar shows real correlations
- [ ] Statistics calculate from actual data
- [ ] Sentiment heatmap renders smoothly
- [ ] Animations feel premium

---

## Part 6: Phase 4 - Audio Integration & Polish
*(Goal: Enable audio playback and complete UI enhancements)*

### 🏠 Repository: podinsight-api

### Step 4.1: Audio Streaming API

**Prompt for Claude Code:**
```
@api/topic_velocity.py

Create audio streaming endpoint using S3 pre-signed URLs.

Sprint 0 context:
- Audio paths in episodes.s3_audio_path
- S3 bucket: pod-insights-raw
- Use existing patterns

Create GET /api/audio/stream/{episode_id}:

1. Validation:
   - Verify episode exists
   - Check user access (if authenticated)
   - Validate UUID format

2. Pre-signed URL generation:
   - 1-hour expiration
   - Read-only access
   - Include response headers for audio

3. Response:
   {
     "stream_url": "https://...",
     "expires_at": "2025-06-20T11:00:00Z",
     "duration_seconds": 3600,
     "content_type": "audio/mpeg"
   }

4. Features:
   - Support range requests for seeking
   - Rate limit: 10/minute per IP
   - Log all streaming requests

5. S3 CORS configuration needed:
   - Include in response documentation
   - Headers for range requests

Use connection pool for database queries.
```

### 🏠 Repository: podinsight-dashboard

### Step 4.2: Audio Player UI

**Prompt for Claude Code:**
```
@components/ui/
@components/dashboard/

Add audio player using v0 components.

Find and use existing components:
- Look for Player, Audio, or Media components
- Find Progress or Slider components
- Use existing Button components

Create minimal audio player:

1. Player bar (fixed bottom):
   - Play/pause button
   - Progress slider  
   - Time display (current/total)
   - Episode title
   - Glass morphism style

2. Integration points:
   - Search results: play button per result
   - Entity mentions: play button
   - Click → fetch pre-signed URL → play

3. Features:
   - Start at specific timestamp
   - Keyboard shortcuts (space = play/pause)
   - Continue playing while browsing
   - Handle URL expiration (re-fetch)

4. Player context:
   - Global audio state
   - Current episode info
   - Playback position

Use HTML5 audio with React refs.
Don't create new UI components - use v0's!
```

**Testing Checkpoints:**
- [ ] Audio plays within 2 seconds of click
- [ ] Seeking works smoothly
- [ ] Player persists during navigation
- [ ] Keyboard shortcuts work
- [ ] No CORS errors

---

## Part 7: Testing & Validation Checkpoints

### Phase 0 (Tech Debt) Success Criteria
- [ ] 6 broken components removed (with @ts-nocheck)
- [ ] 6 specific packages uninstalled (not @radix-ui packages)
- [ ] All TypeScript errors resolved
- [ ] Connection pooling prevents limit errors
- [ ] Baseline performance tests pass
- [ ] No regression in Sprint 0 features
- [ ] Removal tracking document created

### Phase 1 (Search) Success Criteria
- [ ] Embeddings loaded for all 1,171 episodes
- [ ] Search query "AI agents" returns relevant results in <2 seconds
- [ ] Cache hit rate >80% after warm-up
- [ ] Entity search for "OpenAI" shows accurate counts
- [ ] "Crypto/Web3" search works (no spaces!)
- [ ] Rate limiting prevents abuse

### Phase 2 (Auth) Success Criteria
- [ ] Users can create accounts and login
- [ ] Sessions persist across refreshes
- [ ] Saved searches appear in profile
- [ ] RLS policies prevent data leaks
- [ ] Email delivery <30 seconds

### Phase 3 (Visualizations) Success Criteria
- [ ] ALL v0 components integrated
- [ ] SIGNAL bar shows real correlations
- [ ] Statistics use actual data
- [ ] Sentiment heatmap smooth rendering
- [ ] Signal service runs in <10 minutes

### Phase 4 (Audio) Success Criteria
- [ ] Audio plays within 2 seconds
- [ ] Seeking works properly
- [ ] Player persists during navigation
- [ ] Pre-signed URLs expire correctly
- [ ] No CORS issues

### Performance Requirements

| Feature | Target | Measurement | Sprint 0 Baseline |
|---------|--------|-------------|-------------------|
| Search query | <2s | Submit to results | N/A |
| Entity lookup | <500ms | API response | N/A |
| Audio start | <2s | Click to sound | N/A |
| Page load | <2s | All rendered | Currently ~2s |
| API response | <100ms | All endpoints | Currently ~50ms |
| Bundle size | <250KB | After cleanup | Currently 235KB |

### Regression Tests (Run Before Each Deploy)

```bash
# Create test_regression.py
pytest tests/test_regression.py -v

# Tests should verify:
# - All 5 topics return data
# - "Crypto/Web3" specifically (no spaces)
# - Topic velocity chart loads
# - API response time <100ms
# - Bundle size <200KB
```

---

## Part 8: Sprint Review & Demo Script

### Demo Flow (15 minutes)

1. **Technical Debt Victory (1 min)**
   - "Reduced bundle size by 40%"
   - "Zero TypeScript errors"
   - Show performance metrics

2. **Natural Language Search (4 min)**
   - Type: "What are VCs saying about AI agent valuations?"
   - Show instant results with excerpts
   - Click → Play audio snippet
   - "From 1,000 hours to specific insights in 2 seconds"

3. **Entity Intelligence (3 min)**
   - Search: "Sequoia Capital"
   - Show 47 mentions trending up
   - Click "Track" → Saves to profile
   - Show weekly mention chart

4. **Enhanced Dashboard (3 min)**
   - SIGNAL: "AI Agents and DePIN discussed together 67% of episodes"
   - Statistics row with real numbers
   - Switch to Sentiment heatmap
   - "Market sentiment at a glance"

5. **Personalization (2 min)**
   - Login as demo user
   - Show saved searches
   - Show tracked entities
   - "Your personal intelligence agent"

6. **Technical Achievement (2 min)**
   - "Zero new services - used pgvector"
   - "$60/month additional cost"
   - "Every v0 component now active"
   - "Built on Sprint 0's foundation"

### Key Messages
- "Search makes our data 100x more valuable"
- "Entity tracking reveals hidden networks"  
- "Audio brings conversations to life"
- "Technical debt clearance enabled velocity"

---

## Appendix A: Critical Troubleshooting

### Sprint 0 Issues to Avoid

| Issue | Cause | Prevention |
|-------|-------|------------|
| Topic returns 0 results | Wrong name (spaces) | Use EXACT_TOPIC_NAMES constant |
| Foreign key errors | Using guid not id | Always use episode.id UUID |
| Entity queries fail | Using 'type' field | Use 'label' field instead |
| KPIs not loading | Expecting wrapped array | Handle direct array format |
| Dates incorrect | Using metadata | Get from raw bucket |
| Import errors | v0-types naming | Fix in Phase 0 |
| Bundle too large | Unused packages | Remove in Phase 0 |

### Emergency Fixes

1. **Search index corrupted**: 
   ```sql
   DROP INDEX IF EXISTS embedding_idx;
   CREATE INDEX embedding_idx ON episodes USING ivfflat (embedding vector_cosine_ops);
   ```

2. **Connection pool exhausted**:
   ```python
   # In api/.env
   MAX_CONNECTIONS=5  # Reduce from 10
   ```

3. **OpenAI quota hit**:
   ```python
   # Disable search temporarily
   SEARCH_ENABLED=false
   ```

---

## Appendix B: Cost Management

### Additional Monthly Costs
- OpenAI API: ~$50 (reduced by caching)
- S3 bandwidth: ~$10 (audio streaming)
- SendGrid: $0 (free tier sufficient)
- **Total: ~$60/month additional**

### Cost Optimization
- Query cache reduces OpenAI by 80%
- Pre-signed URLs minimize bandwidth
- Materialized views prevent database upgrade
- Rate limiting caps maximum spend

### Monitoring Thresholds
- OpenAI: Alert at $40/month
- Supabase: Alert at 1.5GB transfer
- Vercel: Alert at 80GB bandwidth
- SendGrid: Alert at 80 emails/day

---

## Appendix C: Working with Claude Code

### Repository Context Updates

Add to each PROJECT.md after Phase 0:

```markdown
## Sprint 1 Status

### Completed
- Phase 0: Technical debt resolved
- Bundle size: 235KB → 150KB  
- TypeScript: All errors fixed
- Connection pooling: Implemented

### In Progress
- [Current phase and status]

### Critical Constants
- Topics: Exactly 5, "Crypto/Web3" no spaces
- Entity type field: 'label' not 'type'
- Foreign keys: Use episode.id (UUID)
```

### Claude Code Best Practices

1. **Always provide context:**
   ```
   @[relevant files]
   
   Sprint 0 learning: Entity type is in 'label' field, not 'type'.
   I need to create an entity search endpoint...
   ```

2. **Reference existing patterns:**
   ```
   @main.py
   
   Create a new service following the same patterns as main.py:
   - Progress bars
   - Database connections  
   - Error handling
   ```

3. **Be specific about repos:**
   ```
   Working in: podinsight-api repository
   Next step: Will switch to podinsight-dashboard
   ```

---

## Appendix D: Sprint 1 Execution Order

### Week 1: Foundation
- **Day 1**: Phase 0 - Technical debt (smart cleanup approach)
- **Day 2-3**: Phase 1 - Database setup, embeddings loading
- **Day 4-5**: Phase 1 - Search API endpoints

### Week 2: Features  
- **Day 1-2**: Phase 2 - Authentication
- **Day 3**: Phase 3 - v0 components, SIGNAL bar
- **Day 4**: Phase 3 - Sentiment heatmap
- **Day 5**: Phase 4 - Audio playback

### Daily Checklist
```markdown
- [ ] Run regression tests
- [ ] Check bundle size
- [ ] Verify "Crypto/Web3" works
- [ ] Test API response times
- [ ] Commit with clear message
- [ ] Update PROJECT.md
```

---

*This playbook incorporates all Sprint 0 learnings. Phase 0 (Technical Debt) is MANDATORY before starting new features. Every prompt includes specific context about data quirks, exact naming, and repository locations. Follow the testing checklists to avoid Sprint 0 issues.*