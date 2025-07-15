# How to Verify MongoDB Text Index is Working

## Quick Ways to Check

### 1. From MongoDB Atlas UI
- Go to your cluster → Collections → podinsight → transcript_chunks_768d
- Click "Indexes" tab
- Look for an index with `"text": "text"` in the definition
- If you see it, the index exists (but may not be working properly)

### 2. From MongoDB Shell/Compass
```javascript
// List all indexes
db.transcript_chunks_768d.getIndexes()

// Look for output like:
{
  "v": 2,
  "key": {
    "_fts": "text",
    "_ftsx": 1
  },
  "name": "text_1",
  "weights": {
    "text": 1
  },
  "default_language": "english",
  "language_override": "language",
  "textIndexVersion": 3
}
```

### 3. Using Explain to Verify Usage

The most important test - is the index actually being USED?

```javascript
// Run this in MongoDB shell
db.transcript_chunks_768d.find(
  { $text: { $search: "ai valuations" } }
).explain("executionStats")

// Check the output for these key indicators:
```

## Signs the Index IS Working ✅

1. **In the explain output**:
   ```javascript
   "winningPlan": {
     "stage": "TEXT",  // ✅ Good! Using text index
     "indexName": "text_1"
   }
   ```

2. **Execution stats show**:
   - `executionTimeMillis`: < 1000 (under 1 second)
   - `totalDocsExamined`: Much less than total collection size
   - `indexesUsed`: ["text_1"]

3. **In your logs**:
   - `[TEXT_SEARCH] Execution time: 0.XXs` (under 1 second)
   - No "remainingTimeMS: 9" warnings

## Signs the Index is NOT Working ❌

1. **In the explain output**:
   ```javascript
   "winningPlan": {
     "stage": "COLLSCAN",  // ❌ Bad! Full collection scan
   }
   ```

2. **Execution stats show**:
   - `executionTimeMillis`: > 5000 (many seconds)
   - `totalDocsExamined`: Equal to total documents in collection
   - `indexesUsed`: []

3. **In your logs**:
   - `[TEXT_SEARCH] Execution time: 24.XXs` (many seconds)
   - "remainingTimeMS: 9" warnings
   - Timeouts or near-timeouts

## Common Issues and Solutions

### Issue 1: Index exists but not used
**Symptom**: You see the index in getIndexes() but explain shows COLLSCAN

**Possible causes**:
- Field name mismatch (index on "text" but documents have "transcript")
- Index corruption
- Query too complex

**Solution**:
```javascript
// Check actual field names in documents
db.transcript_chunks_768d.findOne()

// If field name is different, create index on correct field
db.transcript_chunks_768d.createIndex({"actual_field_name": "text"})
```

### Issue 2: Index creation failed silently
**Symptom**: No text index in getIndexes()

**Solution**:
```javascript
// Create with explicit error checking
db.transcript_chunks_768d.createIndex(
  {"text": "text"},
  {background: true}
)

// Check for errors
db.getLastError()
```

### Issue 3: Performance still poor with index
**Symptom**: TEXT stage in explain but still slow

**Possible causes**:
- Too many search terms
- Index doesn't fit in memory
- Network latency

**Solution**:
- Limit search terms to 5-6
- Check index size: `db.transcript_chunks_768d.stats()`
- Consider compound index if filtering by other fields

## Run Diagnostic Script

To get all this information automatically:

```bash
cd /Users/jamesgill/PodInsights/podinsight-api
python scripts/check_text_index_safe.py
```

This script will:
1. Check if text index exists
2. Verify document structure
3. Test with explain()
4. Measure actual performance
5. Provide specific recommendations
