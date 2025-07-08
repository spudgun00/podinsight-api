# Master Data Architecture Document - PodInsightHQ

**Document Version**: 1.0
**Created**: 2025-01-03
**Purpose**: Definitive reference for database schemas, field mappings, and data architecture

---

## 🔍 Sources Analyzed

1. database_field_mapping_rosetta_stone.md (2025-01-03)
2. PodInsightHQ Database Schema Documentation.md
3. database-schema.md (multiple versions)
4. S3_BUCKET_STRUCTURE_CORRECTED.md
5. ACTUAL_S3_AWS_INFRASTRUCTURE.md
6. data_processing_architecture.md
7. PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md (data sections)

---

## 🚨 Discrepancies Found

### 1. GUID Field Naming Problem (CRITICAL)
- **MongoDB `episode_metadata`**: Uses field `guid`
- **MongoDB `transcript_chunks_768d`**: Uses field `episode_id` (contains GUID value!)
- **Supabase `episodes`**: Uses field `guid`
- **Impact**: Joins require knowing `episode_id` = `guid`
- **Resolution**: ✅ Always join using `episode_metadata.guid = transcript_chunks_768d.episode_id`

### 2. Episode Count Discrepancies
- **MongoDB metadata**: 1,236 documents
- **MongoDB transcripts**: 1,171 documents
- **Supabase episodes**: 1,171 rows
- **Documentation claims**: Various (1,171 to 5,000)
- **Resolution**: ✅ 1,171 fully processed episodes is correct

### 3. S3 Structure Reality vs Documentation
- **Documentation**: Simple paths like `embeddings/{guid}.npy`
- **Reality**: Multiple versions `{guid}.npy`, `{guid}_768d_unfiltered.npy`
- **Resolution**: ✅ Use dynamic discovery, never hardcode paths

### 4. Entity Storage Location
- **Documentation**: `entities/` folder
- **Reality**: `cleaned_entities/` folder
- **Resolution**: ✅ Always use `cleaned_entities/`

---

## ✅ Verified Data Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                            │
├─────────────────────────────────────────────────────────────┤
│  S3 BUCKETS           │  MONGODB ATLAS    │   SUPABASE     │
│  ──────────           │  ─────────────    │   ────────     │
│  • Audio files        │  • Transcripts    │  • Metadata    │
│  • Embeddings         │  • Chunks         │  • Entities    │
│  • Processing data    │  • Vectors        │  • Relations   │
└───────────┬───────────┴────────┬─────────┴────────┬────────┘
            │                    │                   │
            │                    ▼                   │
            │         ┌──────────────────┐          │
            └────────▶│  DATA PIPELINE   │◀─────────┘
                      │  ──────────────  │
                      │ • ETL Scripts    │
                      │ • Enrichment     │
                      │ • Vectorization  │
                      └──────────────────┘
```

---

## 📊 Database Schemas

### MongoDB Collections

#### 1. episode_metadata (1,236 documents)
```javascript
{
  "_id": ObjectId("..."),
  "guid": "0e983347-7815-4b62-87a6-84d988a772b7",  // PRIMARY KEY
  "raw_entry_original_feed": {
    "episode_title": "Chris Dixon: AI Winter to AI Boom",
    "podcast_title": "a16z Podcast",
    "podcast_slug": "a16z-podcast",
    "published_date_iso": "2025-06-09T10:00:00",
    "mp3_url_original": "https://...",
    "duration": 3915,
    "fetch_processed_utc": "2025-06-23T10:32:39.326872"
  },
  "s3_audio_path": "s3://pod-insights-raw/a16z-podcast/.../audio.mp3",
  "s3_artifacts_prefix_stage": "s3://pod-insights-stage/a16z-podcast/...",
  "embedding_path": "s3://pod-insights-stage/.../embeddings/...npy",
  "final_transcript_json_path": "s3://pod-insights-stage/.../transcripts/...",
  "segments_file_path": "s3://pod-insights-stage/.../segments/...",
  "cleaned_entities_path": "s3://pod-insights-stage/.../cleaned_entities/...",
  "episode_kpis_path": "s3://pod-insights-stage/.../kpis/...",
  "processing_status": "completed",
  "processed_utc_transcribe_enrich_end": "2025-06-23T14:48:08.469987",
  "_import_timestamp": "2025-06-25T07:35:59.353Z",
  "schema_version": 1,
  "segment_count": 411,
  "entity_stats": {
    "cleaned_entity_count": 144
  },
  "hosts": [],
  "guests": [{"name": "Chris Dixon", "role": "guest"}],
  "categories": [],
  "itunes_explicit": false
}
```

#### 2. episode_transcripts (1,171 documents)
```javascript
{
  "_id": ObjectId("..."),
  "episode_id": "1216c2e7-42b8-42ca-92d7-bad784f80af2",  // ACTUALLY GUID!
  "feed_slug": "a16z-podcast",
  "full_text": "Welcome to the a16z Podcast. Today we have...",
  "word_count": 12373,
  "reading_time_minutes": 13,
  "created_at": "2025-06-25T07:35:59.353Z"
}
```

#### 3. transcript_chunks_768d (823,763 documents)
```javascript
{
  "_id": ObjectId("..."),
  "episode_id": "1216c2e7-42b8-42ca-92d7-bad784f80af2",  // ACTUALLY GUID!
  "feed_slug": "a16z-podcast",
  "chunk_index": 42,
  "text": "People use the term AI winter to describe...",
  "start_time": 120.5,
  "end_time": 135.8,
  "speaker": "SPEAKER_01",
  "embedding_768d": [0.024, -0.154, ...],  // 768 dimensions
  "created_at": "2025-06-25T12:00:00Z",
  "updated_at": "2025-06-25T12:00:00Z"
}

// Indexes
{
  "episode_chunk_unique": {"episode_id": 1, "chunk_index": 1},
  "feed_slug_1": {"feed_slug": 1},
  "created_at_-1": {"created_at": -1},
  "text_search_index": {"text": "text"},
  "vector_index_768d": {
    "embedding_768d": "cosmosSearch",
    "kind": "vector-hnsw",
    "dimensions": 768,
    "similarity": "cosine"
  }
}
```

#### 4. sentiment_results (62 documents)
```javascript
{
  "_id": ObjectId("..."),
  "topic": "AI Agents",
  "week": "2025-W24",
  "sentiment_score": 0.75,
  "episode_count": 23,
  "sample_quotes": [...],
  "calculated_at": "2025-06-25T03:00:00Z"
}
```

#### 5. episode_intelligence (50 documents)
```javascript
{
  "_id": ObjectId("..."),
  "episode_id": "02fc268c-61dc-4074-b7ec-882615bc6d85",  // GUID matching episode_metadata
  "signals": {
    "investable": [
      {
        "content": "We passed on Uber's seed round",
        "confidence": 0.85,
        "timestamp": "00:23:45"
      }
    ],
    "competitive": [
      {
        "content": "OpenAI is building a direct competitor to our portfolio company",
        "confidence": 0.92,
        "timestamp": "00:15:30"
      }
    ],
    "portfolio": [
      {
        "content": "Our portfolio company Figma just crossed $100M ARR",
        "confidence": 0.95,
        "timestamp": "00:08:12"
      }
    ],
    "soundbites": [
      {
        "content": "that's where the gold is, is that non consensus bet",
        "confidence": 0.88,
        "timestamp": "00:45:20"
      }
    ]
  },
  "relevance_score": 85,  // Pre-calculated relevance score (0-100)
  "created_at": "2025-01-01T12:00:00Z"
}
```

#### 6. podcast_authority (31 documents)
```javascript
{
  "_id": ObjectId("..."),
  "feed_slug": "all-in",
  "podcast_name": "All-In with Chamath, Jason, Sacks & Friedberg",
  "tier": 1,  // 1-5, where 1 is highest authority
  "authority_score": 95,  // 0-100 score
  "metrics": {
    "average_episode_views": 2500000,
    "subscriber_count": 1200000,
    "industry_influence": "high"
  },
  "updated_at": "2025-01-01T00:00:00Z"
}
```

#### 7. user_intelligence_prefs (varies by user count)
```javascript
{
  "_id": ObjectId("..."),
  "user_id": "demo-user",
  "preferences": {
    "portfolio_companies": ["Figma", "Notion", "Airtable", "Retool"],
    "topics": ["AI", "developer tools", "enterprise software", "crypto"],
    "keywords": ["seed round", "Series A", "YC", "product-market fit"],
    "notification_settings": {
      "frequency": "weekly",
      "email_enabled": true,
      "slack_enabled": false
    }
  },
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### Supabase PostgreSQL Tables

#### 1. episodes (1,171 rows)
```sql
CREATE TABLE episodes (
    guid VARCHAR PRIMARY KEY,
    podcast_slug VARCHAR NOT NULL,
    podcast_name VARCHAR NOT NULL,
    episode_title VARCHAR NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    word_count INTEGER,
    duration_seconds INTEGER,
    s3_audio_path TEXT,
    s3_stage_prefix TEXT,
    s3_embeddings_path TEXT,
    processing_status VARCHAR DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_episodes_podcast ON episodes(podcast_slug);
CREATE INDEX idx_episodes_published ON episodes(published_at DESC);
```

#### 2. extracted_entities (123k+ rows)
```sql
CREATE TABLE extracted_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_guid VARCHAR REFERENCES episodes(guid),
    entity_name VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL, -- PERSON, ORG, GPE, MONEY
    confidence_score NUMERIC(3,2),
    context TEXT,
    start_position INTEGER,
    end_position INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_entities_episode ON extracted_entities(episode_guid);
CREATE INDEX idx_entities_name ON extracted_entities(entity_name);
CREATE INDEX idx_entities_type ON extracted_entities(entity_type);
```

#### 3. topic_mentions (Sprint 0 table)
```sql
CREATE TABLE topic_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_guid VARCHAR REFERENCES episodes(guid),
    topic_name VARCHAR NOT NULL,
    mention_count INTEGER NOT NULL,
    confidence NUMERIC(3,2),
    week_number VARCHAR(7), -- Format: 2025-W01
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_mentions_topic ON topic_mentions(topic_name);
CREATE INDEX idx_mentions_week ON topic_mentions(week_number);
```

#### 4. kpi_metrics
```sql
CREATE TABLE kpi_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_guid VARCHAR REFERENCES episodes(guid),
    metric_type VARCHAR NOT NULL,
    metric_value NUMERIC,
    metric_unit VARCHAR,
    context TEXT,
    confidence NUMERIC(3,2)
);
```

---

## 🗺️ Field Mapping Reference

### Primary Key Relationships

| System | Collection/Table | Primary Key Field | Contains | Notes |
|--------|------------------|-------------------|----------|-------|
| MongoDB | episode_metadata | guid | UUID | Standard format |
| MongoDB | episode_transcripts | episode_id | UUID | ⚠️ Named wrong! |
| MongoDB | transcript_chunks_768d | episode_id + chunk_index | UUID + Int | Composite key |
| Supabase | episodes | guid | UUID | Matches MongoDB |
| S3 | All paths | {guid} in path | UUID | Folder structure |

### Special ID Formats

```javascript
// Standard UUID
"0e983347-7815-4b62-87a6-84d988a772b7"

// Special formats (some podcasts)
"substack:post:153430776"         // Lenny's Podcast
"flightcast:01JVDNHG0SJ6AZNMZ..."  // Latent Space
"pod-027d53417f04df6fe884c85b95"  // StartupRad.io
```

### Cross-System Field Mapping

| Concept | MongoDB metadata | MongoDB chunks | Supabase | S3 Path |
|---------|------------------|----------------|----------|---------|
| Episode ID | guid | episode_id | guid | {guid}/ |
| Podcast Name | raw_entry_original_feed.podcast_title | feed_slug | podcast_name | {feed_slug}/ |
| Episode Title | raw_entry_original_feed.episode_title | - | episode_title | In filename |
| Duration | - | - | duration_seconds | In metadata |
| Publish Date | raw_entry_original_feed.published_date_iso | - | published_at | - |
| Word Count | - | word_count | word_count | - |
| Full Text | - | full_text | - | In transcript file |

---

## 📁 S3 Data Structure (VERIFIED)

### File Organization Pattern
```
pod-insights-stage/
└── {feed-slug}/
    └── {guid}/
        ├── cleaned_entities/
        │   └── {guid}_clean.json              # Extracted entities
        ├── embeddings/
        │   ├── {guid}.npy                     # 384D (legacy)
        │   ├── {guid}_768d_unfiltered.npy     # 768D (current)
        │   └── embedding_768d.npy             # Alternative name
        ├── entities_raw/
        │   └── {guid}.json                    # Raw extraction
        ├── kpis/
        │   └── kpis_{guid}.json               # Business metrics
        ├── meta/
        │   └── meta_{guid}_details.json       # Enhanced metadata
        ├── segments/
        │   ├── {guid}.json                    # Simple format
        │   └── {guid}_full.json               # Detailed format
        └── transcripts/
            ├── {complex_filename}.json         # Variable naming!
            ├── {guid}_text.json               # Text only
            └── {guid}_full.json               # With metadata
```

### Critical File Discovery Pattern
```python
def find_transcript_file(feed_slug: str, guid: str) -> str:
    """NEVER hardcode paths - always discover"""
    transcript_folder = f"{feed_slug}/{guid}/transcripts/"

    # List all files and find .json files
    files = s3_client.list_objects_v2(
        Bucket='pod-insights-stage',
        Prefix=transcript_folder
    )

    # Match any .json file - naming is inconsistent
    for file in files.get('Contents', []):
        if file['Key'].endswith('.json'):
            return file['Key']
```

---

## 🔄 Data Pipeline Flow

### 1. Raw Audio → Processing
```
Source: RSS feeds → Manual download
Storage: pod-insights-raw/{feed}/{guid}/audio/
Format: MP3 files with complex naming
```

### 2. Transcription → Chunks
```
Process: WhisperX → Transcript JSON
Chunking: ~150 word segments with overlap
Output: 823,763 searchable chunks
Storage: MongoDB transcript_chunks_768d
```

### 3. Embedding Generation
```
Model: Instructor-XL (768 dimensions)
Process: Modal.com GPU infrastructure
Storage: S3 as .npy files + MongoDB vectors
Format: float16 arrays for efficiency
```

### 4. Entity Extraction
```
Tool: SpaCy NER
Types: PERSON, ORG, GPE, MONEY only
Storage: Supabase extracted_entities
Count: ~123,000 entities
```

### 5. Sentiment Analysis
```
Process: Nightly batch job
Scope: 5 topics × 12 weeks = 60 cells
Storage: MongoDB sentiment_results
Update: Daily at 3 AM UTC
```

---

## 🔧 Query Patterns

### Find Episodes by Topic
```javascript
// MongoDB aggregation
db.transcript_chunks_768d.aggregate([
  { $match: { text: /AI agents/i } },
  { $group: {
      _id: "$episode_id",
      mentions: { $sum: 1 }
  }},
  { $sort: { mentions: -1 } }
])
```

### Vector Similarity Search
```javascript
// MongoDB vector search
db.transcript_chunks_768d.aggregate([
  {
    $search: {
      index: "vector_index_768d",
      knnBeta: {
        vector: [0.024, -0.154, ...], // 768D query embedding
        path: "embedding_768d",
        k: 100,
        numCandidates: 100
      }
    }
  }
])
```

### Join Episode Metadata
```sql
-- PostgreSQL with proper join
SELECT
    e.episode_title,
    e.podcast_name,
    COUNT(ee.id) as entity_count
FROM episodes e
LEFT JOIN extracted_entities ee ON e.guid = ee.episode_guid
WHERE ee.entity_type = 'ORG'
GROUP BY e.guid
ORDER BY entity_count DESC;
```

---

## 🚨 Data Quality Issues

### Known Problems
1. **Generic Titles**: Some Supabase episodes have "Episode {guid}" titles
2. **Missing Durations**: MongoDB metadata lacks duration field
3. **Nested Data**: MongoDB uses deeply nested `raw_entry_original_feed`
4. **Inconsistent Dates**: Mix of timezone formats
5. **File Naming**: Transcript files have unpredictable names

### Recommended Fixes
1. Sync real titles from MongoDB to Supabase
2. Calculate durations from audio files
3. Flatten MongoDB schema in next migration
4. Standardize all dates to UTC
5. Implement robust file discovery

---

## 📊 Data Statistics

| Metric | Value | Source |
|--------|-------|---------|
| **Total Episodes** | 1,171 | Verified |
| **Total Chunks** | 823,763 | MongoDB count |
| **Average Chunks/Episode** | 703 | Calculated |
| **Total Entities** | ~123,000 | Supabase count |
| **Unique Podcasts** | 31 | S3 folders |
| **Vector Dimensions** | 768 | Instructor-XL |
| **Chunk Size** | ~150 words | Design target |
| **Overlap Between Chunks** | 20 words | Approximate |

---

## ❓ Needs Verification

1. **Exact duplicate episodes** causing 1,236 vs 1,171 discrepancy
2. **Complete list of special ID formats** beyond UUID
3. **Actual chunk overlap percentage** (documented as ~20 words)
4. **Vector index performance** metrics
5. **Data retention policy** for S3 files

---

**Note**: This document represents the verified data architecture as of January 2025. The GUID field naming issue is the most critical gotcha for developers.
