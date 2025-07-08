# Episode Intelligence API - Complete Problem Documentation

## Overview
The Episode Intelligence API endpoints were returning 500 errors despite previous attempts to fix them. This issue involved multiple layers of problems that needed systematic investigation and resolution.

## Problem Timeline & Root Causes

### 1. Initial 500 Error Reports
**Symptoms:**
- All Episode Intelligence endpoints returning 500 errors:
  - `/api/intelligence/dashboard`
  - `/api/intelligence/health`
  - `/api/health` (main health check)

**Initial Investigation Findings:**
- MongoDB connection issues in `api/intelligence.py`
- AsyncIOMotorClient initialization problems
- Deprecated `datetime.utcnow()` usage
- Missing error handling for empty MongoDB collections

### 2. First Fix Attempt
**Changes Made:**
```python
# Fixed MongoDB connection with proper timeouts
_mongodb_client = AsyncIOMotorClient(
    mongodb_uri,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=10000,
    maxPoolSize=10,
    retryWrites=True
)

# Fixed datetime deprecation
datetime.now(timezone.utc)  # Instead of datetime.utcnow()

# Added mock data fallback for MVP
if not episodes:
    logger.info("No episodes found in MongoDB, returning mock data")
    # Return mock episode data...
```

**Result:** Code fixes were correct, but deployment still failed with 500 errors.

### 3. Discovery of Vercel's 12-Function Limit

**Critical Finding:**
```
Build Failed
No more than 12 Serverless Functions can be added to a Deployment on the Hobby plan.
```

**Understanding the Limit:**
- Each `.py` file in the `api/` directory becomes a separate serverless function
- Vercel Hobby plan allows maximum 12 functions per deployment
- We had 14 Python files in `api/` directory:

```
api/
├── audio_clips.py          # Function 1
├── command_bar.py          # Function 2
├── database.py             # Function 3
├── debug_search.py         # Function 4
├── diag.py                 # Function 5
├── heat_sentiment.py       # Function 6
├── index.py                # Function 7
├── intelligence.py         # Function 8
├── intelligence_minimal.py # Function 9
├── mongodb_search.py       # Function 10
├── search.py               # Function 11
├── search_lightweight_768d.py # Function 12
├── test_search.py          # Function 13
└── topic_velocity.py       # Function 14
```

### 4. Failed Consolidation Attempt

**What I Tried (WRONG APPROACH):**
- Attempted to embed intelligence endpoints directly into `api/index.py`
- Modified route registration from `@app.get` to `@topic_velocity_app.get`
- Deleted `api/intelligence.py` and `api/intelligence_minimal.py`
- This broke the entire API structure

**User's Critical Feedback:**
> "You really shouldn't be messing with topic_velocity.py imo. this was a working api"
> "We shouldn't be just randomly trying things"
> "First you need to reverse any changes that you've done that put at risk working api's!"

### 5. Proper Resolution

**Correct Approach:**
1. **Reverted all destructive changes:**
   ```bash
   git reset --hard ae0f217
   ```

2. **Moved non-critical files out of api/ directory:**
   ```bash
   mkdir -p api_disabled
   mv api/diag.py api_disabled/
   ```

3. **Final structure (10 functions - under the limit):**
   ```
   api/
   ├── audio_clips.py
   ├── command_bar.py
   ├── database.py
   ├── heat_sentiment.py
   ├── index.py              # Properly includes intelligence router
   ├── intelligence.py       # All Episode Intelligence endpoints
   ├── mongodb_search.py
   ├── search_lightweight_768d.py
   ├── topic_velocity.py
   └── (other non-critical files moved out)
   ```

## Technical Details

### MongoDB Connection Pattern for Serverless
The AsyncIOMotorClient needed specific configuration for Vercel's serverless environment:

```python
# Global connection reuse
_mongodb_client = None
_db = None

async def get_mongodb():
    global _mongodb_client, _db
    
    if _mongodb_client is None:
        # Lazy initialization with proper timeouts
        _mongodb_client = AsyncIOMotorClient(
            mongodb_uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            maxPoolSize=10,
            retryWrites=True
        )
```

### API Structure (index.py)
The proper way to include additional routers without breaking existing APIs:

```python
from fastapi import FastAPI
from .topic_velocity import app as topic_velocity_app
from .intelligence import router as intelligence_router

app = FastAPI()

# Include new routers BEFORE mounting the main app
app.include_router(intelligence_router)

# Mount existing app last to preserve all routes
app.mount("/", topic_velocity_app)
```

## Key Lessons Learned

1. **Vercel Function Limits:**
   - Hobby plan: 12 functions maximum
   - Each .py file in api/ = 1 function
   - Helper files should be outside api/ or consolidated

2. **Systematic Troubleshooting:**
   - Don't modify working code without understanding the problem
   - Use git reset to quickly recover from mistakes
   - Test one change at a time

3. **MongoDB in Serverless:**
   - Use connection pooling with proper timeouts
   - Implement lazy initialization
   - Always provide fallback data for MVPs

4. **API Architecture:**
   - Use FastAPI routers for modular endpoints
   - Mount order matters (specific routes before catch-all)
   - Preserve working code structure

## Current Status (Updated: July 8, 2025)

### Critical Discovery: Missing `lib` Directory
**Root Cause Found:** ALL API endpoints were failing with `ModuleNotFoundError: No module named 'lib'`

**Investigation Timeline:**
1. Initial assumption: Episode Intelligence specific issue
2. Discovery: ALL endpoints failing (topic-velocity, search, health, intelligence)
3. Vercel logs revealed: `ModuleNotFoundError` in `search_lightweight_768d.py` line 32
4. Root cause: `lib` directory was accidentally deleted in commit `c1c314b`

**Git History Analysis:**
- `2ee39fb` - Moved files from `api/` to `lib/` to reduce function count
- `b887687` - Fixed .gitignore and added lib directory to git
- `c1c314b` - **Accidentally deleted entire lib directory** while adding Episode Intelligence

**Fix Applied:**
```bash
# Restored lib directory from commit b887687
git checkout b887687 -- lib/
git add lib/
git commit -m "fix: Restore lib directory that was accidentally deleted"
git push origin main
```

**Current Deployment Status:**
- Commit `a414307` pushed to restore lib directory
- Vercel deployment triggered
- Awaiting deployment completion to verify fix

## Episode Intelligence Endpoints
All 4 endpoints remain available in `/api/intelligence.py`:
1. `GET /api/intelligence/dashboard` - Get top episodes by relevance score
2. `GET /api/intelligence/brief/{episode_id}` - Get full intelligence brief for specific episode
3. `POST /api/intelligence/share` - Share episode intelligence via email/Slack
4. `PUT /api/intelligence/preferences` - Update user preferences for personalized intelligence
5. `GET /api/intelligence/health` - Health check for intelligence API

## Next Steps for New Session

### Immediate Actions Required:
1. **Verify Deployment Success**
   - Check Vercel deployment status for commit `a414307`
   - Confirm lib directory is included in deployment

2. **Test Core API Endpoints**
   ```bash
   # Test each endpoint to confirm they're working
   curl https://podinsight-api.vercel.app/api/topic-velocity
   curl https://podinsight-api.vercel.app/api/heat-sentiment
   curl https://podinsight-api.vercel.app/api/sentiment_analysis_v2
   ```

3. **Test Episode Intelligence Endpoints**
   ```bash
   # Health check (no auth required)
   curl https://podinsight-api.vercel.app/api/intelligence/health
   
   # Dashboard endpoint (currently auth disabled)
   curl https://podinsight-api.vercel.app/api/intelligence/dashboard
   ```

4. **Story 5B Status**
   - API code is implemented but needs verification
   - Authentication is commented out (lines 15-17 in `api/intelligence.py`)
   - MongoDB connection pattern implemented
   - Mock data fallback in place

### Key Issues to Address:
1. **Authentication**: Currently disabled, needs to be re-enabled per Asana requirements
2. **Testing**: No actual testing was done for Story 5B
3. **Dashboard Integration**: Cannot proceed until API endpoints are working

## Related Documentation
- Episode Intelligence Feature: `docs/sprint4/episode-intelligence-v5-complete.md`
- API Reference: `docs/master-api-reference.md`
- Business Overview: `docs/Business Overview.md`