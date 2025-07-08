# CLAUDE.md for PodInsight API Repository

Copy this file to `/Users/jamesgill/PodInsights/podinsight-api/CLAUDE.md`

## Project Context

This is the FastAPI backend for PodInsightHQ, providing APIs for the Next.js dashboard.

## Asana Integration
- **Workspace GID**: `1210591545825845` (podinsighthq.com)
- **Project GID**: `1210696245097468` (PodInsightHQ Development)
- **Current Sprint**: Sprint 4 - Episode Intelligence

## Key Technical Standards

### MongoDB Integration
- **Connection**: Use Motor (async MongoDB driver)
- **Collections**:
  - `episode_intelligence` - Signal extraction results
  - `user_intelligence_prefs` - User preferences
  - `podcast_authority` - Podcast tier rankings
- **CRITICAL**: MongoDB `episode_id` = Supabase `guid` (NOT uuid!)

### API Standards
- FastAPI with Pydantic models
- JWT authentication via Supabase
- Async/await patterns throughout
- Response time target: <500ms

### Episode Intelligence Endpoints

1. **GET /api/episodes/{episode_guid}/intelligence**
   - Returns signals for single episode
   - Must include relevance_score

2. **GET /api/dashboard/intelligence/summary**
   - Top episodes by relevance score
   - Include signal counts and preview bullets

3. **GET /api/episodes/{episode_guid}/brief**
   - Detailed intelligence brief for modal
   - Include entities and timestamps

### Testing Commands
```bash
# Run tests
./venv/bin/python -m pytest tests/ -v

# Run specific test
./venv/bin/python -m pytest tests/test_intelligence.py -v

# Run with coverage
./venv/bin/python -m pytest --cov=app tests/
```

### Local Development
```bash
# Start server
./venv/bin/python -m uvicorn app.main:app --reload --port 8000

# With environment variables
source .env && ./venv/bin/python -m uvicorn app.main:app --reload
```

## Environment Variables
Required in `.env`:
- `MONGODB_URI` - MongoDB connection string
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Service role key
- `JWT_SECRET_KEY` - For auth tokens

## Code Organization
```
app/
├── api/
│   ├── endpoints/
│   │   ├── episodes.py      # Episode endpoints
│   │   ├── intelligence.py  # New intelligence endpoints
│   │   └── dashboard.py     # Dashboard specific
│   └── dependencies.py      # Shared dependencies
├── core/
│   ├── config.py           # Settings
│   └── security.py         # Auth
├── db/
│   ├── mongodb.py          # MongoDB connection
│   └── supabase.py         # Supabase client
├── models/
│   ├── intelligence.py     # Pydantic models
│   └── episode.py          # Episode models
└── services/
    ├── intelligence.py     # Business logic
    └── relevance.py        # Scoring logic
```

## Common Patterns

### MongoDB Async Query
```python
async def get_episode_intelligence(episode_id: str):
    result = await db.episode_intelligence.find_one(
        {"episode_id": episode_id}
    )
    return result
```

### Supabase Auth Check
```python
@router.get("/protected")
async def protected_route(
    current_user: dict = Depends(get_current_user)
):
    return {"user_id": current_user["id"]}
```

## Performance Guidelines
- Use MongoDB aggregation pipelines
- Implement caching for hot paths
- Batch database operations
- Use connection pooling

## Deployment Notes
- Hosted on Vercel
- Python 3.11 runtime
- Environment variables in Vercel dashboard
- GitHub Actions for CI/CD
