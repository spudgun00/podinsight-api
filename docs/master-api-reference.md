# Master API Reference Document - PodInsightHQ

**Document Version**: 1.1
**Created**: 2025-01-03
**Last Modified**: 2025-01-08
**Purpose**: Comprehensive API reference with all endpoints, integrations, and patterns

---

## 🔍 Sources Analyzed

1. api_architecture_documentation.md (2025-01-03)
2. API_ENDPOINTS.md
3. PodInsightHQ API Endpoints Documentation.md
4. API_INTEGRATION_GUIDE.md
5. PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md (sections on API)
6. complete_system_architecture.md (API layer details)

---

## 🚨 Discrepancies Found

### 1. Internal vs External Endpoints
- **Confusion**: Some docs mix Next.js internal routes with external API
- **Reality**: Two separate API systems
  - Next.js API Routes: `/api/*` (proxy endpoints)
  - FastAPI Backend: `https://podinsight-api.vercel.app/*` (actual API)
- **Resolution**: ✅ Document both layers clearly separated

### 2. Modal.com Status
- **Some docs**: Suggest Modal might be deprecated
- **Reality**: Critical production service for embeddings
- **Endpoints**:
  - Embeddings: `https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run`
  - Health: `https://podinsighthq--podinsight-embeddings-simple-health-check.modal.run`
- **Resolution**: ✅ Modal.com is active and required

### 3. Authentication Status
- **Documentation**: References auth endpoints
- **Reality**: No authentication implemented (planned for Sprint 4)
- **Resolution**: ✅ All endpoints currently public
- **Update (2025-01-08)**: Episode Intelligence endpoints (Story 5B) temporarily have authentication removed to unblock Story 4 dashboard integration. Auth will be re-added when auth system is implemented.

### 4. Audio Endpoint Versions
- **Inconsistency**: Some docs show `/api/audio/*`, others `/api/v1/audio_clips/*`
- **Reality**: `/api/v1/audio_clips/{episode_id}` is correct
- **Resolution**: ✅ Use versioned endpoint

---

## ✅ Verified API Architecture

### API Layers Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Browser)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              NEXT.JS API ROUTES (Proxy Layer)               │
│                 /api/* endpoints                             │
│         Purpose: Hide backend tokens, CORS handling          │
└─────────────────────┬───────────────────────────────────────┘
                      │ Internal fetch with auth token
                      ▼
┌─────────────────────────────────────────────────────────────┐
│            FASTAPI BACKEND (Vercel Serverless)              │
│           https://podinsight-api.vercel.app                 │
│         Purpose: Actual business logic & data access         │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┬─────────────────────┐
        ▼                           ▼                     ▼
┌───────────────┐         ┌──────────────┐      ┌──────────────┐
│  Modal.com    │         │ MongoDB Atlas│      │   Supabase   │
│  (Embeddings) │         │ (Vector DB)  │      │ (Metadata)   │
└───────────────┘         └──────────────┘      └──────────────┘
```

---

## 📋 Complete Endpoint Reference

### Next.js API Routes (Frontend Proxy)

| Endpoint | Method | Purpose | Backend Call |
|----------|--------|---------|--------------|
| `/api/search` | POST | Proxy search requests | `POST {BACKEND}/api/search` |
| `/api/v1/audio_clips/[episode_id]` | GET | Proxy audio generation | `GET {BACKEND}/api/v1/audio_clips/{id}` |

**⚠️ SECURITY ISSUE**: These routes use `BACKEND_API_TOKEN` server-side, exposing backend access

### FastAPI Backend Endpoints

#### 1. Health & Monitoring

##### GET `/`
```json
// Response
{
  "status": "healthy",
  "service": "PodInsightHQ API",
  "version": "1.0.0",
  "deployment_time": "2025-01-03T12:00:00",
  "env_check": {
    "SUPABASE_URL": true,
    "SUPABASE_KEY": true,
    "HUGGINGFACE_API_KEY": true,
    "MONGODB_URI": true,
    "PYTHON_VERSION": "3.9"
  },
  "connection_pool": {
    "status": "healthy",
    "active_connections": 2,
    "max_connections": 10
  }
}
```

##### GET `/api/health`
- **Purpose**: Detailed health check for monitoring
- **Auth**: None
- **Cache**: No
- **Response**: Similar to `/` with additional checks

##### GET `/api/pool-stats`
- **Purpose**: MongoDB connection pool statistics
- **Auth**: None
- **Response**: Connection metrics and utilization

#### 2. Search Endpoints

##### POST `/api/search`
```json
// Request
{
  "query": "What are VCs saying about AI valuations?",
  "limit": 10,
  "offset": 0
}

// Response
{
  "analysis": {
    "answer": "VCs are currently viewing AI valuations with increased scrutiny...",
    "confidence": 0.92,
    "key_themes": ["valuation_discipline", "revenue_multiples", "ai_premium"],
    "sources_count": 6
  },
  "sources": [
    {
      "id": "abc123",
      "title": "Chris Dixon on AI Market Dynamics",
      "show": "The a16z Podcast",
      "date": "June 15, 2025",
      "text": "...valuations in the AI space need to reflect real usage...",
      "relevance": 0.95,
      "timestamp": 1820000,
      "chunk_index": 42,
      "embedding_distance": 0.0823
    }
  ],
  "episodes": [...],
  "search_metadata": {
    "total_chunks_searched": 823763,
    "chunks_retrieved": 100,
    "processing_time_ms": 3240,
    "model_used": "instructor-xl",
    "search_method": "vector_768d"
  }
}
```

**Technical Details**:
- Uses Modal.com for query embedding
- MongoDB vector search with numCandidates=100
- GPT-4 synthesis for answer generation
- Client-side LRU caching

#### 3. Analytics Endpoints

##### GET `/api/topic-velocity`
```json
// Query Parameters
?weeks=12  // Number of weeks (default: 12, max: 52)

// Response
{
  "data": [
    {
      "week": "2025-W01",
      "ai_agents": 45,
      "capital_efficiency": 23,
      "depin": 67,
      "b2b_saas": 89,
      "crypto_web3": 34
    }
  ],
  "signals": [
    {
      "topic": "DePIN",
      "signal": "Explosive growth - 350% increase over baseline",
      "confidence": "high",
      "date": "2025-W01"
    }
  ],
  "notable_performer": {
    "topic": "DePIN",
    "growth_percentage": 350,
    "baseline_mentions": 12,
    "current_mentions": 67
  }
}
```

##### GET `/api/entities`
```json
// Query Parameters
?search=OpenAI&type=ORG&limit=20&timeframe=30d

// Response
{
  "success": true,
  "entities": [
    {
      "name": "OpenAI",
      "type": "ORG",
      "mention_count": 234,
      "episode_count": 89,
      "trend": "up",
      "recent_mentions": [...]
    }
  ],
  "total_entities": 1,
  "filters": {...}
}
```

##### GET `/api/signals`
- **Purpose**: Pre-computed insights and correlations
- **Cache**: 1 hour
- **Response**: Topic correlations, spikes, trending combinations

#### 4. Audio Generation

##### GET `/api/v1/audio_clips/{episode_id}`
```json
// Path Parameters
{episode_id} - Supports multiple formats:
  - UUID: "1216c2e7-42b8-42ca-92d7-bad784f80af2"
  - MongoDB ObjectId: "507f1f77bcf86cd799439011"  # pragma: allowlist secret
  - Special formats: "substack:post:12345", "flightcast:xyz"

// Query Parameters
?start_time_ms=120000  // Required
&duration_ms=30000     // Optional (default: 30000, max: 60000)

// Response
{
  "clip_url": "https://pod-insights-clips.s3.amazonaws.com/temp/clip_abc123.mp3?X-Amz-Algorithm=...",
  "expires_at": "2025-01-03T13:00:00Z",
  "cache_hit": false,
  "episode_id": "1216c2e7-42b8-42ca-92d7-bad784f80af2",
  "start_time_ms": 120000,
  "duration_ms": 30000,
  "generation_time_ms": 2450
}
```

**Implementation**:
- AWS Lambda for processing
- FFmpeg for audio extraction
- S3 for clip storage
- 1-hour pre-signed URLs

#### 5. Episode Intelligence Endpoints (Sprint 4)

##### GET `/api/intelligence/dashboard`
```json
// Query Parameters
?limit=8  // Number of episodes to return (default: 8)

// Response
{
  "episodes": [
    {
      "episode_id": "507f1f77bcf86cd799439011",
      "title": "The Future of AI Agents",
      "podcast_name": "Tech Insights Podcast",
      "published_at": "2024-01-08T10:00:00Z",
      "duration_seconds": 3600,
      "relevance_score": 0.85,
      "signals": [
        {
          "type": "investable",
          "content": "Discussion about Series A fundraising trends in AI startups",
          "confidence": 0.85,
          "timestamp": null
        },
        {
          "type": "competitive",
          "content": "Mention of recent acquisition in the enterprise SaaS space",
          "confidence": 0.75,
          "timestamp": null
        },
        {
          "type": "portfolio",
          "content": "Portfolio company mentioned in context of market expansion",
          "confidence": 0.9,
          "timestamp": null
        },
        {
          "type": "sound_bite",
          "content": "'The future of work is not remote, it's hybrid with AI augmentation'",
          "confidence": 0.9,
          "timestamp": null
        }
      ],
      "summary": "Episode summary not available",
      "key_insights": [
        "AI agents are becoming more sophisticated",
        "Enterprise adoption is accelerating",
        "New funding models emerging"
      ],
      "audio_url": null
    }
  ],
  "total_episodes": 8,
  "generated_at": "2024-01-08T14:30:00Z"
}
```

**Purpose**: Returns consolidated episode intelligence data for dashboard
- **Auth**: None (temporarily removed)
- **Signal Types**: `investable`, `competitive`, `portfolio`, `sound_bite`
- **Usage**: Dashboard transforms response into card-specific data

##### GET `/api/intelligence/brief/{episode_id}`
```json
// Path Parameters
{episode_id} - Episode ID (MongoDB ObjectId or GUID)

// Response
{
  "episode_id": "507f1f77bcf86cd799439011",
  "title": "Episode Title",
  "podcast_name": "Podcast Name",
  "published_at": "2024-01-08T10:00:00Z",
  "duration_seconds": 3600,
  "relevance_score": 0.85,
  "signals": [...],
  "summary": "Detailed episode summary",
  "key_insights": [...],
  "audio_url": null
}
```

**Purpose**: Returns detailed intelligence brief for specific episode
- **Auth**: None (temporarily removed)
- **Use Case**: Modal view with full episode details

##### POST `/api/intelligence/share`
```json
// Request
{
  "episode_id": "507f1f77bcf86cd799439011",
  "method": "email",  // or "slack"
  "recipient": "user@example.com",
  "include_summary": true,
  "personal_note": "Check out this insight"
}

// Response
{
  "success": true,
  "message": "Episode intelligence shared via email to user@example.com",
  "shared_at": "2024-01-08T14:30:00Z"
}
```

**Purpose**: Share episode intelligence via email or Slack
- **Auth**: None (temporarily removed)
- **Methods**: `email`, `slack`
- **Note**: Currently simulated, not sending actual emails

##### PUT `/api/intelligence/preferences`
```json
// Request
{
  "portfolio_companies": ["Company A", "Company B"],
  "interest_topics": ["AI", "SaaS", "Web3"],
  "notification_frequency": "weekly",
  "email_notifications": true,
  "slack_notifications": false
}

// Response
{
  "success": true,
  "preferences": {...},
  "updated_at": "2024-01-08T14:30:00Z"
}
```

**Purpose**: Update user preferences for relevance scoring
- **Auth**: None (temporarily removed)
- **User**: Currently uses "demo-user" for all requests

##### GET `/api/intelligence/health`
```json
// Response
{
  "status": "healthy",
  "service": "intelligence-api",
  "timestamp": "2024-01-08T14:30:00Z",
  "mongodb": "connected"
}
```

**Purpose**: Health check for intelligence API
- **Auth**: None
- **Use**: Monitoring endpoint status

#### 6. Future Endpoints (Documented but Not Implemented)

##### Authentication (Sprint 4)
- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

##### User Features (Future)
- `GET /api/saved_searches`
- `POST /api/tracked_entities`
- `GET /api/user/preferences`

---

## 🔌 External Service Integrations

### Modal.com Endpoints

```python
# Embedding Generation
POST https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run
{
  "text": "Query text to embed",
  "instruction": "Represent the question for retrieving supporting documents:"
}

# Health Check
GET https://podinsighthq--podinsight-embeddings-simple-health-check.modal.run
```

### AWS Services
- **S3**: Direct integration for audio files
- **Lambda**: Audio clip processing (not exposed as API)
- **CloudWatch**: Logging and monitoring

### Database Connections
- **MongoDB Atlas**: Direct connection with connection pooling
- **Supabase**: REST API + direct PostgreSQL connection

---

## 🔧 API Configuration

### Environment Variables
```bash
# Backend API
BACKEND_API_TOKEN=<secret>       # Used by Next.js to call FastAPI
MONGODB_URI=<connection-string>  # MongoDB Atlas
SUPABASE_URL=<url>              # Supabase project
SUPABASE_KEY=<service-key>      # Service role key
OPENAI_API_KEY=<key>            # For GPT-4 synthesis
MODAL_ENABLED=true              # Feature flag

# Frontend (Next.js)
NEXT_PUBLIC_API_URL=https://podinsight-api.vercel.app
```

### Rate Limiting
- **Current**: None implemented
- **Planned**: 20 requests/minute for search
- **Method**: Redis-based rate limiting

### CORS Configuration
```python
# Current (too permissive)
allow_origins=["*"]

# Recommended
allow_origins=[
  "https://podinsight-dashboard.vercel.app",
  "http://localhost:3000"  # Development only
]
```

### Error Handling

```json
// Standard Error Response
{
  "error": "Error type",
  "message": "Human-readable error message",
  "detail": "Technical details (development only)",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**HTTP Status Codes**:
- 200: Success
- 400: Bad Request
- 401: Unauthorized (future)
- 404: Not Found
- 429: Rate Limited (future)
- 500: Internal Server Error
- 503: Service Unavailable (Modal.com down)

---

## 📊 Performance Characteristics

| Endpoint | Cold Start | Warm Response | Timeout |
|----------|------------|---------------|---------|
| `/api/search` | 14s | 3-5s | 40s |
| `/api/topic-velocity` | 2s | <500ms | 30s |
| `/api/entities` | 2s | <500ms | 30s |
| `/api/v1/audio_clips/*` | 5s | 2.5s | 30s |
| `/api/intelligence/dashboard` | 3s | <1s | 30s |
| `/api/intelligence/brief/*` | 2s | <500ms | 30s |
| `/api/intelligence/share` | 1s | <200ms | 30s |
| `/api/intelligence/preferences` | 1s | <200ms | 30s |

**Bottlenecks**:
1. Modal.com cold start (14s) - physics limit of loading 2.1GB model
2. MongoDB vector search - optimized with proper indexing
3. Audio processing - Lambda cold starts

---

## 🔐 Security Considerations

### Current Issues
1. **No Authentication**: All endpoints public (Episode Intelligence endpoints temporarily have auth removed for Story 4)
2. **Token Exposure**: Backend token in Next.js routes
3. **CORS Too Open**: Accepts all origins
4. **No Rate Limiting**: Vulnerable to abuse
5. **No Input Validation**: Basic validation only

### Recommended Fixes
1. Implement JWT authentication (Sprint 4)
2. Use proper auth flow instead of static tokens
3. Restrict CORS to known domains
4. Add Redis-based rate limiting
5. Implement Zod schemas for validation

---

## 📝 API Usage Examples

### Search Request (cURL)
```bash
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI agent architecture patterns", "limit": 5}'
```

### Audio Clip Request
```bash
curl "https://podinsight-api.vercel.app/api/v1/audio_clips/1216c2e7-42b8-42ca-92d7-bad784f80af2?start_time_ms=60000&duration_ms=30000"
```

### Client-Side Integration
```typescript
// Using fetch with error handling
async function searchPodcasts(query: string) {
  try {
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, limit: 10 })
    });

    if (!response.ok) {
      throw new Error(`Search failed: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Search error:', error);
    return { error: 'Search temporarily unavailable' };
  }
}
```

---

## ❓ Needs Verification

1. **Exact Modal.com pricing** after $5k credits exhausted
2. **Lambda concurrency limits** for audio processing
3. **Actual rate limits** needed for each endpoint
4. **Webhook endpoints** mentioned but not documented
5. **GraphQL API** referenced but not implemented

---

**Note**: This document represents the current production API as of January 2025. Authentication and user-specific endpoints are planned for Sprint 4 implementation. Episode Intelligence endpoints (Story 5B) temporarily have authentication removed to unblock Story 4 dashboard integration.
