# MongoDB Text Index Fix Plan

## Issue Summary
- Text search is taking 24.64 seconds (should be <1 second)
- MongoDB Atlas is suggesting to create a text index (indicating current index may be misconfigured)
- PyMongo upgrade question: 4.7.2 → 4.13

## Step 1: Diagnose Text Index Issue

Run the diagnostic script to check your current text index:

```bash
cd /Users/jamesgill/PodInsights/podinsight-api
python scripts/check_text_index_safe.py
```

This will show:
- What indexes currently exist
- Whether the text index is being used
- Performance metrics for simple vs complex queries

## Step 2: Fix Text Index

Based on what MongoDB Atlas is suggesting, you likely need to:

### Option A: If no text index exists
```javascript
// In MongoDB Atlas shell or Compass
use podinsight
db.transcript_chunks_768d.createIndex({"text": "text"})
```

### Option B: If text index exists but isn't working
```javascript
// Drop the existing broken index
db.transcript_chunks_768d.dropIndex("text_index_name")

// Create a new one with explicit configuration
db.transcript_chunks_768d.createIndex(
  { "text": "text" },
  {
    name: "text_index",
    default_language: "english",
    language_override: "language"
  }
)
```

### Option C: If field name mismatch
If your documents have the transcript in a different field (e.g., `transcript` instead of `text`):
```javascript
db.transcript_chunks_768d.createIndex({"transcript": "text"})
```

## Step 3: PyMongo Upgrade Decision

### ⚠️ IMPORTANT: Motor Compatibility Required

If you upgrade PyMongo 4.7.2 → 4.13, you MUST also upgrade Motor:
- PyMongo 4.9+ requires Motor 3.6+
- Check your current Motor version: `pip show motor`

### Upgrade Commands (if you decide to upgrade)
```bash
pip install --upgrade pymongo==4.13.0 motor==3.6.0
```

### Benefits of Upgrading
- Performance improvements
- Better connection handling
- Bug fixes
- Better async support

### Risks
- Must ensure Motor is also upgraded
- Requires Python 3.9+ (check with `python --version`)
- Minor API changes

### My Recommendation
**Hold off on the upgrade for now**. First fix the text index issue, which is the root cause of your performance problem. Once search is working properly, then consider the upgrade.

## Step 4: Query Optimization

The current implementation generates too many search terms. Consider this optimization:

```python
# In improved_hybrid_search.py, modify _extract_query_terms()

# Current: Generates 10+ terms including all synonyms
# Better: Limit to top 5-6 most relevant terms

# Add this after building terms dict:
if len(search_terms) > 6:
    # Sort by weight and take top 6
    sorted_terms = sorted(query_terms.items(), key=lambda x: x[1], reverse=True)
    search_terms = [term for term, _ in sorted_terms[:6]]
```

## Step 5: Verify Fix

After creating/fixing the text index:

1. Run a test query in MongoDB Atlas:
   ```javascript
   db.transcript_chunks_768d.find(
     { $text: { $search: "ai valuations" } }
   ).explain("executionStats")
   ```

2. Check that it shows:
   - `stage: "TEXT"` (not COLLSCAN)
   - `executionTimeMillis: < 1000`

3. Deploy and monitor logs for:
   - `[TEXT_SEARCH] Execution time:` should be <1s
   - Total search time should be <3s

## Expected Results

After fixing the text index:
- Text search: <1 second (down from 24.64s)
- Total search time: <3 seconds (down from 27.56s)
- Stable performance within Vercel's limits

## MongoDB Atlas Index Creation

If using Atlas UI:
1. Go to your cluster
2. Navigate to Collections → podinsight → transcript_chunks_768d
3. Click "Indexes" tab
4. Click "Create Index"
5. Use this JSON:
   ```json
   {
     "text": "text"
   }
   ```
6. Click "Create"

The index creation might take a few minutes depending on collection size.
