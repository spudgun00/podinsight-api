# MongoDB Text Search Performance Issue

## Current Status

After deploying the MongoDB timeout fixes:
- ✅ Connection establishment is fast (0.04s)
- ✅ Vector search is fast (0.67s)
- ❌ **Text search is extremely slow (24.64s)**
- ❌ Total search time: 27.56s (dangerously close to Vercel's 30s limit)

## Root Cause Analysis

The 24-second text search strongly suggests MongoDB is performing a **full collection scan (COLLSCAN)** instead of using a text index. This happens when:

1. No text index exists on the collection
2. The text index exists but the query structure prevents its use
3. The text index is corrupted or needs rebuilding

## Diagnostic Steps

1. **Run the diagnostic script**:
   ```bash
   cd mongodb_info
   python text_search_diagnostics.py
   ```

2. **Check MongoDB Atlas UI**:
   - Go to your cluster → Collections → transcript_chunks_768d
   - Click on "Indexes" tab
   - Look for a text index on the "text" field

3. **If no text index exists**, create one:
   ```javascript
   db.transcript_chunks_768d.createIndex({ "text": "text" })
   ```

## Query Optimization

The current query uses many search terms (10 in the example):
```
"vcs venture capitalists investors ai artificial intelligence ml valuations valuation pricing ai valuations"
```

This might be causing performance issues. Consider:

1. **Limit search terms**: Cap at 5-6 most relevant terms
2. **Remove synonyms**: Don't search for both "ai" and "artificial intelligence"
3. **Use phrase search**: For multi-word terms, use quotes

## Immediate Actions

1. **Fix MongoDB warming** (already done - changed `if collection:` to `if collection is not None:`)

2. **Deploy text index fix**:
   - Run diagnostic script to confirm missing index
   - Create text index if missing
   - Monitor performance improvement

3. **Optimize query generation**:
   - Reduce number of search terms
   - Remove redundant synonyms
   - Test performance with simplified queries

## Expected Results After Fix

- Text search: <1 second (down from 24.64s)
- Total search time: <3 seconds (down from 27.56s)
- No more "remainingTimeMS: 9" warnings
- Stable performance well within Vercel's 30s limit

## Monitoring

Look for these improvements in logs:
- `[TEXT_SEARCH] Execution time: X.XXs` should be <1s
- `[HYBRID_LATENCY]` should be <2000ms
- Total search time should be <3s
