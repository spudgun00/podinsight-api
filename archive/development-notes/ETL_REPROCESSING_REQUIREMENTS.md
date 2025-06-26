# ETL Reprocessing Requirements

**Date**: June 21, 2025
**Purpose**: Requirements for reprocessing transcripts to fix coverage and ID issues

---

## 🎯 Primary Goals

1. **Fix 83% Missing Content** - Include ALL transcript segments
2. **Maintain Episode ID Consistency** - Use Supabase GUIDs throughout
3. **Create Larger, Overlapping Chunks** - Better search context

---

## 📋 Critical Requirements

### 1. Episode ID Handling ✅
```python
# ALWAYS use the GUID from Supabase episodes table
episode_guid = episode['guid']  # e.g., "1216c2e7-42b8-42ca-92d7-bad784f80af2"

# This GUID should be used EVERYWHERE:
- In MongoDB chunk documents as 'episode_id'
- In S3 file paths
- In all cross-references

# Never use Supabase's internal 'id' field
```

### 2. Complete Coverage (NO FILTERING!)
```python
# Current (BAD) - Aggressive filtering:
if segment['duration'] > 0.5 and segment['speaker'] and segment['text'].strip():
    # Only ~17% of segments pass this filter!

# New (GOOD) - Include everything:
for segment in all_segments:
    # Include ALL segments, even if:
    # - No speaker identified
    # - Short duration
    # - Silent portions
    # - Single words
    # Just include everything!
```

### 3. Chunk Creation Strategy
```python
# Current: Tiny chunks (often single sentences)
# New: Larger chunks with overlap

CHUNK_DURATION = 30  # seconds (was ~2-3 seconds)
OVERLAP = 5  # seconds overlap between chunks

# This gives ~120 chunks per hour instead of ~1800
# Each chunk will have meaningful context
```

### 4. Required Fields for Each Chunk
```json
{
  "episode_id": "1216c2e7-42b8-42ca-92d7-bad784f80af2",  // Supabase GUID
  "feed_slug": "a16z-podcast",                            // From S3 path
  "chunk_index": 0,                                        // Sequential
  "text": "Full text of 30-second segment...",            // Complete text
  "embedding_768d": [768 floats],                         // From Modal API
  "start_time": 0.0,                                      // In seconds
  "end_time": 30.0,                                      // In seconds
  "speaker": "Ben Horowitz",                              // If available
  "word_count": 95,                                       // For stats
  "created_at": "2025-06-21T..."                         // Timestamp
}
```

### 5. Modal.com Embedding Generation
```python
# Use the Modal endpoint for 768D embeddings
MODAL_URL = "https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run"

async def generate_embedding(text):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{MODAL_URL}/embed",
            json={"text": text, "model": "instructor-xl"}
        ) as response:
            result = await response.json()
            return result["embedding"]  # 768D vector
```

---

## 🚫 What NOT to Do

1. **Don't filter out content** - Include everything
2. **Don't use Supabase internal IDs** - Only use the 'guid' field
3. **Don't create tiny chunks** - Use 30-second windows
4. **Don't skip silent portions** - They provide context
5. **Don't require speaker identification** - Include unattributed speech

---

## 📊 Expected Outcomes

### Before (Current):
- ~182 chunks per episode (83% loss)
- Episode IDs don't match Supabase
- Tiny chunks with no context
- Many search misses

### After (Target):
- ~1,000+ chunks per episode (near 100% coverage)
- Episode IDs match Supabase GUIDs perfectly
- 30-second chunks with overlap
- Comprehensive search coverage

---

## 🔄 Migration Process

1. **Keep existing collection** during reprocessing
2. **Create new collection**: `transcript_chunks_768d_v2`
3. **Process in batches** to avoid overwhelming Modal
4. **Verify coverage** by comparing segment counts
5. **Switch over** once new collection is complete

---

## 📝 Validation Checklist

- [ ] Episode IDs in chunks match Supabase `guid` field
- [ ] Average ~1000 chunks per hour of content
- [ ] No gaps > 5 seconds between consecutive chunks
- [ ] All chunks have 768D embeddings
- [ ] Text field contains 20-150 words per chunk
- [ ] Chunks have proper start/end timestamps

---

## 🔗 MongoDB Index

Create the same vector search index on the new collection:
```javascript
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding_768d": {
        "dimensions": 768,
        "similarity": "cosine",
        "type": "knnVector"
      }
    }
  }
}
```

Index name: `vector_index_768d_v2`

---

## 💡 Pro Tips

1. **Test with one episode first** to verify the process
2. **Log chunk counts** to ensure complete coverage
3. **Use async/batch processing** for Modal embeddings
4. **Keep S3 paths consistent** with episode GUIDs
5. **Add progress tracking** for long-running process

---

*This ensures the ETL process creates searchable chunks with complete coverage and proper ID alignment.*
