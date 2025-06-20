# Claude Code Session Prompt: MongoDB Integration for PodInsightHQ

## 🎯 Copy This Entire Prompt to Start New Claude Code Session

```
I need your help implementing MongoDB integration for PodInsightHQ's search feature. Here's the complete context:

## Current Situation
We're in Sprint 1 of building PodInsightHQ - a podcast intelligence platform for VCs and founders. We've successfully deployed a search API, but it has a critical flaw: it returns fake excerpts with 4% relevance scores because we never stored the actual transcript text in our database.

## What We've Built So Far (Sprint 1 Progress)
1. ✅ Topic Velocity dashboard (from Sprint 0) - tracks 5 topics across 1,171 podcasts
2. ✅ Search API deployed to Vercel - but returns mock excerpts
3. ✅ Lightweight implementation using Hugging Face API for embeddings
4. ✅ Connection pooling and health checks implemented
5. ❌ No real transcript storage - only detected topics were saved

## The Problem We're Solving
- **Current**: Search returns placeholders like "Episode 7f54be60... This episode covers AI Agents"
- **Why**: In Sprint 0, we only extracted topic mentions, never stored full transcripts
- **Impact**: Search is unusable - 4% relevance scores, no context shown
- **Constraint**: Transcripts (527MB) + Segments (2.3GB) exceed Supabase free tier (500MB)

## The Solution: MongoDB Integration
- We have $5,000 MongoDB Atlas credit (already secured)
- Hybrid architecture: Supabase (structured data) + MongoDB (documents)
- Keep existing episode-level embeddings (good enough for now)
- Enable real full-text search with actual excerpts

## Key Technical Context
1. **Data Volume**: 1,171 podcast episodes, ~527MB of transcripts
2. **S3 Structure**: Transcripts stored as JSON with segments array
3. **Existing Stack**: FastAPI (Vercel), Supabase (PostgreSQL + pgvector), Next.js dashboard
4. **Embeddings**: We have episode-level embeddings (140KB .npy files) - NOT redoing these now
5. **Topics Tracked**: "AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS", "Crypto/Web3"

## Important Decisions Made
1. **Not re-processing embeddings**: Would take 3 days, current ones work fine with MongoDB full-text search
2. **Hybrid architecture is correct**: Don't try to fit everything in one database
3. **Text search first**: Vector search can be added later to MongoDB
4. **3-4 hour implementation**: With your help generating code instantly

## Key Documents to Reference
@mongodb-action-plan.md - The prescriptive step-by-step guide we'll follow
@sprint1-mongodb-integration.md - Architecture diagrams and context
@sprint1-progress-log.md - What's been completed in Sprint 1
@api/search_lightweight.py - Current search implementation to update

## Working Directory
/Users/jamesgill/PodInsights/podinsight-api

## Our Goal for This Session
Transform our fake search into real search by:
1. Setting up MongoDB Atlas (20 min)
2. Migrating transcripts from S3 to MongoDB (1.5 hours)
3. Updating search API to query MongoDB (1 hour)
4. Testing everything works with >70% relevance scores (30 min)

## First Task
Let's start with Phase 0 from mongodb-action-plan.md. I'll handle the MongoDB Atlas setup (clicking through their UI), but I need you to:
1. Review the quick-start test script that's already created
2. Help me verify the connection works
3. Then we'll move to Phase 1: creating the migration script

## Critical Success Criteria
- Real excerpts showing actual conversation context
- Relevance scores >70% for good matches (not 4%)
- Search results that would impress Paul Graham
- No breaking changes to existing API contracts

Are you ready to help me implement this MongoDB integration? Let's start by reviewing mongodb-quick-start.py to test my MongoDB connection once I've set it up.
```

## 📋 Additional Context for Claude Code (Include if Asked)

### Current File Structure
```
podinsight-api/
├── api/
│   ├── search_lightweight.py  # Current search (returns mock excerpts)
│   ├── topic_velocity.py      # Main FastAPI app
│   └── database.py            # Supabase connection pool
├── mongodb-quick-start.py     # Test MongoDB connection
├── mongodb-action-plan.md     # Step-by-step guide
└── requirements.txt           # Needs pymongo and motor added
```

### Transcript Structure in S3
```json
{
  "segments": [
    {
      "text": "Welcome to the podcast. Today we're discussing AI agents...",
      "speaker": "SPEAKER_01",
      "start": 0.0,
      "end": 5.2
    },
    // ... more segments
  ]
}
```

### Expected MongoDB Document Structure
```javascript
{
  _id: ObjectId(),
  episode_id: "uuid-from-supabase",  // Foreign key
  podcast_name: "The Twenty Minute VC",
  episode_title: "Episode on AI Agents",
  published_at: ISODate("2025-06-15"),
  full_text: "Complete transcript text...",  // Segments joined
  segments: [...],  // Original array preserved
  topics: ["AI Agents", "B2B SaaS"],  // From topic_mentions
  s3_path: "pod-insights-stage/...",
  word_count: 15234,
  duration_seconds: 3600
}
```

### Testing Requirements at Each Step
1. **Connection Test**: Must connect before proceeding
2. **Migration Test**: Try 10 episodes before all 1,171
3. **Search Test**: Must return real excerpts with >50% scores
4. **Production Test**: Must work on Vercel with <2 second response

### What NOT to Do
- Don't try to re-process embeddings (3 day rabbit hole)
- Don't store transcripts in Supabase (exceeds free tier)
- Don't change existing API response format (frontend expects it)
- Don't skip testing at each phase

## 🚀 Best Practices Included in This Prompt

1. **Complete Context**: Current situation, problem, solution, constraints
2. **Clear Goal**: Transform fake search into real search in 3-4 hours
3. **Specific References**: Exact files and documents to use
4. **Technical Details**: Data structures, volumes, architecture
5. **Success Criteria**: Measurable outcomes (70%+ scores, real excerpts)
6. **What NOT to Do**: Prevents common pitfalls
7. **Progressive Approach**: Start with connection test, then build up
8. **Testing Focus**: Test at every step before moving forward

This prompt gives Claude Code everything needed to help you implement MongoDB integration efficiently and correctly!