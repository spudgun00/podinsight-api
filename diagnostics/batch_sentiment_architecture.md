# Batch Sentiment Processing Architecture

## Problem
Current sentiment API times out (300s) trying to process 800k+ chunks on-demand.

## Solution: Nightly Batch Processing

### Architecture Overview
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Nightly Cron   │───▶│  Batch Processor │───▶│ sentiment_results│
│  (midnight)     │    │  (no time limit) │    │   collection    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Dashboard     │◀───│   Fast Read API  │◀───│  Pre-computed   │
│   (< 100ms)     │    │   (simple lookup)│    │    Results      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 1. Nightly Batch Process (`/scripts/batch_sentiment.py`)
- Runs at midnight UTC via cron/GitHub Actions
- No timeout constraints (can take 10+ minutes)
- Processes all 800k+ chunks systematically
- Stores results in `sentiment_results` collection

### 2. Pre-computed Results Collection Schema
```javascript
{
  _id: ObjectId,
  topic: "AI Agents",
  week: "W1",
  year: 2025,
  sentiment_score: 0.65,
  episode_count: 12,
  chunk_count: 340,
  sample_size: 100,
  computed_at: ISODate,
  metadata: {
    date_range: "2025-06-01 to 2025-06-08",
    keywords_found: ["great", "amazing", "interesting"],
    confidence: 0.89
  }
}
```

### 3. Fast Read API (`/api/sentiment_analysis_v2.py`)
- Simple MongoDB lookup (no computation)
- Returns results in < 100ms
- Filters by weeks/topics from pre-computed data
- Falls back to empty data if batch hasn't run

### 4. Deployment Options

#### Option A: GitHub Actions (Recommended)
```yaml
# .github/workflows/nightly-sentiment.yml
name: Nightly Sentiment Analysis
on:
  schedule:
    - cron: '0 0 * * *'  # Midnight UTC
jobs:
  compute-sentiment:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: python scripts/batch_sentiment.py
```

#### Option B: Vercel Cron Functions
```javascript
// /api/cron/sentiment.js
export default function handler(req, res) {
  // Vercel cron endpoint
  // Triggers batch process
}
```

#### Option C: External Service (Render, Railway)
- Deploy batch processor separately
- More reliable for long-running jobs

### 5. Implementation Plan

1. **Create `sentiment_results` collection**
2. **Build batch processor script**
3. **Create fast read API**
4. **Set up nightly cron job**
5. **Update dashboard to use new API**

### 6. Benefits
- ✅ **Instant Response**: Dashboard loads in <100ms
- ✅ **No Timeouts**: Batch process has unlimited time
- ✅ **Reliable**: Pre-computed data always available
- ✅ **Scalable**: Can process millions of chunks overnight
- ✅ **Fresh Data**: Updates daily automatically
- ✅ **Fallback**: Current API still works for real-time testing

### 7. Migration Strategy
1. Deploy both APIs (current + batch)
2. Run first batch process manually
3. Switch dashboard to new API
4. Keep old API for debugging
5. Enable nightly automation

This approach transforms a 300-second timeout problem into a <100ms user experience!
