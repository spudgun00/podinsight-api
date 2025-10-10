# 🔍 PodInsight Dashboard - Search Component Troubleshooting Guide

Hi! I'm troubleshooting display issues in the PodInsight dashboard search component. The backend API is working, but the frontend is showing inconsistent data (e.g., "Unknown Podcast" titles, 0% relevancy scores).

---

## 📍 Context & Current Status

**Repository**: `/Users/jamesgill/PodInsights/podinsight-dashboard` (FRONTEND)
**Backend API**: `https://podinsight-api.vercel.app`
**Component**: Test Search Component (primary testing interface)
**Status**: ⚠️ Backend working, frontend display issues

### Known Issues:
1. **Podcast titles showing "Unknown Podcast"** (inconsistent - sometimes works, sometimes doesn't)
2. **Relevancy scores showing 0%** (should show actual scores from API)
3. **Other display inconsistencies** in search results

---

## 📚 CRITICAL: Read Documentation First!

**Before starting diagnosis, READ THESE FILES for essential context:**

### 1. **Backend API Runbook** (YOUR BIBLE):
`/Users/jamesgill/PodInsights/podinsight-api/documentation/DASHBOARD_INTEGRATION_RUNBOOK.md`
- **Version**: 1.5.2
- **Search API Section**: Lines 358-617 (260 lines)
- **What it contains**:
  - Complete search endpoint specification
  - Response schema with all fields
  - Expected data structure
  - Error handling patterns
  - Integration examples

**KEY SECTIONS TO READ:**
- **Task 2: Search Component** (lines 358-617) - Search implementation details
- **Search Response Schema** - Shows exact field names and structure
- **API Response Examples** - What working responses look like

### 2. **Architecture Documentation**:
`/Users/jamesgill/PodInsights/podinsight-api/documentation/PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md`
- MongoDB data model
- API endpoint specifications
- Field naming conventions

### 3. **MongoDB Data Model**:
`/Users/jamesgill/PodInsights/podinsight-api/documentation/MONGODB_DATA_MODEL.md`
- Episode metadata structure
- Field names and types
- Data relationships

---

## 🔧 Diagnostic Process

### Step 1: Verify Backend API is Working

**Test the search endpoint directly:**

```bash
# Test search API with a known query
curl -s "https://podinsight-api.vercel.app/api/search?query=artificial+intelligence&limit=5" | jq '.'
```

**What to check:**
- ✅ Status 200 response
- ✅ `results` array with data
- ✅ Each result has `podcast_name` field (not null/empty)
- ✅ Each result has `score` field (not 0)
- ✅ Each result has `episode_title`, `snippet`, `timestamp`

**Expected Response Structure:**
```json
{
  "query": "artificial intelligence",
  "results": [
    {
      "episode_id": "uuid-here",
      "podcast_name": "Actual Podcast Name",  // ← Should NOT be "Unknown"
      "episode_title": "Episode Title",
      "snippet": "...matched text...",
      "timestamp": "00:12:34",
      "score": 85.5,  // ← Should NOT be 0
      "start_time": 754.0,
      "end_time": 784.0
    }
  ],
  "total_results": 10,
  "search_type": "hybrid"
}
```

### Step 2: Check Frontend API Call

**Find where the search API is called in the dashboard:**

Look for files like:
- `app/test-command-bar/page.tsx` or similar test component
- `lib/api.ts` or `utils/api.ts` (API utility functions)
- Any component that calls `/api/search`

**Questions to investigate:**

1. **Is the API call correct?**
   ```typescript
   // Example correct call:
   const response = await fetch(
     `https://podinsight-api.vercel.app/api/search?query=${encodeURIComponent(query)}&limit=10`
   );
   const data = await response.json();
   ```

2. **Are we reading the response correctly?**
   - Check if accessing `data.results` (not `data` directly)
   - Check if mapping over the results array properly

3. **Are we using the correct field names?**
   - ✅ `podcast_name` (NOT `podcastName` or `podcast_title`)
   - ✅ `episode_title` (NOT `title` or `episodeTitle`)
   - ✅ `score` (NOT `relevancy` or `relevance_score`)

### Step 3: Check Data Mapping & Display

**Common frontend bugs to look for:**

#### Bug Pattern #1: Wrong Field Names
```typescript
// ❌ WRONG - camelCase doesn't match API
result.podcastName  // undefined → shows "Unknown Podcast"

// ✅ CORRECT - snake_case from API
result.podcast_name
```

#### Bug Pattern #2: Wrong Score Field
```typescript
// ❌ WRONG - API doesn't return this field
result.relevancy_score  // undefined → shows 0%

// ✅ CORRECT - API returns "score"
result.score
```

#### Bug Pattern #3: Not Handling API Response Structure
```typescript
// ❌ WRONG - trying to map data directly
data.map(result => ...)  // data is object, not array

// ✅ CORRECT - map over results array
data.results.map(result => ...)
```

#### Bug Pattern #4: Default Values Masking Issues
```typescript
// ❌ WRONG - hides the real issue
const podcast = result.podcast_name || "Unknown Podcast"

// ✅ BETTER - see what's actually undefined
console.log("Raw result:", result)
console.log("podcast_name:", result.podcast_name)
```

### Step 4: Check Component State & Props

**TypeScript interface issues:**

Check if there's a type mismatch:
```typescript
// Type definition might not match API response
interface SearchResult {
  podcastName: string;  // ❌ Wrong - API uses podcast_name
  podcast_name: string; // ✅ Correct
}
```

### Step 5: Console Logging for Diagnosis

**Add these debug logs to find the issue:**

```typescript
// 1. Log the raw API response
console.log("API Response:", data);

// 2. Log the results array
console.log("Results array:", data.results);

// 3. Log each result as it's mapped
data.results.map((result, index) => {
  console.log(`Result ${index}:`, {
    podcast_name: result.podcast_name,
    episode_title: result.episode_title,
    score: result.score,
    fullResult: result
  });
  return result;
});

// 4. Log what's being displayed
console.log("Displaying:", {
  title: result.podcast_name || "Unknown Podcast",  // See if OR is triggering
  score: result.score || 0
});
```

---

## 🎯 Specific Issues to Investigate

### Issue #1: "Unknown Podcast" Appearing

**Root Cause Possibilities:**
1. ❌ Using wrong field name (`podcastName` vs `podcast_name`)
2. ❌ Not accessing `data.results` array correctly
3. ❌ TypeScript interface mismatch
4. ❌ Destructuring error (e.g., `const { podcastName } = result`)

**How to diagnose:**
```typescript
// Add this to see what you're actually getting
const result = data.results[0];
console.log("All keys:", Object.keys(result));
console.log("podcast_name value:", result.podcast_name);
console.log("podcast_name type:", typeof result.podcast_name);
```

**Expected Output:**
```
All keys: ['episode_id', 'podcast_name', 'episode_title', 'snippet', 'timestamp', 'score', 'start_time', 'end_time']
podcast_name value: "No Priors: Artificial Intelligence | Technology | Startups"
podcast_name type: "string"
```

### Issue #2: 0% Relevancy Score

**Root Cause Possibilities:**
1. ❌ Using wrong field name (API returns `score`, not `relevancy_score`)
2. ❌ Not converting score to percentage (API returns 0-100, might expect 0-1)
3. ❌ Type coercion issue (reading as string instead of number)

**How to diagnose:**
```typescript
const result = data.results[0];
console.log("Score value:", result.score);
console.log("Score type:", typeof result.score);
console.log("As percentage:", result.score + "%");
```

**Expected Output:**
```
Score value: 85.5
Score type: "number"
As percentage: "85.5%"
```

### Issue #3: Inconsistent Behavior

**If it works sometimes but not others:**

1. **Check for race conditions:**
   - Are you updating state before API completes?
   - Are multiple searches overlapping?

2. **Check for cached data:**
   - Are you mixing cached and fresh data?
   - Is old data persisting in state?

3. **Check for conditional rendering:**
   - Are you showing different data in different UI states?
   - Are loading/error states hiding the real data?

---

## 🔍 Quick Diagnostic Commands

**Test backend directly:**
```bash
# 1. Test search endpoint
curl -s "https://podinsight-api.vercel.app/api/search?query=AI&limit=1" | jq '.results[0] | {podcast_name, score}'

# 2. Expected output:
# {
#   "podcast_name": "Some Podcast Name",
#   "score": 78.3
# }
```

**Check Next.js component:**
```bash
# Find test search component
find /Users/jamesgill/PodInsights/podinsight-dashboard -name "*test*" -o -name "*search*" | grep -i component

# Search for API calls
grep -r "api/search" /Users/jamesgill/PodInsights/podinsight-dashboard/app --include="*.tsx" --include="*.ts"
```

---

## 📊 Verified Backend Data Quality

**As of last check (2025-10-10):**
- ✅ Total episodes in MongoDB: **1,236**
- ✅ Episodes with `podcast_title`: **1,236 (100%)**
- ✅ Blank/null podcast titles: **0**
- ✅ Transcript endpoint: **WORKING**
- ✅ Search endpoint: **WORKING**

**This means the backend data is CLEAN. Any "Unknown Podcast" is a frontend display bug, not a data issue.**

---

## 🎯 Action Plan

### DO THIS NOW:

1. **Read the documentation** (runbook lines 358-617)
2. **Test the API directly** with curl to confirm backend is working
3. **Add console.logs** to your search component to see raw API response
4. **Check field names** - compare your code to API response structure
5. **Verify you're accessing `data.results`** not `data` directly
6. **Look for TypeScript interface mismatches**

### Then Ask These Specific Questions:

Once you have the diagnostic data, we can answer:
- **Q1**: "Why is podcast_name showing as undefined in my component?"
- **Q2**: "Why is the score field showing as 0 when API returns valid scores?"
- **Q3**: "What field names does the API actually return?" (document this)
- **Q4**: "Is there a TypeScript type mismatch between API and component?"

---

## 🚨 Common Pitfalls

1. **Don't assume camelCase** - API uses snake_case (`podcast_name`, not `podcastName`)
2. **Don't trust TypeScript types** - verify they match actual API response
3. **Don't use default values during debugging** - they hide the real issue
4. **Don't skip console.logging** - you need to see the raw data
5. **Don't forget `data.results`** - API returns object with results array, not array directly

---

## 📝 Expected Questions I Should Ask You

After reading docs and testing, I should ask:

1. "Can you show me the curl output from testing the search API?"
2. "What does `console.log(data)` show after the API call?"
3. "Can you show me the component code where results are mapped?"
4. "What TypeScript interface are you using for search results?"
5. "Can you show me the exact line where podcast_name is accessed?"

---

## 🔧 FIXED: Backend Issues (2025-10-10)

### Issue #1: "Unknown Podcast" ✅ FIXED
**Root Cause**: `search_lightweight_768d.py` line 524 was using `podcast_title` but hybrid search returns `podcast_name`
**Fix**: Changed to `result.get("podcast_name")` - deployed to production
**Status**: ✅ Resolved - API now returns actual podcast names

### Issue #2: Only 2 Sources Showing (When Expecting 5)
**Root Cause**: **FRONTEND ISSUE** - Backend IS returning 5 results
**Evidence**: `curl` test shows `returned_count: 5`
**Fix Required**: Dashboard code limiting display to 2 results
**Check For**:
- `.slice(0, 2)` or `.take(2)` in results mapping
- CSS hiding results 3-5 (overflow, height limits)
- Conditional rendering showing only first 2
- Loop or map only iterating twice

## ✅ Success Criteria

When troubleshooting is complete:
- ✅ Search results show actual podcast names (not "Unknown Podcast") - **BACKEND FIXED**
- ✅ Relevancy scores show correct percentages (not 0%)
- ✅ All 5 results display (not just 2) - **FRONTEND FIX NEEDED**
- ✅ All fields display consistently
- ✅ TypeScript types match actual API response
- ✅ Console shows no undefined values
- ✅ Understanding of root cause documented

---

## 🔗 Quick Reference

**Backend API Base**: `https://podinsight-api.vercel.app`

**Key Endpoints:**
- Search: `GET /api/search?query={query}&limit={limit}`
- Transcript: `GET /api/transcript/{episode_id}`

**API Response Field Names (USE THESE EXACT NAMES):**
- `podcast_name` ← podcast title
- `episode_title` ← episode title
- `score` ← relevancy score (0-100)
- `snippet` ← matched text
- `timestamp` ← formatted time
- `start_time` ← seconds (float)
- `end_time` ← seconds (float)
- `episode_id` ← UUID string

**MongoDB Collection Names:**
- `episode_metadata` ← episode/podcast metadata
- `transcript_chunks_768d` ← transcript chunks with embeddings

---

## 🎬 Next Steps

1. Read the documentation files listed above
2. Test backend API with curl commands
3. Add console.logs to your component
4. Report back with:
   - What the API returns (curl output)
   - What your component sees (console.log output)
   - What's being displayed (screenshot/description)
5. We'll identify the exact bug together

Let's find those bugs! 🐛🔍
