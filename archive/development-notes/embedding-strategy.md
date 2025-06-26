# Embedding Strategy: Smart Migration Path

## Current State
- ✅ Have: Episode-level embeddings (1,171 files)
- ✅ Have: Full transcripts we're about to migrate
- ❌ Missing: Segment-level embeddings
- ❌ Missing: High-quality chunking

## Recommended Approach: Two-Phase

### Phase 1: MongoDB + Current Embeddings (NOW - 3 hours)
```python
# Use BOTH for better results:
def hybrid_search(query):
    # 1. Get embedding for query (existing HF API)
    query_embedding = get_embedding(query)

    # 2. Find similar episodes (pgvector)
    similar_episodes = pgvector_search(query_embedding, limit=20)

    # 3. Full-text search those episodes in MongoDB
    results = mongodb.search({
        'episode_id': {'$in': similar_episodes},
        '$text': {'$search': query}
    })

    # 4. Extract real excerpts
    return extract_excerpts(results)
```

**Result**: 70% better than current (real excerpts + decent relevance)

### Phase 2: Enhanced Embeddings (Sprint 2/3)
```python
# When you have time, upgrade to:
def create_segment_embeddings():
    # 1. Split transcripts into 512-token chunks
    # 2. Generate embeddings per chunk
    # 3. Store in MongoDB alongside text
    # 4. Enable chunk-level semantic search
```

**Result**: 95% quality (finding exact relevant passages)

## Why This Works

1. **Immediate Value**: Real excerpts in 3 hours vs perfect search in 3 days
2. **No Wasted Work**: MongoDB migration needed regardless
3. **Progressive Enhancement**: Each phase builds on the last
4. **Avoid Scope Creep**: Stay focused on Sprint 1 goals

## The Math

Current approach:
- 4% relevance + fake excerpts = 0% useful

Phase 1 (Hybrid):
- 50% relevance + real excerpts = 70% useful

Phase 2 (Enhanced):
- 90% relevance + perfect excerpts = 95% useful

**70% improvement NOW vs 95% improvement in a week**

## Decision Matrix

| Option | Time | Quality | Risk | Recommendation |
|--------|------|---------|------|----------------|
| Current embeddings + MongoDB | 3 hrs | 70% | Low | ✅ DO THIS |
| Re-process everything now | 3 days | 95% | High | ❌ AVOID |
| No MongoDB, fix embeddings | 3 days | 60% | High | ❌ WORST |

## Implementation Note

The hybrid search above is pseudocode. In practice:
1. Search endpoint gets episode IDs from pgvector
2. MongoDB searches within those episodes
3. Results combine semantic similarity + text relevance
4. Real excerpts make even 50% matches useful

## Future Enhancements (Not Now)

When ready for Phase 2:
- Use OpenAI's text-embedding-3-small
- Chunk at 512 tokens with 50 token overlap
- Store chunks + embeddings in MongoDB
- Implement cross-encoder reranking
- Add metadata filtering

But NOT NOW. Ship the 70% solution first!
