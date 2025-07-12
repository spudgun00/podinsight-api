# Live Data Fix Handover Document

## Issue Summary
The dashboard has a demo/live data toggle. Demo mode works perfectly using mock data, but live mode fails with CORS errors and 500 status codes on all API endpoints.

## Current Status
- **CORS fix already committed** (commit 71e96f3) - Headers are properly configured in vercel.json
- **Environment variables are configured** in Vercel with "All Environments" setting
- **Root cause identified**: Deployment needs refresh to load environment variables

## Failed Endpoints
1. `/api/prewarm` - CORS preflight error (actually 500 error masked as CORS)
2. `/api/intelligence/dashboard` - 500 error
3. `/api/signals` - 500 error

## Key Findings

### 1. CORS Errors Are Symptoms, Not the Cause
- When an endpoint returns 500, browser shows CORS error
- CORS headers are correctly configured in vercel.json:
```json
{
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Credentials", "value": "true" },
        { "key": "Access-Control-Allow-Origin", "value": "*" },
        { "key": "Access-Control-Allow-Methods", "value": "GET,OPTIONS,PATCH,DELETE,POST,PUT" },
        { "key": "Access-Control-Allow-Headers", "value": "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization" }
      ]
    }
  ]
}
```

### 2. All Endpoints Depend on External Services
- MongoDB (for data storage)
- Supabase (for metadata)
- Modal (for embeddings)
- If any service connection fails → 500 error → appears as CORS error

### 3. Environment Variable Configuration
**Vercel has all required variables configured:**
- SUPABASE_URL ✓
- SUPABASE_KEY ✓ (Note: Code expects this, not SUPABASE_SERVICE_ROLE_KEY)
- MONGODB_URI ✓
- OPENAI_API_KEY ✓
- HUGGINGFACE_API_KEY ✓
- MODAL_EMBEDDING_URL ✓

**Important discovery:**
- Local .env has `SUPABASE_SERVICE_ROLE_KEY`
- Code expects `SUPABASE_KEY` with fallback to `SUPABASE_ANON_KEY`
- Vercel already has `SUPABASE_KEY` configured correctly

### 4. User Mentioned Disconnecting GitHub
User mentioned: "i did disconnect the github folder for a bit and it may have done something"
This could have disrupted the deployment pipeline.

## Simple Fix (Path of Least Resistance)

### Step 1: Trigger a Redeployment
1. Go to Vercel Dashboard
2. Navigate to the project
3. Go to "Deployments" tab
4. Click "Redeploy" on the latest deployment
5. Select "Use existing Build Cache" → NO (force fresh build)
6. Deploy

### Step 2: Verify Environment Variables Loaded
After deployment:
1. Check deployment logs for "Environment variables loaded" message
2. Test the health endpoint: https://podinsight-api.vercel.app/api/health
3. Should see all env vars as `true` in the response

### Step 3: Test Live Data
1. Go to dashboard
2. Toggle to "Live Data"
3. Endpoints should now return 200 status with data

## Alternative Solutions (If Redeployment Doesn't Work)

### Option A: Manual Environment Variable Check
```bash
# In Vercel CLI
vercel env pull
vercel env ls production
```

### Option B: Force New Deployment
```bash
# Make a trivial change
echo "# Deployment trigger" >> README.md
git add . && git commit -m "fix: Trigger deployment for env vars"
git push
```

### Option C: Check Service Connections
Test each service individually:
1. MongoDB: Check connection string in Atlas dashboard
2. Supabase: Verify API keys haven't been rotated
3. Modal: Check if credits exhausted or service down

## Code References
- CORS configuration: /vercel.json:12-22
- Supabase key usage: /lib/database.py & /api/topic_velocity.py
- Environment check endpoint: /api/intelligence.py:29-61

## Next Steps
1. Trigger redeployment as described above
2. If issues persist, check individual service connections
3. Monitor deployment logs for any error messages
4. Once working, consider adding monitoring for these endpoints

## Additional Notes
- Authentication is temporarily disabled on intelligence endpoints (planned for Sprint 4)
- "All Environments" setting in Vercel means variables apply to production (correct)
- CORS allowing all origins (`*`) is intentional for now but should be restricted later

## Contact
If issues persist after redeployment, check:
1. Vercel deployment logs
2. Vercel function logs for specific error messages
3. Service dashboards (MongoDB Atlas, Supabase, Modal) for any issues
