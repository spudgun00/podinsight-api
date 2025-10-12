# 🚀 Session Resume: Populate duration_seconds Field in MongoDB

## 📍 Context

**Repository**: `/Users/jamesgill/PodInsights/podinsight-api` (BACKEND)
**Task**: Create and run migration script to populate `duration_seconds` field for all episodes
**Priority**: Medium - Improves search result display, eliminates need for frontend workarounds

---

## 🎯 Objective

Populate the `duration_seconds` field in the `episode_metadata` collection for all 1,236 episodes by calculating it from transcript chunks (same method the transcript endpoint uses).

---

## 📚 Background

### Current Situation:
- **MongoDB Status**: 0 out of 1,236 episodes have `duration_seconds` (0.0% coverage)
- **Transcript Endpoint**: Works perfectly - calculates duration from last chunk's `end_time`
- **Search Endpoint**: Cannot provide duration (only fetches matching chunks, not all chunks)
- **User Impact**: Dashboard cannot show episode duration in search results

### Why This Field Is Missing:
- Field was never populated during initial ETL/ingestion
- Each episode has transcript chunks with timestamps, but metadata lacks total duration
- Transcript endpoint calculates on-the-fly, but this is inefficient for search results

### Why We Should Fix This:
✅ Better UX - search results show complete metadata
✅ No frontend workarounds needed
✅ One-time task with permanent benefit
✅ Simple calculation (grab last chunk's `end_time`)
✅ Improves data quality in MongoDB

---

## 🔍 Technical Details

### How Transcript Endpoint Calculates Duration:

**File**: `/Users/jamesgill/PodInsights/podinsight-api/api/routers/transcripts.py`
**Line**: 79

```python
duration_seconds = int(transcript_chunks[-1].end_time) if transcript_chunks else 0
```

**Logic**:
1. Fetches ALL transcript chunks for an episode (sorted by chunk_index)
2. Takes the last chunk in the array
3. Uses that chunk's `end_time` as the total episode duration
4. Works because chunks are sequential and last chunk ends when episode ends

### MongoDB Collections:

**episode_metadata** (needs updating):
```javascript
{
  "_id": ObjectId("..."),
  "episode_id": "uuid-here",
  "podcast_title": "Podcast Name",
  "episode_title": "Episode Title",
  "published_at": "2024-01-15T10:30:00Z",
  "duration_seconds": null,  // ← THIS FIELD IS MISSING/NULL
  // ... other fields
}
```

**transcript_chunks_768d** (source of truth):
```javascript
{
  "_id": ObjectId("..."),
  "episode_id": "uuid-here",
  "chunk_index": 145,  // Last chunk for this episode
  "start_time": 3542.5,
  "end_time": 3572.8,  // ← THIS IS THE EPISODE DURATION
  "text": "... final words of the episode",
  // ... other fields
}
```

---

## 🛠️ Implementation Plan

### Step 1: Create Migration Script

**File**: `scripts/populate_duration_seconds.py`

**Script should**:
1. Connect to MongoDB
2. Get all episode_ids from `episode_metadata`
3. For each episode:
   - Query `transcript_chunks_768d` for chunks with that episode_id
   - Sort by chunk_index descending, limit 1 (get last chunk)
   - Extract `end_time` from last chunk
   - Update `episode_metadata` with `duration_seconds = int(end_time)`
4. Track progress (show count updated)
5. Handle errors gracefully (log episodes with no chunks)

**Pseudo-code**:
```python
async def populate_duration_seconds():
    db = client["podinsight"]
    metadata_collection = db["episode_metadata"]
    chunks_collection = db["transcript_chunks_768d"]

    # Get all episodes
    episodes = await metadata_collection.find({}).to_list(None)

    updated = 0
    errors = 0

    for episode in episodes:
        episode_id = episode["episode_id"]

        # Get last chunk for this episode
        last_chunk = await chunks_collection.find_one(
            {"episode_id": episode_id},
            sort=[("chunk_index", -1)]  # Descending = last chunk first
        )

        if last_chunk and "end_time" in last_chunk:
            duration = int(last_chunk["end_time"])

            # Update episode_metadata
            await metadata_collection.update_one(
                {"episode_id": episode_id},
                {"$set": {"duration_seconds": duration}}
            )
            updated += 1
        else:
            errors += 1
            print(f"⚠️  No chunks found for episode: {episode_id}")

    print(f"✅ Updated {updated} episodes")
    print(f"❌ {errors} episodes had no chunks")
```

### Step 2: Test on Small Sample

Before running on all 1,236 episodes:
1. Test on 5 episodes first
2. Verify the duration matches what transcript endpoint returns
3. Check MongoDB to confirm field is populated

**Test command**:
```bash
# Test on 5 episodes
python scripts/populate_duration_seconds.py --limit 5 --dry-run

# Verify results
python scripts/check_duration.py
```

**Expected output**:
```
Testing duration population...
✅ Episode abc123: 3572 seconds
✅ Episode def456: 2845 seconds
✅ Episode ghi789: 4120 seconds
✅ Episode jkl012: 1890 seconds
✅ Episode mno345: 3205 seconds

Verification:
Total documents: 1,236
Has duration_seconds: 5 (0.4%)  ← Should increase after full run
```

### Step 3: Run Full Migration

Once tested and verified:
```bash
# Run on all episodes
python scripts/populate_duration_seconds.py

# Verify completion
python scripts/check_duration.py
```

**Expected final output**:
```
Total documents: 1,236
Has duration_seconds: 1,236 (100.0%)  ← SUCCESS!
Missing/null/zero duration: 0 (0.0%)
```

### Step 4: Update Documentation

After successful migration:
1. Update `DASHBOARD_TROUBLESHOOTING_SEARCH_COMPONENT.md` Issue #4:
   - Change status from "LIMITATION DOCUMENTED" to "FIXED"
   - Note the field is now populated
   - Remove frontend workarounds

2. Update `FRONTEND_FIX_SEARCH_RESULTS.md`:
   - Change `duration_seconds` from optional to required
   - Remove "Handling Optional Fields" section
   - Update TypeScript interface: `duration_seconds: number` (not optional)

3. Test search endpoint to verify duration now appears in results

---

## 📋 Step-by-Step Checklist

### Phase 1: Create Script
- [ ] Create `scripts/populate_duration_seconds.py`
- [ ] Implement MongoDB connection with proper timeout handling
- [ ] Implement logic to fetch last chunk per episode
- [ ] Implement update logic with progress tracking
- [ ] Add error handling and logging
- [ ] Add `--limit` flag for testing
- [ ] Add `--dry-run` flag to preview without updating

### Phase 2: Test
- [ ] Run with `--limit 5 --dry-run` to preview changes
- [ ] Run with `--limit 5` to update 5 episodes
- [ ] Use `/tmp/check_duration.py` to verify 5 episodes updated
- [ ] Test one episode with transcript endpoint to compare duration
- [ ] Verify durations match between migration and transcript endpoint

### Phase 3: Execute
- [ ] Run full migration on all 1,236 episodes
- [ ] Monitor for errors
- [ ] Verify 100% coverage with `check_duration.py`
- [ ] Spot-check 10 random episodes to confirm accuracy

### Phase 4: Update Docs
- [ ] Update `DASHBOARD_TROUBLESHOOTING_SEARCH_COMPONENT.md` Issue #4
- [ ] Update `FRONTEND_FIX_SEARCH_RESULTS.md` TypeScript interface
- [ ] Remove "Handling Optional Fields" section from frontend guide
- [ ] Commit and push documentation updates

### Phase 5: Verify
- [ ] Test search endpoint: `curl "https://podinsight-api.vercel.app/api/search?query=AI&limit=5"`
- [ ] Verify response includes `duration_seconds` for all results
- [ ] Inform dashboard team that field is now populated
- [ ] Celebrate! 🎉

---

## 🔧 Key Files & References

### Files to Create:
- `scripts/populate_duration_seconds.py` - Migration script (NEW)

### Files to Reference:
- `/Users/jamesgill/PodInsights/podinsight-api/api/routers/transcripts.py:79` - Shows duration calculation
- `/tmp/check_duration.py` - Existing verification script

### Files to Update After Migration:
- `documentation/DASHBOARD_TROUBLESHOOTING_SEARCH_COMPONENT.md` - Update Issue #4 status
- `documentation/FRONTEND_FIX_SEARCH_RESULTS.md` - Remove optional field handling

### MongoDB Collections:
- **Source**: `transcript_chunks_768d` (contains `end_time` per chunk)
- **Target**: `episode_metadata` (needs `duration_seconds` populated)

---

## 🚨 Important Considerations

### Environment:
- **MongoDB URI**: Use `os.environ.get("MONGODB_URI")`
- **Timeout**: Set `serverSelectionTimeoutMS=30000` (30 seconds for long operations)
- **Deployment**: This is a one-time script, run locally (not deployed to Vercel)

### Error Handling:
- Some episodes might have NO chunks (data quality issue)
- Handle gracefully: log warning, skip update, continue
- Track count of errors for investigation

### Performance:
- 1,236 episodes = should take 2-5 minutes max
- Use `asyncio` for better performance
- Consider batch updates if needed (but probably not necessary)

### Verification:
- After migration, compare a few episodes with transcript endpoint
- Ensure durations match exactly
- Check for any episodes with `duration_seconds = 0` (indicates missing chunks)

---

## 💡 Example Verification Test

After running migration, verify one episode manually:

```bash
# 1. Get a random episode_id from MongoDB
python -c "
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def get_random_episode():
    client = AsyncIOMotorClient(os.environ.get('MONGODB_URI'))
    db = client['podinsight']
    episode = await db['episode_metadata'].find_one()
    print(f\"Episode ID: {episode['episode_id']}\")
    print(f\"Duration from metadata: {episode.get('duration_seconds', 'MISSING')}\")
    client.close()

asyncio.run(get_random_episode())
"

# 2. Get duration from transcript endpoint
curl -s "https://podinsight-api.vercel.app/api/transcript/{episode_id}" | jq '.duration_seconds'

# 3. Compare - they should match!
```

---

## 📊 Expected Results

**Before Migration**:
```
Total documents: 1,236
Has duration_seconds: 0 (0.0%)
Missing/null/zero duration: 1,236 (100.0%)
```

**After Migration**:
```
Total documents: 1,236
Has duration_seconds: 1,236 (100.0%)
Missing/null/zero duration: 0 (0.0%)
```

**Sample Episodes After**:
```
Episode abc123...: duration_seconds = 3572
Episode def456...: duration_seconds = 2845
Episode ghi789...: duration_seconds = 4120
```

---

## 🎯 Success Criteria

Migration is complete when:
- ✅ All 1,236 episodes have `duration_seconds` field populated
- ✅ Verification script shows 100% coverage
- ✅ Spot-check confirms durations match transcript endpoint
- ✅ Search API returns duration for all results
- ✅ Documentation updated to reflect field is now populated
- ✅ Dashboard team notified they can use the field
- ✅ No frontend workarounds needed

---

## 🚀 Quick Start for Next Session

```bash
# 1. Start in correct directory
cd /Users/jamesgill/PodInsights/podinsight-api

# 2. Create migration script
# (Follow implementation plan above)

# 3. Test on 5 episodes
python scripts/populate_duration_seconds.py --limit 5

# 4. Verify
python /tmp/check_duration.py

# 5. Run full migration
python scripts/populate_duration_seconds.py

# 6. Update docs and push to GitHub
```

Good luck! This should be a straightforward task that provides immediate value. 🎉
