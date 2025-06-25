# MongoDB Data Model - Single Source of Truth

**Last Updated**: June 25, 2025  
**Purpose**: Document the ACTUAL MongoDB data model and ID relationships  
**Critical**: The `guid` field is the primary key linking all collections

## ✅ ID RELATIONSHIP CLARIFIED

The ID fields are correctly aligned:
- `episode_metadata`: Uses `guid` (e.g., "1216c2e7-42b8-42ca-92d7-bad784f80af2")
- `transcript_chunks_768d`: Uses `episode_id` which **IS the GUID** (e.g., "1216c2e7-42b8-42ca-92d7-bad784f80af2")

**These IDs match perfectly**. The field is named `episode_id` but contains the GUID value.

## 📊 MongoDB Collections Overview

### Database: `podinsight`

| Collection | Document Count | Primary Key | Purpose |
|------------|---------------|-------------|----------|
| `episode_metadata` | 1,236 | `guid` | Complete episode metadata from S3 |
| `episode_transcripts` | 1,171 | `guid` | Full episode transcripts |
| `transcript_chunks_768d` | 823,763 | `episode_id` | Vector embeddings for search |

## 📄 Collection Schemas

### 1. `episode_metadata` Collection
**Purpose**: Master source for all episode metadata  
**Source**: Imported from S3 metadata files on June 25, 2025

```javascript
{
  _id: ObjectId("685ba6df1531246a77e71c63"),
  
  // PRIMARY KEY - This should link all collections
  guid: "0e983347-7815-4b62-87a6-84d988a772b7",
  
  // Nested metadata from RSS feed
  raw_entry_original_feed: {
    guid: "0e983347-7815-4b62-87a6-84d988a772b7",
    podcast_slug: "a16z-podcast",
    podcast_title: "a16z Podcast",
    episode_title: "Chris Dixon: Stablecoins, Startups, and the Crypto Stack",
    feed_url: "https://feeds.simplecast.com/JGE3yC0V",
    published_date_iso: "2025-06-09T10:00:00",
    mp3_url_original: "https://mgln.ai/e/1344/...",
    s3_audio_path_raw: "s3://pod-insights-raw/a16z-podcast/0e983347.../audio/...",
    audio_content_hash: "a91b445992e1fd87d051350fb45c50e40a9e1a5597df99837d2538e520e37791",
    fetch_processed_utc: "2025-06-23T10:32:39.326872",
    processing_status: "fetched",
    schema_version: "1.0_minimal_fetch"
  },
  
  // Top-level metadata fields
  schema_version: 1,
  podcast_title: "a16z Podcast",
  podcast_feed_url: "https://feeds.simplecast.com/JGE3yC0V",
  podcast_generator: null,
  podcast_language: null,
  podcast_itunes_author: null,
  podcast_copyright: null,
  
  // Episode-specific fields
  episode_title: null,  // Note: Actual title is in raw_entry_original_feed
  episode_summary_original: null,
  episode_copyright: null,
  published_original_format: null,
  categories: [],
  episode_url: null,
  audio_url_original_feed: null,
  audio_type_original_feed: null,
  audio_length_bytes_original_feed: null,
  
  // iTunes metadata
  itunes_explicit: false,
  itunes_episode_type: null,
  itunes_subtitle: null,
  itunes_summary: null,
  
  // People involved
  hosts: [],
  guests: [
    {name: "Chris Dixon", role: "guest"},
    {name: "A16Z Crypto", role: "guest"},
    {name: "Chris", role: "guest"}
  ],
  
  // Processing paths
  segments_path: "/tmp/podcast_transcribe_0e983347.../segments/...",
  entities_path: "/tmp/podcast_transcribe_0e983347.../entities_raw/...",
  embedding_path: "/tmp/podcast_transcribe_0e983347.../embeddings/...",
  cleaned_entities_path: "s3://pod-insights-stage/a16z-podcast/0e983347.../cleaned_entities/...",
  
  // Statistics
  entity_stats: {
    raw_entity_count: 219,
    cleaned_entity_count: 144
  },
  
  // Content references
  title: null,
  link: null,
  summary: null,
  segment_count: 411,
  supports_timestamp: true,
  transcript_s3_path: null,
  final_transcript_json_path: "s3://pod-insights-stage/a16z-podcast/0e983347.../transcripts/...",
  segments_file_path: "s3://pod-insights-stage/a16z-podcast/0e983347.../segments/...",
  episode_kpis_path: "s3://pod-insights-stage/a16z-podcast/0e983347.../kpis/...",
  
  // Processing metadata
  processed_utc_transcribe_enrich_end: "2025-06-23T14:48:08.469987",
  processing_status: "completed",
  s3_audio_path: "s3://pod-insights-raw/a16z-podcast/0e983347.../audio/...",
  s3_artifacts_prefix_stage: "s3://pod-insights-stage/a16z-podcast/0e983347.../",
  
  // Import metadata
  _import_timestamp: ISODate("2025-06-25T07:35:59.353Z"),
  _s3_path: "s3://pod-insights-stage/a16z-podcast/0e983347.../meta/..."
}
```

### 2. `episode_transcripts` Collection
**Purpose**: Full transcript text with segments  
**Expected Key**: Should use `guid` to match `episode_metadata`

```javascript
{
  _id: ObjectId("..."),
  guid: "0e983347-7815-4b62-87a6-84d988a772b7",  // Should match episode_metadata
  podcast_name: "a16z Podcast",
  episode_title: "Chris Dixon: Stablecoins, Startups, and the Crypto Stack",
  published_at: ISODate("2025-06-09T10:00:00Z"),
  
  // Full transcript
  full_text: "Complete episode transcript combined from all segments...",
  word_count: 12373,
  
  // Time-coded segments
  segments: [
    {
      text: "Welcome to the a16z podcast...",
      speaker: "SPEAKER_01",
      start_time: 0.0,
      end_time: 5.2
    },
    // ... more segments
  ],
  
  // Topics (denormalized from analysis)
  topics: ["Crypto", "Stablecoins", "Web3"],
  
  // Migration metadata
  migrated_at: ISODate("2025-06-25T00:00:00Z"),
  source_s3_path: "s3://pod-insights-stage/a16z-podcast/..."
}
```

### 3. `transcript_chunks_768d` Collection
**Purpose**: Vector embeddings for semantic search  
**✅ KEY**: The `episode_id` field contains the GUID value

```javascript
{
  _id: ObjectId("68583bba8741b0b51e8d1f43"),  // MongoDB's internal ID
  
  // PRIMARY KEY - This IS the GUID (just named differently)
  episode_id: "1216c2e7-42b8-42ca-92d7-bad784f80af2",  // Same as episode_metadata.guid!
  
  feed_slug: "a16z-podcast",  // This might be the only common field
  chunk_index: 23,
  text: "Chris Dixon explains how stablecoins are...",
  start_time: 1420.5,
  end_time: 1450.2,
  speaker: "SPEAKER_01",
  
  // 768-dimensional embedding from Instructor-XL model
  embedding_768d: [0.023, -0.154, 0.891, ...],  // 768 float values
  
  // Metadata for search results
  chunk_metadata: {
    word_count: 150,
    topics: ["Stablecoins", "Crypto"]
  }
}
```

## 🔗 ID Relationships (Correct Understanding)

### The Reality
```
episode_metadata.guid = transcript_chunks_768d.episode_id

Example:
- episode_metadata.guid: "1216c2e7-42b8-42ca-92d7-bad784f80af2"
- transcript_chunks_768d.episode_id: "1216c2e7-42b8-42ca-92d7-bad784f80af2" ✅ SAME!
```

### Key Points
1. The `episode_id` field in chunks **contains the GUID value**
2. The naming is inconsistent but the values match
3. No mapping or transformation needed
4. The API code should already work if it's comparing these values

### Why Search Might Still Show "Unknown Episode"
1. **Deployment Issue**: API changes not yet deployed to Vercel
2. **Data Subset**: Some chunks might be from a different dataset
3. **Query Logic**: API might not be looking up metadata correctly

## 🚀 API Integration Points

### Current Implementation (SHOULD WORK)
```python
# In mongodb_vector_search.py
# This is actually CORRECT - episode_id contains the GUID value
episode_guids = list(set(chunk['episode_id'] for chunk in chunks))
metadata_docs = list(self.db.episode_metadata.find({"guid": {"$in": episode_guids}}))
```

### This Should Work Because:
1. `chunk['episode_id']` = "1216c2e7-42b8-42ca-92d7-bad784f80af2"
2. `metadata.guid` = "1216c2e7-42b8-42ca-92d7-bad784f80af2"
3. The MongoDB query correctly matches these values

## 📊 Data Flow

```
User Search Query
    ↓
Modal.com Embedding (768D)
    ↓
MongoDB Vector Search (transcript_chunks_768d)
    Returns: episode_id (contains GUID value) ✅
    ↓
MongoDB Metadata Lookup (episode_metadata)
    Searches: guid (matches episode_id) ✅
    ↓
✅ Match Found → Real Episode Title
```

## 🔧 Recommended Solution (Going Forward)

### 1. **Document the Schema Clearly**
Add comments in code and documentation that `episode_id` contains GUID values:
```javascript
// transcript_chunks_768d.episode_id contains the RSS feed GUID
// This matches episode_metadata.guid
```

### 2. **Consider Field Renaming (Long-term)**
For clarity, consider renaming during next major refactor:
```javascript
// Future schema improvement
db.transcript_chunks_768d.updateMany(
  {},
  {$rename: {"episode_id": "episode_guid"}}
)
```

### 3. **Add Validation**
Ensure all new chunks have valid GUIDs:
```javascript
// Validation rule
{
  episode_id: {
    $regex: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
  }
}
```

## 📋 Action Items

1. **Immediate**: Verify Vercel deployment has completed
2. **Short-term**: Add clear documentation about field relationships
3. **Long-term**: Consider renaming fields for clarity

## 🎯 Success Criteria

The system will work correctly when:
- Vector search returns chunks with `episode_id`
- API can map these to `guid` values
- Metadata enrichment finds matching episodes
- Search results show real episode titles

---

**Note**: This document reflects the ACTUAL state as of June 25, 2025. The ID mismatch is preventing the search from displaying real episode titles.