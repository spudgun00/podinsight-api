# Episode Intelligence Visual Data Flow

## Dashboard Card Visual Breakdown

### What Each Card Shows:

```
┌─────────────────────────────────────────────────────────┐
│ AIL                                              92     │  ← relevance_score × 100
│                                                         │
│ White House BTS, Google buys Wiz,                      │  ← title (truncated)
│ Treasury vs Fed, Space Rescue                          │
│                                                         │
│ 🔴 "I give them their first 25K check..."              │  ← signals[0].content
│ 🟠 "We passed on Uber's seed round"                    │  ← signals[1].content
│ 🟢 "Looking for alpha in non-consensus..."             │  ← signals[2].content
│                                                         │
│ All-In Pod • 2h ago • 1h 23m                          │  ← podcast_name • time_ago • duration
└─────────────────────────────────────────────────────────┘
```

### Signal Type Color Mapping:
- 🔴 Red = `investable` (investment opportunities)
- 🟠 Orange = `competitive` (competitor intelligence)
- 🟢 Green = `sound_bite` (strategic insights)
- 🔵 Blue = `portfolio` (portfolio mentions)

---

## Data Flow Architecture

```
MongoDB                          API                           Frontend
─────────────────────────────────────────────────────────────────────────

episode_intelligence     →    /api/intelligence/dashboard   →    Dashboard Cards
collection                    Returns top 6 episodes              (6 cards)
                             sorted by relevance_score
                                      ↓
                             {
                               episodes: [...],
                               total_episodes: 50
                             }
                                      ↓
                                                              Transform to UI cards
                                                              with color-coded signals


episode_intelligence     →    /api/intelligence/brief/{id}  →    Episode Modal
single document               Returns full episode details        (detailed view)
                                      ↓
                             {
                               episode_id: "...",
                               signals: [...all],
                               key_insights: [...],
                               audio_url: "..."
                             }
                                      ↓
                                                              Display all signals
                                                              with play buttons


episode_intelligence     →    /api/intelligence/episodes    →    All Episodes List
all documents                 Returns paginated list             (table view)
                             with filters
                                      ↓
                             {
                               episodes: [...50],
                               page: 1,
                               total_pages: 5
                             }
```

---

## Current Data Flow (What's Actually Happening)

```
MongoDB                          API                           Frontend
─────────────────────────────────────────────────────────────────────────

episode_intelligence     →    /api/intelligence/dashboard   →    Empty Array ❌
50 documents exist            Returns: { episodes: [] }          No cards shown

                                      ↓ BROKEN

                             Backend query issue:
                             Not filtering for episodes
                             with intelligence data


episode_intelligence     →    /api/intelligence/brief/{id}  →    Works ✅
single document               Returns full episode               Modal displays
                             with all signals                   correctly


debug endpoint           →    /api/intelligence/            →    Shows 50 episodes ✅
                             find-episodes-with-                exist with data
                             intelligence
```

---

## Fix Required in Backend

### Current Query (Suspected):
```python
# In dashboard endpoint
episodes = db.episode_intelligence.find().limit(6)  # Returns empty
```

### Should Be:
```python
# In dashboard endpoint
episodes = db.episode_intelligence.find({
    "signals": {"$exists": True, "$ne": []},  # Has signals
    "relevance_score": {"$exists": True}       # Has score
}).sort("relevance_score", -1).limit(6)       # Top 6 by score
```

---

## Testing the Fix

### 1. Verify Dashboard Returns Data:
```bash
curl https://podinsight-api.vercel.app/api/intelligence/dashboard
# Should return 6 episodes with signals
```

### 2. Check Each Episode Has Required Fields:
- episode_id ✓
- title ✓
- podcast_name ✓
- published_at ✓
- duration_seconds ✓
- relevance_score ✓
- signals[] with at least 3 items ✓

### 3. Verify Signal Structure:
```json
{
  "type": "investable|competitive|sound_bite|portfolio",
  "content": "The actual quote or insight",
  "confidence": 0.8,
  "timestamp": "32:29"
}
```

---

## Frontend Implementation Status

✅ **Ready to Connect:**
- useIntelligenceDashboard hook exists
- Data transformer handles signal types correctly
- UI components expect correct data structure
- Just needs backend to return data

❌ **Blocked By:**
- Backend dashboard endpoint returning empty array
- Need backend team to fix the MongoDB query

---

## Quick Win Solution

While waiting for backend fix, the frontend could:
1. Call individual brief endpoints for first 6 episodes
2. Transform that data for dashboard display
3. But this is inefficient (6 API calls vs 1)

Better to fix the backend query properly.
