# PodInsightHQ API - Vercel Deployment Instructions

**Last Updated:** June 15, 2025
**Repository:** https://github.com/spudgun00/podinsight-api
**Target Platform:** Vercel
**Estimated Time:** 15-20 minutes

## Prerequisites

Before starting deployment:
- [ ] Vercel account created (https://vercel.com/signup)
- [ ] GitHub repository synced with latest changes
- [ ] Supabase credentials available
- [ ] Local API tested and working

## Step 1: Connect GitHub Repository to Vercel

1. **Log in to Vercel Dashboard**
   - Navigate to https://vercel.com/dashboard
   - Click "Add New..." → "Project"

2. **Import Git Repository**
   - Click "Import Git Repository"
   - If not connected, authorize Vercel to access your GitHub account
   - Search for `podinsight-api`
   - Click "Import" next to the repository

## Step 2: Configure Project Settings

### Framework Preset
- **Framework Preset:** Other (not Next.js)
- **Root Directory:** `.` (leave as default)
- **Build Command:** Leave empty (serverless functions don't need build)
- **Output Directory:** Leave empty
- **Install Command:** `pip install -r requirements.txt`

### Python Runtime Configuration
Vercel automatically detects Python from the `api/` directory structure.

## Step 3: Environment Variables

**CRITICAL:** Add all environment variables before deploying.

Click "Environment Variables" and add the following:

### Required Variables

| Variable Name | Description | Example Value |
|---------------|-------------|---------------|
| `SUPABASE_URL` | Your Supabase project URL | `https://ydbtuijwsvwwcxkgogtb.supabase.co` |
| `SUPABASE_KEY` | Supabase anon/public key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `PYTHON_VERSION` | Python runtime version | `3.12` |

### Optional Variables (if needed)

| Variable Name | Description | Example Value |
|---------------|-------------|---------------|
| `TZ` | Timezone for logging | `UTC` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

**Where to find Supabase credentials:**
1. Log in to Supabase Dashboard
2. Select your project (podhq-staging)
3. Go to Settings → API
4. Copy "URL" and "anon public" key

## Step 4: Advanced Configuration

### Function Configuration
Click "Functions" tab and configure:

1. **Region Configuration**
   - Region: `lhr1` (London)
   - This reduces latency for UK/EU users

2. **Memory & Duration**
   - Already configured in `vercel.json`:
     ```json
     {
       "functions": {
         "api/topic_velocity.py": {
           "memory": 512,
           "maxDuration": 10
         }
       }
     }
     ```

3. **Environment**
   - Node.js Version: 18.x (default)
   - Python Version: 3.12 (auto-detected)

## Step 5: Deploy

1. **Review Configuration**
   - Double-check all environment variables
   - Verify region is set to `lhr1`
   - Confirm Python version is 3.12

2. **Click "Deploy"**
   - Vercel will clone your repository
   - Install dependencies
   - Deploy serverless functions
   - Process typically takes 1-2 minutes

3. **Monitor Deployment**
   - Watch the build logs for any errors
   - Common issues:
     - Missing environment variables
     - Dependency installation failures
     - Import errors in Python code

## Step 6: Verify Deployment

Once deployed, you'll receive a URL like:
- `https://podinsight-api.vercel.app`
- or `https://podinsight-api-[unique-id].vercel.app`

### Test Endpoints

1. **Health Check**
   ```bash
   curl https://podinsight-api.vercel.app/api/topic-velocity
   ```

2. **Main Endpoint**
   ```bash
   curl "https://podinsight-api.vercel.app/api/topic-velocity?weeks=4"
   ```

## Deployment URL Pattern

Your API will be available at:
- **Production:** `https://podinsight-api.vercel.app/api/topic-velocity`
- **Preview:** `https://podinsight-api-git-[branch]-[username].vercel.app/api/topic-velocity`

### Finding Your URL
1. Go to Vercel Dashboard
2. Click on your project
3. The URL is shown at the top
4. All endpoints are under `/api/` path

## Troubleshooting Common Issues

### Issue: 500 Internal Server Error
**Cause:** Missing environment variables
**Solution:**
1. Check Vercel Functions logs
2. Verify all env vars are set correctly
3. Redeploy after adding missing variables

### Issue: 404 Not Found
**Cause:** Incorrect URL path
**Solution:**
- Ensure you're using `/api/topic-velocity` (not just `/topic-velocity`)
- Check that file is named `topic_velocity.py` in `api/` folder

### Issue: CORS Errors
**Cause:** Frontend domain not allowed
**Solution:**
- CORS is set to allow all origins (`*`)
- If still failing, check browser console for specific error

### Issue: Timeout Errors
**Cause:** Query taking too long
**Solution:**
1. Check Supabase query performance
2. Verify indexes exist on database
3. Consider increasing function timeout

### Issue: Import Error
**Cause:** Missing dependencies
**Solution:**
1. Verify all packages in requirements.txt
2. Check for typos in import statements
3. Ensure packages are compatible with Python 3.12

## Viewing Function Logs

### Real-time Logs
1. Go to Vercel Dashboard
2. Click on your project
3. Navigate to "Functions" tab
4. Click on `topic_velocity`
5. View real-time logs and metrics

### Log Types
- **Build Logs:** Show deployment process
- **Function Logs:** Show runtime errors and print statements
- **Access Logs:** Show all HTTP requests

### Debugging with Logs
- Add `print()` statements in your code
- They appear in Function Logs
- Use for debugging data issues

## Rollback Procedure

If deployment fails or introduces bugs:

### Option 1: Instant Rollback (Recommended)
1. Go to Vercel Dashboard
2. Click "Deployments" tab
3. Find the last working deployment
4. Click "..." menu → "Promote to Production"
5. Previous version is instantly restored

### Option 2: Git Revert
1. Revert the problematic commit:
   ```bash
   git revert HEAD
   git push origin main
   ```
2. Vercel auto-deploys the revert
3. Fix issues in a new branch

### Option 3: Disable Function
1. Go to project settings
2. Add environment variable: `DISABLE_API=true`
3. Modify code to check this variable
4. Returns maintenance message

## Post-Deployment Monitoring

### Metrics to Watch
1. **Response Time:** Should stay under 500ms
2. **Error Rate:** Should be near 0%
3. **Invocations:** Track API usage
4. **Cold Starts:** Monitor frequency

### Setting Up Alerts
1. Go to Project Settings → Integrations
2. Add monitoring service (e.g., Datadog, Sentry)
3. Configure alerts for:
   - Error rate > 1%
   - Response time > 500ms
   - Function crashes

## Security Considerations

### Environment Variables
- Never commit `.env` files
- Use Vercel's environment variable UI
- Rotate Supabase keys periodically

### API Protection
- Consider adding API keys for production
- Implement rate limiting if needed
- Monitor for unusual traffic patterns

## Next Steps

After successful deployment:
1. Share API URL with frontend team
2. Document exact topic names for frontend
3. Set up monitoring alerts
4. Plan for scaling if needed

## Support Resources

- **Vercel Documentation:** https://vercel.com/docs
- **Vercel Support:** https://vercel.com/support
- **Python on Vercel:** https://vercel.com/docs/functions/runtimes/python
- **Project Repository:** https://github.com/spudgun00/podinsight-api

---

**Note:** This deployment creates a staging environment. For production deployment with custom domain, additional configuration may be required.
