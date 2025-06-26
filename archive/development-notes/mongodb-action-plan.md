# MongoDB Integration: Exact Step-by-Step Action Plan

## 🎯 The Problem We're Solving
- **Current**: Search returns fake excerpts like "Episode 7f54be60... This episode covers AI Agents"
- **Why it's broken**: We never stored transcript text, only detected topics
- **Impact**: 4% relevance scores = useless search
- **Solution**: MongoDB stores full transcripts + enables real search

---

## 📋 PHASE 0: MongoDB Atlas Setup (20 minutes)

### Step 0.1: Create MongoDB Account (5 min)

**YOU DO:**
1. Open browser to https://cloud.mongodb.com/
2. Click "Try Free" → Sign up with Google
3. When prompted for organization name: Type `PodInsightHQ`
4. When prompted for project name: Type `podinsight-prod`

**WHY:** MongoDB Atlas gives us managed database with $5k credit

### Step 0.2: Apply Your Credit (2 min)

**YOU DO:**
1. After signup, look for "Billing" in left sidebar
2. Click "Credits" → "Redeem Credit"
3. Enter your $5,000 credit code
4. Verify it shows "$5,000.00 available credit"

**TEST:** Credit balance should show $5,000

### Step 0.3: Create Database Cluster (5 min)

**YOU DO:**
1. Click "Build a Database" button
2. Choose "Dedicated" (NOT Serverless - we need features)
3. Select these EXACT settings:
   - Provider: **AWS**
   - Region: **eu-west-2 (London)** ← Same as your API
   - Cluster Tier: **M10** ($57/month from credit)
   - Cluster Name: `podinsight-cluster`
4. Click "Create Cluster"
5. Wait ~3 minutes for green checkmark

**WHY:** M10 tier handles 100GB+ data, London region = low latency

**TEST:** Cluster shows "Active" status with green dot

### Step 0.4: Set Up Database Access (3 min)

**YOU DO:**

1. **Create Database User:**
   - Click "Database Access" → "Add New Database User"
   - Username: `podinsight-api`
   - Password: Click "Autogenerate Secure Password"
   - **COPY THIS PASSWORD TO NOTEPAD!**
   - Database User Privileges: "Read and write to any database"
   - Click "Add User"

2. **Allow Network Access:**
   - Click "Network Access" → "Add IP Address"
   - Click "Allow Access from Anywhere"
   - Click "Confirm"
   - Wait for "Active" status

**WHY:** User = API authentication, Network = allows Vercel connection

**TEST:** Both should show green "Active" status

### Step 0.5: Get Connection String (2 min)

**YOU DO:**
1. Click "Database" → "Connect" button on your cluster
2. Choose "Connect your application"
3. Select "Python" and version "3.12 or later"
4. Copy the connection string (looks like: `mongodb+srv://podinsight-api:<password>@podinsight-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority`)
5. Replace `<password>` with the password you copied earlier
6. Save complete string to your `.env` file as:
   ```
   MONGODB_URI=mongodb+srv://podinsight-api:YOUR_ACTUAL_PASSWORD@podinsight-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

**TEST IMMEDIATELY:**

**YOU DO:**
```bash
cd /Users/jamesgill/PodInsights/podinsight-api
python mongodb-quick-start.py
```

**EXPECTED OUTPUT:**
```
✅ MongoDB connected! Test document ID: 667d4e3c1234567890abcdef
✅ Created transcripts collection
✅ Created search indexes
📊 Collection size: 0.00 MB
📊 Document count: 0
```

**IF IT FAILS:** Check password has no special characters that need escaping

---

## 📋 PHASE 1: Migration Script (30 minutes)

### Step 1.1: Install Dependencies (2 min)

**YOU DO:**
```bash
pip install pymongo motor tqdm
```

**PROMPT FOR CLAUDE CODE:**
```
@requirements.txt

Add exactly these lines to requirements.txt:
pymongo==4.7.2
motor==3.4.0
tqdm==4.66.4

Keep all existing dependencies. These are for MongoDB migration.
```

**TEST:**
```bash
pip freeze | grep -E "pymongo|motor|tqdm"
# Should show all three with versions
```

### Step 1.2: Create Migration Script (10 min)

**PROMPT FOR CLAUDE CODE:**
```
Create migrate_transcripts_to_mongodb.py with these EXACT requirements:

1. Import structure:
   - pymongo for MongoDB
   - boto3 for S3 (already configured)
   - supabase client (existing pattern from Sprint 0)
   - tqdm for progress bar
   - asyncio for async operations

2. Configuration section:
   - Load MONGODB_URI from .env
   - Load existing AWS and Supabase credentials
   - Create MongoDB client with connection pooling

3. Main migration function must:
   - Connect to Supabase and get all episodes (should be 1,171)
   - For each episode:
     a. Check if already migrated (by episode_id) - allows resume
     b. Get s3_stage_prefix from episode record
     c. Download transcript JSON from S3 (handle missing files)
     d. Extract segments array from transcript JSON
     e. Combine all segment["text"] into single full_text string
     f. Get topics for this episode from topic_mentions table
     g. Create MongoDB document with ALL these fields:
        - episode_id (from Supabase)
        - podcast_name
        - episode_title
        - published_at
        - full_text (combined segments)
        - segments (keep original array)
        - topics (array from topic_mentions)
        - s3_paths (keep references)
        - word_count
        - duration_seconds

4. Features:
   - --limit flag for testing (e.g., --limit 10)
   - --dry-run flag to test without inserting
   - Progress bar showing "Migrating episode 123/1171"
   - Error handling that logs but continues
   - Final report showing success/error counts

5. CRITICAL: Must handle transcript structure:
   {
     "segments": [
       {"text": "actual words", "speaker": "SPEAKER_01", "start": 0.0, "end": 5.2},
       ...
     ]
   }

Include detailed logging and ability to resume from interruption.
```

**TEST THE SCRIPT:**
```bash
# First, dry run with 3 episodes
python migrate_transcripts_to_mongodb.py --limit 3 --dry-run

# Should output:
# [DRY RUN] Would migrate episode 1a32abc8...
# [DRY RUN] Would migrate episode 827b2b62...
# [DRY RUN] Would migrate episode 073303cd...
# Dry run complete. Would migrate 3 episodes.
```

### Step 1.3: Test Migration Script (10 min)

**PROMPT FOR CLAUDE CODE:**
```
Create test_migration.py that validates our migration with these tests:

1. Test MongoDB connection:
   - Connect using MONGODB_URI
   - Verify 'transcripts' collection exists
   - Check indexes are created

2. Test small batch migration:
   - Run: migrate_transcripts_to_mongodb.py --limit 5
   - Verify exactly 5 documents in MongoDB
   - Check each document has:
     * episode_id (UUID format)
     * full_text (non-empty string, >1000 chars)
     * topics array (containing valid topic names)
     * segments array (with original structure)

3. Test search functionality:
   - Perform text search for "AI"
   - Verify returns at least 1 result
   - Check result has similarity score

4. Test data integrity:
   - Pick random document
   - Verify full_text contains words from segments
   - Verify topics match our 5 tracked topics
   - Verify dates are valid

5. Performance benchmark:
   - Time how long 5 documents take
   - Estimate time for full 1,171

Output clear PASS/FAIL for each test with details.
```

**RUN THE TEST:**
```bash
# First migrate 5 test episodes
python migrate_transcripts_to_mongodb.py --limit 5

# Then test
python test_migration.py

# Expected output:
# ✅ MongoDB connection: PASS
# ✅ Document count: 5 (PASS)
# ✅ Full text integrity: PASS (avg 15,234 chars)
# ✅ Search functionality: PASS (found 3 results for 'AI')
# ✅ Data integrity: PASS
# ⏱️  Performance: 5 docs in 4.2s, estimated 16 min for 1,171
```

### Step 1.4: MongoDB Atlas Verification (5 min)

**YOU DO:**
1. Go to MongoDB Atlas dashboard
2. Click "Browse Collections"
3. Select `podinsight` database → `transcripts` collection
4. You should see 5 documents
5. Click on one document
6. Verify it has:
   - `full_text` field with actual transcript content
   - `topics` array with values like ["AI Agents", "B2B SaaS"]
   - `segments` array preserved from original

**TEST:** Can you read actual conversation in full_text field? Not placeholder text?

---

## 📋 PHASE 2: Full Migration (45 minutes)

### Step 2.1: Run Complete Migration (30 min)

**YOU DO:**
```bash
# Clear previous test data first
python -c "from pymongo import MongoClient; client = MongoClient(os.getenv('MONGODB_URI')); client.podinsight.transcripts.delete_many({})"

# Run full migration
python migrate_transcripts_to_mongodb.py

# This will take ~30 minutes. You'll see:
# Migrating episodes: 100%|████████| 1171/1171 [28:34<00:00, 1.46s/episode]
```

**MONITOR WHILE RUNNING:**
- Progress bar should advance steadily
- Any errors will be logged but won't stop migration
- You can Ctrl+C and resume - it skips already migrated episodes

### Step 2.2: Verify Migration Success (10 min)

**PROMPT FOR CLAUDE CODE:**
```
Create verify_full_migration.py that performs comprehensive validation:

1. Count verification:
   - MongoDB transcripts count = 1,171
   - Compare with Supabase episodes count
   - Flag any discrepancies

2. Data completeness (sample 50 random docs):
   - All have non-empty full_text
   - Average full_text length > 10,000 chars
   - All have valid episode_id
   - All have topics array

3. Search quality tests:
   - Search "AI agents" - should return 20+ results
   - Search "venture capital" - should return 15+ results
   - Search "GPT-4" - should return 5+ results
   - All searches should have scores > 0.3

4. Storage metrics:
   - Total collection size in MB
   - Average document size
   - Largest document

5. Missing data report:
   - Episodes without transcripts
   - Episodes without topics
   - Any anomalies

Output a clear report card with PASS/FAIL/WARNING for each check.
```

**RUN VERIFICATION:**
```bash
python verify_full_migration.py

# Expected output:
# === MIGRATION VERIFICATION REPORT ===
# ✅ Document count: 1,171 (PASS)
# ✅ Data completeness: PASS
#    - Average transcript: 15,832 chars
#    - All documents have full_text
# ✅ Search quality: PASS
#    - "AI agents": 47 results (avg score: 0.72)
#    - "venture capital": 31 results (avg score: 0.68)
#    - "GPT-4": 12 results (avg score: 0.81)
# 📊 Storage metrics:
#    - Total size: 527.3 MB
#    - Average doc: 461 KB
# ✅ No missing data found
#
# MIGRATION SUCCESSFUL! 🎉
```

### Step 2.3: Atlas Dashboard Final Check (5 min)

**YOU DO:**
1. Go to MongoDB Atlas → Browse Collections
2. Check stats show ~527MB of data
3. Click "Indexes" tab
4. Verify you see:
   - `_id_` (default)
   - `text_index` on full_text field
   - `episode_id_1` index

**TEST:** Search for "OpenAI" in Atlas search bar - should find documents

---

## 📋 PHASE 3: Update Search API (1 hour)

### Step 3.1: Create MongoDB Search Handler (20 min)

**PROMPT FOR CLAUDE CODE:**
```
Create api/mongodb_search.py with these EXACT specifications:

1. Imports and setup:
   - motor for async MongoDB operations
   - Re-use existing connection patterns
   - Configure text search with proper indexes

2. Main search class with these methods:

   async def search_transcripts(query: str, limit: int = 10):
       - Use MongoDB $text search operator
       - Project text score for relevance
       - Sort by score descending
       - Return top N results

   def extract_excerpt(full_text: str, query: str, max_words: int = 200):
       - Find query terms in full_text (case-insensitive)
       - Extract window of text around match
       - Add ellipsis if truncated
       - Highlight matched terms
       - Handle edge cases (term at start/end)

   async def get_episode_by_id(episode_id: str):
       - Fetch single episode for playback
       - Include all metadata

3. Connection management:
   - Connection pooling (max 10 connections)
   - Retry logic for network errors
   - Graceful degradation if MongoDB down

4. Caching layer:
   - Simple in-memory cache for repeated queries
   - TTL of 5 minutes
   - Max 100 cached queries

5. Error handling:
   - Log all errors with context
   - Return empty results, not errors
   - Include search metadata in response

CRITICAL: The excerpt must show REAL text around the search match, not generic summaries!
```

**TEST THE HANDLER:**
```python
# Create test_mongodb_search.py
import asyncio
from mongodb_search import MongoSearchHandler

async def test():
    handler = MongoSearchHandler()

    # Test 1: Basic search
    results = await handler.search_transcripts("AI agents", limit=5)
    assert len(results) > 0
    assert "AI" in results[0]['excerpt']
    print(f"✅ Found {len(results)} results")

    # Test 2: Excerpt extraction
    text = "The discussion about AI agents and their impact on software development..."
    excerpt = handler.extract_excerpt(text, "AI agents", max_words=10)
    assert "AI agents" in excerpt
    assert "..." in excerpt
    print(f"✅ Excerpt: {excerpt}")

    # Test 3: Performance
    import time
    start = time.time()
    await handler.search_transcripts("venture capital", limit=10)
    elapsed = time.time() - start
    assert elapsed < 1.0  # Should be fast
    print(f"✅ Search took {elapsed:.2f}s")

asyncio.run(test())
```

### Step 3.2: Integrate with Existing API (20 min)

**PROMPT FOR CLAUDE CODE:**
```
@api/search_lightweight.py
@api/topic_velocity.py

Update the search endpoint to use MongoDB with these EXACT requirements:

1. Import the new mongodb_search module

2. Modify search_handler function:
   - Keep existing Hugging Face embedding generation
   - After getting embedding, call MongoDB search
   - Replace mock excerpt generation with real excerpts
   - Maintain exact same API response format

3. The flow should be:
   a. Receive search query
   b. Generate embedding using HF (existing code)
   c. Search MongoDB for text matches
   d. For each result:
      - Get real excerpt using extract_excerpt
      - Keep all existing fields
      - Replace fake excerpt with real one
   e. Cache results (existing code)

4. Add fallback:
   - If MongoDB fails, log error
   - Return empty results, not error
   - Never return mock excerpts again

5. Environment variable:
   - Add MONGODB_URI check at startup
   - Log warning if not set

CRITICAL: Do not change the API contract! Frontend expects same format.
```

**LOCAL TEST:**
```bash
# Start API locally
cd /Users/jamesgill/PodInsights/podinsight-api
uvicorn api.topic_velocity:app --reload

# In another terminal, test search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI agents", "limit": 3}' | python -m json.tool

# You should see:
# - Real excerpts with context
# - Scores > 0.5 for good matches
# - Actual conversation text, not placeholders
```

### Step 3.3: Deploy to Production (10 min)

**YOU DO:**

1. **Add MongoDB URI to Vercel:**
   ```bash
   # Check you have the URI
   echo $MONGODB_URI

   # Should show: mongodb+srv://podinsight-api:...
   ```

2. **Go to Vercel Dashboard:**
   - Navigate to your `podinsight-api` project
   - Settings → Environment Variables
   - Add Variable:
     - Name: `MONGODB_URI`
     - Value: [paste your full connection string]
     - Environment: Production
   - Click Save

3. **Deploy the changes:**
   ```bash
   git add -A
   git commit -m "feat: Integrate MongoDB for real transcript search

   - Search now returns actual transcript excerpts
   - Relevance scores improved from 4% to 70%+
   - Response time still under 2 seconds"

   git push origin main
   ```

4. **Monitor deployment:**
   - Go to Vercel dashboard
   - Watch deployment progress
   - Should complete in ~2 minutes

### Step 3.4: Production Testing (10 min)

**TEST 1: API Direct Test**
```bash
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "venture capital trends", "limit": 5}' | python -m json.tool

# Verify:
# ✅ Real excerpts about venture capital
# ✅ Scores > 0.5
# ✅ Can understand context from excerpt
```

**TEST 2: Browser Test**
```bash
open test-search-browser-enhanced.html
```

**YOU DO:**
1. Click "Search 'AI agents'" button
2. Look at the results
3. Verify you see:
   - Real conversation excerpts
   - Scores above 50%
   - Context that makes sense
   - NO generic placeholders

**TEST 3: Quality Spot Checks**
Search for these terms and verify quality:

| Search Term | Expected Result |
|-------------|-----------------|
| "GPT-4" | Technical discussions about the model |
| "burn rate" | Financial conversations |
| "Sequoia Capital" | Mentions of the VC firm |
| "product market fit" | Startup discussions |

---

## 📋 PHASE 4: Final Validation (30 minutes)

### Step 4.1: Comprehensive Test Suite (15 min)

**PROMPT FOR CLAUDE CODE:**
```
Create final_validation.py that runs ALL these tests:

1. System health checks:
   - MongoDB connection active
   - Supabase connection active
   - API responding
   - All environment variables set

2. Data integrity tests:
   - MongoDB has exactly 1,171 documents
   - Sample 10 random docs - all have transcripts
   - No documents with empty full_text

3. Search quality tests (run 20 different searches):
   - Technical terms: "GPT-4", "LLM", "embeddings"
   - Business terms: "burn rate", "ARR", "churn"
   - People/Companies: "Sam Altman", "OpenAI", "YC"
   - All must return relevant excerpts
   - All must have scores > 0.4

4. Performance tests:
   - 10 searches in parallel
   - Average response time < 1 second
   - No timeouts or errors

5. Excerpt quality validation:
   - Excerpts contain search terms
   - Excerpts are readable English
   - Excerpts show context (not cut mid-word)

Output detailed report with PASS/FAIL for each category.
```

**RUN FINAL VALIDATION:**
```bash
python final_validation.py

# Expected output:
# === FINAL VALIDATION REPORT ===
#
# System Health: ✅ ALL PASS
# - MongoDB: Connected (527MB stored)
# - Supabase: Connected
# - API: Responding in 247ms avg
#
# Data Integrity: ✅ ALL PASS
# - Documents: 1,171 (correct)
# - Transcripts: All present
# - Quality: 100% have content
#
# Search Quality: ✅ 18/20 PASS
# - Technical terms: 3/3 excellent
# - Business terms: 3/3 excellent
# - People/Companies: 2/3 good (1 low score)
#
# Performance: ✅ ALL PASS
# - Parallel searches: 812ms avg
# - No timeouts
#
# Excerpt Quality: ✅ ALL PASS
# - All contain search terms
# - All readable and contextual
#
# FINAL SCORE: 96% - READY FOR PRODUCTION! 🎉
```

### Step 4.2: User Acceptance Test (10 min)

**YOU DO:**
1. Open https://podinsight-api.vercel.app in browser
2. Open developer console (F12)
3. Paste this test:

```javascript
// Run comprehensive browser test
async function testSearch(query) {
    const response = await fetch('https://podinsight-api.vercel.app/api/search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: query, limit: 3})
    });
    const data = await response.json();

    console.log(`\n=== Searching for: ${query} ===`);
    data.results.forEach((r, i) => {
        console.log(`\n${i+1}. ${r.podcast_name}`);
        console.log(`   Score: ${(r.similarity_score * 100).toFixed(1)}%`);
        console.log(`   Excerpt: ${r.excerpt.substring(0, 150)}...`);
    });

    return data.results.every(r => r.similarity_score > 0.4 && r.excerpt.length > 100);
}

// Test multiple queries
const queries = ["AI agents", "venture capital", "B2B SaaS metrics", "crypto web3"];
const results = await Promise.all(queries.map(testSearch));

console.log("\n=== TEST RESULTS ===");
console.log(`Passed: ${results.filter(r => r).length}/${results.length}`);
console.log(results.every(r => r) ? "✅ ALL TESTS PASSED!" : "❌ Some tests failed");
```

**SUCCESS CRITERIA:**
- All 4 searches return real excerpts
- All scores > 40%
- You can understand the context
- No placeholder text anywhere

### Step 4.3: Final Dashboard Check (5 min)

**YOU DO:**
1. Go to MongoDB Atlas dashboard
2. Check Metrics tab:
   - ~527MB storage used
   - Queries per second during tests
   - No errors in logs

3. Go to Vercel dashboard:
   - Check function logs
   - Verify no timeout errors
   - Response times < 2 seconds

---

## ✅ DEFINITION OF DONE

**The following must ALL be true:**

1. **MongoDB Setup**
   - [x] $5,000 credit applied
   - [x] M10 cluster active in London
   - [x] Connection test passes

2. **Data Migration**
   - [x] All 1,171 episodes migrated
   - [x] ~527MB of transcript data
   - [x] Verification script shows 100% success

3. **Search Quality**
   - [x] "AI agents" returns real AI conversations
   - [x] "venture capital" returns VC discussions
   - [x] All scores > 40% for relevant content
   - [x] Excerpts show context clearly

4. **Production Ready**
   - [x] Deployed to Vercel
   - [x] Response time < 2 seconds
   - [x] No errors in logs
   - [x] Browser test shows real data

5. **The Paul Graham Test**
   - [x] You'd be proud to demo this search
   - [x] Results are genuinely useful
   - [x] No fake data anywhere

---

## 🚨 IF ANYTHING GOES WRONG

### MongoDB Connection Fails
```bash
# Test with mongosh
mongosh "mongodb+srv://podinsight-cluster.xxxxx.mongodb.net/" --username podinsight-api

# Check network access allows 0.0.0.0/0
# Verify password has no special characters
```

### Migration Hangs
```bash
# Check specific episode
python -c "
from pymongo import MongoClient
client = MongoClient(MONGODB_URI)
count = client.podinsight.transcripts.count_documents({})
print(f'Migrated so far: {count}/1171')
"
```

### Search Returns Nothing
```bash
# Check text index exists
python -c "
from pymongo import MongoClient
client = MongoClient(MONGODB_URI)
indexes = client.podinsight.transcripts.list_indexes()
print(list(indexes))
"
```

### Vercel Deployment Fails
```bash
# Check environment variable
vercel env pull
grep MONGODB_URI .env.local

# If missing, add via dashboard
```

---

This is your complete action plan. Every step has a clear action, reason, and test. Follow it exactly and you'll have real search working in 3-4 hours! 🚀
