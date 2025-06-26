# Vector Search Implementation Findings

**Date**: June 21, 2025
**Status**: 768D Vector Search Working but with Data Quality Issues

---

## Executive Summary

The 768D vector search using Modal.com and MongoDB Atlas is technically functioning correctly, achieving high similarity scores (0.96+) for semantic queries. However, there are significant data quality and user experience issues that need to be addressed before this can provide a good search experience.

---

## ✅ What's Working

1. **Modal.com Integration**
   - Instructor-XL (2GB model) successfully deployed on Modal
   - Endpoint healthy and responding with 768D embeddings
   - Response times: ~0.3-0.5s per embedding

2. **MongoDB Atlas Vector Search**
   - Vector index (`vector_index_768d`) created and READY
   - 823,763 chunks indexed with 768D embeddings
   - Semantic search returning high-quality matches (scores 0.96+)

3. **API Integration**
   - `search_lightweight_768d.py` correctly using Modal for embeddings
   - Fallback chain working: Vector → Text → pgvector
   - No more local model loading (good for Vercel's 250MB limit)

---

## ❌ Critical Issues

### 1. **Metadata Mismatch**
- **Problem**: Zero overlap between episode IDs in different collections
  - `transcript_chunks_768d`: 1,171 unique episodes (created June 21, 2025)
  - `transcripts`: 1,000 unique episodes (migrated June 19, 2025)
  - **0 matching episode_ids between collections**

- **Impact**: Search results show "Unknown Episode" instead of actual episode titles
- **Root Cause**: Different data ingestion runs with different episode sets

### 2. **Truncated Text Chunks**
- **Problem**: Chunks are extremely short (single sentences, 2-5 seconds each)
  ```
  Example chunks:
  - "Nobody wants to do data entry." (30 chars)
  - "Like, what does that mean?" (26 chars)
  - "An AI." (6 chars)
  ```

- **Impact**: Users can't read meaningful context around search matches
- **Root Cause**: Chunking strategy created sentence-level segments with gaps

### 3. **Incomplete Coverage**
- **Problem**: 142 gaps found between chunks in a single episode
  - Original: 1,082 segments in full transcript
  - Indexed: Only 182 chunks (83% reduction)

- **Impact**: Missing content that might be relevant to searches
- **Root Cause**: Filtering/grouping during chunk creation removed silent portions

---

## 📊 Data Structure Analysis

### Current Collections:

1. **transcript_chunks_768d** (823,763 docs)
   ```
   Fields: chunk_index, episode_id, embedding_768d, text,
           start_time, end_time, feed_slug, speaker
   ```
   - Has embeddings but minimal metadata
   - Very short text segments
   - Episode IDs don't match other collections

2. **transcripts** (1,000 docs)
   ```
   Fields: episode_id, podcast_name, episode_title, published_at,
           segments, full_text, topics, word_count
   ```
   - Has rich metadata and full segments
   - No connection to the 768D chunks
   - Different episode set entirely

---

## 🔍 Technical Decisions to Review

### 1. **File Naming Confusion**
- `search_lightweight_768d.py` - Currently used (good)
- `search_heavy.py` - Uses local models (should be removed)
- `search_lightweight.py` - Old version (should be removed)

**Recommendation**: Rename to just `search.py` since Modal makes it "lightweight"

### 2. **Supabase Caching**
- Code was trying to cache embeddings in non-existent Supabase table
- Already commented out during testing
- MongoDB vector search has its own in-memory cache

**Recommendation**: Implement MongoDB-based caching if needed

### 3. **Chunking Strategy**
Current approach creates very small, disconnected segments.

**Options to consider**:
- Re-chunk with larger windows (e.g., 30-60 second segments)
- Include surrounding context in search results
- Use sliding windows with overlap

---

## 🎯 Recommendations

### Immediate (for MVP):
1. **Accept current limitations** but clearly indicate truncation with "..."
2. **Use feed_slug** for podcast names (already implemented as fallback)
3. **Show timestamps** prominently so users know it's a snippet

### Short-term (1-2 weeks):
1. **Re-align data**: Re-run embeddings using episodes from transcripts collection
2. **Expand context**: Show ±2 chunks around each match for better readability
3. **Add metadata**: Store episode titles and dates with chunks

### Long-term (1+ month):
1. **Better chunking**: Re-process with paragraph-level or topic-based chunks
2. **Hybrid search**: Combine vector search with keyword highlighting
3. **Full segment retrieval**: Link from chunks to full segment text

---

## 💡 Key Questions for Product Team

1. **User Expectation**: Do users expect to read full conversations or just find relevant moments?

2. **Context Window**: How much text should surround a search match?

3. **Data Re-processing**: Is it feasible to re-run the embedding pipeline with better chunking?

4. **Episode Metadata**: How important is showing episode title, date, guest names?

5. **Search Accuracy vs Coverage**: Better to have precise small chunks or broader context?

---

## 📈 Performance Metrics

- **Modal API**: 0.3-0.5s per embedding
- **MongoDB Vector Search**: 0.5-2.5s per query
- **Total Search Time**: 3-6s (including metadata fetching)
- **Result Quality**: 0.96+ similarity scores
- **Coverage**: ~17% of original transcript content

---

## 🚨 Risk Assessment

**High Risk**:
- Poor user experience due to truncated text
- Missing relevant content due to chunking gaps

**Medium Risk**:
- Episode metadata not available
- Potential Modal API costs at scale

**Low Risk**:
- Technical implementation is solid
- Fallback mechanisms working

---

## Next Steps

1. **Get product decision** on acceptable chunk size and context
2. **Estimate effort** for re-processing data with better chunking
3. **Consider hybrid approach**: Use current system for finding moments, then fetch full context
4. **Plan data alignment**: Match episode IDs between collections

---

*Prepared by: Technical Analysis Team*
*For: Product and Engineering Leadership*
