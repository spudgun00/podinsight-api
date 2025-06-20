# Episode Titles Solution - Complete Analysis

## Problem Identified

✅ **ROOT CAUSE CONFIRMED**: All episodes in the Supabase database have generic titles like "Episode fa77104a" instead of meaningful episode titles.

## Database Structure Analysis

### Supabase Episodes Table (13 columns available):
```
- id                 (Primary key)
- guid               (Episode identifier)
- podcast_name       (✅ Good data: "This Week in Startups", "a16z Podcast", etc.)
- episode_title      (🚨 Bad data: "Episode 8ed9141e", "Episode 55fd6289", etc.)
- published_at       (✅ Good data: "2025-02-11T02:02:45+00:00")
- duration_seconds   (✅ Good data: 3915, 2551, etc.)
- s3_stage_prefix    (File paths)
- s3_audio_path      (Audio file locations)
- s3_embeddings_path (Embedding file locations)
- word_count         (Transcript word counts)
- created_at         (Record creation)
- updated_at         (Last modified)
- embedding          (Vector embeddings)
```

### MongoDB Transcripts Collection:
- **1000 documents** with full transcript data
- **Episode titles are also empty** in MongoDB
- Contains: `episode_id`, `podcast_name`, `full_text`, `segments`, `topics`

## Immediate Solution for Entity API

Replace the current generic titles with meaningful display names using available data:

### Current (Broken):
```sql
SELECT episode_title FROM episodes WHERE id = ?
-- Result: "Episode fa77104a" 
```

### Fixed Query:
```sql
SELECT 
    CASE 
        WHEN duration_seconds > 0 THEN 
            CONCAT(
                podcast_name, 
                ' - ', 
                ROUND(duration_seconds / 60), 
                ' min (', 
                TO_CHAR(published_at::date, 'Mon DD, YYYY'), 
                ')'
            )
        ELSE 
            CONCAT(
                podcast_name, 
                ' (', 
                TO_CHAR(published_at::date, 'Mon DD, YYYY'), 
                ')'
            )
    END as display_title,
    podcast_name,
    published_at,
    duration_seconds,
    id,
    guid
FROM episodes 
WHERE id = ?
```

### Results Comparison:

**BEFORE (Current):**
- ❌ Episode 8ed9141e
- ❌ Episode 55fd6289  
- ❌ Episode 7abc9af1

**AFTER (Fixed):**
- ✅ This Week in Startups - 65 min (Feb 11, 2025)
- ✅ a16z Podcast - 43 min (Mar 11, 2025)
- ✅ a16z Podcast - 35 min (Jan 28, 2025)

## Implementation Steps

1. **Update Entity API Query** - Replace `episode_title` with the improved display format
2. **Test with Sample Data** - Verify the new format works correctly
3. **Deploy Changes** - Push the fix to production
4. **Verify Results** - Check that entity responses now show meaningful titles

## Available Fields for Entity API

The following fields are available and contain good data:

```json
{
  "id": "3a50ef5b-6965-4ae5-a062-2841f83ca24b",
  "podcast_name": "This Week in Startups",
  "published_at": "2025-02-11T02:02:45+00:00",
  "duration_seconds": 3915,
  "word_count": 12373
}
```

## Alternative Display Formats

Choose the format that works best for your entity API:

1. **Podcast + Date**: `"This Week in Startups (Feb 11, 2025)"`
2. **Podcast + Duration + Date**: `"This Week in Startups - 65 min (Feb 11, 2025)"`
3. **Podcast + Duration**: `"This Week in Startups - 65 min"`
4. **Minimal**: `"This Week in Startups"`

## Long-term Solutions (Future Sprints)

1. **Title Recovery**: Parse RSS feeds to get original episode titles
2. **S3 Metadata**: Check if episode metadata exists in S3 storage
3. **Transcript Analysis**: Generate titles from transcript content
4. **Data Pipeline Fix**: Ensure future episodes capture proper titles

## Testing Commands

You can test the solution with these sample episode IDs:
- `3a50ef5b-6965-4ae5-a062-2841f83ca24b` (This Week in Startups)
- `1b50f025-61ca-4f14-b539-dc1b384944e9` (a16z Podcast)
- `48ecc221-27e6-4c40-9b4e-e8e3dd670474` (Acquired)

## Impact

This fix will immediately improve user experience by showing:
- **Meaningful podcast names** instead of "Episode xyz"
- **Episode dates** for context
- **Episode duration** for planning
- **Professional appearance** in entity results

The solution uses only existing data fields, requires no database changes, and can be deployed immediately.