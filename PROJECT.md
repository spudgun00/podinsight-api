# PodInsightHQ API

## Purpose
Serve topic velocity data for the dashboard via a single endpoint.

## Key Decisions
- Framework: FastAPI on Vercel serverless
- Single endpoint: GET /api/topic-velocity
- Response format: JSON optimized for Recharts
- Performance target: <500ms response time
- Region: London (lhr1)

## Success Criteria
- Returns data for 4 default topics
- 12 weeks of historical data
- CORS enabled for frontend access