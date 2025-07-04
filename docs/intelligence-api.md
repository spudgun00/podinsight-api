# Episode Intelligence API Documentation

## Overview
The Episode Intelligence API provides AI-generated briefs and insights from podcast episodes. All endpoints require authentication using JWT tokens from Supabase Auth.

## Authentication
All intelligence endpoints require a valid JWT token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## Endpoints

### 1. GET /api/intelligence/dashboard
Returns top 6-8 episodes by relevance score for the authenticated user.

**Response:**
```json
{
  "episodes": [
    {
      "episode_id": "string",
      "title": "string",
      "podcast_name": "string",
      "published_at": "2025-07-04T12:00:00Z",
      "duration_seconds": 3600,
      "relevance_score": 0.85,
      "signals": [
        {
          "type": "investable",
          "content": "Series A funding discussion",
          "confidence": 0.9
        }
      ],
      "summary": "Episode summary...",
      "key_insights": ["insight1", "insight2"],
      "audio_url": "https://..."
    }
  ],
  "total_episodes": 8,
  "generated_at": "2025-07-04T12:00:00Z"
}
```

### 2. GET /api/intelligence/brief/{episode_id}
Returns full intelligence brief for a specific episode.

**Parameters:**
- `episode_id`: MongoDB ObjectId or GUID

**Response:**
```json
{
  "episode_id": "string",
  "title": "string",
  "podcast_name": "string",
  "published_at": "2025-07-04T12:00:00Z",
  "duration_seconds": 3600,
  "relevance_score": 0.85,
  "signals": [...],
  "summary": "Detailed episode summary...",
  "key_insights": [...],
  "audio_url": "https://..."
}
```

### 3. POST /api/intelligence/share
Share episode intelligence via email or Slack.

**Request Body:**
```json
{
  "episode_id": "string",
  "method": "email", // or "slack"
  "recipient": "user@example.com",
  "include_summary": true,
  "personal_note": "Check this out!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Episode intelligence shared via email to user@example.com",
  "shared_at": "2025-07-04T12:00:00Z"
}
```

### 4. PUT /api/intelligence/preferences
Update user preferences for personalized intelligence.

**Request Body:**
```json
{
  "portfolio_companies": ["Company A", "Company B"],
  "interest_topics": ["AI", "SaaS", "FinTech"],
  "notification_frequency": "weekly",
  "email_notifications": true,
  "slack_notifications": false
}
```

**Response:**
```json
{
  "success": true,
  "preferences": {...},
  "updated_at": "2025-07-04T12:00:00Z"
}
```

### 5. GET /api/intelligence/health
Health check endpoint (no authentication required).

**Response:**
```json
{
  "status": "healthy",
  "service": "intelligence-api",
  "timestamp": "2025-07-04T12:00:00Z",
  "mongodb": "connected"
}
```

## Signal Types
- **investable**: Funding announcements, investment opportunities
- **competitive**: Acquisitions, exits, competitive intelligence
- **portfolio**: Mentions of portfolio companies
- **sound_bite**: Quotable insights and predictions

## Error Responses
- **401 Unauthorized**: Missing or invalid authentication token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Episode not found
- **500 Internal Server Error**: Server error

## Testing
Use the provided test script to verify endpoints:
```bash
python3 test_intelligence_endpoints.py
```

## Implementation Notes
- All endpoints use MongoDB for data storage
- Relevance scoring is personalized based on user preferences
- Response times should be < 200ms as per requirements
- Authentication uses Supabase JWT tokens
- Episode IDs can be either MongoDB ObjectIds or GUIDs