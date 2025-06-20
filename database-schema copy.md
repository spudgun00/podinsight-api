# PodInsightHQ Database Schema Documentation

**Last Updated:** June 2025  
**Database:** PostgreSQL (Supabase)  
**Extensions:** pgvector v0.8.0

## Overview

PodInsightHQ uses PostgreSQL hosted on Supabase with pgvector extension for semantic search capabilities. The schema supports podcast episode storage, topic tracking, entity extraction, user management, and vector similarity search.

## Migration History

| Migration | Date | Description | Status |
|-----------|------|-------------|---------|
| 001_initial_schema | Genesis Sprint | Core tables for episodes, topics, KPIs, entities | ✅ Applied |
| 002_vector_search | Sprint 1 | Added embeddings, search functions, cache | 🔄 In Progress |
| 003_auth_tables | Sprint 1 | User management and saved searches | 🔄 In Progress |

## Core Tables

### 1. episodes
**Purpose:** Master table storing all podcast episode metadata and content

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| guid | TEXT | UNIQUE, NOT NULL | RSS feed GUID |
| podcast_name | TEXT | NOT NULL | Name of the podcast |
| episode_title | TEXT | NOT NULL | Episode title |
| published_at | TIMESTAMP | NOT NULL, INDEX | Publication date |
| duration_seconds | INTEGER | | Episode length |
| s3_stage_prefix | TEXT | NOT NULL | Base S3 path for processed data |
| s3_audio_path | TEXT | | Full S3 path to audio file |
| s3_embeddings_path | TEXT | | Path to .npy embedding file |
| word_count | INTEGER | | Transcript word count |
| embedding | vector(1536) | | OpenAI embedding vector (Sprint 1) |

**Indexes:**
- `idx_episodes_published_at` on published_at
- `idx_episodes_guid` on guid (UNIQUE)
- `idx_episodes_embedding` on embedding USING ivfflat (Sprint 1)

### 2. topic_mentions
**Purpose:** Tracks which topics are discussed in each episode

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| episode_id | UUID | FOREIGN KEY episodes(id), NOT NULL | Episode reference |
| topic_name | TEXT | NOT NULL | Topic name (e.g., "AI Agents") |
| mention_date | DATE | NOT NULL | Date of mention |
| week_number | INTEGER | NOT NULL | ISO week number |

**Indexes:**
- `idx_topic_mentions_episode` on episode_id
- `idx_topic_mentions_topic` on topic_name
- `idx_topic_mentions_week` on week_number

**Constraints:**
- UNIQUE(episode_id, topic_name) - One mention per topic per episode

### 3. extracted_kpis
**Purpose:** Stores financial metrics and KPIs mentioned in episodes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| episode_id | UUID | FOREIGN KEY episodes(id), NOT NULL | Episode reference |
| kpi_type | TEXT | NOT NULL | Type of KPI (e.g., "revenue", "valuation") |
| kpi_value | TEXT | NOT NULL | Extracted value |
| context | TEXT | | Surrounding context |
| confidence | FLOAT | CHECK (confidence >= 0 AND confidence <= 1) | Extraction confidence |
| timestamp | INTEGER | | Position in episode (seconds) |

**Indexes:**
- `idx_kpis_episode` on episode_id
- `idx_kpis_type` on kpi_type

### 4. extracted_entities
**Purpose:** People, companies, and other entities mentioned in episodes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| episode_id | UUID | FOREIGN KEY episodes(id), NOT NULL | Episode reference |
| entity_name | TEXT | NOT NULL | Original entity name |
| entity_type | TEXT | NOT NULL | Type (PERSON, ORG, GPE, MONEY) |
| normalized_name | TEXT | NOT NULL | Standardized name |
| confidence | FLOAT | CHECK (confidence >= 0 AND confidence <= 1) | Recognition confidence |
| role | TEXT | | Role/context (e.g., "guest", "investor") |
| organization | TEXT | | Associated organization |

**Indexes:**
- `idx_entities_episode` on episode_id
- `idx_entities_normalized` on normalized_name
- `idx_entities_type` on entity_type

## Search & Caching Tables (Sprint 1)

### 5. query_cache
**Purpose:** Cache embeddings for frequently searched queries to reduce OpenAI API costs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| query_hash | TEXT | PRIMARY KEY | SHA256 of lowercased query |
| query_text | TEXT | NOT NULL | Original query text |
| embedding | vector(1536) | NOT NULL | Cached embedding |
| created_at | TIMESTAMP | DEFAULT NOW() | First search time |
| last_used | TIMESTAMP | DEFAULT NOW() | Last access time |
| use_count | INTEGER | DEFAULT 1 | Number of times used |

**Indexes:**
- `idx_query_cache_last_used` on last_used DESC

**Maintenance:**
- Auto-cleanup function removes entries unused for 30+ days

### 6. topic_signals
**Purpose:** Pre-computed topic correlations and insights for SIGNAL bar

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| signal_type | TEXT | NOT NULL | Type of signal (e.g., "correlation") |
| signal_data | JSONB | NOT NULL | Computed insights |
| calculated_at | TIMESTAMP | NOT NULL | Computation timestamp |

**Indexes:**
- `idx_signals_type` on signal_type
- `idx_signals_calculated` on calculated_at DESC

## User Management Tables (Sprint 1)

### 7. users
**Purpose:** User accounts integrated with Supabase Auth

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, REFERENCES auth.users(id) | Supabase Auth ID |
| email | TEXT | UNIQUE, NOT NULL | User email |
| created_at | TIMESTAMP | DEFAULT NOW() | Registration date |
| subscription_tier | TEXT | DEFAULT 'free' | User tier (free, pro, team) |

### 8. saved_searches
**Purpose:** User's saved search queries

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| user_id | UUID | FOREIGN KEY users(id), NOT NULL | User reference |
| query | TEXT | NOT NULL | Search query |
| created_at | TIMESTAMP | DEFAULT NOW() | Save date |

**Indexes:**
- `idx_saved_searches_user` on user_id

### 9. tracked_entities
**Purpose:** Entities users are monitoring

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| user_id | UUID | FOREIGN KEY users(id), NOT NULL | User reference |
| entity_name | TEXT | NOT NULL | Entity being tracked |
| entity_type | TEXT | NOT NULL | Type (PERSON, ORG) |

**Indexes:**
- `idx_tracked_entities_user` on user_id
- UNIQUE(user_id, entity_name)

## Materialized Views

### entity_weekly_mentions_mv
**Purpose:** Pre-aggregated entity mention counts for performance

```sql
CREATE MATERIALIZED VIEW entity_weekly_mentions_mv AS
SELECT 
    e.normalized_name,
    e.entity_type,
    EXTRACT(WEEK FROM ep.published_at) as week_number,
    EXTRACT(YEAR FROM ep.published_at) as year,
    COUNT(*) as mention_count,
    COUNT(DISTINCT ep.id) as episode_count
FROM extracted_entities e
JOIN episodes ep ON e.episode_id = ep.id
GROUP BY e.normalized_name, e.entity_type, week_number, year;
```

**Indexes:**
- `idx_entity_weekly_name` on normalized_name
- `idx_entity_weekly_type` on entity_type

**Refresh:** Nightly via `refresh_entity_mentions()` function

## Key Functions

### similarity_search(query_embedding vector, limit int)
```sql
-- Find similar episodes using pgvector
CREATE OR REPLACE FUNCTION similarity_search(
    query_embedding vector(1536),
    result_limit int DEFAULT 10
)
RETURNS TABLE (
    episode_id UUID,
    similarity_score float,
    podcast_name text,
    episode_title text
) AS $
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        1 - (e.embedding <-> query_embedding) as similarity_score,
        e.podcast_name,
        e.episode_title
    FROM episodes e
    WHERE e.embedding IS NOT NULL
    ORDER BY e.embedding <-> query_embedding
    LIMIT result_limit;
END;
$ LANGUAGE plpgsql;
```

## Row Level Security (RLS)

Currently disabled for MVP, but will be enabled for:
- `saved_searches` - Users can only see their own
- `tracked_entities` - Users can only see their own
- `users` - Users can only update their own profile

## Performance Considerations

1. **Vector Indexes:** Using IVFFlat for approximate nearest neighbor search
2. **Materialized Views:** Pre-computed aggregations refreshed nightly
3. **Query Cache:** Reduces OpenAI API calls by ~80%
4. **Connection Pooling:** Will enable pgBouncer if concurrent connections >20

## Data Statistics (As of Genesis Sprint)

| Table | Row Count | Notes |
|-------|-----------|-------|
| episodes | 1,171 | All processed |
| topic_mentions | ~1,400 | 5 tracked topics |
| extracted_kpis | ~50,000 | Financial metrics |
| extracted_entities | ~123,000 | People, companies, locations |
| query_cache | 0 | Will grow with usage |

## Future Considerations

- **Partitioning:** May partition episodes by year if >10,000 episodes
- **Read Replicas:** For scaling search queries
- **Additional Indexes:** Based on query patterns in production