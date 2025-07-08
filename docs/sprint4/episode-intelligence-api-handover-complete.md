# Episode Intelligence API - Complete Session Handover Document

## Session Date: 2025-07-08
## Current Status: Story 5B - API Implementation (Partially Working)

---

## 🎯 Business Context

### What is Episode Intelligence?
Episode Intelligence is an AI-powered briefing system that transforms 90-minute podcast episodes into 30-second actionable intelligence specifically for VCs. It automatically surfaces:
- **Investable opportunities** - Companies raising funds, check sizes, round details
- **Competitive intelligence** - What other VCs are doing, deals they passed on
- **Portfolio mentions** - Updates about user's portfolio companies
- **Sound bites** - Quotable insights and predictions

### The Problem It Solves
VCs consume 15+ hours of podcast content weekly but miss critical signals buried in conversations. They fear missing the next Uber announcement or competitor move because they couldn't listen to every episode.

### Sprint 4 Goal
Deliver an MVP with 50 pre-processed episodes from 5 core podcasts (All-In, 20VC, Acquired, European VC, Invest Like the Best) that demonstrates value to 10 beta VCs who will say "I can't imagine my morning without this."

---

## 📋 Sprint 4 Story Progress

### Story 5B: MongoDB Schema & API Endpoints
**Status**: IN PROGRESS - API endpoints created but signal extraction failing for most episodes

### Completed:
1. ✅ Created all API endpoints:
   - `/api/intelligence/dashboard` - Get top episodes by relevance
   - `/api/intelligence/brief/{episode_id}` - Get detailed brief
   - `/api/intelligence/share` - Share via email/Slack
   - `/api/intelligence/preferences` - Update user preferences
   - `/api/intelligence/health` - Health check

2. ✅ MongoDB collections created:
   - `episode_intelligence` - 50 documents with MVP episode data
   - `podcast_authority` - 17 documents with podcast tier rankings
   - `user_intelligence_prefs` - User preference storage

3. ✅ Fixed timestamp validation error that was causing Pydantic validation failures

### Current Issue:
**The dashboard returns empty results despite having 50 episodes with intelligence data.**

---

## 🔍 Technical Investigation Summary

### What We Discovered:

1. **All 50 episode_intelligence documents have matching metadata** ✓
   - Confirmed via `/api/intelligence/check-guid-matching` endpoint
   - No GUID mismatch issues

2. **Signal extraction works for SOME episodes but not others**:
   - ✅ Episode `02fc268c-61dc-4074-b7ec-882615bc6d85` extracts 12 signals successfully
   - ❌ Episode `1216c2e7-42b8-42ca-92d7-bad784f80af2` has signals but extracts 0
   - ❌ Most other episodes fail signal extraction

3. **The issue is in the `get_episode_signals` function** (line 149 in `api/intelligence.py`):
   ```python
   def get_episode_signals(db, episode_id: str) -> List[Signal]:
   ```
   This function finds the documents but returns empty signal lists for most episodes.

4. **Root causes identified**:
   - Fixed: Timestamp field can be dict `{"start": 1949.825, "end": 1957.393}` instead of string
   - Remaining: Other signal data format variations that cause extraction to fail silently

### Debug Endpoints Created:
- `/api/intelligence/debug` - Shows collection counts and samples
- `/api/intelligence/find-episodes-with-intelligence` - Lists episodes with signals
- `/api/intelligence/test-signals/{episode_id}` - Tests signal extraction for specific episode
- `/api/intelligence/check-guid-matching` - Shows which GUIDs match between collections
- `/api/intelligence/dashboard-debug` - Returns dashboard search logs
- `/api/intelligence/debug-dashboard-issue` - Shows document structure details

---

## 📁 Key Files and Locations

### API Repository Structure:
```
podinsight-api/
├── api/
│   └── intelligence.py          # Main API file with all endpoints and get_episode_signals
├── docs/
│   ├── Business Overview.md     # Overall business context
│   ├── master-api-reference.md  # API documentation (updated)
│   ├── master-data-architecture.md  # Database schemas (updated)
│   └── sprint4/
│       ├── episode-intelligence-v5-complete.md  # Sprint plan
│       └── episode-intelligence-api-handover.md # Previous session notes
```

### MongoDB Collections:
- **Database**: `podinsight`
- **Collections**:
  - `episode_metadata` - 1,236 documents (all episodes)
  - `episode_intelligence` - 50 documents (MVP subset)
  - `podcast_authority` - 17 documents
  - `user_intelligence_prefs` - User preferences

### Important Context:
1. **episode_id field**: Was added to episode_metadata documents to match the GUID value, ensuring consistency across collections
2. **MVP Scope**: Only 50 episodes have intelligence data (not all 1,236)
3. **Authentication**: Temporarily removed from Episode Intelligence endpoints to unblock frontend integration

---

## 🐛 The Current Bug

### Symptom:
Dashboard endpoint returns empty results despite 50 episodes having intelligence data.

### Root Cause:
The `get_episode_signals` function successfully finds episode_intelligence documents but fails to extract signals from most of them. Only a few episodes (like `02fc268c-61dc-4074-b7ec-882615bc6d85`) work correctly.

### Why It's Happening:
1. We fixed one timestamp format issue (dict vs string)
2. But there are other data format variations in the 50 documents
3. The function silently returns empty arrays when extraction fails
4. No proper error logging to identify the specific issues

### What Needs to Be Done:
1. Add detailed logging to `get_episode_signals` to identify why signals aren't extracted
2. Handle all data format variations in the 50 episode_intelligence documents
3. Ensure consistent signal extraction across all episodes

---

## 🚀 Next Session Prompt

Use this prompt to start the next session:

```
I need help fixing the Episode Intelligence API dashboard. Here's the context:

We're working on Story 5B of Sprint 4 - implementing the Episode Intelligence API for a VC podcast intelligence platform. The API endpoints are created and deployed on Vercel, but the dashboard returns empty results.

Key findings from previous session:
1. 50 episode_intelligence documents exist in MongoDB with signals data
2. All 50 have matching episode_metadata entries (no GUID issues)
3. The get_episode_signals function in api/intelligence.py finds documents but returns empty signal arrays for most episodes
4. Only some episodes work (e.g., 02fc268c-61dc-4074-b7ec-882615bc6d85 returns 12 signals)
5. Most episodes fail (e.g., 1216c2e7-42b8-42ca-92d7-bad784f80af2 returns 0 signals despite having data)

The handover document is at: @docs/sprint4/episode-intelligence-api-handover-complete.md

Please help me:
1. Debug why get_episode_signals fails for most episodes
2. Fix the signal extraction to work for all 50 episodes
3. Get the dashboard returning real intelligence data

The goal is to complete Story 5B so the frontend team can integrate with working API endpoints.
```

---

## 📊 Current Deployment Status

- **API URL**: https://podinsight-api.vercel.app
- **Latest Commit**: `fb47767` - Added dashboard-debug endpoint
- **Deployment**: Vercel (auto-deploy on push to main)
- **MongoDB**: Connected and accessible
- **Known Working Episodes**: 
  - `02fc268c-61dc-4074-b7ec-882615bc6d85` ✓
  - Others need investigation

---

## 🎯 Success Criteria for Story 5B

1. Dashboard endpoint returns 6-8 episodes with intelligence data
2. Each episode shows 3-4 signals with proper content
3. Relevance scoring works based on podcast authority
4. All 50 MVP episodes have extractable signals
5. API is ready for frontend integration (Story 4)

---

## 📝 Notes for Next Session

1. **DO NOT** make drastic architectural changes - the issue is in signal extraction, not the overall approach
2. **DO** add comprehensive logging to understand signal format variations
3. **DO** test each of the 50 episodes to identify patterns in what works/fails
4. The MongoDB connection and data retrieval work fine - focus on the signal extraction logic
5. Consider creating a batch test script to validate all 50 episodes at once

---

**Document Created**: 2025-07-08
**Last Updated**: 2025-07-08 22:55 UTC
**Author**: Claude Assistant with James Gill