# Text Search Performance Fix

## Root Cause Identified

The text index IS working perfectly (0.06s for queries), but the application code adds a `$lookup` stage that joins with `episode_metadata` collection, causing the 24+ second delays.

## The Problem

The text search pipeline:
1. ✅ Text search with index (fast - 0.06s)
2. ❌ $lookup join with episode_metadata (SLOW - 24s)
3. $unwind the metadata
4. $project to extract fields

The `$lookup` is performing a join for every document, which is extremely expensive.

## Solutions

### Option 1: Remove the $lookup (Fastest)

If the metadata fields aren't critical for search results, remove the lookup entirely:

```python
# In improved_hybrid_search.py, _text_search method
# Remove these stages from the pipeline:
# - $lookup
# - $unwind
# - The metadata field projections
```

### Option 2: Optimize with Index on episode_metadata

Create an index on the join field:

```javascript
// In MongoDB Atlas
db.episode_metadata.createIndex({"episode_id": 1})
```

### Option 3: Denormalize Data (Best Long-term)

Store the frequently needed metadata directly in transcript_chunks_768d:

```javascript
// During ETL, add these fields to each chunk:
{
  "podcast_name": "...",
  "episode_title": "...",
  "published": "..."
}
```

### Option 4: Limit Before Lookup (Quick Fix)

Move the $limit before the $lookup to reduce join operations:

```python
pipeline = [
    {
        "$match": {
            "$text": {"$search": search_string}
        }
    },
    {
        "$addFields": {
            "text_score": {"$meta": "textScore"}
        }
    },
    {"$sort": {"text_score": -1}},
    {"$limit": limit},  # MOVE THIS BEFORE $lookup
    # Then do $lookup only on the limited results
    {
        "$lookup": {
            "from": "episode_metadata",
            "localField": "episode_id",
            "foreignField": "episode_id",
            "as": "metadata"
        }
    },
    # ... rest of pipeline
]
```

## Immediate Fix

The quickest fix is Option 4 - it's a one-line change that should reduce the lookup operations from thousands to just 50 (or whatever your limit is).

## Testing the Fix

After applying the fix, you should see:
- Text search time: <1 second (down from 24.64s)
- Total search time: <3 seconds
- No more timeout warnings

## Verification

To verify the episode_metadata collection has an index:

```javascript
// In MongoDB Atlas shell
db.episode_metadata.getIndexes()

// If no index on episode_id, create one:
db.episode_metadata.createIndex({"episode_id": 1})
```

This index will make the $lookup operations much faster.
