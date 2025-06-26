# EMERGENCY: MongoDB Storage Bloat Issue - Full Context

## Critical Issue Summary
**Date**: 2025-06-22
**Status**: UNRESOLVED - Requires immediate attention
**Impact**: Storage increased from 20GB to 38GB (~18GB waste)
**Cause**: Duplicated full episode text across ALL chunks instead of storing once per episode

## Root Cause Analysis

### What Happened
1. User requested importing episode text files to MongoDB for episode-level search
2. Claude (assistant) created `import_episode_text.py` script
3. **CRITICAL ERROR**: Script added `full_episode_text` to EVERY chunk in an episode
4. For episodes with 100+ chunks, this duplicated the same text 100+ times
5. Storage exploded from 20GB to 38GB during import process

### The Problematic Code
```python
# FROM: import_episode_text.py:89-100
result = await chunks_collection.update_many(
    {"episode_id": episode_id},
    {"$set": {
        "full_episode_text": full_text,  # ❌ DUPLICATED ACROSS ALL CHUNKS
        "episode_title_full": data.get('title'),
        "text_word_count": len(full_text.split()),
        "text_char_count": len(full_text)
    }}
)
```

### Current MongoDB State
- **Collection**: `transcript_chunks_768d`
- **Affected Fields**: `full_episode_text`, `episode_title_full`, `text_word_count`, `text_char_count`, `text_imported_at`
- **Problem**: These fields duplicated across ~500K+ chunks
- **Connection Status**: MongoDB cluster experiencing connection issues due to resource strain

## Attempted Solutions

### 1. Emergency Cleanup Scripts Created
- `emergency_cleanup.py` - Comprehensive cleanup with verification
- `emergency_cleanup_simple.py` - Direct cleanup without checks
- `emergency_mongo_cleanup.js` - MongoDB shell script

### 2. Connection Issues
```
pymongo.errors.ServerSelectionTimeoutError: No replica set members match selector "Primary()"
Topology: ReplicaSetNoPrimary
- shard-00-00: Connection refused
- shard-00-01: RSSecondary (responding)
- shard-00-02: Connection refused
```

## Required Cleanup Operation
```javascript
// MongoDB shell command needed:
db.transcript_chunks_768d.updateMany(
    {},
    {
        $unset: {
            "full_episode_text": "",
            "episode_title_full": "",
            "text_word_count": "",
            "text_char_count": "",
            "text_imported_at": ""
        }
    }
);
```

## Next Session Action Plan

### Immediate Priority (Session Start)
1. **Check MongoDB cluster health**
   ```bash
   source venv/bin/activate
   python emergency_cleanup_simple.py
   ```

2. **If Python fails, use MongoDB Compass**
   - Connect to cluster: `podinsight-cluster.bgknvz.mongodb.net`
   - Navigate to `podinsight.transcript_chunks_768d`
   - Execute cleanup script via Compass shell

3. **Verify cleanup success**
   ```python
   # Check storage recovery
   chunks_with_text = await chunks_collection.count_documents({"full_episode_text": {"$exists": True}})
   # Should return 0
   ```

### Post-Cleanup: Correct Implementation
**Goal**: Store episode text ONCE per episode, not per chunk

**Option 1**: Separate episodes collection
```python
# Create: db.episodes_text
{
    "episode_id": "guid",
    "full_text": "...",
    "title": "...",
    "metadata": {...}
}
```

**Option 2**: Add to first chunk only
```python
# Only update first chunk per episode
await chunks_collection.update_one(
    {"episode_id": episode_id, "chunk_sequence": 0},
    {"$set": {"full_episode_text": full_text}}
)
```

## File References
- Emergency scripts: `emergency_cleanup.py`, `emergency_cleanup_simple.py`
- Problematic script: `import_episode_text.py:89-100`
- MongoDB script: `emergency_mongo_cleanup.js`
- Business case: `EPISODE_LEVEL_SEARCH_BUSINESS_CASE.md`

## User Context
User discovered issue when disk space monitoring showed sudden jump from 20GB to 38GB. User message: *"what are you doing??? the file size disk space has gone from 20gb to 38gb???"*

User explicitly requested: *"do it! sort this out. be reeally careful! you are making significant costly mistakes"*

## Technical Context
- **MongoDB**: Atlas cluster with replica set
- **Collection**: `transcript_chunks_768d` (~500K+ documents)
- **Environment**: `/Users/jamesgill/PodInsights/podinsight-api/venv`
- **Connection**: Motor async client with increased timeouts

## Prevention for Future
1. Always calculate storage impact before bulk operations
2. Test on small subset first (e.g., single episode)
3. Use separate collections for different data types
4. Implement proper episode-level vs chunk-level data architecture

---
**Status**: Awaiting new session to execute cleanup and implement correct solution
