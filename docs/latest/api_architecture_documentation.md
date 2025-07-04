# PodInsightHQ API Architecture Documentation
**Created**: 2025-01-03  
**Purpose**: Complete API reference, infrastructure connections, and deployment architecture

## 📊 API Architecture Overview

### Technology Stack
- **Framework**: FastAPI (Python)
- **Deployment**: Vercel Serverless Functions
- **Region**: London (lhr1)
- **Databases**: MongoDB Atlas + Supabase
- **External Services**: Modal.com, AWS Lambda, OpenAI
- **Search**: MongoDB Vector Search (768D embeddings)

## 🔗 Complete API Endpoints

### Core Routes (via vercel.json rewrites)

| Route Pattern | Handler | Description |
|--------------|---------|-------------|
| `/api/diag/*` | `/api/diag.py` | Diagnostic endpoints |
| `/api/sentiment_analysis_v2` | `/api/sentiment_analysis_v2.py` | Sentiment analysis |
| `/api/test_audio` | `/api/test_audio.py` | Audio service test |
| `/api/hello` | `/api/hello.py` | Simple hello endpoint |
| `/api/*` | `/api/index.py` | All other API routes |

### 1. Health & Status Endpoints

#### GET `/`
**Purpose**: Main health check  
**Auth**: None  
**Response**:
```json
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

#### GET `/api/health`
**Purpose**: Monitoring health check  
**Auth**: None  
**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-03T12:00:00",
  "checks": {
    "huggingface_api_key": "configured",
    "database": "connected",
    "connection_pool": {...}
  },
  "version": "1.0.0"
}
```

#### GET `/api/pool-stats`
**Purpose**: Database connection pool statistics  
**Auth**: None  
**Response**:
```json
{
  "success": true,
  "stats": {
    "active_connections": 2,
    "max_connections": 10,
    "total_requests": 1542,
    "connection_errors": 0,
    "utilization_percent": 20.0
  },
  "timestamp": "2025-01-03T12:00:00"
}
```

### 2. Topic Intelligence Endpoints

#### GET `/api/topic-velocity`
**Purpose**: Track trending topics across podcasts  
**Auth**: None  
**Query Parameters**:
- `weeks` (int, default: 12): Number of weeks to return
- `topics` (string, optional): Comma-separated list of topics

**Request Example**:
```
GET /api/topic-velocity?weeks=8&topics=AI%20Agents,Crypto%2FWeb3
```

**Response Example**:
```json
{
  "data": {
    "AI Agents": [
      {
        "week": "2025-W01",
        "mentions": 45,
        "date": "Jan 1-7"
      }
    ],
    "Crypto/Web3": [...]
  },
  "metadata": {
    "total_episodes": 1171,
    "date_range": "2025-01-01 to 2025-06-14",
    "data_completeness": "topics_only"
  }
}
```

#### GET `/api/topics`
**Purpose**: List all available topics  
**Auth**: None  
**Response**:
```json
{
  "success": true,
  "topics": ["AI Agents", "B2B SaaS", "Capital Efficiency", "Crypto/Web3", "DePIN"],
  "count": 5
}
```

### 3. Search Endpoints

#### POST `/api/search`
**Purpose**: Natural language episode search with AI synthesis  
**Auth**: None (Rate limited: 20/minute per IP)  
**Request Body**:
```json
{
  "query": "What are VCs saying about AI agents?",
  "limit": 10,
  "offset": 0
}
```

**Response Example**:
```json
{
  "answer": {
    "text": "VCs are increasingly excited about AI agents...",
    "citations": [
      {
        "episode_id": "1216c2e7-42b8-42ca-92d7-bad784f80af2",
        "episode_title": "The Future of AI Agents",
        "podcast_name": "a16z Podcast",
        "published_date": "June 15, 2025",
        "timestamp": {"start": 120.5, "end": 180.3}
      }
    ]
  },
  "results": [
    {
      "episode_id": "1216c2e7-42b8-42ca-92d7-bad784f80af2",
      "podcast_name": "a16z Podcast",
      "episode_title": "The Future of AI Agents",
      "published_at": "2025-06-15T10:00:00Z",
      "published_date": "June 15, 2025",
      "similarity_score": 0.892,
      "excerpt": "**AI agents** are becoming increasingly sophisticated...",
      "word_count": 12500,
      "duration_seconds": 3600,
      "topics": ["AI Agents", "Automation"],
      "s3_audio_path": "s3://pod-insights-raw/...",
      "timestamp": {"start_time": 120.5, "end_time": 180.3}
    }
  ],
  "total_results": 42,
  "cache_hit": false,
  "search_id": "abc123",
  "query": "What are VCs saying about AI agents?",
  "limit": 10,
  "offset": 0,
  "search_method": "vector_768d",
  "processing_time_ms": 245
}
```

### 4. Entity Tracking Endpoints

#### GET `/api/entities`
**Purpose**: Track people and companies mentioned  
**Auth**: None  
**Query Parameters**:
- `search` (string): Fuzzy match entity names
- `type` (string): Filter by PERSON, ORG, GPE, MONEY
- `limit` (int, default: 20, max: 100)
- `timeframe` (string): e.g., "30d", "90d"

**Request Example**:
```
GET /api/entities?search=OpenAI&type=ORG&limit=5
```

**Response Example**:
```json
{
  "success": true,
  "entities": [
    {
      "name": "OpenAI",
      "type": "ORG",
      "mention_count": 234,
      "episode_count": 89,
      "trend": "up",
      "recent_mentions": [
        {
          "episode_title": "All-In Podcast - 65 min (Jun 12, 2025)",
          "date": "June 12, 2025",
          "context": "Mentioned in All-In Podcast - 65 min (Jun 12, 2025)"
        }
      ]
    }
  ],
  "total_entities": 1,
  "filters": {
    "search": "OpenAI",
    "type": "ORG",
    "timeframe": null,
    "limit": 5
  }
}
```

### 5. Signal Detection Endpoints

#### GET `/api/signals`
**Purpose**: Pre-computed insights for dashboard  
**Auth**: None  
**Query Parameters**:
- `signal_type` (string): 'correlation', 'spike', 'trending_combo'
- `limit` (int, default: 10)

**Response Example**:
```json
{
  "signals": {
    "correlation": [
      {
        "topics": ["AI Agents", "Capital Efficiency"],
        "co_occurrence_percent": 45,
        "episode_count": 23
      }
    ],
    "spike": [
      {
        "topic": "DePIN",
        "spike_factor": 3.5,
        "current_week_mentions": 28
      }
    ]
  },
  "signal_messages": [
    "AI Agents + Capital Efficiency appear together in 45% of episodes (23 co-occurrences)",
    "DePIN exploding with 3.5x normal activity (28 mentions this week)"
  ],
  "last_updated": "2025-01-03T10:00:00Z"
}
```

### 6. Audio Generation Endpoints

#### GET `/api/v1/audio_clips/{episode_id}`
**Purpose**: Generate audio clips on-demand  
**Auth**: None  
**Path Parameters**:
- `episode_id`: GUID, ObjectId, or special format (substack:xxx)

**Query Parameters**:
- `start_time_ms` (int, required): Start time in milliseconds
- `duration_ms` (int, default: 30000): Duration (max 60000)

**Request Example**:
```
GET /api/v1/audio_clips/1216c2e7-42b8-42ca-92d7-bad784f80af2?start_time_ms=120000&duration_ms=30000
```

**Response Example**:
```json
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

### 7. Sentiment Analysis Endpoints

#### GET `/api/sentiment_analysis_v2`
**Purpose**: Pre-computed sentiment data  
**Auth**: None  
**Query Parameters**:
- `weeks` (int, default: 12)
- `topics` (array): Topics to analyze

**Response Example**:
```json
{
  "success": true,
  "data": [
    {
      "topic": "AI Agents",
      "week_key": "2025-W01",
      "positive": 15,
      "negative": 3,
      "neutral": 8,
      "total_mentions": 26,
      "sentiment_score": 0.73
    }
  ],
  "metadata": {
    "weeks": 12,
    "topics": ["AI Agents"],
    "generated_at": "2025-01-03T12:00:00Z",
    "source": "pre_computed_batch",
    "api_version": "v2"
  }
}
```

### 8. Debug Endpoints

#### GET `/api/debug/mongodb`
**Purpose**: Test MongoDB connection and search  
**Auth**: None  
**Response**:
```json
{
  "status": "success",
  "mongodb_uri_set": true,
  "connection": "connected",
  "database_name": "podinsight",
  "collection_name": "transcripts",
  "test_searches": {
    "bitcoin": {"count": 1, "score": 0.95, "has_highlights": true},
    "AI": {"count": 1, "score": 0.89, "has_highlights": true}
  }
}
```

## 🏗️ Infrastructure Connections

### 1. MongoDB Connection

**Location**: `/api/mongodb_vector_search.py`
```python
class MongoVectorSearchHandler:
    def _get_collection(self):
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DATABASE", "podinsight")
        
        loop_id = id(asyncio.get_running_loop())
        client = MongoVectorSearchHandler._client_per_loop.get(loop_id)
        
        if client is None:
            client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=10,
                retryWrites=True
            )
            MongoVectorSearchHandler._client_per_loop[loop_id] = client
        
        db = client[db_name]
        return db["transcript_chunks_768d"]
```

**Collections Used**:
- `episode_metadata`: Episode information
- `episode_transcripts`: Full transcripts
- `transcript_chunks_768d`: Vector embeddings
- `sentiment_results`: Pre-computed sentiment

### 2. Supabase Connection

**Location**: `/api/database.py`
```python
class SupabasePool:
    def _create_client(self) -> Client:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
        return create_client(url, key)
    
    @asynccontextmanager
    async def acquire(self):
        async with self.semaphore:
            self.active_connections += 1
            try:
                yield self.client
            finally:
                self.active_connections -= 1
```

**Tables Used**:
- `episodes`: Episode metadata
- `topic_mentions`: Topic tracking
- `topic_signals`: Pre-computed signals
- `extracted_entities`: Named entities

### 3. Modal.com Connection

**Location**: `/lib/embeddings_768d_modal.py`
```python
class ModalInstructorXLEmbedder:
    def __init__(self):
        self.modal_url = os.getenv('MODAL_EMBEDDING_URL', 
            'https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run')
    
    async def _encode_query_async(self, query: str) -> Optional[List[float]]:
        async with aiohttp.ClientSession() as session:
            payload = {"text": query}
            async with session.post(
                self.modal_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=25)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("embedding", data)
```

**Purpose**: Generate 768-dimensional embeddings for search queries

### 4. AWS Lambda Connection (Audio)

**Location**: `/api/audio_clips.py`
```python
LAMBDA_FUNCTION_URL = os.environ.get("AUDIO_LAMBDA_URL")
LAMBDA_API_KEY = os.environ.get("AUDIO_LAMBDA_API_KEY")

lambda_payload = {
    "feed_slug": feed_slug,
    "guid": guid,
    "start_time_ms": start_time_ms,
    "duration_ms": duration_ms
}

headers = {
    "Content-Type": "application/json",
    "X-API-Key": LAMBDA_API_KEY
}

async with httpx.AsyncClient() as client:
    response = await client.post(
        LAMBDA_FUNCTION_URL,
        json=lambda_payload,
        headers=headers,
        timeout=55.0
    )
```

**Purpose**: Generate audio clips using FFmpeg in AWS Lambda

### 5. S3 Integration

**Pre-signed URLs**: Generated by AWS Lambda for audio clips
```python
# Lambda returns pre-signed URL
{
    "clip_url": "https://pod-insights-clips.s3.amazonaws.com/...",
    "expires_at": "2025-01-03T13:00:00Z"
}
```

**S3 Buckets**:
- `pod-insights-raw`: Raw audio files
- `pod-insights-stage`: Processed data
- `pod-insights-clips`: Generated clips (temp)

## 🔌 External Service Integrations

### 1. OpenAI Integration

**Location**: `/api/synthesis.py`
```python
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ],
    max_tokens=500,
    temperature=0.7
)
```

**Used By**: `/api/search` endpoint for answer synthesis

### 2. Modal.com Endpoints

**Embedding Service**:
- URL: `https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run`
- Method: POST
- Input: `{"text": "query string"}`
- Output: `{"embedding": [768 floats]}`
- Used by: Search functionality

### 3. AWS Lambda Functions

**Audio Clip Generator**:
- URL: Set via `AUDIO_LAMBDA_URL` env var
- Auth: API Key via `X-API-Key` header
- Purpose: FFmpeg-based audio processing
- Returns: S3 pre-signed URLs

## 🚀 Deployment Architecture

### Vercel Configuration

**vercel.json**:
```json
{
  "regions": ["lhr1"],
  "functions": {
    "api/index.py": {
      "memory": 1024,
      "maxDuration": 30
    }
  },
  "env": {
    "PYTHONPATH": "."
  },
  "rewrites": [
    {"source": "/api/diag", "destination": "/api/diag"},
    {"source": "/api/sentiment_analysis_v2", "destination": "/api/sentiment_analysis_v2"},
    {"source": "/api/test_audio", "destination": "/api/test_audio"},
    {"source": "/api/hello", "destination": "/api/hello"},
    {"source": "/api/(.*)", "destination": "/api/index"}
  ]
}
```

### Environment Variables

**Required**:
```bash
# Database
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=podinsight
SUPABASE_URL=https://...supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# External Services
OPENAI_API_KEY=sk-proj-...
HUGGINGFACE_API_KEY=hf_...
MODAL_EMBEDDING_URL=https://...modal.run
AUDIO_LAMBDA_URL=https://...amazonaws.com/
AUDIO_LAMBDA_API_KEY=...

# AWS (auto-loaded from ~/.aws/)
# S3_BUCKET_STAGE=pod-insights-stage
# S3_BUCKET_RAW=pod-insights-raw

# Optional
DEBUG_MODE=false
ANSWER_SYNTHESIS_ENABLED=true
```

### Function Types

**Serverless Functions** (via Vercel):
- All API endpoints run as serverless functions
- 30-second timeout limit
- 1024MB memory allocation
- Auto-scaling based on demand

**Edge Functions**: Not currently used

**Background Jobs**:
- Sentiment analysis: Nightly batch via separate script
- No real-time background processing

## 📊 API Reference Table

| Endpoint | Method | Purpose | Auth | Rate Limit |
|----------|--------|---------|------|------------|
| `/` | GET | Health check | None | None |
| `/api/health` | GET | Monitoring health | None | None |
| `/api/pool-stats` | GET | Connection pool stats | None | None |
| `/api/topic-velocity` | GET | Trending topics data | None | None |
| `/api/topics` | GET | List available topics | None | None |
| `/api/search` | POST | Natural language search | None | 20/min |
| `/api/entities` | GET | Entity tracking | None | None |
| `/api/signals` | GET | Pre-computed insights | None | None |
| `/api/v1/audio_clips/{id}` | GET | Generate audio clips | None | None |
| `/api/sentiment_analysis_v2` | GET | Sentiment data | None | None |
| `/api/debug/mongodb` | GET | MongoDB diagnostics | None | None |

## 🔒 Security Considerations

1. **No Authentication**: All endpoints are public
2. **Rate Limiting**: Only on `/api/search` (20/min per IP)
3. **Environment Variables**: Stored securely in Vercel
4. **Database Access**: Service role keys for full access
5. **CORS**: Enabled for all origins (`*`)
6. **Input Validation**: Via Pydantic models
7. **SQL Injection**: Protected by ORMs
8. **Secrets**: Never logged or exposed in responses

## 📈 Performance Optimizations

1. **Connection Pooling**: Reuse database connections
2. **Query Caching**: 5-minute TTL for search results
3. **Vector Index**: MongoDB Atlas Search for fast similarity
4. **Pre-computed Data**: Sentiment and signals batch processed
5. **CDN**: Audio clips served via S3/CloudFront
6. **Regional Deployment**: London region for EU users

---

**Note**: This documentation reflects the API state as of 2025-01-03. Regular updates recommended as the API evolves.