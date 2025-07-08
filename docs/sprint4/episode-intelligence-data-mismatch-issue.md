# Episode Intelligence Data Mismatch Issue

## Current Status (2025-01-08)

### What's Working
1. ✅ The API code is correctly updated and deployed
2. ✅ `episode_metadata.episode_id` field now contains GUID values (matching `guid` field)
3. ✅ The API is properly checking the `episode_id` field

### The Problem
The `episode_intelligence` collection contains different episode IDs than `episode_metadata`:

```json
// episode_metadata sample
{
  "guid": "0e983347-7815-4b62-87a6-84d988a772b7",
  "episode_id": "0e983347-7815-4b62-87a6-84d988a772b7"  // Same as guid ✓
}

// episode_intelligence sample
{
  "episode_id": "02fc268c-61dc-4074-b7ec-882615bc6d85"  // Different ID ✗
}
```

### Data Summary
- `episode_metadata`: 1,236 documents
- `episode_intelligence`: 50 documents
- **Matching episodes**: 0

## Root Cause
The `episode_intelligence` collection was populated with different episode IDs than the GUIDs used in `episode_metadata`. This means:
1. The Episode Intelligence API cannot find matching intelligence data
2. The API returns mock data as a fallback

## Solution Required

### Option 1: Update episode_intelligence Collection (Recommended)
Update the `episode_id` field in `episode_intelligence` to match the GUIDs from `episode_metadata`.

**MongoDB Script:**
```javascript
// First, create a mapping of titles to GUIDs from episode_metadata
var guidMap = {};
db.episode_metadata.find().forEach(function(doc) {
  if (doc.raw_entry_original_feed && doc.raw_entry_original_feed.episode_title) {
    guidMap[doc.raw_entry_original_feed.episode_title] = doc.guid;
  }
});

// Then update episode_intelligence with matching GUIDs
db.episode_intelligence.find().forEach(function(intel) {
  // You'll need to determine how to match episodes
  // This might require looking at other fields like title, date, etc.
  // For now, this is a placeholder
  print("Episode Intelligence ID: " + intel.episode_id);
  // Update logic would go here
});
```

### Option 2: Create New Mapping Collection
Create a mapping collection that links `episode_intelligence.episode_id` to `episode_metadata.guid`.

### Option 3: Re-populate episode_intelligence
Re-run the Episode Intelligence generation process using the correct GUIDs from `episode_metadata`.

## Testing the Fix

Once the episode IDs are aligned, test with:

```bash
# Check if IDs now match
curl https://podinsight-api.vercel.app/api/intelligence/test-match | jq

# Check if dashboard returns real data
curl https://podinsight-api.vercel.app/api/intelligence/dashboard?limit=1 | jq
```

Success indicators:
- `intelligence_match_found: true` in test-match
- Real episode titles (not "Sample Episode") in dashboard
- Multiple signals per episode

## Current API Behavior
Until the data is fixed, the API will:
1. Search for matching intelligence data using `episode_id`
2. Find no matches
3. Return mock data with a warning message

## Priority
**CRITICAL** - This blocks the entire Episode Intelligence feature (Story 5B) and Dashboard integration (Story 4)
