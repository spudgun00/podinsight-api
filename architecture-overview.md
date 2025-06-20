# PodInsightHQ Architecture Overview

**Last Updated:** June 17, 2025  
**Version:** 1.0.0  
**Status:** Production MVP  

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATA SOURCES (S3)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐              ┌─────────────────────┐              │
│  │  pod-insights-raw   │              │ pod-insights-stage  │              │
│  │  ├── podcast-1/     │              │  ├── transcripts/   │              │
│  │  ├── podcast-2/     │              │  ├── kpis/          │              │
│  │  └── ...            │              │  ├── entities/      │              │
│  │    (RSS metadata)   │              │  └── embeddings/    │              │
│  └─────────────────────┘              └─────────────────────┘              │
│            │                                     │                          │
└────────────┼─────────────────────────────────────┼─────────────────────────┘
             │                                     │
             │         ┌───────────────────┐       │
             └────────▶│                   │◀──────┘
                       │   ETL PIPELINE    │
                       │  (Python Script)  │
                       │                   │
                       │ • Read S3 files   │
                       │ • Extract topics  │
                       │ • Parse KPIs      │
                       │ • Filter entities │
                       └─────────┬─────────┘
                                 │
                                 ▼
                       ┌─────────────────────┐
                       │                     │
                       │     SUPABASE       │
                       │    (PostgreSQL)    │
                       │                     │
                       │ Tables:            │
                       │ • episodes (1,171) │
                       │ • topic_mentions   │
                       │ • extracted_kpis   │
                       │ • extracted_entities│
                       │                     │
                       │ + pgvector ready   │
                       └─────────┬───────────┘
                                 │
                                 ▼
                       ┌─────────────────────┐
                       │                     │
                       │    FASTAPI API     │
                       │   (Vercel Edge)    │
                       │                     │
                       │ /api/topic-velocity│
                       │                     │
                       │ • ~50ms response   │
                       │ • CORS enabled     │
                       │ • London region    │
                       └─────────┬───────────┘
                                 │
                                 ▼
                       ┌─────────────────────┐
                       │                     │
                       │  NEXT.JS DASHBOARD │
                       │    (Vercel Edge)   │
                       │                     │
                       │ • Topic Velocity   │
                       │ • Recharts viz     │
                       │ • Basic Auth       │
                       │ • Dark theme       │
                       └─────────────────────┘
```

## Component Details

### 1. Data Sources (S3 Buckets)

**pod-insights-raw**
- Contains original RSS feed data with publication dates
- Structure: `{podcast_name}/{episode_guid}/`
- Used to retrieve missing metadata (like publication dates)

**pod-insights-stage**
- Contains processed podcast data
- 1,171 episodes across 29 podcast feeds
- File types per episode:
  - `transcripts/` - Full episode transcripts with segments
  - `kpis/` - Extracted financial metrics (50,909 total)
  - `entities/` - Named entities (123,948 filtered)
  - `embeddings/` - Vector embeddings (ready for Sprint 1)

### 2. ETL Pipeline (podinsight-etl)

**Technology:** Python 3.9+
**Type:** One-time batch script (not continuous)
**Duration:** ~20-30 minutes for full run

**Key Features:**
- Adaptive file discovery (handles complex S3 naming)
- Generator pattern for memory efficiency
- Resume capability to skip processed episodes
- Progress tracking with real-time updates

**Topic Detection:**
- 5 tracked topics with 74 pattern variations
- Topics: AI Agents, Capital Efficiency, DePIN, B2B SaaS, Crypto/Web3
- Maximum 1 mention per topic per episode

**Data Processing:**
- Episodes: Extracts title, duration, word count, dates
- Topics: Pattern matching across transcript text
- KPIs: Parses financial metrics from structured data
- Entities: Filters to PERSON, ORG, GPE, MONEY types only

### 3. Database (Supabase/PostgreSQL)

**Provider:** Supabase (Free tier)
**Location:** Default region
**Extensions:** pgvector v0.8.0 (ready for semantic search)

**Schema Overview:**
```sql
episodes (1,171 rows)
├── id (UUID primary key)
├── podcast_name, episode_title
├── published_at (corrected from raw bucket)
├── duration_seconds, word_count
└── s3_paths for audio/embeddings

topic_mentions (1,292 rows)
├── episode_id (foreign key)
├── topic_name (one of 5 topics)
├── mention_date, week_number
└── confidence_score

extracted_kpis (50,909 rows)
├── episode_id (foreign key)
├── kpi_type (MONEY, PERCENTAGE)
├── value, context
└── confidence_score

extracted_entities (123,948 rows)
├── episode_id (foreign key)
├── entity_type (PERSON, ORG, GPE, MONEY)
├── entity_name (normalized)
└── confidence_score
```

**Performance:**
- Indexes on all foreign keys and date fields
- Optimized for weekly aggregation queries
- Sub-100ms query times for topic velocity

### 4. API Layer (podinsight-api)

**Technology:** FastAPI + Python 3.12
**Hosting:** Vercel Serverless Functions
**Region:** London (lhr1)
**URL:** https://podinsight-api.vercel.app

**Endpoints:**
- `GET /` - Health check with env validation
- `GET /api/topic-velocity` - Main data endpoint
  - Parameters: `weeks` (default: 12), `topics` (comma-separated)
  - Returns: Recharts-compatible JSON format
  - Performance: ~50ms average (10x better than target)

**Features:**
- CORS enabled for all origins
- Error handling with graceful fallbacks
- Weekly data aggregation with proper date handling
- Caching headers for 5-minute revalidation

### 5. Frontend Dashboard (podinsight-dashboard)

**Technology:** Next.js 14 + TypeScript + Tailwind CSS
**Hosting:** Vercel Edge Network
**URL:** https://podinsight-dashboard.vercel.app

**Key Features:**
- Topic Velocity Chart (Recharts)
- Real-time data from 1,171 episodes
- 4 default topics displayed (5th available via API)
- Interactive tooltips and legend
- Time period selector (1M, 3M, 6M, All)
- Compare mode for period-over-period analysis
- Premium v0 UI with animations

**Performance:**
- First load: < 2 seconds
- Bundle size: 235KB (under 500KB target)
- API calls: ~50ms
- Smooth 60fps animations

**Security:**
- Basic auth protection (username: admin)
- Environment variables for sensitive data
- HTTPS only via Vercel

## Data Flow

### 1. Initial Data Load (One-time)
```
S3 Buckets → ETL Script → Supabase
   1,171        20 min      4 tables
  episodes                populated
```

### 2. Real-time Data Access
```
User Request → Dashboard → API → Supabase → API → Dashboard
              (Next.js)  (FastAPI)         (50ms)  (Recharts)
```

### 3. Topic Detection Flow
```
Transcript Text → Pattern Matching → Topic Assignment → Database
 "AI agents are"    74 patterns      Max 1/episode     Store mention
```

## Environment Variables

### ETL Script
```bash
AWS_ACCESS_KEY_ID=xxx        # Auto from ~/.aws/credentials
AWS_SECRET_ACCESS_KEY=xxx    # Auto from ~/.aws/credentials
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx
S3_BUCKET_STAGE=pod-insights-stage
S3_BUCKET_RAW=pod-insights-raw
```

### API
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx
PYTHON_VERSION=3.12
```

### Dashboard
```bash
NEXT_PUBLIC_API_URL=https://podinsight-api.vercel.app
BASIC_AUTH_PASSWORD=xxx
```

## Performance Metrics

| Component | Metric | Target | Actual | Status |
|-----------|--------|--------|--------|--------|
| ETL | Processing Speed | N/A | 1.8 eps/sec | ✅ |
| ETL | Total Runtime | < 1 hour | ~20-30 min | ✅ |
| Database | Query Time | < 200ms | < 100ms | ✅ |
| API | Response Time | < 500ms | ~50ms | ✅ |
| Dashboard | Page Load | < 2s | < 2s | ✅ |
| Dashboard | Bundle Size | < 500KB | 235KB | ✅ |

## Scalability Considerations

### Current Limits
- Supabase free tier: 2GB transfer/month
- Vercel free tier: 100GB bandwidth/month
- Database connections: 20 concurrent (needs pooling soon)
- API compute: 100K requests/day

### Growth Path
1. **Sprint 1:** Add pgBouncer for connection pooling
2. **Sprint 2:** Implement caching layer (Redis)
3. **Sprint 3:** Consider Supabase Pro ($25/month)
4. **Future:** Multi-region deployment for global users

## Security Model

### Current Implementation
- Basic auth for dashboard (staging protection)
- API keys stored in environment variables
- HTTPS everywhere via Vercel
- Row-level security ready in Supabase (not enabled)

### Sprint 1 Additions
- User authentication (Supabase Auth)
- API rate limiting
- Row-level security for multi-tenant data

## Technology Stack Summary

| Layer | Technology | Version | Hosting |
|-------|-----------|---------|---------|
| Data Storage | AWS S3 | - | AWS |
| ETL | Python | 3.9+ | Local/EC2 |
| Database | PostgreSQL | 15 | Supabase |
| Vector DB | pgvector | 0.8.0 | Supabase |
| API | FastAPI | 0.115 | Vercel |
| Frontend | Next.js | 14.2 | Vercel |
| UI Library | Recharts | 2.15 | - |
| Styling | Tailwind CSS | 3.4 | - |
| Language | TypeScript | 5.8 | - |

## Monitoring & Observability

### Current
- Vercel Analytics (API & Dashboard)
- Supabase Dashboard (Database metrics)
- Function logs in Vercel

### Planned (Sprint 2)
- Sentry for error tracking
- Custom performance monitoring
- User analytics (privacy-compliant)

---

*This architecture supports the Genesis Sprint goal: Transform 1,000+ hours of podcast intelligence into actionable insights in under 72 hours.*