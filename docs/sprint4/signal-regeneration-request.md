# Episode Intelligence Signal Regeneration Request

## Document Date: 2025-07-09
## Priority: High
## Requested By: Episode Intelligence API Team

---

## 🎯 Executive Summary

We need to regenerate AI signals for 2 specific episodes that currently have empty signal arrays in the `episode_intelligence` collection. Additionally, we need documentation on how to run the signal generation pipeline on-demand for future maintenance.

---

## 📋 Current Situation

### Database Status
- **Total episodes with intelligence**: 50
- **Episodes with signals**: 48 (96% success rate)
- **Episodes with EMPTY signals**: 2 (4%)
- **Total signals across all episodes**: 591

### Episodes Requiring Signal Regeneration

| Episode ID | Current Status | Required Action |
|------------|----------------|-----------------|
| `1216c2e7-42b8-42ca-92d7-bad784f80af2` | All signal arrays empty | Regenerate signals |
| `46dc5446-2e3b-46d6-b4af-24e7c0e8beff` | All signal arrays empty | Regenerate signals |

### What These Episodes Look Like in MongoDB

```json
{
  "episode_id": "1216c2e7-42b8-42ca-92d7-bad784f80af2",
  "signals": {
    "investable": [],
    "competitive": [],
    "portfolio": [],
    "soundbites": []
  },
  // ... other fields exist but signals are empty
}
```

---

## 🔧 Technical Context

### Expected Signal Structure
Based on the 48 successful episodes, signals should contain:

```json
{
  "signals": {
    "investable": [
      {
        "type": "investable",
        "content": "Company X raising $10M Series A",
        "chunk_id": "chunk_reference_id",
        "timestamp": {
          "start": 1949.825,
          "end": 1957.393
        },
        "confidence": 0.8,
        "entities": ["Company X"],
        "metadata": {
          "source": "gpt-4o-mini"
        }
      }
    ],
    "competitive": [...],
    "portfolio": [...],
    "soundbites": [...]
  }
}
```

### Signal Distribution in Successful Episodes
- Average signals per episode: ~12
- Top performing episode: 79 signals
- Distribution:
  - Investable: 101 total across 48 episodes
  - Competitive: 102 total
  - Portfolio: 56 total
  - Soundbites: 332 total

---

## 📝 Requirements

### 1. Immediate Need: Regenerate Signals for 2 Episodes

Please run the signal extraction pipeline for these specific episode IDs:
- `1216c2e7-42b8-42ca-92d7-bad784f80af2`
- `46dc5446-2e3b-46d6-b4af-24e7c0e8beff`

### 2. Documentation Need: Pipeline Operation Guide

We need a documented process for running the signal generation pipeline on-demand. This guide should include:

#### A. Prerequisites
- Required environment variables
- API keys needed (OpenAI, etc.)
- Database access requirements
- Any dependency installations

#### B. Step-by-Step Instructions
1. How to run for a single episode by ID
2. How to run for multiple episodes (batch)
3. How to run for episodes with empty signals only
4. How to run for a date range of episodes

#### C. Monitoring & Validation
- How to check if signal generation succeeded
- Expected log outputs
- How to validate signal quality
- Error handling and retry logic

#### D. Common Issues & Troubleshooting
- What to do if API rate limits are hit
- How to handle transcript/audio fetch failures
- Debugging empty signal generation
- Rollback procedures if needed

---

## 🚀 Suggested Pipeline Guide Template

```markdown
# Episode Intelligence Signal Generation Pipeline

## Quick Start
```bash
# Single episode
python run_signal_extraction.py --episode-id "1216c2e7-42b8-42ca-92d7-bad784f80af2"

# Multiple episodes
python run_signal_extraction.py --episode-ids "id1,id2,id3"

# All empty signal episodes
python run_signal_extraction.py --empty-signals-only

# Date range
python run_signal_extraction.py --start-date "2024-01-01" --end-date "2024-01-31"
```

## Environment Setup
1. Copy `.env.example` to `.env`
2. Set required variables:
   - `OPENAI_API_KEY=sk-...`
   - `MONGODB_URI=mongodb+srv://...`
   - `AI_MODEL=gpt-4o-mini` (or preferred model)

## Pipeline Stages
1. **Fetch Episode**: Get metadata and transcript
2. **Chunk Processing**: Split transcript into analyzable chunks
3. **AI Extraction**: Run each chunk through AI model
4. **Signal Categorization**: Sort into investable/competitive/portfolio/soundbites
5. **Validation**: Ensure minimum signal quality
6. **Storage**: Update episode_intelligence collection

## Monitoring
- Logs location: `./logs/signal_extraction_YYYY-MM-DD.log`
- Success metric: At least 1 signal extracted
- Quality check: Signals have content, confidence, and proper categorization
```

---

## 📊 Success Criteria

1. Both episodes have populated signal arrays after regeneration
2. Signal count is comparable to similar episodes (expect 5-20 signals per episode)
3. All signal types have proper structure (content, timestamp, confidence, etc.)
4. Pipeline documentation allows API team to self-serve future regenerations

---

## 🤝 Collaboration Notes

### For ETL Team
- These 2 episodes already exist in `episode_metadata` collection
- They have transcripts (we confirmed via the API)
- The issue appears to be with the AI extraction step, not data availability

### For API Team
- No code changes needed in the API
- The `get_episode_signals` function is working correctly
- Once signals are regenerated, the dashboard will automatically show them

---

## 📞 Contact

If you need additional context or access to debug endpoints:
- API health check: `https://podinsight-api.vercel.app/api/intelligence/health`
- Debug specific episode: `https://podinsight-api.vercel.app/api/intelligence/debug-signal-structure/{episode_id}`
- Audit all episodes: `https://podinsight-api.vercel.app/api/intelligence/audit-empty-signals`

---

**Document Created**: 2025-07-09
**API Repository**: https://github.com/spudgun00/podinsight-api
**Related Story**: Sprint 4, Story 2 - AI Signal Extraction