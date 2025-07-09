# Episode Intelligence Data Mapping Document

## Overview
This document maps each UI element in the Episode Intelligence feature to its corresponding MongoDB field and collection. The feature has three distinct views:

1. **Dashboard View** - 6 episode cards
2. **Episode Modal** - Detailed view when clicking a card
3. **All Episodes Modal** - Full list view

---

## 1. Dashboard View (6 Episode Cards)

### Visual Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Episode Intelligence                          View All (12) > │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│ │ Card 1      │ │ Card 2      │ │ Card 3      │            │
│ └─────────────┘ └─────────────┘ └─────────────┘            │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│ │ Card 4      │ │ Card 5      │ │ Card 6      │            │
│ └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Each Episode Card Contains:

```
┌─────────────────────────────────────────────┐
│ [PODCAST_ABBREVIATION]  [SIGNAL_STRENGTH]   │
│                                             │
│ [EPISODE_TITLE]                             │
│                                             │
│ [SIGNAL_1]                                  │
│ [SIGNAL_2]                                  │
│ [SIGNAL_3]                                  │
│                                             │
│ [PODCAST_NAME] • [TIME_AGO] • [DURATION]    │
└─────────────────────────────────────────────┘
```

### Data Mapping for Episode Card

| UI Element | MongoDB Collection | MongoDB Field | Example | Notes |
|------------|-------------------|---------------|---------|-------|
| **PODCAST_ABBREVIATION** | `episode_metadata` | Derived from `podcast_name` | "AIL" | First letters of podcast name |
| **SIGNAL_STRENGTH** | `episode_intelligence` | `relevance_score` | 92 | Multiply by 100 for percentage |
| **EPISODE_TITLE** | `episode_intelligence` | `title` | "White House BTS, Google buys Wiz..." | |
| **SIGNAL_1/2/3** | `episode_intelligence` | `signals[].content` | "I give them their first 25K check..." | First 3 signals |
| **PODCAST_NAME** | `episode_intelligence` | `podcast_name` | "All-In Pod" | |
| **TIME_AGO** | `episode_intelligence` | `published_at` | "2h ago" | Calculate from published_at |
| **DURATION** | `episode_intelligence` | `duration_seconds` | "1h 23m" | Convert seconds to h/m format |

### API Response Structure Required

```json
GET /api/intelligence/dashboard?limit=6

{
  "episodes": [
    {
      "episode_id": "685ba724e4f9ec2f07562253",
      "title": "White House BTS, Google buys Wiz...",
      "podcast_name": "All-In with Chamath, Jason, Sacks & Friedberg",
      "published_at": "2025-03-22",
      "duration_seconds": 4980,
      "relevance_score": 0.92,
      "signals": [
        {
          "type": "investable",
          "content": "I give them their first 25K check or 125K check",
          "confidence": 0.8,
          "timestamp": "32:29"
        },
        {
          "type": "competitive",
          "content": "We passed on Uber's seed round",
          "confidence": 0.9,
          "timestamp": "30:53"
        },
        {
          "type": "sound_bite",
          "content": "We're looking for alpha in non-consensus bets",
          "confidence": 0.8,
          "timestamp": "29:55"
        }
      ]
    }
  ],
  "total_episodes": 50,
  "generated_at": "2025-07-09T13:00:00Z"
}
```

---

## 2. Episode Modal (Detailed View)

### Visual Layout
```
┌─────────────────────────────────────────────────────────────┐
│ [X]                                                         │
│                                                             │
│ [EPISODE_TITLE]                                             │
│ [PODCAST_NAME] • [FULL_DATE] • [DURATION]                   │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Key Insights                                             │ │
│ │ • [INSIGHT_1]                                            │ │
│ │ • [INSIGHT_2]                                            │ │
│ │ • [INSIGHT_3]                                            │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ All Signals                                              │ │
│ │ ┌───────────────────────────────────────────────────┐   │ │
│ │ │ [SIGNAL_TYPE] • [TIMESTAMP] • [CONFIDENCE]        │   │ │
│ │ │ [SIGNAL_CONTENT]                                   │   │ │
│ │ │ [▶ Play Audio Clip]                               │   │ │
│ │ └───────────────────────────────────────────────────┘   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [Share via Email] [Share via Slack]                        │
└─────────────────────────────────────────────────────────────┘
```

### Data Mapping for Episode Modal

| UI Element | MongoDB Collection | MongoDB Field | Example | Notes |
|------------|-------------------|---------------|---------|-------|
| **EPISODE_TITLE** | `episode_intelligence` | `title` | "White House BTS, Google buys Wiz..." | |
| **PODCAST_NAME** | `episode_intelligence` | `podcast_name` | "All-In with Chamath..." | |
| **FULL_DATE** | `episode_intelligence` | `published_at` | "March 22, 2025" | Format date |
| **DURATION** | `episode_intelligence` | `duration_seconds` | "1h 23m" | Convert seconds |
| **INSIGHT_1/2/3** | `episode_intelligence` | `key_insights[]` | "Investment opportunity: First checks..." | Array of strings |
| **SIGNAL_TYPE** | `episode_intelligence` | `signals[].type` | "investable" | Badge color based on type |
| **TIMESTAMP** | `episode_intelligence` | `signals[].timestamp` | "32:29" | For audio clip |
| **CONFIDENCE** | `episode_intelligence` | `signals[].confidence` | "80%" | Multiply by 100 |
| **SIGNAL_CONTENT** | `episode_intelligence` | `signals[].content` | Full signal text | |
| **AUDIO_URL** | `episode_intelligence` | `audio_url` | S3 URL | For clip generation |

### API Response Structure Required

```json
GET /api/intelligence/brief/{episode_id}

{
  "episode_id": "685ba724e4f9ec2f07562253",
  "title": "White House BTS, Google buys Wiz, Treasury vs Fed, Space Rescue",
  "podcast_name": "All-In with Chamath, Jason, Sacks & Friedberg",
  "published_at": "2025-03-22",
  "duration_seconds": 4980,
  "relevance_score": 0.92,
  "signals": [
    {
      "type": "investable",
      "content": "I give them their first 25K check or 125K check",
      "confidence": 0.8,
      "timestamp": "32:29"
    }
    // ... all signals
  ],
  "summary": "Episode discusses latest tech investments and market trends...",
  "key_insights": [
    "Investment opportunity: I give them their first 25K check or 125K check",
    "Market intelligence: We passed on Uber's seed round",
    "Strategic insight: Looking for alpha in non-consensus bets"
  ],
  "audio_url": "s3://pod-insights-raw/all-in-with.../audio/episode.mp3"
}
```

---

## 3. All Episodes Modal (List View)

### Visual Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Episode Intelligence                                    [X] │
├─────────────────────────────────────────────────────────────┤
│ [Search...] [Filter: Podcast ▼] [Filter: Signal ▼] [Reset] │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [TITLE] | [PODCAST] | [SIGNALS] | [DATE] | [SCORE]      │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ Episode 1 details...                                    │ │
│ │ Episode 2 details...                                    │ │
│ │ ... (paginated)                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Data Mapping for All Episodes List

| UI Element | MongoDB Collection | MongoDB Field | Example | Notes |
|------------|-------------------|---------------|---------|-------|
| **TITLE** | `episode_intelligence` | `title` | "White House BTS..." | Truncated |
| **PODCAST** | `episode_intelligence` | `podcast_name` | "All-In Pod" | |
| **SIGNALS** | `episode_intelligence` | `signals[]` | "3 🔴 2 🟠" | Count by type |
| **DATE** | `episode_intelligence` | `published_at` | "Mar 22" | Short format |
| **SCORE** | `episode_intelligence` | `relevance_score` | "92%" | Multiply by 100 |

---

## MongoDB Collections Structure

### 1. `episode_intelligence` Collection
```javascript
{
  "_id": ObjectId("..."),
  "episode_id": "685ba724e4f9ec2f07562253",
  "title": "White House BTS, Google buys Wiz...",
  "podcast_name": "All-In with Chamath, Jason, Sacks & Friedberg",
  "published_at": ISODate("2025-03-22"),
  "duration_seconds": 4980,
  "relevance_score": 0.92,
  "signals": [
    {
      "type": "investable",
      "content": "I give them their first 25K check or 125K check",
      "confidence": 0.8,
      "timestamp": "32:29"
    }
  ],
  "summary": "Episode summary...",
  "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
  "audio_url": "s3://..."
}
```

### 2. `episode_metadata` Collection (for additional info if needed)
```javascript
{
  "_id": ObjectId("..."),
  "episode_id": "685ba724e4f9ec2f07562253",
  "feed_name": "all-in-with-chamath-jason-sacks-friedberg",
  "guid": "02fc268c-61dc-4074-b7ec-882615bc6d85",
  "published_at": ISODate("2025-03-22"),
  "duration": "01:23:00"
}
```

---

## Current Issue Analysis

### Problem
The `/api/intelligence/dashboard` endpoint returns empty array despite 50 episodes having intelligence data.

### Root Cause
Backend query is not filtering correctly for episodes with intelligence data.

### Evidence
- Debug endpoint shows 50 episodes: `/api/intelligence/find-episodes-with-intelligence`
- Individual brief endpoints work: `/api/intelligence/brief/{id}`
- Dashboard endpoint returns empty: `/api/intelligence/dashboard`

### Solution Required
Backend needs to fix the dashboard query to properly filter and return episodes with intelligence data, sorted by relevance score.

---

## Implementation Checklist

- [ ] Fix backend dashboard endpoint to return episodes with intelligence
- [ ] Ensure response includes all required fields mapped above
- [ ] Sort by relevance_score descending
- [ ] Limit to 6 for dashboard view
- [ ] Include total_episodes count for "View All" button
- [ ] Format timestamps properly (ISO 8601)
- [ ] Ensure signals array includes type, content, confidence, timestamp

---

This mapping document provides the complete data flow from MongoDB to UI for all three views of the Episode Intelligence feature.
