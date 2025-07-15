# MongoDB Text Search Investigation Results

## Summary
The MongoDB text index is working correctly. The issue is with the query logic when using multiple quoted phrases.

## Key Findings

### 1. Text Index Status
- ✅ Text index exists: `text_search_index` on the `text` field
- ✅ Index is functional and returns results for simple queries
- ✅ Collection has 823,763 documents
- ✅ Index size is reasonable (251.15 MB)

### 2. Query Behavior Analysis

#### Working Queries:
- Single terms: `ai` → 22,575 results (0.07s)
- Single quoted phrases: `"venture capital"` → 756 results (0.05s)
- Multiple unquoted terms (OR logic): `ai valuation` → 23,765 results (0.08s)
- Mixed with one quoted phrase: `ai "artificial intelligence"` → 266 results (0.18s)

#### Failing Queries:
- Multiple quoted phrases: `"venture capitalists" "artificial intelligence"` → 0 results
- Production query with many quoted phrases → 0 results (36s!)

### 3. Root Cause
MongoDB text search treats multiple quoted phrases as AND conditions. The query:
```
vcs "venture capitalists" investors ai "artificial intelligence" ml valuations valuation pricing "ai valuations"
```

Is looking for documents that contain:
- The words: vcs OR investors OR ai OR ml OR valuations OR valuation OR pricing
- AND the exact phrase "venture capitalists"
- AND the exact phrase "artificial intelligence"
- AND the exact phrase "ai valuations"

No documents in the collection contain all three quoted phrases together.

### 4. Performance Issue
The 36-second query time for complex queries with multiple quoted phrases suggests MongoDB is doing an expensive search trying to find documents matching all conditions.

## Recommendations

### 1. Immediate Fix - Modify Query Logic
Instead of using multiple quoted phrases, use OR logic:

```javascript
// Instead of:
'vcs "venture capitalists" investors ai "artificial intelligence" ml valuations'

// Use:
'vcs venture capitalists investors ai artificial intelligence ml valuations'
```

This will find documents containing ANY of these terms, then use scoring to rank by relevance.

### 2. Code Changes in improved_hybrid_search.py

The issue is in the `_text_search` method around line 391:
```python
if not any(w in stop_words for w in words_in_phrase):
    search_terms.append(f'"{term}"')  # This adds quotes!
```

**Options:**
1. Remove quotes entirely for multi-word phrases
2. Limit to only one quoted phrase per query
3. Use a more sophisticated query builder that understands when to use quotes

### 3. Alternative Approach - Scoring-Based Ranking
Instead of relying on exact phrase matching, use:
1. Unquoted terms for broad matching
2. Post-process results to boost documents containing exact phrases
3. Rely on the hybrid scoring system to rank results

### 4. Consider Query Preprocessing
Before sending to MongoDB:
1. Extract the most important phrase (if any) to quote
2. Leave other terms unquoted
3. Use the text score combined with vector similarity for final ranking

## Test Results Summary

| Query Type | Example | Results | Time |
|------------|---------|---------|------|
| Single term | `ai` | 22,575 | 0.07s |
| Single phrase | `"venture capital"` | 756 | 0.05s |
| Multiple terms (OR) | `ai valuation` | 23,765 | 0.08s |
| One quoted phrase | `ai "artificial intelligence"` | 266 | 0.18s |
| Two quoted phrases | `"venture capitalists" "artificial intelligence"` | 0 | 0.04s |
| Complex production query | Multiple quotes | 0 | 36s |

## Next Steps
1. Update the text search query builder to avoid multiple quoted phrases
2. Test the modified query logic
3. Monitor query performance after changes
4. Consider adding query complexity limits or warnings
