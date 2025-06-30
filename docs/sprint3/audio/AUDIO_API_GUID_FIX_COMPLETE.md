# Audio API GUID Fix - Implementation Complete

**Date**: June 30, 2025
**Fixed By**: Backend Team
**Status**: ✅ FIXED - Ready for deployment

## Issue Summary

The frontend team reported 500 errors when calling the audio API with episode IDs from search results. The root cause was a mismatch in ID formats:

- **Search API returns**: GUIDs (e.g., `673b06c4-cf90-11ef-b9e1-0b761165641d`)
- **Audio API expected**: MongoDB ObjectIds (e.g., `685ba776e4f9ec2f0756267a`)

## Solution Implemented

Modified `api/audio_clips.py` to accept both ID formats:

1. **Auto-detection**: The API now detects whether the episode_id is:
   - ObjectId format (24 hex characters)
   - GUID format (8-4-4-4-12 pattern)

2. **Dual path support**:
   - **GUID path**: Directly queries `transcript_chunks_768d` collection
   - **ObjectId path**: Uses original flow through `episode_metadata` (backward compatible)

## Code Changes

```python
# New validation logic
is_object_id = False
is_guid = False

# Check for ObjectId format (24 hex characters)
try:
    if len(episode_id) == 24:
        ObjectId(episode_id)
        is_object_id = True
except Exception:
    pass

# Check for GUID format (8-4-4-4-12 with hyphens)
guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
if re.match(guid_pattern, episode_id):
    is_guid = True

# Different MongoDB lookup based on ID type
if is_guid:
    # Direct lookup - skip episode_metadata
    guid = episode_id
    chunk = db.transcript_chunks_768d.find_one({"episode_id": guid})
else:
    # Original path - lookup guid via episode_metadata
    episode = db.episode_metadata.find_one({"_id": ObjectId(episode_id)})
    guid = episode.get("guid")
```

## Testing

### Test Script Created
```bash
python scripts/test_guid_audio_fix.py
```

This tests:
- ObjectId format (backward compatibility)
- GUID format (from search results)
- Both should now work correctly

### Frontend Test Data
These GUIDs from the frontend report will now work:
- `673b06c4-cf90-11ef-b9e1-0b761165641d`
- `9497d063-69c2-4701-9951-931c1599b170`

## Deployment

The fix has been committed and will be live after Vercel deployment (~6 minutes).

## What Frontend Needs to Know

1. **No changes required** on frontend
2. Continue sending episode IDs exactly as received from search API
3. The audio API now handles both formats automatically
4. Error messages are improved to indicate invalid ID format

## Verification Steps

Once deployed, test with:

```bash
# Test with GUID (from search results)
curl "https://podinsight-api.vercel.app/api/v1/audio_clips/673b06c4-cf90-11ef-b9e1-0b761165641d?start_time_ms=556789"

# Should return 200 OK with audio clip URL (or 422 if no transcript data)
```

## Architecture Clarification

The system now supports two flows:

1. **Search → Audio (NEW)**:
   ```
   Search API returns GUID → Audio API accepts GUID → Direct MongoDB lookup
   ```

2. **Legacy ObjectId flow (PRESERVED)**:
   ```
   ObjectId → episode_metadata lookup → Extract GUID → Continue as before
   ```

## Contact

If issues persist after deployment, check:
1. CloudWatch logs for specific error details
2. Verify the episode has transcript data in MongoDB
3. Ensure audio files exist in S3 for that episode

The fix maintains 100% backward compatibility while supporting the frontend's GUID-based requests.
