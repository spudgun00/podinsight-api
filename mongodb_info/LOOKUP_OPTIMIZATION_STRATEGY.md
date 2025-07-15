# MongoDB $lookup Optimization Strategy

## The Challenge
- We NEED the $lookup to join episode_metadata for podcast names, titles, and dates
- Without it, search results would lack crucial context
- But $lookup is expensive, especially when done on thousands of documents

## Current Status
✅ **Text Search (3.72s)**: Already optimized with `$limit` before `$lookup`
❌ **Vector Search (8.94s)**: Was doing `$lookup` on all results BEFORE limiting

## The Fix Applied
1. **Vector Search Pipeline Optimization**:
   - Added `$project` to reduce document size before lookup
   - Moved `$limit` BEFORE `$lookup`
   - This means we only join metadata for the top N results, not all candidates

2. **Why This Works**:
   - Vector search returns results sorted by similarity score
   - We only need metadata for the final results shown to users
   - Limiting before lookup reduces joins from potentially 200 to just 50-100

## Example Impact
Before:
- Vector search finds 200 candidates
- Does 200 $lookup operations (expensive!)
- Then limits to 50 results

After:
- Vector search finds 200 candidates
- Sorts by score, limits to 50
- Does only 50 $lookup operations (75% reduction!)

## Future Optimizations
1. **Denormalization** (Best long-term):
   - Store frequently needed fields directly in transcript_chunks_768d
   - Fields: podcast_name, episode_title, published_date
   - Eliminates need for $lookup entirely

2. **Caching**:
   - Cache episode_metadata in application memory
   - Do joins in application code instead of MongoDB

3. **Batch Loading**:
   - Load all needed metadata in one query
   - Join in application code

## Monitoring
After deployment, watch for:
- Vector search time should drop from 8.94s to <2s
- Total search time should be <5s
- No increase in memory usage
