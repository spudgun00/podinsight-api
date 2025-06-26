# PodInsight Complete System Documentation
*Generated: June 25, 2025*

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current System State](#current-system-state)
3. [Architecture Overview](#architecture-overview)
4. [Infrastructure Components](#infrastructure-components)
5. [Data Model](#data-model)
6. [API Endpoints](#api-endpoints)
7. [Scripts and Tools](#scripts-and-tools)
8. [Embedding System](#embedding-system)
9. [Search Pipeline](#search-pipeline)
10. [Known Issues](#known-issues)
11. [Testing Framework](#testing-framework)
12. [Deployment Process](#deployment-process)

---

## Executive Summary

PodInsight is a podcast search system that uses 768-dimensional vector embeddings to enable semantic search across transcript chunks. The system consists of:
- **MongoDB Atlas** for data storage and vector search
- **Vercel** for API hosting
- **Modal.com** for serverless embedding generation
- **Instructor-XL** model for 768D embeddings

### Current Status (June 25, 2025)
- ✅ Episode metadata displays correctly (fixed async MongoDB queries)
- ✅ Some queries work (e.g., "artificial intelligence")
- ⚠️ Some queries still return 0 results (e.g., "openai", "venture capital")
- ❌ Data quality tests: 4/5 passing
- ❌ E2E tests: timing out

---

## Current System State

### What's Working
1. **MongoDB Integration**: Episode metadata correctly retrieved from `episode_metadata` collection
2. **Vector Search Infrastructure**: Index is 100% built (823,763 documents)
3. **Some Queries**: Multi-word queries like "artificial intelligence" now return results
4. **Episode Display**: Real episode titles show instead of placeholders

### What's Not Working
1. **Inconsistent Search Results**: Some queries that should have matches return 0 results
2. **Embedding Instruction Issue**: Removed instruction to test impact, but original embedding method unclear
3. **Test Coverage**: Data quality and E2E tests failing

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│                    (Next.js Frontend - Vercel)                   │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Search API (Vercel)                         │
│                 /api/search → search_lightweight_768d.py         │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Embedding Generation                          │
│              Modal.com (Instructor-XL Model)                     │
│   https://podinsighthq--podinsight-embeddings-simple-*.modal.run│
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MongoDB Atlas Cluster                        │
│                        (London Region)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Database: podinsight                                     │   │
│  │                                                          │   │
│  │ Collections:                                             │   │
│  │ - transcript_chunks_768d (823,763 docs)                 │   │
│  │   └─ Vector Index: vector_index_768d                    │   │
│  │ - episode_metadata (1,236 docs)                         │   │
│  │ - episode_transcripts (1,171 docs)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         S3 Storage                               │
│              Audio Files & Processing Artifacts                  │
│  - pod-insights-raw (original audio)                            │
│  - pod-insights-stage (processed artifacts)                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Infrastructure Components

### 1. MongoDB Atlas
- **Cluster**: atlas-12vjb5-shard
- **Region**: London (3 nodes)
- **Connection**: `MONGODB_URI` environment variable
- **Database**: `podinsight`
- **Memory Usage**: 2.39GB per node
- **Status**: All nodes READY, 100% indexed

### 2. Vercel Deployment
- **URL**: https://podinsight-api.vercel.app
- **Framework**: FastAPI running on Vercel
- **Environment Variables**:
  - `MONGODB_URI`
  - `SUPABASE_URL` (legacy)
  - `SUPABASE_ANON_KEY` (legacy)
  - `HUGGINGFACE_API_KEY`
  - `MODAL_EMBEDDING_URL`

### 3. Modal.com Infrastructure
- **Workspace**: podinsighthq
- **App Name**: podinsight-embeddings-simple
- **GPU**: A10G
- **Model**: Instructor-XL (hkunlp/instructor-xl)
- **Endpoints**:
  - Generate: https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run
  - Health: https://podinsighthq--podinsight-embeddings-simple-health-check.modal.run

### 4. S3 Storage
- **Raw Audio**: `s3://pod-insights-raw/`
- **Processed Data**: `s3://pod-insights-stage/`
- **File Structure**: `{podcast-slug}/{episode-guid}/`

---

## Data Model

### MongoDB Collections

#### 1. transcript_chunks_768d (Vector Search Collection)
```javascript
{
  "_id": ObjectId,
  "episode_id": "0e983347-7815-4b62-87a6-84d988a772b7",  // GUID
  "feed_slug": "a16z-podcast",
  "chunk_index": 42,
  "text": "Chris Dixon discusses stablecoins...",
  "start_time": 1234.56,
  "end_time": 1245.67,
  "speaker": "Chris Dixon",
  "embedding_768d": [0.0246, 0.0037, ...],  // 768 floats
  "created_at": ISODate("2025-06-23T10:00:00Z")
}
```

**Indexes**:
- `vector_index_768d` - Vector search index on `embedding_768d` field
- `episode_chunk_unique` - Compound index on episode_id + chunk_index
- `feed_slug_1` - Index on podcast feed
- `created_at_-1` - Descending index on creation time

#### 2. episode_metadata (Enrichment Data)
```javascript
{
  "_id": ObjectId,
  "guid": "0e983347-7815-4b62-87a6-84d988a772b7",  // Matches episode_id
  "raw_entry_original_feed": {
    "guid": "0e983347-7815-4b62-87a6-84d988a772b7",
    "podcast_slug": "a16z-podcast",
    "podcast_title": "a16z Podcast",
    "episode_title": "Chris Dixon: Stablecoins, Startups, and the Crypto Stack",
    "published_date_iso": "2025-06-09T10:00:00",
    "s3_audio_path_raw": "s3://pod-insights-raw/...",
    // ... more fields
  },
  "guests": [
    {"name": "Chris Dixon", "role": "guest"},
    {"name": "A16Z Crypto", "role": "guest"}
  ],
  "segment_count": 411,
  // ... processing metadata
}
```

#### 3. episode_transcripts (Full Transcripts)
```javascript
{
  "_id": ObjectId,
  "episode_id": "0e983347-7815-4b62-87a6-84d988a772b7",
  "transcript": "Full episode transcript...",
  "word_count": 12345,
  // ... other fields
}
```

### ID Relationships
- `transcript_chunks_768d.episode_id` = `episode_metadata.guid`
- Both use GUID format (various UUID versions supported)

---

## API Endpoints

### 1. Health Check
```
GET https://podinsight-api.vercel.app/api/health
```
Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-25T13:29:06.838420",
  "checks": {
    "huggingface_api_key": "configured", # pragma: allowlist secret
    "database": "connected",
    "connection_pool": {...}
  },
  "version": "1.0.0"
}
```

### 2. Search API
```
POST https://podinsight-api.vercel.app/api/search
Content-Type: application/json

{
  "query": "artificial intelligence",
  "limit": 10,
  "offset": 0
}
```
Response:
```json
{
  "results": [
    {
      "episode_id": "234789ad-1ade-4789-8a47-07267a688eac",
      "podcast_name": "The AI Daily Brief",
      "episode_title": "Just How Fast is AI Evolving?",
      "published_at": "2025-01-26T13:16:51",
      "published_date": "January 26, 2025",
      "similarity_score": 0.898094892501831,
      "excerpt": "...",
      "word_count": 127,
      "duration_seconds": 0,
      "topics": [],
      "s3_audio_path": "s3://...",
      "timestamp": {
        "start_time": 72.181,
        "end_time": 81.004
      }
    }
  ],
  "total_results": 3,
  "cache_hit": false,
  "search_id": "search_803b3eb2_1750858170.904438",
  "query": "artificial intelligence",
  "limit": 10,
  "offset": 0,
  "search_method": "vector_768d"
}
```

### 3. Modal.com Embedding Endpoint
```
POST https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run
Content-Type: application/json

{
  "text": "your text to embed"
}
```
Response:
```json
{
  "embedding": [0.0150, 0.0116, ...],  // 768 floats
  "dimension": 768,
  "model": "instructor-xl",
  "gpu_available": true,
  "inference_time_ms": 22.86,
  "total_time_ms": 22.89,
  "model_load_time_ms": 0.0
}
```

---

## Scripts and Tools

### Core API Files

#### /api/search_lightweight_768d.py
Main search handler that:
1. Receives search request
2. Generates embedding via Modal
3. Performs MongoDB vector search
4. Enriches results with metadata
5. Returns formatted results

Key functions:
- `search_handler_lightweight_768d()` - Main entry point
- `generate_embedding_768d_local()` - Calls Modal endpoint
- `expand_chunk_context()` - Expands chunk with surrounding context

#### /api/mongodb_vector_search.py
MongoDB vector search implementation:
- `MongoVectorSearchHandler` class
- `vector_search()` - Performs Atlas vector search
- `_enrich_with_metadata()` - Adds episode metadata
- Handles async MongoDB operations with motor

#### /api/embeddings_768d_modal.py
Modal.com client for embeddings:
- `ModalInstructorXLEmbedder` class
- `encode_query()` - Synchronous wrapper
- `_encode_query_async()` - Async implementation
- Handles Modal API communication

### Modal.com Scripts

#### /scripts/modal_web_endpoint_simple.py
Modal deployment script (CRITICAL - controls embedding behavior):
```python
# Current configuration (June 25, 2025)
INSTRUCTION = ""  # Empty - was "Represent the venture capital podcast discussion:"
MODEL = "hkunlp/instructor-xl"
GPU = "A10G"
```

Key functions:
- `generate_embedding()` - Web endpoint
- `get_model()` - Model loading/caching
- `_generate_embedding()` - Core embedding logic

### Testing Scripts

#### /scripts/test_data_quality.py
Data quality validation:
- Health check
- Known query testing
- Latency testing
- Bad input handling
- Concurrent load testing

#### /scripts/test_e2e_production.py
End-to-end production tests:
- Full search workflow
- Result validation
- Performance metrics

#### /scripts/debug_vector_search.py
Diagnostic tool that:
- Checks embedding presence
- Tests Modal endpoint
- Performs manual vector search
- Validates MongoDB indexes

#### /scripts/check_orphan_episodes.py
Verifies metadata coverage:
- Finds chunks without metadata
- Reports coverage statistics
- Identifies missing episodes

### Utility Scripts

#### /scripts/analyze_182_chunk_episode.py
Analyzes episodes with many chunks

#### /scripts/test_embedder_direct.py
Direct embedding tests

#### /scripts/modal_embeddings_simple.py
Alternative Modal embedding implementation

#### /scripts/test_embedding_instruction.py
Tests different embedding instructions (created during debugging)

---

## Embedding System

### Current Configuration (June 25, 2025)

#### Model: Instructor-XL
- **Full Name**: hkunlp/instructor-xl
- **Dimensions**: 768
- **Type**: Sentence transformer with instruction capability
- **Location**: Hosted on Modal.com with GPU acceleration

#### Instruction Issue
**Original Setup**: Unknown - chunks may have been embedded with:
- No instruction
- "Represent the venture capital podcast discussion:"
- Some other instruction

**Current Setup** (after fix):
- `INSTRUCTION = ""` (empty string)
- This improved results for some queries but not all

#### Embedding Process
1. User query → API
2. API calls Modal endpoint
3. Modal formats text based on INSTRUCTION setting
4. Instructor-XL generates 768D embedding
5. Embedding used for MongoDB vector search

---

## Search Pipeline

### Step-by-Step Flow

1. **Request Reception** (`/api/search`)
   - Validate query parameters
   - Generate query hash for caching

2. **Embedding Generation**
   - Call Modal.com endpoint
   - Apply instruction (currently empty)
   - Get 768D vector

3. **Vector Search** (MongoDB Atlas)
   ```javascript
   {
     "$vectorSearch": {
       "index": "vector_index_768d",
       "path": "embedding_768d",
       "queryVector": [768 floats],
       "numCandidates": 100,
       "limit": 10
     }
   }
   ```

4. **Metadata Enrichment**
   - Get episode GUIDs from chunks
   - Query `episode_metadata` collection
   - Add podcast name, episode title, etc.

5. **Context Expansion**
   - Fetch surrounding chunks (±20 seconds)
   - Concatenate for better readability

6. **Response Formatting**
   - Convert to API response format
   - Add timestamps, scores, etc.

---

## Known Issues

### 1. Embedding Instruction Mismatch
**Problem**: Query embeddings may not match how chunks were originally embedded
**Impact**: Poor search results for many queries
**Current Fix**: Removed instruction, but this is a temporary solution
**Proper Fix**: Need to determine original embedding method

### 2. Inconsistent Search Results
**Symptoms**:
- "artificial intelligence" → 3 results ✅
- "openai" → 0 results ❌
- "venture capital" → 0 results ❌

**Possible Causes**:
- Original embeddings used different preprocessing
- Case sensitivity issues
- Different tokenization
- Missing content in index

### 3. Test Failures
**Data Quality**: 4/5 tests pass (Known Queries fail)
**E2E Tests**: Timeout after 2 minutes
**Root Cause**: Search returning 0 results for expected queries

### 4. Legacy Supabase Dependencies
- Some code still references Supabase
- Audio paths come from Supabase tables
- Should be fully migrated to MongoDB

---

## Testing Framework

### Test Suites

1. **Data Quality** (`test_data_quality.py`)
   - Health endpoint
   - Known queries validation
   - Response time checks
   - Input validation
   - Concurrent request handling

2. **E2E Production** (`test_e2e_production.py`)
   - Full search workflow
   - Multi-step scenarios
   - Performance benchmarks

3. **Debug Tools**
   - `debug_vector_search.py` - Direct MongoDB testing
   - `check_orphan_episodes.py` - Data integrity

### Running Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Run specific test suite
python3 scripts/test_data_quality.py
python3 scripts/test_e2e_production.py

# Debug tools
python3 scripts/debug_vector_search.py
python3 scripts/check_orphan_episodes.py
```

---

## Deployment Process

### API Deployment (Vercel)
1. Code changes pushed to GitHub
2. Vercel automatically builds and deploys
3. Environment variables configured in Vercel dashboard
4. Typical deployment time: 1-2 minutes

```bash
# Deploy API
git add .
git commit -m "fix: your changes"
git push origin main
```

### Modal Deployment
1. Ensure Modal CLI installed and authenticated
2. Deploy from virtual environment

```bash
# Deploy Modal endpoint
source venv/bin/activate
modal deploy scripts/modal_web_endpoint_simple.py
```

### MongoDB Changes
- Index changes through Atlas UI
- Schema changes don't require deployment
- Connection string in environment variables

---

## Environment Variables

### Required for API (Vercel)
```
MONGODB_URI=mongodb+srv://...
MODAL_EMBEDDING_URL=https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run
HUGGINGFACE_API_KEY=hf_...
SUPABASE_URL=https://... (legacy)
SUPABASE_ANON_KEY=... (legacy)
```

### Required for Local Development
Create `.env` file:
```
MONGODB_URI=mongodb+srv://...
MODAL_EMBEDDING_URL=https://...
HUGGINGFACE_API_KEY=hf_...
```

---

## Critical Files Reference

### API Core
- `/api/search_lightweight_768d.py` - Main search handler
- `/api/mongodb_vector_search.py` - Vector search implementation
- `/api/embeddings_768d_modal.py` - Modal client
- `/api/database.py` - Database connections
- `/api/mongodb_search.py` - Text search fallback

### Modal Service
- `/scripts/modal_web_endpoint_simple.py` - Modal deployment (CRITICAL)

### Testing
- `/scripts/test_data_quality.py` - Quality checks
- `/scripts/test_e2e_production.py` - E2E tests
- `/scripts/debug_vector_search.py` - Debugging tool

### Documentation
- `/MONGODB_DATA_MODEL.md` - Database schema
- `/MODAL_ARCHITECTURE_DIAGRAM.md` - Modal integration
- `/SESSION_SUMMARY_JUNE_25_2025.md` - Recent work summary
- `/SPRINT_LOG_JUNE_25_2025.md` - Detailed sprint log

---

## Recommendations

### Immediate Actions
1. **Determine Original Embedding Method**: Check ETL pipeline to understand how chunks were embedded
2. **Test Different Instructions**: Try various instruction formats to find best match
3. **Adjust Similarity Threshold**: Current threshold may be too high
4. **Add Logging**: Enhanced logging for embedding generation and search

### Medium-term Improvements
1. **Re-embed All Chunks**: Use consistent instruction across all data
2. **Implement Caching**: MongoDB-based query cache
3. **Add Monitoring**: Track search success rates
4. **Improve Tests**: Add more comprehensive test cases

### Long-term Considerations
1. **Upgrade Embedding Model**: Consider newer models
2. **Hybrid Search**: Combine vector + text search
3. **A/B Testing**: Test different embedding strategies
4. **Performance Optimization**: Implement connection pooling

---

## Support Contacts

- **MongoDB Atlas**: Through Atlas console support
- **Vercel**: Dashboard support options
- **Modal.com**: support@modal.com or Discord
- **GitHub Repo**: https://github.com/spudgun00/podinsight-api

---

*This document represents the complete system state as of June 25, 2025*
