# Vercel API Functions Guide - PodInsightHQ

## Overview

This document provides a comprehensive overview of all API functions deployed on Vercel for the PodInsightHQ project. Currently, we have 10 serverless functions running within Vercel's Hobby plan limit of 12 functions.

---

## Function Directory Structure

```
api/
├── index.py              # Main API router and composition root
├── audio_clips.py        # Audio clip generation endpoint
├── database.py           # Database connection utilities
├── diag.py              # Diagnostics and health checks
├── mongodb_search.py     # MongoDB text search handler
├── mongodb_vector_search.py  # Vector search implementation
├── search_lightweight_768d.py # Main search endpoint
├── sentiment_analysis_v2.py   # Sentiment analysis service
├── synthesis.py          # OpenAI answer synthesis
└── topic_velocity.py     # Topic velocity calculations

lib/                      # Utility modules (not deployed as functions)
├── __init__.py
├── embedding_utils.py
├── embeddings_768d_modal.py
└── sentiment_analysis.py (old version)
```

---

## Detailed Function Documentation

### 1. **index.py** - Main API Router
- **Purpose**: Central composition root that mounts all API routes
- **Endpoints**: None directly (acts as a router)
- **Key Features**:
  - Mounts audio_clips router at `/api/v1/audio_clips`
  - Mounts topic_velocity app as catch-all
  - Handles CORS configuration
  - Main entry point for Vercel
- **Dependencies**: FastAPI, all other API modules
- **Critical**: YES - Required for all API functionality

### 2. **audio_clips.py** - Audio Clip Generation (Sprint 3)
- **Purpose**: Generate on-demand 30-second audio clips from podcasts
- **Endpoints**:
  - `GET /api/v1/audio_clips/{episode_id}` - Generate/retrieve audio clip
  - `GET /api/v1/audio_clips/health` - Health check
- **Key Features**:
  - MongoDB lookup for episode metadata
  - Lambda function integration
  - Pre-signed URL generation
  - S3 caching logic
- **External Services**: AWS Lambda, S3, MongoDB
- **Response Time**: <200ms (cache hit), 2-3s (cache miss)

### 3. **database.py** - Database Connection Pool
- **Purpose**: Manages PostgreSQL connection pooling
- **Endpoints**: None (utility module)
- **Key Features**:
  - AsyncPG connection pool management
  - Connection string parsing
  - Health check support
  - Graceful connection handling
- **Configuration**: Uses `POSTGRES_CONNECTION_STRING` env var
- **Used By**: search_lightweight_768d.py, topic_velocity.py

### 4. **diag.py** - Diagnostics Endpoint
- **Purpose**: System diagnostics and debugging information
- **Endpoints**:
  - `GET /api/diag` - Basic diagnostics
  - `GET /api/diag/{path}` - Extended diagnostics
- **Key Features**:
  - Environment variable inspection
  - System health checks
  - Debug information exposure
  - Request/response logging
- **Security Note**: Should be restricted in production

### 5. **mongodb_search.py** - MongoDB Text Search
- **Purpose**: Traditional text-based search functionality
- **Endpoints**: None (handler module)
- **Key Features**:
  - Text index search
  - Relevance scoring
  - Metadata enrichment
  - Fallback for vector search
- **Database**: MongoDB `transcript_chunks_768d` collection
- **Used By**: search_lightweight_768d.py

### 6. **mongodb_vector_search.py** - Vector Search Implementation
- **Purpose**: Semantic search using vector embeddings
- **Endpoints**: None (handler module)
- **Key Features**:
  - 768-dimensional vector search
  - Cosine similarity matching
  - Hybrid search capabilities
  - Chunk expansion for context
- **Database**: MongoDB Atlas Vector Search
- **Performance**: ~150ms average query time

### 7. **search_lightweight_768d.py** - Main Search Endpoint
- **Purpose**: Primary search API with AI synthesis
- **Endpoints**:
  - `POST /api/search` - Main search endpoint
- **Key Features**:
  - Vector + text search hybrid
  - OpenAI answer synthesis
  - Citation formatting
  - Chunk deduplication
  - Performance tracking
- **Response Format**:
  ```json
  {
    "results": [...],
    "answer": {
      "text": "AI-generated summary",
      "citations": [...]
    },
    "search_time_ms": 150,
    "synthesis_time_ms": 1500
  }
  ```

### 8. **sentiment_analysis_v2.py** - Sentiment Analysis Service
- **Purpose**: Analyze sentiment trends in podcast content
- **Endpoints**:
  - `POST /api/sentiment_analysis_v2` - Analyze sentiment
- **Key Features**:
  - Time-series sentiment analysis
  - Multi-topic tracking
  - Aggregate statistics
  - Visualization data preparation
- **Database**: MongoDB aggregation pipelines
- **Use Case**: Dashboard charts and insights

### 9. **synthesis.py** - OpenAI Answer Synthesis
- **Purpose**: Generate AI summaries for search results
- **Endpoints**: None (utility module)
- **Key Features**:
  - GPT-4o-mini integration
  - Citation parsing and formatting
  - Retry logic with exponential backoff
  - Error handling and fallbacks
- **Cost**: ~$0.001 per synthesis
- **Performance**: 1.5-2.5s average

### 10. **topic_velocity.py** - Topic Velocity Calculations
- **Purpose**: Track topic popularity and trends over time
- **Endpoints**:
  - `GET /api/topic_velocity` - Get velocity data
  - `POST /api/search` - Legacy search endpoint
  - `GET /api/health` - Health check
  - Multiple other utility endpoints
- **Key Features**:
  - Topic frequency analysis
  - Time-based aggregations
  - Trend calculations
  - Multi-topic comparisons
- **Database**: PostgreSQL time-series queries

---

## Environment Variables Required

```bash
# Database Connections
POSTGRES_CONNECTION_STRING=postgresql://...
MONGODB_URI=mongodb+srv://...

# AWS Configuration (for audio clips)
AUDIO_LAMBDA_URL=https://...lambda-url.eu-west-2.on.aws/
AUDIO_LAMBDA_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-west-2

# OpenAI (for synthesis)
OPENAI_API_KEY=sk-...
ANSWER_SYNTHESIS_ENABLED=true

# Feature Flags
ENABLE_VECTOR_SEARCH=true
```

---

## API Flow Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  index.py   │──── Main Router
└──────┬──────┘
       │
       ├────────────────────────────────┐
       │                                │
       ▼                                ▼
┌─────────────────┐           ┌──────────────────┐
│ audio_clips.py  │           │ topic_velocity.py│
│  /api/v1/audio  │           │   (catch-all)    │
└────────┬────────┘           └────────┬─────────┘
         │                             │
         ▼                             ▼
    ┌─────────┐                 ┌─────────────┐
    │ Lambda  │                 │   Search    │
    │   S3    │                 │  Synthesis  │
    └─────────┘                 └─────────────┘
```

---

## Function Limits and Optimization

### Current Usage: 10/12 functions

### Optimization Strategies Applied:
1. **Moved utilities to lib/**:
   - embedding_utils.py
   - embeddings_768d_modal.py
   - Old sentiment_analysis.py

2. **Consolidated routes**:
   - All routes through index.py
   - Shared database connections
   - Reusable utility functions

### Future Optimization Options:
1. **Combine similar functions**:
   - Merge mongodb_search.py and mongodb_vector_search.py
   - Consolidate database utilities

2. **External services**:
   - Move heavy processing to AWS Lambda
   - Use Modal for embedding generation
   - Consider edge functions for caching

---

## Performance Characteristics

| Function | Cold Start | Warm Response | Memory Usage |
|----------|------------|---------------|--------------|
| index.py | 2-3s | <50ms | 256MB |
| audio_clips.py | 1-2s | 200ms | 256MB |
| search_lightweight_768d.py | 3-4s | 150-2000ms | 512MB |
| topic_velocity.py | 2-3s | 100-500ms | 512MB |
| sentiment_analysis_v2.py | 2-3s | 300-1000ms | 512MB |

---

## Monitoring and Debugging

### Key Metrics to Track:
1. **Function invocations** - Via Vercel dashboard
2. **Response times** - CloudWatch for Lambda, Vercel logs for API
3. **Error rates** - 4xx vs 5xx errors
4. **Cold start frequency** - Impacts user experience
5. **Memory usage** - Avoid OOM errors

### Debugging Tools:
- `/api/diag` - System diagnostics
- Vercel logs - Real-time function logs
- CloudWatch - Lambda execution logs
- MongoDB Atlas - Database performance

---

## Security Considerations

1. **API Keys**:
   - Lambda API key for audio generation
   - OpenAI key for synthesis
   - Never exposed in client code

2. **Input Validation**:
   - All endpoints validate inputs
   - SQL injection prevention
   - MongoDB injection prevention

3. **Rate Limiting**:
   - Currently not implemented
   - Recommended for production

4. **CORS Configuration**:
   - Configured in index.py
   - Adjust for production domains

---

## Deployment Checklist

1. **Environment Variables**:
   - [ ] All required vars set in Vercel
   - [ ] Secrets properly configured
   - [ ] Feature flags set correctly

2. **Database Connectivity**:
   - [ ] PostgreSQL connection string valid
   - [ ] MongoDB URI accessible
   - [ ] Indexes created and optimized

3. **External Services**:
   - [ ] AWS Lambda deployed and accessible
   - [ ] S3 buckets configured with proper permissions
   - [ ] OpenAI API key has sufficient credits

4. **Function Count**:
   - [ ] Under 12 function limit
   - [ ] No unnecessary files in api/

5. **Testing**:
   - [ ] Health endpoints responding
   - [ ] Search functionality working
   - [ ] Audio generation tested
   - [ ] Synthesis enabled and working

---

## Common Issues and Solutions

### Issue 1: Function Count Exceeded
**Solution**: Move utility files to lib/ directory

### Issue 2: Cold Start Timeouts
**Solution**: Implement warmup endpoints or use Vercel Pro for longer timeouts

### Issue 3: MongoDB Connection Errors
**Solution**: Check IP whitelist in MongoDB Atlas

### Issue 4: Lambda Timeout
**Solution**: Increase Lambda timeout or optimize FFmpeg processing

### Issue 5: Memory Errors
**Solution**: Increase function memory in vercel.json

---

## Future Roadmap

1. **Phase 1**: Current Implementation ✓
   - Basic search functionality
   - Audio clip generation
   - AI synthesis

2. **Phase 2**: Optimization
   - Add Redis caching layer
   - Implement rate limiting
   - Optimize cold starts

3. **Phase 3**: Enhanced Features
   - Real-time transcription
   - Multi-language support
   - Advanced analytics

4. **Phase 4**: Scale
   - Move to Vercel Pro/Enterprise
   - Implement edge functions
   - Global CDN for audio

---

**Document Version**: 1.0
**Last Updated**: December 30, 2024
**Maintained By**: PodInsightHQ Engineering Team
