# Story 5B Deployment Checklist

## Pre-Deployment Steps

### 1. Environment Variables
Add the following to Vercel environment variables:
- [ ] `SUPABASE_JWT_SECRET` - Get from Supabase Dashboard > Settings > API > JWT Secret

### 2. Code Review
- [x] Authentication middleware implemented (`api/middleware/auth.py`)
- [x] All 4 intelligence endpoints implemented
- [x] Endpoints integrated into main app (`api/index.py`)
- [x] All endpoints require authentication
- [x] Proper error handling with status codes

### 3. Testing
- [ ] Run local tests with `python3 test_intelligence_endpoints.py`
- [ ] Verify all endpoints return 401 without auth
- [ ] Test with valid JWT token
- [ ] Measure response times (must be < 200ms)

## Deployment Steps

1. **Add JWT Secret to Vercel:**
   ```bash
   vercel env add SUPABASE_JWT_SECRET production
   ```

2. **Deploy to Vercel:**
   ```bash
   vercel --prod
   ```

3. **Verify Deployment:**
   - Check health endpoint: `GET /api/intelligence/health`
   - Test auth on all endpoints
   - Monitor response times

## Post-Deployment

1. **Update Asana:**
   - [ ] Mark "Build intelligence endpoints" as complete
   - [ ] Mark "Extend FastAPI app" as complete  
   - [ ] Mark "Implement authentication" as complete

2. **Document in Asana:**
   - Response times for each endpoint
   - Any issues encountered
   - Next steps for optimization

## Critical Notes

1. **Authentication is P0** - No endpoints should work without valid JWT
2. **MongoDB mapping** - episode_id in MongoDB = GUID from Supabase
3. **No caching for MVP** - Monitor response times for future optimization
4. **Error handling** - All errors should return appropriate HTTP status codes

## Endpoint Summary

| Method | Endpoint | Auth Required | Purpose |
|--------|----------|---------------|---------|
| GET | /api/intelligence/dashboard | Yes | Top 8 episodes by relevance |
| GET | /api/intelligence/brief/{id} | Yes | Full episode brief |
| POST | /api/intelligence/share | Yes | Share via email/Slack |
| PUT | /api/intelligence/preferences | Yes | Update user preferences |
| GET | /api/intelligence/health | No | Health check |

## Known Limitations (MVP)

1. Share functionality simulated (logs only, no actual email/Slack)
2. Relevance scoring is basic (not using full Story 2 implementation)
3. Mock signals generated if none exist in database
4. No caching implemented yet

## Success Criteria

- [ ] All endpoints return data in < 200ms
- [ ] Authentication works on all protected endpoints
- [ ] No public endpoints except health check
- [ ] Error responses include appropriate status codes
- [ ] All 3 Asana subtasks marked complete