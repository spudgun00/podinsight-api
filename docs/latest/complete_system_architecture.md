# PodInsightHQ Complete System Architecture
**Created**: 2025-01-03  
**Purpose**: Comprehensive system architecture, user journeys, service interactions, and performance analysis

## 📊 System Overview

PodInsightHQ is a serverless podcast intelligence platform that processes 1,000+ hours of startup/VC podcast content into actionable insights. The system uses modern cloud services for scalability and cost efficiency.

### Key Technologies
- **Frontend**: Next.js on Vercel
- **API**: FastAPI on Vercel Serverless Functions
- **ML/AI**: Modal.com (embeddings), OpenAI (synthesis)
- **Storage**: MongoDB Atlas (vector search), Supabase (structured data), S3 (media)
- **Processing**: AWS Lambda (audio clips)

## 🏗️ Complete Architecture Diagram

```mermaid
graph TB
  subgraph "Frontend (Vercel)"
    A[Next.js Dashboard]
    B[Episode Intelligence UI]
    C[Topic Velocity Charts]
    D[Search Interface]
  end
  
  subgraph "API Layer (Vercel Serverless)"
    E[FastAPI Main App<br/>30s timeout, 1024MB]
    F[Rate Limiter<br/>Redis, 20/min]
    G[CORS Middleware<br/>Allow: *]
    H[Connection Pool<br/>MongoDB: 10 max]
  end
  
  subgraph "API Endpoints"
    I[/api/search<br/>Natural Language]
    J[/api/topic-velocity<br/>Trending Topics]
    K[/api/entities<br/>People & Companies]
    L[/api/signals<br/>Pre-computed Insights]
    M[/api/v1/audio_clips<br/>Clip Generation]
  end
  
  subgraph "ML/AI Services"
    N[Modal.com<br/>768D Embeddings<br/>~$0.0001/req]
    O[OpenAI API<br/>GPT-4 Synthesis<br/>~$0.01/req]
    P[Hugging Face<br/>384D Fallback<br/>Free tier]
  end
  
  subgraph "Processing (AWS)"
    Q[Lambda Functions<br/>Audio Processing<br/>~$0.0002/clip]
    R[FFmpeg<br/>Clip Generation]
    S[S3 Buckets<br/>Audio Storage]
  end
  
  subgraph "Storage Layer"
    T[MongoDB Atlas<br/>Vector Search<br/>823K chunks]
    U[Supabase<br/>Structured Data<br/>1,171 episodes]
    V[Redis<br/>Rate Limiting<br/>Search Cache]
  end
  
  %% Frontend to API connections
  A --> E
  B --> E
  C --> E
  D --> E
  
  %% API middleware flow
  E --> F
  F --> G
  G --> H
  H --> I
  H --> J
  H --> K
  H --> L
  H --> M
  
  %% Search flow
  I --> N
  N --> T
  T --> O
  
  %% Fallback search flow
  I -.-> P
  P -.-> U
  
  %% Audio flow
  M --> Q
  Q --> R
  R --> S
  
  %% Data access patterns
  J --> U
  K --> U
  L --> T
  L --> U
  
  %% Cache layer
  I --> V
  V --> I
  
  style A fill:#e1f5fe
  style B fill:#e1f5fe
  style C fill:#e1f5fe
  style D fill:#e1f5fe
  style E fill:#fff3e0
  style N fill:#f3e5f5
  style O fill:#f3e5f5
  style Q fill:#e8f5e9
  style T fill:#fce4ec
  style U fill:#fce4ec
```

## 🚀 Complete User Journey: Search for "AI valuations"

### Step-by-Step Flow (Total: 5-7 seconds)

#### 1. **User Input** (0ms)
- User types "What are VCs saying about AI valuations?"
- Frontend sends POST to `/api/search`
- Request payload:
```json
{
  "query": "What are VCs saying about AI valuations?",
  "limit": 10,
  "offset": 0
}
```

#### 2. **Rate Limit Check** (5-10ms)
- Redis checks IP-based rate limit (20/min)
- Key: `rate_limit:{ip_address}:search`
- If exceeded, returns 429 error

#### 3. **Embedding Generation** (1-2s, cold: 3-5s)
- Call Modal.com embedding service
- URL: `https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run`
- Generate 768-dimensional vector
- Cost: ~$0.0001
- Cold start includes model loading

#### 4. **MongoDB Vector Search** (200-500ms)
- Search 823K transcript chunks
- Uses Atlas Search vector index
- Query:
```javascript
{
  "index": "vector_index",
  "path": "embedding_768d",
  "queryVector": [768 floats],
  "numCandidates": 100,
  "limit": 10
}
```
- Returns top 10 relevant chunks with scores

#### 5. **Result Processing** (50ms)
- Deduplicate chunks (max 2 per episode)
- Format results with timestamps
- Add episode metadata from `episode_metadata` collection
- Convert timestamps to human-readable format

#### 6. **OpenAI Synthesis** (2-3s)
- Send top chunks to GPT-4
- System prompt for 2-sentence summary
- Generate superscript citations
- Cost: ~$0.01
- Model: `gpt-4o-mini`

#### 7. **Response Caching** (10ms)
- Store in Redis with 5-min TTL
- Key: SHA256 hash of query + params
- Prevents duplicate API calls

#### 8. **Return Response** (50ms)
- Format JSON response
- Include answer, citations, and metadata
- Total response size: ~5-10KB

### Response Example:
```json
{
  "answer": {
    "text": "VCs are increasingly cautious about AI valuations, with many noting that the market has become overheated¹². Several prominent investors suggest waiting for more reasonable entry points as the hype cycle cools³.",
    "citations": [
      {
        "episode_id": "abc123",
        "episode_title": "AI Market Dynamics",
        "podcast_name": "All-In Podcast",
        "timestamp": "15:23"
      }
    ]
  },
  "results": [...],
  "processing_time_ms": 3245
}
```

## 🔄 Backend Service Interactions

### Service Dependency Matrix

| Service | Purpose | When Called | Latency | Cost |
|---------|---------|-------------|---------|------|
| **Modal.com** | 768D embeddings | Every search query | 1-2s (warm), 3-5s (cold) | ~$0.0001/req |
| **OpenAI** | Answer synthesis | When synthesis enabled | 2-3s | ~$0.01/req |
| **MongoDB** | Vector/text search | All searches | 200-500ms | Data transfer |
| **Supabase** | Pre-computed data | Topics, entities | 50-100ms | Free tier |
| **AWS Lambda** | Audio processing | Clip requests | 2-4s | ~$0.0002/clip |
| **Redis** | Rate limiting, cache | Every request | 5-10ms | Included |

### Detailed Service Flows

#### Modal.com Embedding Service
```python
# Request flow
POST https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run
Content-Type: application/json

{
  "text": "What are VCs saying about AI valuations?"
}

# Response
{
  "embedding": [0.024, -0.154, ...] # 768 floats
}
```

#### OpenAI Synthesis
```python
# Lazy client initialization
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Synthesis request
response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": SYNTHESIS_PROMPT},
        {"role": "user", "content": formatted_chunks}
    ],
    max_tokens=500,
    temperature=0.7
)
```

#### MongoDB Vector Search
```python
# Connection with pooling
client = AsyncIOMotorClient(
    MONGODB_URI,
    maxPoolSize=10,
    serverSelectionTimeoutMS=10000
)

# Vector search pipeline
pipeline = [
    {
        "$vectorSearch": {
            "index": "vector_index",
            "path": "embedding_768d",
            "queryVector": embedding,
            "numCandidates": 100,
            "limit": limit
        }
    }
]
```

#### S3 Pre-signed URL Generation
1. Frontend requests: `GET /api/v1/audio_clips/{episode_id}?start_time_ms=120000&duration_ms=30000`
2. API validates episode ID (GUID, ObjectId, or special format)
3. Lambda invoked with parameters:
```json
{
  "feed_slug": "a16z-podcast",
  "guid": "abc-123-def",
  "start_time_ms": 120000,
  "duration_ms": 30000
}
```
4. Lambda processes with FFmpeg
5. Uploads to S3: `s3://pod-insights-clips/temp/clip_abc123.mp3`
6. Generates pre-signed URL (1hr expiry)
7. Returns to frontend

## 💰 Cost Analysis

### Per-Operation Costs

| Operation | Service | Cost | Monthly (1K users) |
|-----------|---------|------|-------------------|
| Search query | Modal.com | $0.0001 | $100 |
| Answer synthesis | OpenAI GPT-4 | $0.01 | $10,000 |
| Audio clip | AWS Lambda | $0.0002 | $200 |
| Data transfer | MongoDB | Variable | ~$50 |
| Hosting | Vercel Pro | Fixed | $20 |

### Cost Optimization Strategies
1. **Disable synthesis for basic searches**: Save $0.01/query
2. **Cache popular queries**: Reduce Modal/OpenAI calls by 30%
3. **Batch process embeddings**: Reduce Modal costs
4. **Use GPT-3.5 for synthesis**: 10x cost reduction
5. **Implement user authentication**: Control usage

### Current Free Tier Usage
- Hugging Face: 30K requests/month
- Supabase: 500MB database, 2GB transfer
- S3: 5GB storage, 20K requests
- Vercel: 100GB bandwidth

## 📈 Performance Characteristics

### Response Time Breakdown

| Component | Cold Start | Warm | Optimization |
|-----------|------------|------|--------------|
| API Init | 1-2s | 0ms | Pre-warm functions |
| Modal Embedding | 3-5s | 1-2s | Cache common queries |
| MongoDB Search | 500ms-1s | 200-500ms | Optimize indexes |
| OpenAI Synthesis | 2-3s | 2-3s | Use streaming |
| Total Search | 5-7s | 3-4s | Target: <3s |

### Scaling Profile

#### Current Limits
- **Concurrent requests**: ~100 (Vercel limit)
- **MongoDB connections**: 10 (pool size)
- **Rate limit**: 20 searches/min/IP
- **Function timeout**: 30 seconds
- **Memory**: 1024MB per function

#### Bottlenecks Identified
1. **Modal cold starts**: Biggest latency contributor
   - Solution: Implement keep-warm strategy
2. **OpenAI synthesis**: Unavoidable 2-3s
   - Solution: Stream responses, show results first
3. **MongoDB connection pool**: Limited to 10
   - Solution: Increase pool size, add read replicas
4. **Single region**: London only
   - Solution: Multi-region deployment

### Performance Optimizations

#### Implemented
- Connection pooling for MongoDB
- Redis caching (5-min TTL)
- Vector indexing for fast search
- Pre-computed topic/sentiment data
- Async request handling

#### Recommended
1. **Edge caching**: Use Vercel Edge Network
2. **Request coalescing**: Batch similar queries
3. **Progressive loading**: Stream results as available
4. **Background warming**: Keep functions warm
5. **CDN for audio**: CloudFront for global delivery

## 🔒 Security Considerations

### Current State
- ❌ No authentication on any endpoint
- ❌ CORS allows all origins (`*`)
- ✅ Rate limiting prevents abuse
- ✅ Environment variables properly secured
- ✅ Input validation with Pydantic
- ❌ No API key management

### Recommended Improvements
1. Implement JWT authentication
2. Restrict CORS to known domains
3. Add API key management
4. Implement request signing
5. Add audit logging
6. Enable DDoS protection

## 📊 Monitoring & Observability

### Current Monitoring
- Basic health checks at `/api/health`
- Connection pool stats at `/api/pool-stats`
- Error logging to Vercel logs

### Recommended Additions
1. **APM Integration**: DataDog or New Relic
2. **Custom Metrics**:
   - Search latency percentiles
   - Cache hit rates
   - Error rates by endpoint
   - Cost per user
3. **Alerts**:
   - High error rates
   - Slow response times
   - Cost anomalies
   - Connection pool exhaustion

## 🚦 Deployment Pipeline

### Current Process
1. Push to GitHub
2. Vercel auto-deploys from main branch
3. Environment variables from Vercel dashboard
4. No staging environment

### Recommended Improvements
1. Add staging environment
2. Implement blue-green deployments
3. Add integration tests
4. Automated performance testing
5. Rollback capabilities

## 📈 Future Architecture Considerations

### Short-term (3 months)
1. Add authentication layer
2. Implement multi-region deployment
3. Add WebSocket support for real-time updates
4. Optimize cold starts
5. Add GraphQL API option

### Medium-term (6 months)
1. Kubernetes deployment option
2. Self-hosted embedding models
3. Real-time transcription pipeline
4. Advanced caching strategies
5. Multi-language support

### Long-term (12 months)
1. Edge computing for embeddings
2. Federated search across sources
3. Custom AI models
4. Enterprise features
5. White-label platform

---

**Note**: This architecture documentation reflects the system state as of 2025-01-03. Regular updates recommended as the platform evolves.