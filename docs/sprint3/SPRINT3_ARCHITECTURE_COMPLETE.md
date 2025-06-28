# Sprint 3 Architecture Documentation - Command Bar Features

## Overview
This document serves as the single source of truth for PodInsightHQ's Sprint 3 features, encompassing the on-demand audio clip generation system (Phase 1A - deployed) and the answer synthesis pipeline (Phase 1B - to be implemented).

## Key Architectural Decisions
- **On-demand Audio Generation**: Saves $10K/year by avoiding 60-80% duplicate clips
- **Lambda for Audio Processing**: Keeps main API lightweight and scalable
- **30-second Clips**: Centered on chunk timestamps for optimal context
- **10-chunk Context Window**: ~1000 tokens for comprehensive answer synthesis

## Complete System Architecture

### 1. Data Flow Diagram

```mermaid
graph TD
    subgraph User Interaction
        A[User] -- 1. Search Query --> B(API Gateway)
    end

    subgraph Phase 1A: Audio Clip Generation - DEPLOYED
        B -- 2. /api/v1/audio_clips Request --> C(AWS Lambda: audio-clip-generator)
        C -- 3. Check Cache --> F[S3: pod-insights-clips]
        C -- 4. Lookup Episode --> D[MongoDB: episode_metadata]
        C -- 5. Fetch Raw Audio --> E[S3: pod-insights-raw]
        C -- 6. FFmpeg Extract 30s --> C
        C -- 7. Store Clip --> F
        C -- 8. Return Pre-signed URL --> B
    end

    subgraph Phase 1B: Answer Synthesis - TO BUILD
        B -- 9. /api/search Request --> G(podinsight-api: Enhanced Endpoint)
        G -- 10. Vector Search --> H[MongoDB: transcript_chunks_768d]
        H -- 11. Return Top 10 Chunks --> G
        G -- 12. Synthesize Answer --> I[OpenAI GPT-3.5]
        I -- 13. 2-Sentence Summary --> G
        G -- 14. Format Citations --> G
        G -- 15. Complete Response --> B
        B -- 16. Results to User --> A
    end

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#ccf,stroke:#333,stroke-width:2px
    style F fill:#fcc,stroke:#333,stroke-width:2px
```

### 2. MongoDB Schema

#### Collection: `episode_metadata`
```json
{
  "_id": ObjectId,
  "guid": "string",           // Primary key used by Lambda
  "episode_id": "string",     // Legacy identifier
  "podcast_name": "string",
  "episode_title": "string",
  "published_date": Date,
  "duration_seconds": number,
  "s3_audio_path": "string",  // Full S3 path to raw audio
  "transcript_status": "string",
  "created_at": Date,
  "updated_at": Date
}
```

#### Collection: `transcript_chunks_768d`
```json
{
  "_id": ObjectId,
  "episode_id": "string",     // Links to episode_metadata.guid
  "chunk_index": number,      // Sequential order within episode
  "text": "string",          // Transcript segment (~100 tokens)
  "start_time": number,      // Start time in seconds
  "end_time": number,        // End time in seconds
  "embedding_768d": [        // 768-dimensional vector
    number, number, ..., number
  ],
  "created_at": Date
}
```

#### Collection: `podcast_metadata`
```json
{
  "_id": ObjectId,
  "feed_slug": "string",     // e.g., "a16z-podcast"
  "podcast_name": "string",  // Display name
  "category": "string",
  "total_episodes": number,
  "updated_at": Date
}
```

### 3. S3 Bucket Structure

#### Bucket: `pod-insights-raw` (Existing)
```
s3://pod-insights-raw/
├── <feed_slug>/
│   └── <episode_guid>/
│       └── audio/
│           └── <original_filename>.mp3
```
Example: `s3://pod-insights-raw/a16z-podcast/0e983347-7815-4b62-87a6-84d988a772b7/audio/episode_audio.mp3`

#### Bucket: `pod-insights-clips` (Created by CloudFormation)
```
s3://pod-insights-clips/
└── audio_clips/
    └── <episode_guid>/
        └── <start_ms>-<end_ms>.mp3
```
Example: `s3://pod-insights-clips/audio_clips/0e983347-7815-4b62-87a6-84d988a772b7/30000-60000.mp3`

### 4. API Specifications

#### Audio Clip Endpoint (Phase 1A - DEPLOYED)

**Lambda API Gateway**: `https://39wfiyyk92.execute-api.eu-west-2.amazonaws.com/prod`

```http
GET /api/v1/audio_clips/{episode_id}?start_time_ms={start}&duration_ms=30000

Response 200:
{
  "clip_url": "https://pod-insights-clips.s3.eu-west-2.amazonaws.com/...",
  "cache_hit": true,
  "generation_time_ms": 0
}

Response 404:
{
  "error": "Episode not found"
}
```

#### Enhanced Search Endpoint (Phase 1B - TO BUILD)

```http
POST /api/search
{
  "query": "What are VCs saying about AI valuations?",
  "limit": 10
}

Response 200:
{
  "answer": "VCs express concern that AI agent valuations are outpacing actual capital efficiency¹². Recent rounds show 50-100x revenue multiples despite unclear moats².",
  "citations": [
    {
      "index": 1,
      "episode_id": "0e983347-7815-4b62-87a6-84d988a772b7",
      "episode_title": "AI Bubble or Breakthrough?",
      "podcast_name": "a16z Podcast",
      "timestamp": "27:04",
      "start_seconds": 1624,
      "chunk_index": 45,
      "text": "The valuations we're seeing in AI agents..."
    }
  ],
  "raw_chunks": [...],
  "processing_time_ms": 2150
}
```

### 5. Complete Process Flow

#### User Query to Answer Journey

```
1. USER INTERACTION
   └─> User types: "What are VCs saying about AI valuations?"

2. QUERY PROCESSING (podinsight-api)
   ├─> Embed query using Modal.com (existing endpoint)
   └─> Returns 768-dimensional vector

3. SEARCH PHASE (MongoDB Atlas)
   ├─> Vector search on 823,000+ chunks
   ├─> Find 100 candidates, select top 20
   ├─> Apply diversity filter (max 2 per episode)
   └─> Return top 10 chunks (~1000 tokens)

4. ANSWER SYNTHESIS (OpenAI - Phase 1B)
   ├─> Send chunks + metadata to GPT-3.5
   ├─> Generate 2-sentence summary (60 words max)
   ├─> Extract citations with superscripts
   └─> Return formatted answer

5. AUDIO GENERATION (AWS Lambda - Phase 1A)
   When user clicks play:
   ├─> Check S3 cache for existing clip
   ├─> If miss: Fetch full MP3 from pod-insights-raw
   ├─> Extract 30s using FFmpeg (center on timestamp)
   ├─> Store in pod-insights-clips bucket
   └─> Return pre-signed URL (24hr expiry)
```

#### Key Services and Their Roles

| Service | Role | Cost Model |
|---------|------|------------|
| **Modal.com** | Query embedding (768D) | Already built, no additional cost |
| **MongoDB Atlas** | Vector search + metadata | $500 credits (existing) |
| **OpenAI API** | Answer synthesis | Pay-per-token ($0.0015/1K tokens) |
| **AWS Lambda** | Audio clip generation | Pay-per-invocation + duration |
| **S3 Storage** | Store generated clips | Pay only for stored clips |
| **FFmpeg Layer** | Audio processing | One-time setup, no runtime cost |

### 6. Infrastructure Details

#### AWS Lambda Function (Phase 1A)
- **Name**: `audio-clip-generator`
- **Runtime**: Python 3.9
- **Memory**: 1GB
- **Timeout**: 60 seconds
- **Layers**:
  - `ffmpeg-podinsight` (custom layer, 58MB)
- **Environment Variables**:
  ```
  MONGODB_URI=mongodb+srv://...
  S3_SOURCE_BUCKET=pod-insights-raw
  S3_CLIPS_BUCKET=pod-insights-clips
  AWS_REGION=eu-west-2
  ```

#### Performance Metrics (Production)
- **Cache Hit**: <200ms (direct S3 URL return)
- **Cache Miss**: 1128ms (includes FFmpeg processing)
- **Cold Start**: ~1650ms
- **Memory Usage**: 94MB of 1GB allocated

### 6. Answer Synthesis Pipeline (Phase 1B)

#### MongoDB Aggregation Pipeline
```javascript
[
  // 1. Vector Search with improved recall
  {
    $vectorSearch: {
      index: "vector_index_768d",
      path: "embedding_768d",
      queryVector: embedding,
      numCandidates: 100,    // Increased from 20
      limit: 20
    }
  },

  // 2. Join with episode metadata
  {
    $lookup: {
      from: "episode_metadata",
      localField: "episode_id",
      foreignField: "guid",
      as: "episode"
    }
  },

  // 3. Diversity - Max 2 chunks per episode
  {
    $group: {
      _id: "$episode_id",
      chunks: { $push: "$$ROOT" },
      max_score: { $max: "$score" }
    }
  },
  { $unwind: { path: "$chunks", includeArrayIndex: "rank" } },
  { $match: { rank: { $lt: 2 } } },

  // 4. Final selection - top 10 for LLM
  { $sort: { "chunks.score": -1 } },
  { $limit: 10 }
]
```

#### OpenAI Integration
```python
SYSTEM_PROMPT = """
You are a podcast intelligence assistant. Given search results,
provide a 2-sentence synthesis (max 60 words) that directly
answers the question. Cite sources with superscript numbers ¹².

Rules:
- Be specific and actionable
- Use exact quotes when impactful
- Require ≥2 distinct episodes as sources
"""

# Model: gpt-3.5-turbo-0125
# Temperature: 0
# Max tokens: 80
```

### 7. Frontend Integration (Phase 2)

The command bar will make sequential API calls:
1. **Search**: `POST /api/search` → Get answer + citations
2. **Audio** (on-demand): When user clicks play:
   - Frontend calls: `GET /api/v1/audio_clips/{episode_id}?start_time_ms={start}`
   - Shows loading spinner (2-3s on first play)
   - Plays 30-second clip inline

### 8. Cost Analysis

#### Detailed Monthly Cost Breakdown ($26/month)

| Component | Usage/Month | Cost | What This Covers |
|-----------|-------------|------|------------------|
| **OpenAI GPT-3.5** | 1,000 queries | $18 | Answer synthesis for user questions (Phase 1B) |
| **Lambda Execution** | 500 clips | $5 | Audio clip generation compute time |
| **S3 Storage (NEW clips)** | 10GB growing | $2 | Storage for generated 30-second clips only |
| **S3 Requests** | 10,000 | $1 | GET/PUT operations for clip generation |
| **Total Operational** | | **$26/month** | Running costs for new features |

#### What's NOT Included in $26/month:
- **Existing MP3s**: Full podcast episodes already stored in `pod-insights-raw` bucket
- **MongoDB Atlas**: Covered by existing $500 credits
- **Modal.com**: Query embeddings use existing endpoint
- **API hosting**: Vercel free tier / existing infrastructure

#### Cost Comparison:
| Approach | Monthly Cost | Annual Cost | What You Pay For |
|----------|--------------|-------------|------------------|
| **Pre-generate all clips** | $833 | $10,000 | 823,000 clips (80% never played) |
| **On-demand generation** | $26 | $312 | Only clips users actually play |
| **Savings** | **$807/month** | **$9,688/year** | 97% cost reduction |

#### Lambda Function Details:
- **Function**: `audio-clip-generator`
- **Process**:
  1. Receives request with episode_id and timestamp
  2. Checks if clip already exists in S3 cache
  3. If not, fetches full MP3 from existing storage
  4. Uses FFmpeg to extract 30-second segment
  5. Stores new clip in `pod-insights-clips` bucket
  6. Returns pre-signed URL valid for 24 hours
- **Cost drivers**:
  - Invocations: ~500/month @ $0.20 per 1M requests
  - Duration: ~1 second per clip @ $0.0000166667 per GB-second
  - Total: ~$5/month for typical usage

### 9. Security & Access

- **MongoDB**: IP whitelist includes Lambda (0.0.0.0/0 required)
- **S3 Buckets**:
  - `pod-insights-raw`: Private, Lambda IAM role access
  - `pod-insights-clips`: Private, pre-signed URLs for access
- **API Gateway**: Public endpoint with future rate limiting
- **Lambda IAM Role**: S3 read/write, CloudWatch logs

### 10. Monitoring & Observability

- **CloudWatch Logs**: All Lambda executions logged
- **Metrics to Track**:
  - Audio generation success rate (target: >95%)
  - Cache hit rate (target: >80% after 7 days)
  - Generation time p95 (target: <3s)
  - OpenAI response time (target: <2s)

## Implementation Status

### ✅ Completed (Phase 1A)
- Lambda function deployed and operational
- FFmpeg layer configured
- S3 buckets created
- MongoDB connection established
- API Gateway endpoint live
- Performance validated in production

### 🔲 To Implement (Phase 1B & 2)
- [ ] Enhance /api/search with OpenAI integration
- [ ] Citation extraction and formatting
- [ ] Frontend command bar component
- [ ] Audio player with loading states
- [ ] Integration testing end-to-end

## Critical Notes

1. **Audio Clip Timing**: Clips are generated as `[start_time - 15s, start_time + 15s]` to center on the chunk
2. **Citation Matching**: Use chunk_index to match OpenAI citations back to source chunks
3. **Error Handling**: Both Lambda and API must handle gracefully:
   - Missing episodes
   - S3 access failures
   - OpenAI timeouts
   - Invalid timestamps

---

*Last Updated: December 28, 2024*
*Status: Phase 1A Complete, Phase 1B Ready to Implement*
