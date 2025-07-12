# Vercel Functions Inventory

## Current Functions Count: 13+ (exceeds 12 limit)

### Active Functions in api/ directory

1. **api/audio_clips.py** ✅ ACTIVE
   - Purpose: Audio clip generation endpoints
   - Used by: Included in api/index.py as router
   - Status: Keep - core feature

2. **api/improved_hybrid_search.py** ✅ ACTIVE
   - Purpose: New hybrid search implementation (vector + text)
   - Used by: Standalone function, newest search implementation
   - Status: Keep - latest search improvement

3. **api/index.py** ✅ ACTIVE
   - Purpose: Main app entry point
   - Includes: audio_clips, intelligence, prewarm routers
   - Status: Keep - main entry point

4. **api/intelligence.py** ✅ ACTIVE
   - Purpose: Episode intelligence endpoints
   - Used by: Included in api/index.py as router
   - Status: Keep - core feature

5. **api/mongodb_search.py** ⚠️ LEGACY
   - Purpose: Old MongoDB text search handler
   - Used by: api/topic_velocity.py imports get_search_handler()
   - Status: Still in use, but likely replaced by improved_hybrid_search

6. **api/mongodb_vector_search.py** ⚠️ LEGACY
   - Purpose: Old MongoDB vector search handler
   - Used by: api/search_lightweight_768d.py imports get_vector_search_handler()
   - Status: Still in use, but likely replaced by improved_hybrid_search

7. **api/prewarm.py** ✅ ACTIVE
   - Purpose: Modal pre-warming endpoint (just added)
   - Used by: Included in api/index.py as router
   - Status: Keep - new feature for cost optimization

8. **api/search_lightweight_768d.py** ✅ ACTIVE
   - Purpose: Current lightweight search implementation
   - Used by: api/topic_velocity.py imports search_handler_lightweight_768d
   - Status: Keep - currently active search

9. **api/sentiment_analysis_v2.py** ✅ ACTIVE
   - Purpose: Sentiment analysis endpoint (reads pre-computed data)
   - Used by: Standalone function with vercel.json rewrite
   - Status: Keep or consolidate - low priority feature

10. **api/synthesis.py** ✅ ACTIVE
    - Purpose: Search synthesis functionality
    - Used by: Likely used by search endpoints
    - Status: Keep - core search feature

11. **api/topic_velocity.py** ✅ ACTIVE
    - Purpose: Core topic tracking functionality
    - Used by: Mounted at root in api/index.py
    - Status: Keep - core feature

### Non-Function Files

12. **api/database.py** ❌ NOT A FUNCTION
    - Purpose: Database utilities
    - Used by: Imported by other modules
    - Status: Helper file, not counted as function

13. **api/middleware/__init__.py** ❌ NOT A FUNCTION
    - Purpose: Middleware package init
    - Status: Helper file, not counted as function

14. **api/middleware/auth.py** ❌ NOT A FUNCTION
    - Purpose: Authentication middleware
    - Status: Helper file, not counted as function

### Functions from vercel.json rewrites

15. **/api/diag** ⚠️ REFERENCED
    - File: Likely in .vercel/cache/index/api/diag.py
    - Status: Test/debug endpoint

16. **/api/test_audio** ⚠️ REFERENCED
    - File: test/api_test_endpoints/test_audio.py
    - Status: Test endpoint

## Recommendations

### Safe to Remove/Archive:
1. **api/diag** - Test endpoint, remove from vercel.json
2. **api/test_audio** - Test endpoint, remove from vercel.json

### Requires Investigation:
1. **api/mongodb_search.py** - Used by topic_velocity.py, but might be replaceable with improved_hybrid_search
2. **api/mongodb_vector_search.py** - Used by search_lightweight_768d.py, but might be replaceable with improved_hybrid_search

### Consolidation Options:
1. Move **sentiment_analysis_v2.py** into api/index.py as a router (like audio_clips)
2. Investigate if search can be unified under improved_hybrid_search.py

## Dependencies to Check Before Removing:

- mongodb_search.py is imported by:
  - api/topic_velocity.py (line 25)

- mongodb_vector_search.py is imported by:
  - api/search_lightweight_768d.py (line 219)

Both seem to be legacy implementations that might be replaced by improved_hybrid_search.py
