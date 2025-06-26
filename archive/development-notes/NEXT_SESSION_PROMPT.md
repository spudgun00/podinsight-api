# Claude Code Session Prompt: Sprint 1 Authentication Phase

## 🎯 **Project Context (2-minute read)**

**PodInsightHQ** = AI-powered search and insights platform for 1,171 podcast episodes from startup/VC shows.

### **Current Status: Sprint 1 - Phase 2 (Authentication)**
- ✅ **MongoDB Search**: Working perfectly with real transcript excerpts
- ✅ **API Deployed**: https://podinsight-api.vercel.app/api/search
- 🔄 **Next Phase**: User authentication system for saved searches

### **Key Architecture**
```
MongoDB Atlas ($5k credit)     Supabase (existing)      Vercel
├── Full transcripts        ←→ ├── Episodes metadata  → ├── FastAPI
├── Search indexes             ├── Auth system          └── React dashboard
└── Real excerpts              └── User data
```

### **Critical Technical Context**
- **Database**: Supabase PostgreSQL with existing connection pool
- **API**: FastAPI with existing patterns in `api/topic_velocity.py`
- **Auth Choice**: Supabase Auth (already configured)
- **Frontend**: React dashboard at `/Users/jamesgill/PodInsights/podinsight-dashboard`

## 🚀 **Your Mission: Implement Authentication**

**Goal**: Enable alpha users (5 people) to create accounts and save searches.

**Files to Focus On**:
- `@api/topic_velocity.py` - Main API file with existing patterns
- `@sprint1-playbook-updated.md` - Complete implementation guide (lines 499-590)
- `@api/database.py` - Connection pool (already working)

**Success Criteria**:
- [ ] Users can create accounts via Supabase Auth
- [ ] JWT token validation working
- [ ] Saved searches persist in database
- [ ] Frontend auth UI integrated

## 📋 **Next Steps**

1. **Read the detailed guide**: `@sprint1-playbook-updated.md` lines 499-590 have step-by-step prompts
2. **Start with API**: Phase 2.1 - Supabase Auth Setup (backend first)
3. **Then Frontend**: Phase 2.2 - Auth UI using existing v0 components
4. **Follow patterns**: Use same code style as existing `topic_velocity.py`

## ⚠️ **Critical Success Factors**

- **Use connection pool**: Import from `api/database.py` (already working)
- **Follow existing patterns**: Copy style from `topic_velocity.py`
- **Rate limiting**: Use slowapi like search endpoint
- **CORS setup**: Already configured, just extend
- **No new dependencies**: Supabase client already installed

## 🔗 **Quick Reference**

- **Health Check**: https://podinsight-api.vercel.app/api/health
- **Search API**: https://podinsight-api.vercel.app/api/search (working example)
- **Repo Structure**: This is `podinsight-api` (backend), dashboard is separate repo

---

**Ready?** Ask for the specific Phase 2.1 prompt from the playbook to begin!
