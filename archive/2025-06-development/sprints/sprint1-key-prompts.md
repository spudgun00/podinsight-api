# Sprint 1 MongoDB Integration - Key Prompts & Testing Guide

## 🚀 Quick Start Prompts for Claude Code

### Phase 0: MongoDB Setup Test (5 minutes)
```bash
# After creating MongoDB Atlas account and getting connection string
python mongodb-quick-start.py
```

### Phase 1: Migration Infrastructure (30 minutes)

#### 1.1 Dependencies
```
Add MongoDB dependencies to requirements.txt:
- pymongo for migration script
- motor for async API operations
Keep all existing dependencies.
```

#### 1.2 Migration Script
```
Create migrate_transcripts_to_mongodb.py that:
1. Connects to MongoDB, Supabase, and S3
2. Fetches all 1,171 episodes from Supabase
3. For each episode, downloads transcript from S3
4. Combines segments into full_text
5. Stores in MongoDB with episode metadata
6. Includes --limit flag, progress bar, error handling
7. Tracks already migrated episodes (resume capability)
```

#### 1.3 Test Migration
```
Create test_migration.py that verifies:
1. MongoDB connection works
2. Test with --limit 10 first
3. Documents have all required fields
4. full_text properly combined
5. Search index functioning
```

### Phase 2: Run Migration (45 minutes)

#### 2.1 Test Run
```bash
python migrate_transcripts_to_mongodb.py --limit 10
# Verify 10 documents in MongoDB Atlas UI
```

#### 2.2 Full Migration
```bash
python migrate_transcripts_to_mongodb.py
# Monitor progress bar - should take ~30 minutes
```

#### 2.3 Verification
```
Create verify_migration.py that checks:
1. Count matches Supabase (1,171)
2. Sample 10 documents for integrity
3. Test searches work
4. Performance benchmarks
```

### Phase 3: Update Search API (1 hour)

#### 3.1 MongoDB Search Handler
```
Create api/mongodb_search.py using motor (async MongoDB):
1. Full-text search using $text operator
2. Extract 200-word excerpts around matches
3. Calculate proper relevance scores
4. Return same format as current API
5. Include connection pooling and caching
```

#### 3.2 API Integration
```
Update api/search_lightweight.py to:
1. Import mongodb_search module
2. Replace mock excerpt generation with real MongoDB search
3. Keep HuggingFace embedding generation
4. Maintain all existing API contracts
5. Add MONGODB_URI to environment
```

#### 3.3 Deployment
```bash
# Add to Vercel environment variables
MONGODB_URI=mongodb+srv://...

# Deploy
git add -A
git commit -m "feat: Add MongoDB for real transcript search"
git push origin main
```

### Phase 4: Testing & Optimization (30 minutes)

#### 4.1 Local Testing
```bash
# Test search locally
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI agents", "limit": 5}'

# Should see:
# - Real excerpts (not placeholders)
# - Scores > 50% for good matches
# - Actual transcript content
```

#### 4.2 Production Testing
```bash
# Test on Vercel
python test_deployment.py

# Or use enhanced test page
open test-search-browser-enhanced.html
```

## 🧪 Comprehensive Test Suite

### Unit Tests
```python
# test_mongodb_integration.py
import pytest
from mongodb_search import MongoSearchHandler

@pytest.mark.asyncio
async def test_search_returns_real_excerpts():
    handler = MongoSearchHandler()
    results = await handler.search_transcripts("AI agents", limit=5)

    assert len(results) > 0
    assert "..." in results[0]['excerpt']  # Real excerpt
    assert results[0]['similarity_score'] > 0.5
    assert "AI" in results[0]['excerpt']  # Contains search term
```

### Integration Tests
```bash
# Test all search scenarios
./test_search_quality.sh

# Should verify:
# - "AI agents" returns AI discussions
# - "venture capital" returns VC content
# - "GPT-4" returns technical content
# - All scores > 50% for relevant matches
```

### Performance Tests
```python
# test_performance.py
def test_search_under_2_seconds():
    response = requests.post(API_URL + "/search",
                           json={"query": "AI agents"})
    assert response.elapsed.total_seconds() < 2.0
```

## ✅ Definition of Done Checklist

### MongoDB Setup
- [ ] Atlas account created with $5,000 credit
- [ ] M10 cluster running in eu-west-2
- [ ] Connection test passes

### Migration Complete
- [ ] All 1,171 episodes migrated
- [ ] ~527MB of transcript data in MongoDB
- [ ] No errors in migration log

### API Working
- [ ] Local search returns real excerpts
- [ ] Scores are 70%+ (not 4%!)
- [ ] Production deployment successful

### Search Quality 100%
- [ ] Open test-search-browser-enhanced.html
- [ ] Search "AI agents" - see real AI conversations
- [ ] Search "venture capital" - read actual VC discussions
- [ ] Every result shows context clearly
- [ ] No more mock data anywhere!

## 🚨 Common Issues & Solutions

### "Connection timeout to MongoDB"
```bash
# Check Network Access in Atlas
# Ensure "Allow from anywhere" is enabled
# Verify connection string has correct password
```

### "Search returns no results"
```python
# Check text index exists
db.transcripts.getIndexes()

# If missing, create it:
db.transcripts.createIndex({"full_text": "text"})
```

### "Migration hangs"
```bash
# Check S3 credentials
# Verify episodes have s3_stage_prefix
# Look for specific episode ID in logs
```

### "Excerpts are empty"
```python
# Verify full_text field is populated
# Test extract_excerpt function separately
# Check for encoding issues
```

## 📊 Success Metrics

Before: 4% scores, fake excerpts
After: 70%+ scores, real transcript content

The search should feel like magic - users can find exact conversations from 1,000+ hours of podcasts in under 2 seconds!
