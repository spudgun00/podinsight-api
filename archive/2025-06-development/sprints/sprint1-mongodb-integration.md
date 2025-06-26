# Sprint 1.5: MongoDB Integration for Real Search
*Critical infrastructure change: Implementing MongoDB for transcript storage and real search capabilities*

**Last Updated:** June 19, 2025
**Status:** 🚀 READY TO START
**Estimated Time:** 6-8 hours
**Priority:** CRITICAL (blocks meaningful search)

---

## 📊 Definition of Done

### Search Must Be 100% Real
- ✅ **Real Excerpts**: Actual transcript text, not placeholders
- ✅ **Relevant Scores**: 70%+ for good matches (not 4%!)
- ✅ **See Context**: 200-word excerpts showing WHY it matched
- ✅ **Fast Response**: Under 2 seconds for any search
- ✅ **All Episodes**: 1,171 episodes searchable
- ✅ **Production Ready**: Live on API, working in browser

### Success Criteria
1. Search "AI agents" returns real conversation excerpts
2. Scores above 70% for relevant matches
3. Can read the excerpt and understand the context
4. Works on https://podinsight-api.vercel.app/api/search
5. No more mock data anywhere

### Test Queries That Must Work
- "AI agents" → Real discussions about AI agents
- "venture capital" → Actual VC conversations
- "burn rate" → Specific financial discussions
- "GPT-4" → Technical AI discussions
- "Sequoia" → Company mentions

## 🎯 Why This Change Now?

### The Problem
- Current search returns fake excerpts with 4% relevance scores
- Transcripts (527MB) + Segments (2.3GB) exceed Supabase free tier (500MB)
- Users can't see WHY content matches their search
- Search looks like a prototype, not a real product

### The Solution
- MongoDB Atlas ($5,000 credit secured) for document storage
- Real full-text search with actual excerpts
- Proper relevance scores (70%+ instead of 4%)
- Clean architecture: structured data (Supabase) vs unstructured (MongoDB)

---

## ⏱️ Realistic Timeline (Working with Claude Code)

### Total Time: 3-4 hours

| Phase | Solo Estimate | With Claude Code | What We Do |
|-------|--------------|------------------|------------|
| **MongoDB Setup** | 30 min | 20 min | You click, I guide |
| **Migration Script** | 1 hour | 30 min | I write code instantly |
| **Run Migration** | 2 hours | 45 min | Script runs itself |
| **Update API** | 2 hours | 1 hour | I code, you test |
| **Testing & Polish** | 1 hour | 30 min | Verify together |
| **Total** | 6.5 hours | **3.5 hours** | 🚀 |

### Why It's Faster Together
- ✅ No time spent researching MongoDB syntax
- ✅ No debugging migration scripts
- ✅ Instant code generation
- ✅ Clear testing steps
- ✅ I catch errors before they happen

---

## 🏗️ New Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Current Architecture                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Supabase (Free Tier - 500MB limit)                                │
│  ┌────────────────────────────────────┐                            │
│  │ ✅ Episodes (metadata only)         │ ← Small, structured       │
│  │ ✅ Topic Mentions                   │ ← Tiny                    │
│  │ ✅ Users/Auth (future)              │ ← Perfect for Supabase    │
│  │ ❌ Transcripts (527MB)              │ ← TOO BIG!               │
│  │ ❌ Segments (2.3GB)                 │ ← WAY TOO BIG!           │
│  │ ❌ Real search                      │ ← No text to search!     │
│  └────────────────────────────────────┘                            │
│                                                                      │
│  Result: Fake excerpts, 4% scores, no value                        │
└─────────────────────────────────────────────────────────────────────┘

                              ↓ UPGRADE ↓

┌─────────────────────────────────────────────────────────────────────┐
│                      New Hybrid Architecture                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Supabase ($300 credit)              MongoDB Atlas ($5,000 credit) │
│  ┌─────────────────────┐             ┌─────────────────────────┐   │
│  │ ✅ Episodes (meta)   │ ←────────→ │ ✅ Transcripts (527MB)  │   │
│  │ ✅ Topic Mentions    │ episode_id │ ✅ Segments (2.3GB)     │   │
│  │ ✅ Users/Auth        │ ←────────→ │ ✅ Full-text search    │   │
│  │ ✅ KPIs             │             │ ✅ Vector search       │   │
│  │ ✅ Entities         │             │ ✅ Real excerpts       │   │
│  └─────────────────────┘             └─────────────────────────┘   │
│   Structured data only                Unstructured documents        │
│                                                                      │
│  Result: Real excerpts, 70%+ scores, actual value!                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Playbook

### Phase 0: MongoDB Setup (30 minutes)

#### Step 0.1: Create MongoDB Atlas Account

**Prompt for Manual Steps:**
```
1. Go to https://cloud.mongodb.com/
2. Sign up/Login
3. Click "Redeem Credits" → Enter your $5,000 credit code
4. Create Organization: "PodInsightHQ"
5. Create Project: "podinsight-prod"
```

#### Step 0.2: Create Cluster

**Prompt for Manual Steps:**
```
1. Click "Build a Cluster"
2. Choose "Dedicated" (not Serverless)
3. Select:
   - Provider: AWS
   - Region: eu-west-2 (London) - same as your API
   - Tier: M10 ($60/month = 83 months on credit!)
   - Cluster Name: "podinsight-cluster"
4. Click "Create Cluster" (takes ~5 minutes)
```

#### Step 0.3: Set Up Database Access

**Prompt for Manual Steps:**
```
1. Go to "Database Access" → "Add New Database User"
   - Username: podinsight-api
   - Password: [Generate secure password]
   - Role: "Read and write to any database"

2. Go to "Network Access" → "Add IP Address"
   - Click "Allow Access from Anywhere" (for now)
   - Note: Tighten this later to Vercel IPs

3. Go to "Clusters" → "Connect" → "Connect your application"
   - Choose "Python" and "3.12 or later"
   - Copy the connection string
   - Replace <password> with your actual password
   - Add to .env as MONGODB_URI
```

**Testing Checkpoint:**
```bash
# In podinsight-api directory
python mongodb-quick-start.py

# Should see:
# ✅ MongoDB connected! Test document ID: xxx
# ✅ Created transcripts collection
# ✅ Created search indexes
```

---

### Phase 1: Data Migration Infrastructure (1 hour)

#### Step 1.1: Install Dependencies

**Prompt for Claude Code:**
```
@requirements.txt

Add MongoDB dependencies to requirements.txt:
- pymongo (for migration script)
- motor (for async API operations)

Keep all existing dependencies.
```

#### Step 1.2: Create Migration Script

**Prompt for Claude Code:**
```
Create a comprehensive migration script: migrate_transcripts_to_mongodb.py

Requirements:
1. Connect to MongoDB (using MONGODB_URI from .env)
2. Connect to Supabase (existing connection pattern)
3. Connect to S3 (existing boto3 setup)

Migration logic:
1. Fetch all episodes from Supabase
2. For each episode:
   - Use s3_stage_prefix to locate transcript
   - Download transcript JSON from S3
   - Extract full text by joining all segments
   - Get topics for this episode from topic_mentions
   - Create MongoDB document with:
     * episode_id (for joining with Supabase)
     * All episode metadata
     * full_text (combined segments)
     * segments array (keep for future features)
     * topics array
     * s3_paths for reference

Include:
- Progress bar (tqdm)
- Error handling and retry logic
- Ability to resume (check if episode already migrated)
- --limit flag for testing
- Detailed logging
- Final statistics report

The transcript structure from S3 is:
{
  "segments": [
    {"text": "...", "speaker": "SPEAKER_01", "start": 0.0, "end": 5.2},
    ...
  ]
}
```

#### Step 1.3: Create Migration Test

**Prompt for Claude Code:**
```
Create test_migration.py that:

1. Tests with --limit 10 flag first
2. Verifies MongoDB documents have all required fields
3. Checks that full_text is properly combined
4. Confirms search index works
5. Validates episode_id foreign key relationship

Success criteria:
- 10 documents in MongoDB
- Each has non-empty full_text
- Search for "AI" returns results
- Can join back to Supabase data
```

**Testing Checkpoint:**
```bash
# Test migration with 10 episodes
python migrate_transcripts_to_mongodb.py --limit 10

# Verify in MongoDB Atlas UI:
# - Go to Collections → transcripts
# - Should see 10 documents
# - Check one has full_text field

# Run test script
python test_migration.py
```

---

### Phase 2: Full Data Migration (2 hours)

#### Step 2.1: Run Complete Migration

**Prompt for Manual Steps:**
```
# Run full migration (will take ~30-45 minutes)
python migrate_transcripts_to_mongodb.py

# Monitor progress:
# - Should show "Migrating 1,171 episodes"
# - Progress bar advancing
# - Any errors logged but continuing

# Expected output:
# ✅ Migration complete!
# - Episodes migrated: 1,171
# - Total size: ~527MB
# - Errors: [hopefully 0]
# - Time elapsed: ~35 minutes
```

#### Step 2.2: Verify Migration Success

**Prompt for Claude Code:**
```
Create verify_migration.py that checks:

1. Document count matches Supabase episodes
2. Random sampling of 10 documents for data integrity
3. Search functionality test queries:
   - "AI agents"
   - "venture capital"
   - "B2B SaaS metrics"
4. Performance benchmarks:
   - Single document fetch time
   - Search query time
   - Aggregation query time

Report format:
- ✅/❌ for each check
- Performance metrics in ms
- Any data discrepancies found
```

---

### Phase 3: Update Search API (2 hours)

#### Step 3.1: Create MongoDB Search Handler

**Prompt for Claude Code:**
```
@api/search_lightweight.py

Create a new file: api/mongodb_search.py that:

1. Uses motor (async MongoDB driver)
2. Implements search class:
   - Full-text search using MongoDB $text
   - Extract real excerpts from matches
   - Calculate proper relevance scores
   - Return same format as current API

Key features:
- Connection pooling
- Caching for repeated queries
- Excerpt extraction around matched terms
- Highlight matched terms in excerpts

Search method should:
1. Use MongoDB text search
2. Project relevance score
3. Extract 200-word excerpt around match
4. Format results exactly like current API
5. Include error handling
```

#### Step 3.2: Integrate with Existing API

**Prompt for Claude Code:**
```
@api/search_lightweight.py
@api/topic_velocity.py

Update the search endpoint to use MongoDB:

1. Add MongoDB connection using motor
2. Replace mock excerpt generation with real MongoDB search
3. Keep all existing API contracts the same
4. Add feature flag USE_MONGODB_SEARCH (default True)
5. Keep Hugging Face embeddings for query processing
6. Maintain backward compatibility

The flow should be:
1. Receive search query
2. Generate embedding (existing HF code)
3. Search MongoDB for text matches
4. Return real excerpts with proper scores
5. Cache results (existing logic)
```

#### Step 3.3: Add MongoDB to Vercel

**Prompt for Manual Steps:**
```
1. Go to Vercel Dashboard → podinsight-api
2. Settings → Environment Variables
3. Add: MONGODB_URI = [your connection string]
4. Redeploy:
   git add .
   git commit -m "feat: Add MongoDB for real transcript search"
   git push origin main
```

**Testing Checkpoint:**
```bash
# Test locally first
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI agents", "limit": 5}'

# Should see:
# - Real excerpts (not generic descriptions)
# - Scores > 50% for good matches
# - Actual transcript content

# Test production
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "venture capital trends", "limit": 5}'
```

---

### Phase 4: Optimization & Enhancement (1 hour)

#### Step 4.1: Add Search Indexes

**Prompt for Claude Code:**
```
Create optimize_mongodb.py that:

1. Creates compound indexes for common queries
2. Adds text search weights:
   - episode_title: weight 3
   - topics: weight 2
   - full_text: weight 1
3. Creates indexes for date filtering
4. Analyzes index usage
5. Suggests further optimizations

Also create search index through Atlas UI:
- Text index on full_text
- Compound index on [episode_id, published_at]
- Index on topics array
```

#### Step 4.2: Add Advanced Search Features

**Prompt for Claude Code:**
```
Enhance mongodb_search.py with:

1. Date range filtering
2. Topic filtering
3. Podcast name filtering
4. Fuzzy matching for typos
5. Search suggestions/autocomplete
6. "More like this" functionality

Keep all features optional and backward compatible.
```

---

## 🧪 Comprehensive Testing Guide

### Unit Tests

**Create test_mongodb_integration.py:**
```python
import pytest
import asyncio
from mongodb_search import MongoSearchHandler

class TestMongoDBIntegration:

    @pytest.mark.asyncio
    async def test_connection(self):
        """Test MongoDB connection works"""
        handler = MongoSearchHandler()
        assert await handler.test_connection()

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        """Test search returns real excerpts"""
        handler = MongoSearchHandler()
        results = await handler.search_transcripts("AI agents", limit=5)

        assert len(results) > 0
        assert results[0]['excerpt'] != ""
        assert "..." in results[0]['excerpt']  # Has real excerpt
        assert results[0]['similarity_score'] > 0.5

    @pytest.mark.asyncio
    async def test_excerpt_extraction(self):
        """Test excerpt centers on matched terms"""
        handler = MongoSearchHandler()
        text = "Beginning text. The AI agents are transforming how we build software. End text."
        excerpt = handler.extract_excerpt(text, "AI agents", max_words=10)

        assert "AI agents" in excerpt
        assert "..." in excerpt  # Truncated
```

### Integration Tests

**Test every search scenario:**
```bash
# Create test_search_quality.sh
#!/bin/bash

echo "Testing Search Quality..."

# Test 1: Specific technical term
curl -X POST https://podinsight-api.vercel.app/api/search \
  -d '{"query": "GPT-4 capabilities", "limit": 3}' | jq '.results[0].excerpt'

# Test 2: Business concept
curl -X POST https://podinsight-api.vercel.app/api/search \
  -d '{"query": "burn rate", "limit": 3}' | jq '.results[0].excerpt'

# Test 3: Multiple terms
curl -X POST https://podinsight-api.vercel.app/api/search \
  -d '{"query": "AI agents venture capital", "limit": 3}' | jq '.results[0].similarity_score'

# Should see:
# - Real excerpts with context
# - Scores > 0.5 for relevant matches
# - Excerpts contain search terms
```

### Performance Tests

**Create test_performance.py:**
```python
import time
import statistics

def test_search_performance():
    """Ensure search stays under 2 seconds"""

    queries = [
        "AI agents",
        "venture capital",
        "B2B SaaS metrics",
        "DePIN infrastructure",
        "capital efficiency"
    ]

    times = []

    for query in queries:
        start = time.time()
        response = requests.post(
            "https://podinsight-api.vercel.app/api/search",
            json={"query": query, "limit": 10}
        )
        end = time.time()

        assert response.status_code == 200
        times.append(end - start)

    avg_time = statistics.mean(times)
    max_time = max(times)

    print(f"Average search time: {avg_time:.2f}s")
    print(f"Max search time: {max_time:.2f}s")

    assert avg_time < 1.0  # Average under 1 second
    assert max_time < 2.0  # No search over 2 seconds
```

---

## 🚀 Launch Checklist (Definition of Done)

### ✅ Setup Complete
- [ ] MongoDB Atlas account created with $5,000 credit
- [ ] M10 cluster provisioned in eu-west-2
- [ ] Connection string in .env
- [ ] `python mongodb-quick-start.py` passes

### ✅ Migration 100% Done
- [ ] All 1,171 episodes migrated
- [ ] MongoDB shows ~527MB of data
- [ ] Zero errors in migration log
- [ ] Spot check 5 random transcripts have full_text

### ✅ API Working with Real Data
- [ ] Local: `curl localhost:8000/api/search -d '{"query":"AI agents"}'` shows real excerpts
- [ ] Scores are 70%+ for relevant matches (not 4%!)
- [ ] Production: https://podinsight-api.vercel.app/api/search works
- [ ] Response time <2 seconds consistently

### ✅ Search is 100% Real (The Money Shot)
- [ ] Open test-search-browser-enhanced.html
- [ ] Search "AI agents" → See actual AI conversation excerpts
- [ ] Search "venture capital" → Read real VC discussions
- [ ] Search "GPT-4" → Find technical AI content
- [ ] Every result shows WHY it matched (context is clear)
- [ ] Relevance scores make sense (>70% for good matches)
- [ ] Can demo this to anyone with pride!

### ❌ NOT Done Until
- No more mock excerpts anywhere
- No more 4% relevance scores
- Every search returns real value
- You'd be happy to show this to Paul Graham

---

## 📊 Success Metrics

### Before MongoDB
- Search scores: 4% average
- Excerpts: Generic placeholders
- User value: Near zero
- Architecture: Hitting limits

### After MongoDB
- Search scores: 70%+ for relevant content
- Excerpts: Real transcript segments
- User value: Can see WHY content matches
- Architecture: Scalable to 100GB+

---

## 🔧 Troubleshooting

### Common Issues

**"Connection timeout to MongoDB"**
- Check Network Access allows your IP
- Verify connection string has correct password
- Ensure cluster is not paused

**"Search returns no results"**
- Check text index exists: `db.transcripts.getIndexes()`
- Verify documents have full_text field
- Try simpler query terms

**"Migration hangs"**
- Check S3 credentials are valid
- Verify episodes have s3_stage_prefix
- Look for specific episode in logs

**"Excerpts are empty"**
- Check full_text field is populated
- Verify extract_excerpt function works
- Test with known content

---

## 🎯 Next Steps

Once this is complete:
1. **Segments Migration** (Sprint 2): Add the 2.3GB segments data
2. **Vector Search** (Sprint 2): Migrate embeddings for semantic search
3. **Search Analytics** (Sprint 3): Track what users search for
4. **Advanced Features** (Sprint 3): Filters, facets, suggestions

---

## 📝 For Future Team Members

This integration was added because:
1. Original architecture hit Supabase size limits
2. Search was returning fake data (unusable for MVP)
3. MongoDB credit made it free to implement
4. Separates structured (SQL) from unstructured (documents) data

Key decisions:
- M10 tier: Balances cost ($60/mo) with performance
- London region: Same as API for low latency
- Text search first: Vector search can be added later
- Maintain all existing APIs: No breaking changes

The hybrid architecture (Supabase + MongoDB) is intentional and correct. Don't try to consolidate everything into one database.

---

*This playbook ensures anyone can complete the MongoDB integration, turning our fake search into a real, valuable feature.*
