# Master Architecture & Infrastructure Document - PodInsightHQ

**Document Version**: 1.0
**Created**: 2025-01-03
**Purpose**: Single source of truth for all architecture and infrastructure information

---

## 🔍 Sources Analyzed

1. api_architecture_documentation.md (2025-01-03)
2. complete_system_architecture.md (2025-01-03)
3. PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md (2025-06-26) - **MOST AUTHORITATIVE**
4. data_processing_architecture.md
5. s3_infrastructure_documentation.md (2025-07-03)
6. ACTUAL_S3_AWS_INFRASTRUCTURE.md (2025-07-03) - **PRODUCTION VERIFIED**
7. S3_BUCKET_STRUCTURE_CORRECTED.md (2025-06-14) - **SUPERSEDES ORIGINAL**
8. PodInsightHQ System Architecture Overview.md (June 2025)
9. AWS Network Optimization - Before:After Reference.md

---

## 🚨 Discrepancies Found

### 1. S3 File Structure
- **Original Documentation**: Simple paths like `transcripts/transcript.json`
- **Production Reality**: Complex naming like `transcripts/{feed}-{date}-{title}_{guid[:8]}_raw_transcript.json`
- **Resolution**: ✅ Use S3_BUCKET_STRUCTURE_CORRECTED.md patterns - NEVER hardcode file paths

### 2. Episode Count Inconsistencies
- **Various docs**: 1,171 episodes
- **Some references**: ~5,000 unique episodes
- **Chunks count**: 823,763 transcript chunks
- **Resolution**: ✅ 1,171 processed episodes creating 823,763 searchable chunks

### 3. MongoDB Field Naming
- **Issue**: `episode_id` field in chunks actually contains GUID value, not a separate ID
- **Collections**: `episode_metadata` uses `guid`, `transcript_chunks_768d` uses `episode_id`
- **Resolution**: ✅ Always join on `episode_metadata.guid = transcript_chunks_768d.episode_id`

### 4. Infrastructure Costs
- **Initial**: $240/month (Multi-AZ, NAT Gateway)
- **Optimized**: $17.52/month (Single-AZ, no NAT)
- **Resolution**: ✅ Current production uses optimized Single-AZ configuration

### 5. Modal.com Status
- **Confusion**: Some docs suggested deprecation
- **Reality**: Actively used for embeddings generation
- **Resolution**: ✅ Modal.com is production-critical for 768D embeddings

---

## ✅ Verified Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USERS (VCs, Founders)                           │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VERCEL EDGE NETWORK                                  │
│                    ┌─────────────────────────┐                              │
│                    │ Next.js 14 Dashboard     │                              │
│                    │ (podinsight-dashboard)   │                              │
│                    └────────────┬─────────────┘                              │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      VERCEL SERVERLESS (London - lhr1)                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ FastAPI Application (512MB RAM, 30s timeout)                        │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │ Endpoints:                                                          │    │
│  │ • /api/search (Vector search + AI synthesis)                       │    │
│  │ • /api/topic-velocity (Trending topics)                            │    │
│  │ • /api/entities (People & company tracking)                        │    │
│  │ • /api/v1/audio_clips/{id} (30-second clips)                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────────┐
            ▼                     ▼                         ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  MODAL.COM GPU    │ │  MONGODB ATLAS    │ │    SUPABASE       │
│  ─────────────    │ │  ─────────────    │ │  ────────────     │
│ • Instructor-XL   │ │ • 823,763 chunks  │ │ • Episodes meta   │
│ • 768D embeddings │ │ • Vector search   │ │ • 123k entities   │
│ • 2.1GB model     │ │ • $60/month M10   │ │ • User data       │
│ • ~415ms/query    │ │ • eu-west-2       │ │ • Free tier       │
└───────────────────┘ └───────────────────┘ └───────────────────┘

                      ┌───────────────────┐
                      │    AWS S3 (eu-west-2)                   │
                      ├───────────────────────────────────────┤
                      │ • pod-insights-raw (audio files)      │
                      │ • pod-insights-stage (processed)     │
                      │ • pod-insights-clips (30s clips)     │
                      │ • pod-insights-manifests             │
                      └───────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Version/Details | Purpose |
|-----------|------------|-----------------|---------|
| **Frontend** | Next.js | 14 (App Router) | React-based dashboard |
| **Styling** | Tailwind CSS | 3.x + shadcn/ui | Rapid UI development |
| **API Framework** | FastAPI | Python 3.9 | RESTful API |
| **API Hosting** | Vercel | Serverless Functions | Auto-scaling |
| **Vector Database** | MongoDB Atlas | M10 cluster | 768D vector search |
| **Relational DB** | Supabase | PostgreSQL 15 | Structured data |
| **ML/Embeddings** | Modal.com | GPU infrastructure | Instructor-XL model |
| **LLM** | OpenAI | GPT-4 | Answer synthesis |
| **Object Storage** | AWS S3 | 5 buckets | Media & data files |
| **Audio Processing** | AWS Lambda | Python/FFmpeg | Clip generation |

### Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Search Latency** | 3-5s warm | 14s cold start (Modal) |
| **Embedding Generation** | ~415ms | Warm Modal container |
| **Audio Clip Generation** | ~2.45s | 30-second clips |
| **API Response Time** | <500ms | Topic velocity endpoint |
| **Database Connections** | 10 max | MongoDB connection pool |
| **Monthly Uptime** | 99.9%+ | Vercel SLA |

---

## 📊 Infrastructure Details

### AWS Infrastructure (Optimized)

```yaml
Region: eu-west-2 (London)
VPC: 10.20.0.0/16 (podinsight-vpc)

# Single-AZ Deployment (Cost Optimized)
Public Subnet B: 10.20.12.0/24 (eu-west-2b)

# No NAT Gateway (92% cost reduction)
Internet Gateway: igw-05dbca6d970602b48

# S3 VPC Endpoints (free data transfer)
- vpce-0e12be12d3456789a (S3 gateway endpoint)

# Monthly Cost: $17.52 (down from $240)
```

### S3 Bucket Structure (PRODUCTION VERIFIED)

```
pod-insights-stage/
└── {feed-slug}/                          # e.g., "a16z-podcast"
    └── {episode-guid}/                   # Full UUID
        ├── cleaned_entities/             # NOT "entities/"
        │   └── {guid}_clean.json
        ├── embeddings/
        │   ├── {guid}.npy               # 384D (legacy)
        │   └── {guid}_768d_unfiltered.npy # 768D (current)
        ├── kpis/
        │   └── kpis_{guid}.json         # GUID in filename
        ├── meta/
        │   └── meta_{guid}_details.json # GUID in filename
        ├── segments/
        │   └── {guid}.json              # Word-level timing
        └── transcripts/
            └── {complex_filename}.json  # Dynamic discovery required

pod-insights-raw/
└── {feed-slug}/
    └── {guid}/
        └── audio/
            └── {feed}-{date}-{title}_{guid[:8]}_audio.mp3

pod-insights-clips/
└── {feed-slug}/
    └── {guid}/
        └── {start_ms}-{end_ms}.mp3     # e.g., "30000-60000.mp3"
```

### MongoDB Collections

| Collection | Document Count | Purpose | Key Fields |
|------------|----------------|---------|------------|
| **episode_metadata** | 1,236 | Episode details | guid, podcast_title |
| **episode_transcripts** | 1,171 | Full transcripts | episode_id (=guid), full_text |
| **transcript_chunks_768d** | 823,763 | Search chunks | episode_id (=guid), embedding_768d |
| **sentiment_results** | 62 | Sentiment analysis | topic, sentiment_score |

### API Endpoints (Complete List)

| Endpoint | Method | Purpose | Auth | Cache |
|----------|--------|---------|------|-------|
| `/` | GET | Health check | None | No |
| `/api/health` | GET | Detailed health | None | No |
| `/api/pool-stats` | GET | Connection stats | None | No |
| `/api/search` | POST | Semantic search | None | Client-side |
| `/api/topic-velocity` | GET | Topic trends | None | 5 min |
| `/api/entities` | GET | Entity tracking | None | 5 min |
| `/api/signals` | GET | Insights | None | 1 hour |
| `/api/v1/audio_clips/{id}` | GET | Audio clips | None | S3 cache |

---

## ❓ Needs Verification

1. **Exact Episode Count**: Discrepancy between 1,171 and ~5,000 episodes
2. **Podcast Feed Count**: Varies between 29, 30+, and 31 feeds
3. **Modal.com Costs**: Using $5,000 credits but actual monthly cost unclear
4. **Supabase Usage**: Free tier limits and actual data volume
5. **Special Episode ID Formats**: Full list of non-UUID formats (substack:, flightcast:, pod-)

---

## 🔐 Security Notes

### Resolved Issues
- ✅ MongoDB password rotated after git exposure (June 26, 2025)
- ✅ Git history cleaned with filter-repo
- ✅ Pre-commit hooks installed for secret scanning
- ✅ GitHub Actions secret scanning enabled

### Current Security Posture
- Environment variables properly isolated
- API endpoints public (no auth) - planned for Sprint 4
- S3 buckets private with IAM access
- Database connections use connection pooling
- CORS enabled on API (*) - needs tightening

---

## 📈 Scaling Considerations

### Current Limits
- Vercel: 512MB RAM, 30s timeout per function
- MongoDB: M10 cluster (2GB RAM, 2 vCPUs)
- Supabase: Free tier (500MB storage, 2GB transfer)
- Modal.com: Using startup credits

### Growth Path
1. MongoDB: Upgrade to M20 at 2M chunks
2. Supabase: Pro tier at 500MB storage
3. Vercel: Pro plan at 100GB bandwidth
4. Add Redis for caching at 10k DAU
5. Multi-region deployment at 50k users

---

## 🚀 Key Architectural Decisions

1. **Hybrid Infrastructure**: Vercel for API + Modal for ML (solves 512MB limit)
2. **Dual Database**: MongoDB for vectors + Supabase for relations
3. **On-Demand Audio**: Generate clips when requested vs pre-generate all
4. **Single-AZ AWS**: 92% cost reduction with acceptable risk
5. **Dynamic File Discovery**: Handles complex S3 naming patterns
6. **Instructor-XL Model**: 768D embeddings for better search quality

---

**Note**: This document consolidates information as of July 2025. The PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md (June 26, 2025) remains the most comprehensive single source, while S3_BUCKET_STRUCTURE_CORRECTED.md provides accurate file patterns.
