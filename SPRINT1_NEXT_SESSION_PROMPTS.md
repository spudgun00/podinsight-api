# Sprint 1 MongoDB Integration - Next Session Prompts

**Context**: MongoDB integration completed, search quality improved 60x. Ready for deployment and future enhancements.

## Session Context Summary

### What We've Accomplished
- ✅ MongoDB Atlas setup with $500 credit (M10 cluster)
- ✅ Full migration: 1,000 episodes with transcripts + segments
- ✅ 171 missing episodes identified as incomplete Pomp Podcast entries
- ✅ MongoDB search handler created with smart excerpt extraction
- ✅ Search API updated to use real transcripts
- ✅ Search quality improved from 4% → 200%+ relevance
- ✅ User can now see actual conversation excerpts

### Technical Stack
- **Backend**: FastAPI on Vercel, MongoDB Atlas, Supabase PostgreSQL
- **Search**: MongoDB text search with excerpt highlighting
- **Architecture**: Hybrid - MongoDB for documents, Supabase for structured data
- **Performance**: 1-3 second search response time

### Key Files
- `api/mongodb_search.py` - MongoDB search handler
- `api/search_lightweight.py` - Updated search endpoint
- `SPRINT1_MONGODB_INTEGRATION_STATUS.md` - Full status documentation
- `sprint1-playbook-updated.md` - Sprint playbook with all phases

---

## PROMPT SEQUENCE FOR NEXT SESSION

### PROMPT 1: Verify Current State
```
I need to verify the current state of our MongoDB search integration before deployment.

CONTEXT: 
- Sprint 1 MongoDB integration completed
- Search improved from 4% to 200%+ relevance
- Using MongoDB for transcripts, Supabase for metadata

TASK: Check these files and verify current implementation:
1. Read api/mongodb_search.py
2. Read api/search_lightweight.py  
3. Run a test search query locally
4. Verify environment variables are set

Working directory: /Users/jamesgill/PodInsights/podinsight-api

Report findings and confirm ready for deployment.
```

### PROMPT 2: Deploy to Vercel
```
Deploy the MongoDB-enhanced search API to Vercel.

CONTEXT: Local testing complete, MongoDB search working with 200%+ relevance scores.

REQUIRED STEPS:
1. Add MONGODB_URI to Vercel environment variables
2. Ensure all dependencies in requirements.txt
3. Test that Vercel can connect to MongoDB Atlas
4. Deploy and verify production search

The MONGODB_URI is already in local .env file.

IMPORTANT: Vercel may need IP whitelisting in MongoDB Atlas Network Access.
```

### PROMPT 3: Test Production Deployment
```
Test the production search API to ensure MongoDB integration is working.

ENDPOINTS TO TEST:
- https://podinsight-api.vercel.app/api/search

TEST QUERIES:
1. "AI agents" - Should return real conversation excerpts
2. "venture capital funding" - Should show VC discussions
3. "GPT-4 capabilities" - Should find technical content

VERIFY:
- Real excerpts (not placeholders)
- Relevance scores > 1.5 (MongoDB scores)
- Search terms highlighted in bold
- Response time < 3 seconds

Document any issues found.
```

### PROMPT 4: Update Sprint Documentation
```
Update the sprint documentation with deployment results.

FILES TO UPDATE:
1. SPRINT1_MONGODB_INTEGRATION_STATUS.md - Add Phase 4 completion
2. sprint1-playbook-updated.md - Mark deployment tasks complete

INCLUDE:
- Deployment timestamp
- Production URL confirmation
- Any issues encountered and solutions
- Performance metrics from production

Keep documentation concise and factual.
```

### PROMPT 5: Embeddings Strategy Discussion
```
Explain the current embeddings situation and future improvements.

CONTEXT: User asked about embeddings and vectors. Current system uses:
- Episode-level embeddings (not optimal for search)
- MongoDB text search (no embeddings currently)
- Existing embeddings made with lower-quality model

EXPLAIN:
1. Why current search works well without embeddings
2. How segment-level embeddings would improve search
3. What "lower-quality model" means for existing embeddings
4. Recommended approach for Sprint 2/3

Focus on practical impact, not technical details.
```

---

## ADDITIONAL CONTEXT FOR COMPLEX ISSUES

### If MongoDB Connection Fails in Vercel
```
MongoDB connection failing in Vercel deployment.

DEBUG STEPS:
1. Check Vercel logs for connection errors
2. Verify MongoDB Atlas Network Access allows 0.0.0.0/0
3. Check MONGODB_URI format in Vercel env vars
4. Test with connection timeout increase
5. Consider using mongodb+srv:// protocol

Common issues:
- Missing ?retryWrites=true in connection string
- IP whitelist not allowing Vercel IPs
- SSL/TLS certificate issues
```

### If Search Performance Degrades
```
Production search taking >3 seconds.

OPTIMIZE:
1. Check MongoDB Atlas metrics for slow queries
2. Verify text indexes are being used
3. Consider adding caching layer
4. Check if Vercel cold starts are issue
5. Monitor MongoDB connection pool

Target: <2 second response time
```

---

## KEY REMINDERS

1. **MongoDB Scores**: Not percentages! Range 0.5-3.0+
2. **Architecture**: Keep hybrid approach (MongoDB + Supabase)
3. **API Contract**: No breaking changes to frontend
4. **Performance**: Target <2 second search response
5. **Documentation**: Update as you go

## SUCCESS CRITERIA FOR SESSION

- [ ] Search API deployed to production
- [ ] All test queries return real excerpts
- [ ] Documentation fully updated
- [ ] User understands embeddings strategy
- [ ] Ready for Sprint 2 planning