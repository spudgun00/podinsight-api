# Master Operations & Security Document - PodInsightHQ

**Document Version**: 1.0
**Created**: 2025-01-03
**Purpose**: Comprehensive deployment, security, environment configuration, and operational procedures

---

## 🔍 Sources Analyzed

1. DEPLOYMENT_CONFIGURATION.md
2. SECURITY_RECOMMENDATIONS.md
3. PodInsightHQ Complete Environment Variables Reference.md
4. PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md (security & operations sections)
5. AWS Network Optimization - Before:After Reference.md
6. Various sprint documentation references

---

## 🚨 Discrepancies Found

### 1. Environment Variable Organization
- **Issue**: Different documents show different env var structures
- **Some docs**: Separate staging/prod keys (OPENAI_API_KEY_STAGING)
- **Others**: Single keys with environment switching
- **Resolution**: ✅ Use environment-specific keys for safety

### 2. Security Implementation Status
- **Documentation**: References authentication as if implemented
- **Reality**: NO authentication currently exists
- **Backend token**: Exposed in Next.js API routes
- **Resolution**: ✅ Mark as P0 security issue requiring immediate fix

### 3. Cost Figures
- **Infrastructure**: $240/month → $17.52/month (verified)
- **Total platform**: Some docs say ~$15/month, others ~$75/month
- **Modal.com**: Using $5k credits, actual cost unclear
- **Resolution**: ✅ Current verified: $17.52 AWS + $60 MongoDB = ~$78/month

### 4. Deployment Configuration
- **Some docs**: Reference CI/CD pipeline
- **Reality**: Direct push to main → Vercel auto-deploy
- **Resolution**: ✅ No CI/CD currently implemented

---

## 🚨 P0 SECURITY ISSUES (CRITICAL)

### 1. Exposed Backend Access
**Current State**: Public API routes use server-side `BACKEND_API_TOKEN`
**Risk**: Anyone can indirectly access backend with elevated privileges
**Impact**: Complete data access, potential data breach

**Immediate Fix Required**:
```typescript
// VULNERABLE (Current)
export async function POST(request: NextRequest) {
  const response = await fetch(`${API_URL}/api/search`, {
    headers: {
      'Authorization': `Bearer ${process.env.BACKEND_API_TOKEN}` // EXPOSED!
    }
  });
}

// SECURE (Required)
import { auth } from "@/lib/auth";

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session) {
    return new Response("Unauthorized", { status: 401 });
  }
  // ... continue with authenticated request
}
```

### 2. No Authentication System
**Current State**: Zero authentication implemented
**Risk**: Cannot protect routes, track users, or secure data
**Impact**: Anyone can access all features and data

### 3. Database Credentials in Git History
**Status**: ✅ RESOLVED (June 26, 2025)
**Actions Taken**:
- MongoDB password rotated
- Git history cleaned with filter-repo
- Pre-commit hooks installed
- GitHub secret scanning enabled

---

## ✅ Verified Deployment Configuration

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repositories                       │
├─────────────────────────────────────────────────────────────┤
│  podinsight-dashboard │ podinsight-api │ podinsight-etl    │
└──────────┬───────────┴────────┬────────┴───────────────────┘
           │                    │
           │ Push to main       │ Push to main
           │                    │
           ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Vercel Platform                           │
├─────────────────────────────────────────────────────────────┤
│  Auto-deploy on push  │  Serverless Functions  │  Edge CDN  │
│  Preview on PR        │  London region (lhr1)  │  SSL/TLS   │
└─────────────────────────────────────────────────────────────┘
```

### Vercel Configuration

```json
// vercel.json (API)
{
  "functions": {
    "api/*.py": {
      "maxDuration": 30,
      "memory": 1024,
      "runtime": "python3.9"
    }
  },
  "rewrites": [
    { "source": "/api/diag/(.*)", "destination": "/api/diag.py" },
    { "source": "/api/(.*)", "destination": "/api/index.py" }
  ]
}

// next.config.js (Dashboard)
{
  "reactStrictMode": true,
  "images": { "domains": ["pod-insights-clips.s3.amazonaws.com"] }
}
```

### Deployment Process

1. **Development**
   ```bash
   # Local development
   npm run dev  # Next.js on :3000
   uvicorn api.topic_velocity:app --reload  # FastAPI on :8000
   ```

2. **Staging** (Preview deployments)
   - Automatic on PR creation
   - URL: `https://{branch}-podinsight-dashboard.vercel.app`

3. **Production**
   - Push to main branch
   - Automatic deployment
   - Zero-downtime deployment
   - Instant rollback available

---

## 🔐 Environment Variables Reference

### Required Environment Variables

#### API Service (podinsight-api)
```bash
# Database Connections
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/podinsight  # pragma: allowlist secret
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIs...  # Service role key

# External Services
OPENAI_API_KEY_PROD=sk-prod-...
OPENAI_API_KEY_STAGING=sk-staging-...
HUGGINGFACE_API_KEY=hf_...
MODAL_ENABLED=true

# AWS (for audio clips)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-west-2

# Application Config
BACKEND_API_TOKEN=secret-token-here  # TO BE REMOVED
PYTHON_VERSION=3.9
ENV=production  # or staging
```

#### Frontend Service (podinsight-dashboard)
```bash
# Public Variables (exposed to browser)
NEXT_PUBLIC_API_URL=https://podinsight-api.vercel.app
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...

# Server-only Variables
BACKEND_API_TOKEN=secret-token-here  # SECURITY ISSUE
```

#### ETL Scripts (podinsight-etl)
```bash
# AWS S3 Access
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_STAGE=pod-insights-stage
S3_BUCKET_RAW=pod-insights-raw

# Database Access
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIs...
```

### Environment-Specific Configuration

| Variable | Staging | Production | Purpose |
|----------|---------|------------|---------|
| API Keys | *_STAGING suffix | *_PROD suffix | Prevent quota mixing |
| Rate Limits | Higher | Lower | Testing vs protection |
| Cache TTL | Shorter | Longer | Fresh data vs performance |
| Log Level | DEBUG | ERROR | Debugging vs noise |

---

## 📊 Infrastructure & Costs

### Current Monthly Costs (Verified)

| Service | Cost | Details |
|---------|------|---------|
| **AWS Infrastructure** | $17.52 | Single-AZ, no NAT Gateway |
| **MongoDB Atlas** | $60.00 | M10 cluster (2GB RAM) |
| **Vercel** | $0.00 | Hobby tier (for now) |
| **Supabase** | $0.00 | Free tier |
| **Modal.com** | $0.00 | Using $5k credits |
| **Total** | **$77.52** | Without Modal credits: ~$240 |

### Cost Optimization Achieved

```yaml
# Before Optimization
Multi-AZ deployment: $195.84/month
NAT Gateway: $45.00/month
Total: $240.84/month

# After Optimization (Current)
Single-AZ: $0.00 (using public subnets)
No NAT Gateway: $0.00
S3 Gateway Endpoint: $0.00
Data Transfer: ~$17.52/month
Savings: 92% reduction
```

### Scaling Triggers

| Service | Current | Upgrade At | Next Tier | Cost |
|---------|---------|------------|-----------|------|
| MongoDB | M10 | 2M chunks | M20 | $140/mo |
| Vercel | Hobby | 100GB bandwidth | Pro | $20/mo |
| Supabase | Free | 500MB storage | Pro | $25/mo |
| Modal | Credits | Credit exhaustion | Usage | ~$200/mo |

---

## 🚀 Operational Procedures

### Deployment Checklist

#### Pre-deployment
- [ ] Run `npm run build` locally
- [ ] Check TypeScript errors: `npm run type-check`
- [ ] Verify env vars: `vercel env pull`
- [ ] Test critical flows locally
- [ ] Check bundle size: `npm run analyze`

#### Deployment
```bash
# Manual deployment (if needed)
vercel --prod

# Rollback if issues
vercel rollback [deployment-url]
```

#### Post-deployment
- [ ] Verify production URL
- [ ] Test search functionality
- [ ] Check audio playback
- [ ] Monitor error logs: `vercel logs`
- [ ] Check performance metrics

### Monitoring & Alerts

#### Current Monitoring
- Vercel Analytics (basic)
- MongoDB Atlas monitoring
- AWS CloudWatch (S3/Lambda)
- Manual log checking

#### Missing Monitoring (P1)
- [ ] Error tracking (Sentry)
- [ ] Uptime monitoring (UptimeRobot)
- [ ] Performance monitoring (DataDog)
- [ ] Security scanning
- [ ] User analytics

### Emergency Procedures

#### 1. Search Returning 0 Results
```bash
# Check MongoDB connection
curl https://podinsight-api.vercel.app/api/health

# Verify Modal.com
curl https://podinsighthq--podinsight-embeddings-simple-health-check.modal.run

# Check logs
vercel logs https://podinsight-api.vercel.app --follow

# Restart by redeploying
vercel --prod --force
```

#### 2. Site Down
```bash
# Check Vercel status
https://vercel.com/status

# Check MongoDB status
https://status.cloud.mongodb.com

# Immediate rollback
vercel rollback [last-working-deployment]
```

#### 3. Security Breach Response
1. **Immediate Actions**:
   - Rotate all credentials
   - Disable public access
   - Enable Vercel password protection
   - Audit access logs

2. **Within 1 hour**:
   - Change all API keys
   - Force redeploy with new credentials
   - Notify users if data exposed
   - Document incident

### Backup & Recovery

#### Current Backups
- **Code**: GitHub (automatic)
- **MongoDB**: Atlas daily backups (7-day retention)
- **S3**: Versioning enabled
- **Supabase**: Daily backups (7-day retention)

#### Recovery Procedures
- **Code**: `git checkout [commit]`
- **Database**: Atlas point-in-time recovery
- **S3**: Restore previous versions
- **Full recovery time**: <2 hours

---

## 🔒 Security Hardening Checklist

### Immediate (Week 1)
- [x] Rotate MongoDB password (DONE)
- [ ] Remove BACKEND_API_TOKEN from client
- [ ] Implement authentication on all routes
- [ ] Add rate limiting (20 req/min)
- [ ] Restrict CORS to known domains

### Short-term (Month 1)
- [ ] Implement JWT authentication
- [ ] Add API key management
- [ ] Enable CSP headers
- [ ] Set up security monitoring
- [ ] Implement input validation

### Long-term (Quarter)
- [ ] SOC2 compliance audit
- [ ] Penetration testing
- [ ] Security training
- [ ] Incident response plan
- [ ] Data encryption at rest

---

## 📋 Compliance & Policies

### Data Protection
- **PII Handling**: No user PII currently stored
- **Podcast Data**: Publicly available content only
- **User Data** (future): Will require GDPR compliance

### Security Policies
```yaml
Password Requirements:
  - Minimum 12 characters
  - Include special characters
  - Rotate every 90 days
  - No credential sharing

Access Control:
  - Principle of least privilege
  - MFA for all admin access
  - Regular access audits
  - Immediate revocation on departure

Incident Response:
  - 15-minute initial response
  - 1-hour containment target
  - 24-hour notification requirement
  - Post-mortem within 72 hours
```

---

## ❓ Needs Verification

1. **Exact Modal.com costs** after credits expire (~$200/month estimated)
2. **Vercel bandwidth usage** - when will we hit Pro tier?
3. **Disaster recovery testing** - has it been performed?
4. **Security audit status** - any third-party review?
5. **Compliance requirements** - any industry-specific needs?

---

## 🚨 CRITICAL ACTIONS REQUIRED

### P0 - Immediate (This Week)
1. **Fix Authentication**: Implement auth on all API routes
2. **Remove Backend Token**: Eliminate token exposure
3. **Add Rate Limiting**: Prevent API abuse
4. **Enable Monitoring**: Set up error tracking

### P1 - Urgent (This Month)
1. **Full Auth System**: NextAuth.js or Clerk
2. **Security Headers**: CSP, HSTS, etc.
3. **Input Validation**: Zod schemas
4. **Backup Testing**: Verify recovery works

### P2 - Important (This Quarter)
1. **SOC2 Readiness**: Begin compliance work
2. **Load Testing**: Verify scale limits
3. **Security Audit**: External review
4. **Documentation**: Runbooks for all procedures

---

**Note**: This document represents the operational and security state as of January 2025. The lack of authentication is the most critical issue requiring immediate remediation before any public launch.
