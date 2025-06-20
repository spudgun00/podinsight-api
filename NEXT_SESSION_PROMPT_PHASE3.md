# Claude Code Session Prompt: Sprint 1 Enhanced Visualizations

## 🎯 **Project Context (2-minute read)**

**PodInsightHQ** = AI-powered search and insights platform for 1,171 podcast episodes from startup/VC shows.

### **Current Status: Sprint 1 - Phase 3 (Enhanced Visualizations)**
- ✅ **MongoDB Search**: Working perfectly at https://podinsight-api.vercel.app/api/search  
- ✅ **Real Data**: 60x search quality improvement with transcript excerpts
- 🔄 **Next Phase**: Complete v0 UI integration + sentiment visualization

### **Key Architecture**
```
Topic Velocity API → React Dashboard → Enhanced Visuals
├── Real data         ├── Existing v0 components    ├── SIGNAL bar
├── Correlations      ├── Topic velocity chart      ├── Statistics row  
└── Fast responses    └── Glass morphism design     └── Sentiment heatmap
```

### **Critical Context**
- **Two Repositories**: 
  - `podinsight-api` - Backend APIs and data services
  - `podinsight-dashboard` - React frontend with many unused v0 components
- **Design System**: Dark theme + glass morphism already established
- **Components**: Many v0 components exist but aren't integrated

## 🚀 **Your Mission: Complete Visual Enhancements**

**Goal**: Transform the dashboard UI with all v0 components and add sentiment visualization.

**Key Tasks**:
1. **Find existing v0 components** - They exist but aren't all being used
2. **Add SIGNAL bar** - Real correlations from data
3. **Complete statistics** - Use actual data instead of mock
4. **Create sentiment heatmap** - Visual grid showing sentiment over time

**Repositories to Work In**:
- Start: `podinsight-dashboard` at `/Users/jamesgill/PodInsights/podinsight-dashboard`
- Also: `podinsight-etl` for signal service (Step 3.2)
- Reference: `podinsight-api` for API patterns (current repo)

## 📋 **Files to Focus On**

**Dashboard Repo** (main work):
- `@components/ui/` - Find unused v0 components  
- `@components/dashboard/topic-velocity-chart-full-v0.tsx` - Main chart component
- `@lib/types.ts` - Type definitions

**ETL Repo** (for signal service):
- `@main.py` - Database connection patterns
- `@modules/supabase_loader.py` - Existing ETL patterns

**API Repo** (reference):
- `@api/topic_velocity.py` - Working API patterns
- `@sprint1-playbook-updated.md` - Lines 601-746 for detailed prompts

## 🎨 **What We're Building**

### **1. Complete v0 Component Integration** 
- Find existing: SIGNAL bar, statistics cards, enhanced legend
- Integrate ALL unused v0 components 
- Use real data calculations
- **Time**: 2-3 hours

### **2. Signal Correlation Service** (Backend)
- Calculate which topics appear together
- Store correlations for SIGNAL bar
- Work in `podinsight-etl` repo
- **Time**: 1-2 hours

### **3. Sentiment Heatmap** (Visual Wow Factor)
- Topics (Y) vs Weeks (X) grid
- Colors: Red (-1) → Yellow (0) → Green (+1)  
- Mock data for Sprint 1, real analysis later
- **Time**: 2 hours

## ⚠️ **Critical Success Factors**

- **Don't create new components** - Find and use existing v0 components
- **Use real data** - Calculate statistics from actual API data
- **Maintain design system** - Dark theme + glass morphism
- **API integration** - Topic Velocity API provides real data
- **Follow patterns** - Copy existing component integration style

## 🔗 **Quick Reference**

- **Topic Velocity API**: https://podinsight-api.vercel.app/api/topic-velocity
- **API Health**: https://podinsight-api.vercel.app/api/health  
- **Dashboard Repo**: `/Users/jamesgill/PodInsights/podinsight-dashboard`

## 📊 **Success Criteria**

- [ ] ALL existing v0 components found and integrated
- [ ] SIGNAL bar shows real topic correlations  
- [ ] Statistics row uses actual data calculations
- [ ] Sentiment heatmap renders smoothly
- [ ] Glass morphism design maintained throughout

---

**Ready?** Ask for the specific Phase 3.1 prompt from the playbook to begin with v0 component discovery!