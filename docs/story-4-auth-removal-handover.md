# Story 4 - Auth Removal Handover

## Current Situation
Story 4 (Dashboard Integration) is BLOCKED because Story 5B endpoints require authentication but no auth system exists.

## Decision Made
Remove auth requirements from Story 5B endpoints to unblock Story 4 (5 minute fix).

## Tasks for Next Session

### 1. Remove Auth from 4 Endpoints in `api/intelligence.py`

**Line 161**: `get_intelligence_dashboard`
```python
# Remove: user = Depends(require_auth)
# Remove: user_id = user["user_id"] 
# Use: user_id = "demo-user"
```

**Line 253**: `get_intelligence_brief`
```python
# Remove: user = Depends(require_auth)
# Remove: user_id = user["user_id"]
# Use: user_id = "demo-user"
```

**Line 339**: `share_intelligence`
```python
# Remove: user = Depends(require_auth)
# Remove: user_id = user["user_id"]
# Use: user_id = "demo-user"
```

**Line 414**: `update_preferences`
```python
# Remove: user = Depends(require_auth)
# Remove: user_id = user["user_id"]
# Use: user_id = "demo-user"
```

### 2. Add TODO Comments
Add to each modified endpoint:
```python
# TODO: Re-add authentication when auth system is implemented
```

### 3. Test Endpoints
```bash
curl https://podinsight-api.vercel.app/api/intelligence/dashboard
# Should return 200 with episode data (not 403)
```

### 4. Commit & Deploy
```bash
git add api/intelligence.py
git commit -m "fix: Temporarily remove auth from Episode Intelligence endpoints

- Remove auth dependency from all 4 intelligence endpoints
- Use demo-user as placeholder user_id
- Unblocks Story 4 dashboard integration
- Auth will be re-added when auth system is implemented

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

### 5. Update Dashboard Team
Notify that endpoints are now accessible without auth.

## Files to Review
- `api/intelligence.py` - All 4 endpoints need auth removal
- `api/middleware/auth.py` - Keep this for future use

## Context from This Session
- Discovered Story 4/5B confusion
- Created then deleted duplicate endpoints
- Found Story 5B endpoints require auth
- Decided to remove auth temporarily
- All other API endpoints are public anyway

## Success Criteria
- All 4 intelligence endpoints return 200 (not 403)
- Dashboard can fetch data without auth tokens
- Story 4 can proceed with integration

---
**Priority**: HIGH - This unblocks Story 4
**Estimated Time**: 15 minutes including testing