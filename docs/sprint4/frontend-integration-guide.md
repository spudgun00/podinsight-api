# Episode Intelligence Frontend Integration Guide

## Quick Start

The Episode Intelligence API is fully functional and ready for integration. Here's everything you need to build the dashboard feature.

## 🚀 API Endpoints

Base URL: `https://podinsight-api.vercel.app`

### 1. Dashboard Feed
```http
GET /api/intelligence/dashboard?limit=8
```

Returns top episodes sorted by relevance score.

**Example Response:**
```json
{
  "episodes": [
    {
      "episode_id": "02fc268c-61dc-4074-b7ec-882615bc6d85",
      "title": "White House BTS, Google buys Wiz, Treasury vs Fed",
      "podcast_name": "All-In Podcast",
      "published_at": "2024-07-26T16:55:00Z",
      "duration_seconds": 5280,
      "relevance_score": 0.85,
      "signals": [
        {
          "type": "investable",
          "content": "Google acquiring Wiz for $23 billion",
          "confidence": 0.9,
          "timestamp": "32:25"
        },
        {
          "type": "competitive",
          "content": "Sequoia passed on the Series A",
          "confidence": 0.8,
          "timestamp": "45:10"
        }
      ],
      "summary": "Episode discusses major M&A activity...",
      "key_insights": [
        "Google's largest acquisition ever",
        "Market consolidation in cybersecurity",
        "VC sentiment shifting on valuations"
      ],
      "audio_url": "https://..."
    }
  ],
  "total_episodes": 8,
  "generated_at": "2025-01-09T07:45:00Z"
}
```

### 2. Episode Brief
```http
GET /api/intelligence/brief/{episode_id}
```

Get detailed intelligence for a specific episode.

**Example Response:**
```json
{
  "episode_id": "02fc268c-61dc-4074-b7ec-882615bc6d85",
  "title": "White House BTS, Google buys Wiz, Treasury vs Fed",
  "podcast_name": "All-In Podcast",
  "published_at": "2024-07-26T16:55:00Z",
  "duration_seconds": 5280,
  "relevance_score": 0.85,
  "signals": [...], // All signals for this episode
  "summary": "Detailed episode summary...",
  "key_insights": [...],
  "audio_url": "https://..."
}
```

### 3. Update Preferences
```http
PUT /api/intelligence/preferences
```

**Request Body:**
```json
{
  "portfolio_companies": ["Stripe", "Figma", "Notion"],
  "interest_topics": ["AI", "fintech", "B2B SaaS"],
  "notification_frequency": "daily",
  "email_notifications": true,
  "slack_notifications": false
}
```

### 4. Share Intelligence
```http
POST /api/intelligence/share
```

**Request Body:**
```json
{
  "episode_id": "02fc268c-61dc-4074-b7ec-882615bc6d85",
  "method": "email",
  "recipient": "partner@vcfirm.com",
  "include_summary": true,
  "personal_note": "Check out the Wiz acquisition discussion"
}
```

## 📊 Data Overview

- **Total Episodes**: 50
- **Episodes with Signals**: 49 (98%)
- **Average Signals per Episode**: 12
- **Signal Types**:
  - `investable`: Investment opportunities
  - `competitive`: Market intelligence
  - `portfolio`: Portfolio company mentions
  - `sound_bite`: Key quotes and insights

## 🎨 UI/UX Recommendations

### Dashboard View
1. **Signal Pills**: Color-code by type (green=investable, blue=competitive, purple=portfolio, gray=soundbite)
2. **Relevance Score**: Show as a visual indicator (progress bar or stars)
3. **Time to Read**: Calculate from signal count (assume 5 seconds per signal)
4. **Quick Actions**: Listen, Share, Save for Later

### Episode Detail View
1. **Signal Timeline**: Show signals with timestamps for easy navigation
2. **Audio Player**: Integrate with timestamp jumping
3. **Share Options**: Pre-fill with episode title and key signals
4. **Related Episodes**: Show other episodes with similar signals

## 🔧 Implementation Notes

1. **No Authentication**: Currently disabled for MVP
2. **CORS**: Enabled for all origins
3. **Rate Limiting**: None currently
4. **Error Handling**: All endpoints return standard HTTP status codes
5. **Pagination**: Not needed for MVP (only 49 episodes)

## 📱 Mobile Considerations

- All endpoints return lightweight JSON
- Audio URLs can be streamed
- Signals are bite-sized for mobile reading
- Consider offline caching for episode briefs

## 🚦 Testing the API

Quick test to verify the API is working:

```bash
# Get dashboard feed
curl https://podinsight-api.vercel.app/api/intelligence/dashboard?limit=5

# Get specific episode
curl https://podinsight-api.vercel.app/api/intelligence/brief/02fc268c-61dc-4074-b7ec-882615bc6d85
```

## 📞 Support

- API Health Check: `GET /api/intelligence/health`
- Debug Endpoints: Available in development
- Documentation: See `/docs/master-api-reference.md`

---

**Ready to Build!** The API is stable and all endpoints are functioning. Focus on creating a great user experience that surfaces the right signals at the right time for busy VCs.