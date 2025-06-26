# Context for Next Session - PodInsight API Debugging

## What We're Doing
Fixing the PodInsight podcast search API that returns 0 results for most queries. The system searches 823,763 podcast transcript chunks using vector embeddings.

## Why We're Doing This
Users can't search for podcast content. Queries like "venture capital" and "podcast" return 0 results despite the data existing in MongoDB.

## Where We're At
**Status: PARTIALLY WORKING** - Some queries work ("openai"), others fail ("venture capital")

### Working:
- ✅ Modal embedding service (generates 768D vectors)
- ✅ Direct MongoDB queries (returns 5 results for "venture capital")
- ✅ Query normalization (case insensitive)
- ✅ Some queries via API ("openai", "artificial intelligence")

### Failing:
- ❌ API returns 503 for "venture capital", "podcast", "sequoia"
- ❌ Single word queries fail: "venture", "capital", "vc", "ai"

## The Core Issue
**MongoDB returns results but API doesn't for same query** - proving it's an infrastructure/config issue, not code.

Test proof:
```
Query: "venture capital"
- Modal → MongoDB direct: ✅ 5 results (score 0.9920)
- MongoDB text search: ✅ 3 results
- API endpoint: ❌ 503 error
```

## Last Fixes Applied (June 25, 2025)

Following advisor's systematic plan:

1. **Fixed MongoDB pipeline bug** - Changed `$match` filter:
   ```python
   # FROM: {"score": {"$exists": True, "$ne": None}}
   # TO:   {"score": {"$gte": 0}}
   ```

2. **Added query normalization**: `query.strip().lower()`

3. **Enhanced debugging** - Added embedding norm, result counts, scores

4. **Created standardized embedding function** in `embedding_utils.py`

5. **Added CI/CD smoke tests** and fail-fast 503 behavior

**📄 FULL DETAILS: See `E2E_TEST_RESULTS_JUNE_25.md`**

## Suspected Root Causes
1. Environment variable mismatch (MONGODB_DATABASE)
2. Vector index configuration issue
3. API querying different database/collection than direct tests

## Next Steps
1. Enable DEBUG_MODE=true on Vercel
2. Check MongoDB Atlas index status for `vector_index_768d`
3. Verify environment variables match between local and Vercel
4. Test API locally with production MongoDB URI

## Key Files
- Main search: `api/search_lightweight_768d.py`
- MongoDB handler: `api/mongodb_vector_search.py`
- Test script: `scripts/test_venture_capital_query.py`
- Full report: **`E2E_TEST_RESULTS_JUNE_25.md`**

## Critical Insight
The advisor's code fixes are correct. Direct MongoDB queries work perfectly, but the same queries fail through the API. This confirms it's an infrastructure/configuration issue, not a code bug.
