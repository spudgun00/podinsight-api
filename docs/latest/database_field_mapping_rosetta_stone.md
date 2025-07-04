# PodInsightHQ Database Field Mapping - Rosetta Stone
**Created**: 2025-01-03  
**Purpose**: Single source of truth for field mappings across MongoDB, Supabase, and S3

## 📊 Database Overview

### Systems Involved:
1. **MongoDB** (Database: `podinsight`)
   - `episode_metadata` - 1,236 documents
   - `episode_transcripts` - 1,171 documents  
   - `transcript_chunks_768d` - 823,763 documents
   - `sentiment_results` - 62 documents

2. **Supabase** 
   - `episodes` table - 1,171 rows

3. **S3 Buckets**
   - `pod-insights-raw` - Raw audio + minimal metadata
   - `pod-insights-stage` - Transcripts + AI-enriched data

## 🔑 Primary Key Relationships

### Critical ID Mapping
| System | Field Name | Example Value | Notes |
|--------|------------|---------------|-------|
| MongoDB `episode_metadata` | `guid` | "0e983347-7815-4b62-87a6-84d988a772b7" | Primary key |
| MongoDB `episode_transcripts` | `episode_id` | "1216c2e7-42b8-42ca-92d7-bad784f80af2" | Same as guid |
| MongoDB `transcript_chunks_768d` | `episode_id` | "1216c2e7-42b8-42ca-92d7-bad784f80af2" | Contains guid value |
| Supabase `episodes` | `guid` | "8ed9141e-1c61-4164-84d7-f0a2c29fa0bc" | Matches MongoDB |
| S3 Path Structure | `{feed_slug}/{guid}/` | "a16z-podcast/0e983347-7815-4b62-87a6-84d988a772b7/" | Uses guid in path |

**⚠️ Important**: The `episode_id` field in MongoDB chunks actually contains the GUID value, just named differently.

## 📋 Complete Field Mapping - Rosetta Stone

### Core Episode Information

| Concept | MongoDB `episode_metadata` | MongoDB `episode_transcripts` | MongoDB `transcript_chunks_768d` | Supabase `episodes` | S3 Path/File | Sample Value | Notes |
|---------|---------------------------|------------------------------|--------------------------------|-------------------|--------------|--------------|-------|
| **Episode ID** | `guid` | `episode_id` | `episode_id` | `guid` | `{guid}` in path | "0e983347-7815-4b62-87a6-84d988a772b7" | Primary identifier |
| **Episode Title** | `raw_entry_original_feed.episode_title` | - | - | `episode_title` | In transcript JSON | "Chris Dixon: Stablecoins..." | Title in nested object in MongoDB |
| **Podcast Name** | `podcast_title` | - | `feed_slug` | `podcast_name` | `{feed_slug}` in path | "a16z Podcast" | Different fields |
| **Podcast Slug** | `raw_entry_original_feed.podcast_slug` | `feed_slug` | `feed_slug` | - | `{feed_slug}` in path | "a16z-podcast" | Hyphenated version |
| **Publish Date** | `raw_entry_original_feed.published_date_iso` | - | - | `published_at` | In metadata | "2025-06-09T10:00:00" | ISO format |
| **Audio URL** | `raw_entry_original_feed.mp3_url_original` | - | - | - | - | "https://mgln.ai/e/1344/..." | Original feed URL |
| **Duration** | - | - | - | `duration_seconds` | In metadata | 3915 | Seconds |
| **Word Count** | - | `word_count` | - | `word_count` | In transcript | 12373 | Total words |

### Content & Transcript Fields

| Concept | MongoDB `episode_metadata` | MongoDB `episode_transcripts` | MongoDB `transcript_chunks_768d` | Supabase `episodes` | S3 Path/File | Sample Value | Notes |
|---------|---------------------------|------------------------------|--------------------------------|-------------------|--------------|--------------|-------|
| **Full Transcript** | - | `full_text` | - | - | `transcripts/*.json` | "People use the term AI..." | Complete text |
| **Transcript Chunks** | - | - | `text` | - | - | "People use the term AI..." | ~150 word segments |
| **Chunk Index** | - | - | `chunk_index` | - | - | 0, 1, 2... | Sequential |
| **Start Time** | - | - | `start_time` | - | In segments JSON | 1.069 | Seconds |
| **End Time** | - | - | `end_time` | - | In segments JSON | 3.831 | Seconds |
| **Speaker** | - | - | `speaker` | - | In segments JSON | "SPEAKER_01" | May be null |
| **Embeddings** | - | - | `embedding_768d` | - | `embeddings/{guid}.npy` | [0.024, -0.154, ...] | 768-dim vector |

### S3 Storage Paths

| Concept | MongoDB `episode_metadata` | MongoDB `episode_transcripts` | MongoDB `transcript_chunks_768d` | Supabase `episodes` | S3 Path/File | Sample Value | Notes |
|---------|---------------------------|------------------------------|--------------------------------|-------------------|--------------|--------------|-------|
| **S3 Audio Path** | `s3_audio_path` | - | - | `s3_audio_path` | `/audio/episode.mp3` | "s3://pod-insights-raw/..." | Raw bucket |
| **S3 Stage Prefix** | `s3_artifacts_prefix_stage` | - | - | `s3_stage_prefix` | Base folder | "s3://pod-insights-stage/..." | Stage bucket |
| **S3 Embeddings** | `embedding_path` | - | - | `s3_embeddings_path` | `/embeddings/{guid}.npy` | "s3://pod-insights-stage/..." | NumPy arrays |
| **Transcript Path** | `final_transcript_json_path` | - | - | - | `/transcripts/*.json` | Complex filename | See naming patterns |
| **Segments Path** | `segments_file_path` | - | - | - | `/segments/{guid}.json` | Simple naming | |
| **Entities Path** | `cleaned_entities_path` | - | - | - | `/cleaned_entities/*.json` | Different folder name | |
| **KPIs Path** | `episode_kpis_path` | - | - | - | `/kpis/kpis_{guid}.json` | GUID in filename | |

### Processing & System Fields

| Concept | MongoDB `episode_metadata` | MongoDB `episode_transcripts` | MongoDB `transcript_chunks_768d` | Supabase `episodes` | S3 Path/File | Sample Value | Notes |
|---------|---------------------------|------------------------------|--------------------------------|-------------------|--------------|--------------|-------|
| **Created Timestamp** | `_import_timestamp` | `created_at` | `created_at` | `created_at` | - | "2025-06-25T07:35:59.353Z" | Import/creation time |
| **Updated Timestamp** | - | - | `updated_at` | `updated_at` | - | "2025-06-18T12:54:44.795556+00:00" | Last modified |
| **Processing Status** | `processing_status` | - | - | - | - | "completed" | ETL status |
| **Processing End Time** | `processed_utc_transcribe_enrich_end` | - | - | - | - | "2025-06-23T14:48:08.469987" | When enrichment finished |
| **Fetch Time** | `raw_entry_original_feed.fetch_processed_utc` | - | - | - | - | "2025-06-23T10:32:39.326872" | When fetched |
| **Schema Version** | `schema_version` | - | - | - | - | 1 | Data model version |
| **Segment Count** | `segment_count` | - | - | - | - | 411 | Number of segments |
| **Reading Time** | - | `reading_time_minutes` | - | - | - | 13 | Estimated minutes |

### Additional Metadata

| Concept | MongoDB `episode_metadata` | MongoDB `episode_transcripts` | MongoDB `transcript_chunks_768d` | Supabase `episodes` | S3 Path/File | Sample Value | Notes |
|---------|---------------------------|------------------------------|--------------------------------|-------------------|--------------|--------------|-------|
| **Hosts** | `hosts` | - | - | - | - | [] | Array of objects |
| **Guests** | `guests` | - | - | - | - | [{"name": "Chris Dixon", "role": "guest"}] | Array of objects |
| **Categories** | `categories` | - | - | - | - | [] | Episode categories |
| **iTunes Explicit** | `itunes_explicit` | - | - | - | - | false | Content flag |
| **Entity Count** | `entity_stats.cleaned_entity_count` | - | - | - | - | 144 | Number of entities |
| **Audio Hash** | `raw_entry_original_feed.audio_content_hash` | - | - | - | - | "a91b44599..." | SHA256 hash |

## 🔍 Naming Inconsistencies & Gotchas

### 1. **ID Field Naming Confusion**
- ❌ **Problem**: `episode_id` in chunks collection actually contains the GUID
- ✅ **Solution**: Always join on `episode_metadata.guid = transcript_chunks_768d.episode_id`

### 2. **Podcast Name vs Feed Slug**
- **MongoDB**: Uses both `podcast_title` ("a16z Podcast") and `podcast_slug` ("a16z-podcast")
- **Supabase**: Only has `podcast_name` (human-readable)
- **S3**: Uses hyphenated slug in paths
- ⚠️ **Gotcha**: Need to convert between formats

### 3. **Nested vs Flat Data**
- **MongoDB `episode_metadata`**: Many fields nested under `raw_entry_original_feed`
- **Other collections**: Flat structure
- ⚠️ **Gotcha**: Episode title is at `raw_entry_original_feed.episode_title`, not `episode_title`

### 4. **Missing Fields**
- **Duration**: Only in Supabase, not in MongoDB metadata
- **Full transcript**: Only in `episode_transcripts`, not in chunks or metadata
- **Embeddings**: In chunks collection and S3, not in episode metadata

### 5. **Date Format Differences**
- **MongoDB**: ISO strings without timezone ("2025-06-09T10:00:00")
- **Supabase**: ISO strings with timezone ("2025-02-11T02:02:45+00:00")
- **S3 filenames**: May use dates like "2025-01-22" in transcript filenames

### 6. **Complex S3 File Naming**
- **Transcripts**: `{feed}-{date}-{episode-title}_{guid-partial}_raw_transcript.json`
- **Meta files**: `meta_{full-guid}_details.json`
- **KPI files**: `kpis_{full-guid}.json`
- ⚠️ **Gotcha**: Can't hardcode paths, must use pattern matching

### 7. **Different ID Formats**
Valid GUID formats found:
- Standard UUID: `"0e983347-7815-4b62-87a6-84d988a772b7"`
- UUID v1: `"e405359e-ea57-11ef-b8c4-ff74e39a637e"`
- Custom format: `"flightcast:qoefujdsy5huurb987mnjpw2"`

## 📊 Data Coverage Analysis

### Current State (as of document creation):
- ✅ **MongoDB to MongoDB**: 100% of chunks have corresponding metadata
- ❓ **MongoDB to Supabase**: Both have ~1,171 episodes but different GUIDs
- ✅ **MongoDB to S3**: Paths stored in metadata documents

### Missing Data Patterns:
1. **Supabase `episodes`**: Generic titles like "Episode 8ed9141e" suggest incomplete data import
2. **MongoDB `episode_metadata`**: Some fields null despite data in nested `raw_entry_original_feed`
3. **No transcript storage in Supabase**: All transcript data only in MongoDB

## 🔧 MongoDB Index Configuration

### episode_metadata
- `_id_`: Default MongoDB index
- `guid_unique`: Unique index on GUID
- `episode_title_text`: Full-text search on title
- `podcast_slug`: Index on nested field
- `published_date`: Index on publish date
- `processing_date`: Index on processing completion

### episode_transcripts
- `episode_id_1`: Index on episode_id (GUID)
- `feed_slug_1`: Index on podcast slug
- `created_at_-1`: Descending index on creation time

### transcript_chunks_768d
- `episode_chunk_unique`: Compound unique index on episode_id + chunk_index
- `feed_slug_1`: Index on podcast slug
- `created_at_-1`: Descending index on creation time
- `text_search_index`: Full-text search on chunk text

## 💡 Recommendations

### For Development:
1. **Standardize ID field names**: Consider renaming `episode_id` to `guid` for consistency
2. **Flatten nested data**: Extract commonly used fields from `raw_entry_original_feed`
3. **Add missing fields**: Ensure duration, full title available in all systems
4. **Sync Supabase data**: Update generic episode titles with real titles from MongoDB

### For Queries:
1. **Always use GUID for joins**: It's the only reliable link between collections
2. **Check nested fields first**: Many values are under `raw_entry_original_feed`
3. **Handle multiple ID formats**: Support UUIDs and custom formats like "flightcast:xxx"
4. **Use pattern matching for S3**: Don't hardcode file paths

### For Data Quality:
1. **Validate GUID consistency**: Ensure all systems use same GUID for same episode
2. **Complete Supabase migration**: Import full metadata including real titles
3. **Document ID format rules**: Clarify when custom formats are used
4. **Regular sync checks**: Verify data consistency across systems

---

**Note**: This document represents the current state as of 2025-01-03. Regular updates recommended as systems evolve.