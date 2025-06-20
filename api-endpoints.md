# PodInsightHQ API Endpoints Documentation

**Last Updated:** June 2025  
**Base URL:** `https://podinsight-api.vercel.app`  
**API Version:** 1.0

## Overview

The PodInsightHQ API provides programmatic access to podcast intelligence data including topic trends, entity mentions, and semantic search capabilities. Built with FastAPI and deployed on Vercel serverless functions.

## Authentication

### Public Endpoints (No Auth Required)
- `GET /api/topic-velocity`
- `POST /api/auth/signup`
- `POST /api/auth/login`

### Protected Endpoints (Auth Required)
- `POST /api/search` (saves searches when authenticated)
- `GET /api/entities` (tracks entities when authenticated)
- `GET /api/audio/stream/{episode_id}`
- `GET /api/auth/me`
- `POST /api/auth/logout`

### Authentication Method
- **Type:** JWT Bearer Token
- **Header:** `Authorization: Bearer <token>`
- **Token Expiry:** 1 hour (auto-refresh available)

## Rate Limiting

| Endpoint Type | Limit | Window |
|--------------|-------|---------|
| **Search** | 20 requests | per minute |
| **Auth** | 5 requests | per minute |
| **Default** | 200 requests | per hour |
| **Audio Stream** | 10 requests | per minute |

Rate limit headers included in responses:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

## Endpoints

### 0. Health Check

**Endpoint:** `GET /`  
**Description:** Basic health check to verify API is running  
**Authentication:** None required  
**Status:** ✅ Implemented

#### Response
```json
{
  "status": "healthy",
  "environment": "staging",
  "version": "1.0.0"
}
```

### 1. Topic Velocity

**Endpoint:** `GET /api/topic-velocity`  
**Description:** Returns topic mention trends over time  
**Authentication:** None required  
**Cache:** 1 hour

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| weeks | integer | 12 | Number of weeks to return |
| topics | string | "AI Agents,Capital Efficiency,DePIN,B2B SaaS" | Comma-separated topic list |

#### Response
```json
{
  "data": {
    "AI Agents": [
      {
        "week": "2025-W01",
        "mentions": 45,
        "date": "Jan 1-7"
      },
      {
        "week": "2025-W02",
        "mentions": 67,
        "date": "Jan 8-14"
      }
    ],
    "Capital Efficiency": [...],
    "DePIN": [...],
    "B2B SaaS": [...]
  },
  "metadata": {
    "total_episodes": 1171,
    "date_range": "2025-01-01 to 2025-06-14",
    "data_completeness": "topics_only"
  }
}
```

#### Example Request
```bash
curl -X GET "https://podinsight-api.vercel.app/api/topic-velocity?weeks=8"
```

---

### 2. Semantic Search (Sprint 1)

**Endpoint:** `POST /api/search`  
**Description:** Natural language search across all podcast transcripts  
**Authentication:** Optional (required to save searches)  
**Feature Flag:** `SEARCH_ENABLED` must be true

#### Request Body
```json
{
  "query": "What are VCs saying about AI valuations?",
  "limit": 10,
  "offset": 0
}
```

#### Response
```json
{
  "results": [
    {
      "episode_id": "550e8400-e29b-41d4-a716-446655440000",
      "podcast_name": "The Twenty Minute VC",
      "episode_title": "AI Valuations in 2025",
      "published_at": "2025-04-15T00:00:00Z",
      "excerpt": "...the key insight about AI valuations is that they're reflecting future potential rather than current metrics...",
      "similarity_score": 0.89,
      "timestamp_seconds": 1234,
      "s3_audio_path": "pod-insights-raw/twenty-minute-vc/550e8400/audio/episode.mp3"
    }
  ],
  "total_results": 42,
  "query_embedding_cached": true
}
```

#### Error Response (Feature Disabled)
```json
{
  "error": "Search temporarily unavailable",
  "message": "Please try again later",
  "feature_disabled": true
}
```

---

### 3. Entity Search (Sprint 1)

**Endpoint:** `GET /api/entities`  
**Description:** Search and track people, companies, and organizations  
**Authentication:** Optional (required to track entities)

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| search | string | - | Search term (e.g., "Sequoia") |
| type | string | - | Filter by entity type: PERSON, ORG, GPE, MONEY |
| limit | integer | 20 | Max results (up to 100) |
| timeframe | string | - | Time filter: "30d", "90d", "all" |

#### Response
```json
{
  "entities": [
    {
      "name": "Sequoia Capital",
      "type": "ORG",
      "mention_count": 47,
      "episode_count": 23,
      "trend": "up",
      "recent_mentions": [
        {
          "episode_title": "The Future of VC",
          "date": "2025-06-01",
          "context": "...Sequoia Capital announced their new AI fund..."
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
```

---

### 4. Audio Streaming (Sprint 1)

**Endpoint:** `GET /api/audio/stream/{episode_id}`  
**Description:** Generate pre-signed URL for audio streaming  
**Authentication:** Required

#### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| episode_id | UUID | Episode identifier |

#### Query Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| start | integer | Start position in seconds |

#### Response
```json
{
  "stream_url": "https://pod-insights-raw.s3.amazonaws.com/...",
  "expires_at": "2025-06-20T11:00:00Z",
  "duration_seconds": 3600,
  "format": "audio/mpeg"
}
```

---

### 5. Authentication Endpoints (Sprint 1)

#### 5.1 Sign Up

**Endpoint:** `POST /api/auth/signup`  
**Description:** Create new user account

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "created_at": "2025-06-20T10:00:00Z"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### 5.2 Login

**Endpoint:** `POST /api/auth/login`  
**Description:** Authenticate existing user

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:** Same as signup

#### 5.3 Get Current User

**Endpoint:** `GET /api/auth/me`  
**Description:** Get authenticated user details  
**Authentication:** Required

**Response:**
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "created_at": "2025-06-20T10:00:00Z",
    "subscription_tier": "free"
  }
}
```

#### 5.4 Logout

**Endpoint:** `POST /api/auth/logout`  
**Description:** Invalidate current session  
**Authentication:** Required

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

---

## Error Handling

### Standard Error Response
```json
{
  "error": "Error type",
  "message": "Human-readable error message",
  "detail": "Technical details (development only)",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### HTTP Status Codes

| Code | Meaning | Common Scenarios |
|------|---------|------------------|
| 200 | Success | Request completed successfully |
| 201 | Created | New resource created (signup) |
| 400 | Bad Request | Invalid parameters or body |
| 401 | Unauthorized | Missing or invalid auth token |
| 403 | Forbidden | Valid token but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Feature disabled or maintenance |

## CORS Configuration

Allowed origins:
- `http://localhost:3000` (development)
- `https://podinsighthq.vercel.app` (production)
- `https://*.vercel.app` (preview deployments)

Allowed methods: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`

## Performance Metrics

| Endpoint | Target Response Time | Cache Duration |
|----------|---------------------|----------------|
| Topic Velocity | <500ms | 1 hour |
| Search | <2s | Query-based (LRU) |
| Entities | <500ms | 1 hour |
| Audio Stream | <200ms | N/A |
| Auth | <300ms | N/A |

## SDK Examples

### JavaScript/TypeScript
```typescript
// Using fetch
const response = await fetch('https://podinsight-api.vercel.app/api/topic-velocity', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
const data = await response.json();

// Using axios
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://podinsight-api.vercel.app',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const { data } = await api.get('/api/topic-velocity');
```

### Python
```python
import requests

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Topic velocity
response = requests.get(
    'https://podinsight-api.vercel.app/api/topic-velocity',
    headers=headers
)
data = response.json()

# Search
response = requests.post(
    'https://podinsight-api.vercel.app/api/search',
    headers=headers,
    json={'query': 'AI valuations', 'limit': 10}
)
results = response.json()
```

### cURL
```bash
# Topic velocity
curl -H "Authorization: Bearer ${TOKEN}" \
  https://podinsight-api.vercel.app/api/topic-velocity

# Search
curl -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query":"AI valuations","limit":10}' \
  https://podinsight-api.vercel.app/api/search
```

## Webhooks (Future)

Planned webhook events:
- `entity.threshold_reached` - When tracked entity hits mention threshold
- `search.saved` - When user saves a search
- `digest.ready` - When weekly digest is generated

## API Versioning

Current version: `v1` (implicit in URL)

Future versions will use URL versioning:
- `https://podinsight-api.vercel.app/v2/api/...`

## Support

- **Documentation:** https://github.com/YOUR_USERNAME/podinsight-docs
- **Status Page:** https://status.podinsighthq.com (future)
- **Contact:** api-support@podinsighthq.com (future)