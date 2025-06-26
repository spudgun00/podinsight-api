# PodInsightHQ System Architecture Overview

**Last Updated:** June 2025
**Version:** 1.0 (Post-Genesis Sprint)

## Executive Summary

PodInsightHQ is a SaaS platform that transforms podcast content into actionable intelligence for VCs and startup founders. The system processes 1,000+ hours of podcast audio through AI-powered pipelines to extract insights, track trends, and enable natural language search across episodes.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User Layer                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  Next.js Dashboard (Vercel)    │    Mobile (Future)    │   Slack Bot    │
│  - Topic Velocity Chart        │                       │   (Sprint 3)   │
│  - Natural Language Search     │                       │                │
│  - Entity Explorer             │                       │                │
└────────────────┬───────────────┴───────────────────────┴────────────────┘
                 │ HTTPS
┌────────────────▼───────────────────────────────────────────────────────┐
│                           API Layer (Vercel)                            │
├─────────────────────────────────────────────────────────────────────────┤
│  FastAPI Serverless Functions                                           │
│  - /api/topic-velocity    - /api/search (Sprint 1)                     │
│  - /api/entities          - /api/audio/stream                          │
│  - /api/auth/*            - /api/insights (Future)                     │
└────────────────┬───────────────────────────────────────────────────────┘
                 │ PostgreSQL Protocol + HTTPS
┌────────────────▼───────────────────────────────────────────────────────┐
│                        Data Layer (Supabase)                            │
├─────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL + pgvector                                                  │
│  - 1,171 Episodes         - 123k Entities                              │
│  - 1,400 Topic Mentions   - 50k KPIs                                   │
│  - Vector Embeddings      - User Data                                  │
└────────────────┬───────────────────────────────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────────────────────────────┐
│                    Storage Layer (AWS S3)                               │
├─────────────────────────────────────────────────────────────────────────┤
│  pod-insights-raw/        │  pod-insights-stage/      │ pod-insights-  │
│  - Audio files (.mp3)     │  - Transcripts (.json)   │ manifests/     │
│  - Original metadata      │  - Embeddings (.npy)     │ - CSV exports  │
│                           │  - Entities/KPIs         │                │
└───────────────────────────┴────────────────────────────┴───────────────┘
```

## Core Components

### 1. Frontend Dashboard (Next.js)
- **Repository:** `podinsight-dashboard`
- **Hosting:** Vercel Edge Network
- **Key Features:**
  - Server-side rendering for SEO and performance
  - React components with TypeScript
  - Tailwind CSS with dark theme
  - v0.dev AI-generated components
  - Recharts for data visualization
- **Authentication:** Supabase Auth with JWT tokens
- **Performance:** <2 second page load requirement

### 2. API Layer (FastAPI)
- **Repository:** `podinsight-api`
- **Hosting:** Vercel Serverless Functions
- **Architecture:** RESTful API with OpenAPI documentation
- **Key Endpoints:**
  - Topic analysis and trends
  - Semantic search (Sprint 1)
  - Entity tracking
  - Audio streaming via pre-signed URLs
- **Rate Limiting:** 20 requests/minute for search
- **Caching:** In-memory LRU cache for embeddings

### 3. Database (Supabase/PostgreSQL)
- **Hosting:** Supabase (managed PostgreSQL)
- **Extensions:** pgvector for similarity search
- **Key Features:**
  - Row Level Security (RLS) ready
  - Automatic API generation
  - Real-time subscriptions (future)
  - Built-in authentication
- **Performance:**
  - Connection pooling via pgBouncer (when needed)
  - Materialized views for aggregations
  - Strategic indexes on high-query columns

### 4. Storage Layer (AWS S3)
- **Buckets:**
  - `pod-insights-raw`: Source audio files
  - `pod-insights-stage`: Processed data
  - `pod-insights-manifests`: Export files
- **Access Pattern:**
  - ETL writes to stage bucket
  - API reads via pre-signed URLs
  - CORS configured for audio streaming

### 5. ETL Pipeline
- **Repository:** `podinsight-etl`
- **Execution:** Local Python scripts (not deployed)
- **Key Processes:**
  - S3 file discovery (adaptive patterns)
  - Data quality validation
  - Topic detection
  - Entity normalization
  - Embedding loading (Sprint 1)
- **Error Handling:** Resume capability, detailed logging

## Data Flow

### 1. Historical Data Processing (Complete)
```
Podcasts → Manual Download → S3 Raw → External Processing → S3 Stage → ETL → Supabase
```

### 2. Search Query Flow (Sprint 1)
```
User Query → API → OpenAI Embedding → pgvector Search → Relevant Episodes → UI
                ↓
           Query Cache (80% hit rate target)
```

### 3. Audio Playback Flow
```
User Clicks Play → API → Generate Pre-signed URL → Stream from S3 → HTML5 Player
                         (1-hour expiration)
```

## Technology Stack

### Core Technologies
| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| **Frontend** | Next.js | 14 | React with SSR, great DX |
| **Styling** | Tailwind CSS | 3.x | Rapid UI development |
| **API** | FastAPI | 0.104+ | Modern Python, async support |
| **Database** | PostgreSQL | 15 | Robust, pgvector support |
| **Vector DB** | pgvector | 0.8.0 | Native PostgreSQL integration |
| **Hosting** | Vercel | - | Zero-config deployments |
| **Auth** | Supabase Auth | - | Integrated with database |
| **Storage** | AWS S3 | - | Scalable object storage |

### AI/ML Stack
| Service | Purpose | Cost Control |
|---------|---------|--------------|
| **OpenAI API** | Query embeddings, future summaries | Query cache, rate limiting |
| **WhisperX** | Transcript generation (pre-processed) | Already complete |
| **Custom NLP** | Topic detection, entity extraction | Pre-computed |

### Development Tools
- **UI Generation:** v0.dev by Vercel
- **Version Control:** GitHub (3 repositories)
- **Deployment:** GitHub → Vercel auto-deploy
- **Monitoring:** Vercel Analytics, Supabase Dashboard

## Environment Configuration

### Key Environment Variables by Service

**API Service:**
- `OPENAI_API_KEY_STAGING` / `OPENAI_API_KEY_PROD`
- `SUPABASE_URL_STAGING` / `SUPABASE_URL_PROD`
- `SUPABASE_KEY_STAGING` / `SUPABASE_KEY_PROD`
- `SEARCH_ENABLED` (feature flag)

**Frontend:**
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

**ETL:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_STAGE`

## Security Architecture

### Authentication & Authorization
- **User Auth:** Supabase Auth with email/password
- **API Auth:** JWT tokens in httpOnly cookies
- **Staging Protection:** Basic auth via Vercel
- **Future:** OAuth providers, SSO for enterprise

### Data Security
- **At Rest:** Encrypted S3 buckets, encrypted database
- **In Transit:** HTTPS everywhere, SSL database connections
- **Audio Access:** Time-limited pre-signed URLs
- **User Isolation:** RLS policies (to be enabled)

### Rate Limiting & Abuse Prevention
- **Search:** 20 requests/minute per IP
- **API:** 200 requests/hour default
- **OpenAI:** Separate staging/prod keys
- **Monitoring:** 429 response tracking

## Performance Targets

| Metric | Target | Current | Monitoring |
|--------|--------|---------|------------|
| **Page Load** | <2s | 1.8s ✅ | Vercel Analytics |
| **API Response** | <500ms | 247ms ✅ | Custom logging |
| **Search Results** | <2s | TBD | Sprint 1 target |
| **Uptime** | 99.9% | 100% ✅ | UptimeRobot |
| **Database Query** | <100ms | ~50ms ✅ | Supabase Dashboard |

## Scalability Considerations

### Current Scale (MVP)
- **Episodes:** 1,171 (ready to handle 10,000+)
- **Users:** Alpha phase (5-50 users)
- **API Calls:** <1,000/day
- **Storage:** ~200GB total

### Growth Strategy
1. **Database:** Enable connection pooling at 20+ concurrent
2. **API:** Vercel auto-scales, monitor costs
3. **Search:** Implement caching layer (Redis if needed)
4. **Storage:** S3 scales infinitely
5. **Costs:** Monitor at 80% of free tier limits

## Disaster Recovery

### Backup Strategy
- **Database:** Daily Supabase backups (7-day retention)
- **Code:** GitHub repository backups
- **S3 Data:** Cross-region replication (future)

### Recovery Procedures
- **Database Corruption:** Restore from Supabase point-in-time
- **API Outage:** Vercel auto-failover
- **S3 Access Issues:** Cached audio URLs, fallback bucket

## Monitoring & Observability

### Current Monitoring
- **Uptime:** UptimeRobot (5-minute checks)
- **Performance:** Vercel Analytics
- **Errors:** Console logs (basic)
- **Database:** Supabase Dashboard

### Future Monitoring (Sprint 3)
- **APM:** Sentry for error tracking
- **Logs:** Centralized logging
- **Alerts:** Slack notifications
- **Metrics:** Custom dashboards

## Development Workflow

### Deployment Pipeline
```
Developer → Git Push → GitHub → Vercel Auto-Deploy → Production
                              ↓
                         Run Tests (future CI/CD)
```

### Environment Strategy
- **Local:** Developers use `.env.local`
- **Staging:** Shared staging with basic auth
- **Production:** Live at podinsighthq.com

## Cost Structure

### Current Monthly Costs (Post-Genesis)
| Service | Cost | Limit Before Upgrade |
|---------|------|---------------------|
| **Supabase** | $0 | 2GB transfer |
| **Vercel** | $0 | 100GB bandwidth |
| **AWS S3** | ~$5 | N/A |
| **OpenAI** | ~$10 | Usage-based |
| **Total** | ~$15 | Target <$75/month |

### Cost Optimization
- Query caching (80% reduction in OpenAI costs)
- Materialized views (avoid database upgrade)
- CDN caching for static assets
- Monitoring at 80% of limits

## Future Architecture Considerations

### Sprint 2-3 Additions
- **Real-time Features:** WebSocket connections
- **Background Jobs:** Queue system for alerts
- **Search Enhancement:** Elasticsearch if needed
- **Mobile App:** React Native sharing code

### Long-term Vision
- **Multi-region:** Edge deployment for global users
- **Microservices:** Split monolith if needed
- **Data Pipeline:** Apache Airflow for automation
- **ML Pipeline:** Custom model training infrastructure
