# PodInsightHQ API - Deployment Checklist

**Deployment Date:** _________________  
**Deployed By:** _________________  
**Deployment Type:** Staging / Production  
**Target URL:** https://podinsight-api.vercel.app  

## Pre-Deployment Checklist

### GitHub Repository
- [ ] Latest changes committed to main branch
- [ ] All tests passing locally
- [ ] No merge conflicts
- [ ] Repository URL: https://github.com/spudgun00/podinsight-api

### Local Testing
- [ ] API starts without errors on port 8000
- [ ] `/api/topic-velocity` returns correct data format
- [ ] Average response time < 500ms
- [ ] All 5 topics working (including "Crypto/Web3" without spaces)

### Environment Variables Ready
- [ ] SUPABASE_URL copied from Supabase dashboard
- [ ] SUPABASE_KEY copied from Supabase dashboard  
- [ ] Values stored securely (not in any files)

## Deployment Steps

### Step 1: Vercel Setup
- [ ] Logged into Vercel account
- [ ] "Add New Project" clicked
- [ ] GitHub account connected/authorized
- [ ] Repository `podinsight-api` found and selected

### Step 2: Configuration
- [ ] Framework preset set to "Other"
- [ ] Root directory left as default (`.`)
- [ ] Build command left empty
- [ ] Output directory left empty
- [ ] Install command confirmed as `pip install -r requirements.txt`

### Step 3: Environment Variables
- [ ] SUPABASE_URL added correctly
- [ ] SUPABASE_KEY added correctly
- [ ] PYTHON_VERSION set to `3.12`
- [ ] All values double-checked for accuracy

### Step 4: Advanced Settings
- [ ] Region set to `lhr1` (London)
- [ ] Function configuration verified in vercel.json
- [ ] Memory: 512MB confirmed
- [ ] Max duration: 10 seconds confirmed

### Step 5: Deploy
- [ ] All settings reviewed one final time
- [ ] "Deploy" button clicked
- [ ] Build logs monitored for errors
- [ ] Deployment completed successfully
- [ ] Deployment URL noted: _______________________

## Post-Deployment Verification

### API Health Checks
- [ ] Production URL accessible
- [ ] Health check endpoint responding:
  ```
  curl https://podinsight-api.vercel.app/api/topic-velocity
  ```
- [ ] Response includes correct status and version

### Functionality Tests
- [ ] Default topics endpoint working (4 topics, 13 weeks)
- [ ] Custom weeks parameter working (`?weeks=4`)
- [ ] Custom topics parameter working (`?topics=AI+Agents,DePIN`)
- [ ] Error handling working (invalid parameters return proper errors)

### Performance Verification
- [ ] Response time measured and < 500ms
- [ ] No timeout errors
- [ ] No 500 Internal Server errors

### CORS Verification
- [ ] Frontend can access API (if frontend deployed)
- [ ] No CORS errors in browser console
- [ ] OPTIONS requests handled correctly

## Monitoring Setup

### Vercel Dashboard
- [ ] Function logs accessible
- [ ] No error spikes in metrics
- [ ] Cold start frequency acceptable
- [ ] Memory usage under limit

### Alerts (Optional)
- [ ] Error rate monitoring configured
- [ ] Response time alerts set up
- [ ] Notification channel configured

## Documentation Updates

### For Frontend Team
- [ ] API URL shared: https://podinsight-api.vercel.app/api/topic-velocity
- [ ] Topic names documented exactly as in database:
  - "AI Agents"
  - "Capital Efficiency"  
  - "DePIN"
  - "B2B SaaS"
  - "Crypto/Web3" (no spaces around /)
- [ ] Example requests provided
- [ ] Expected response format confirmed

### Internal Documentation
- [ ] Deployment date recorded
- [ ] Any issues encountered documented
- [ ] Performance benchmarks recorded
- [ ] Lessons learned noted

## Rollback Plan

### If Issues Detected
- [ ] Rollback procedure understood
- [ ] Previous deployment ID noted: _______________________
- [ ] Team notified of rollback plan
- [ ] Rollback tested (if needed)

## Sign-Off

### Deployment Successful
- [ ] All checklist items completed
- [ ] API functioning correctly
- [ ] Performance meets requirements
- [ ] No critical issues found

**Deployment Status:** ⬜ Success | ⬜ Success with Issues | ⬜ Failed

**Notes/Issues Encountered:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

**Next Steps:**
_________________________________________________________________
_________________________________________________________________

---

**Completed By:** _________________ **Date:** _________________ **Time:** _________________