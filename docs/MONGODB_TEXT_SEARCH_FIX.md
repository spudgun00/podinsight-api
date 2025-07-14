# MongoDB Text Search Fix Documentation

## Issue Summary
Text search was returning 0 results for queries with multiple expanded terms, despite taking 7.5+ seconds to execute. Vector search was working fine (0.27s).

## Root Cause
The code was wrapping multi-word terms in quotes, creating impossible AND conditions:
- Query: "What are VCs saying about AI valuations?"
- Expanded to: `vcs "venture capitalists" investors ai "artificial intelligence" ml valuations valuation pricing "ai valuations"`
- MongoDB interpreted quoted phrases as requiring ALL to match: "venture capitalists" AND "artificial intelligence" AND "ai valuations"
- No documents in 823K collection contained all three exact phrases

## Fix Applied
**File**: `/api/improved_hybrid_search.py`
**Line**: 391
**Change**: Removed quotes from multi-word terms
```python
# Before:
search_terms.append(f'"{term}"')

# After:
search_terms.append(term)
```

This allows MongoDB to use its default OR logic between all terms.

## Enhanced Logging Added
1. **Search term analysis**:
   - Number of search terms
   - Breakdown of single vs multi-word terms

2. **Performance tracking**:
   - Text search execution time
   - Number of results returned
   - Warning if 0 results

3. **Hybrid search monitoring**:
   - Warning when text search fails but vector succeeds
   - Helps identify index issues

## Questions for MongoDB Consultation

### 1. Immediate Optimization
- Is our current text index optimal for our use case?
- Should we consider compound indexes with weights?
- Are there specific index options for better phrase matching without requiring exact matches?

### 2. Atlas Search Migration
- Would Atlas Search provide better relevance for queries like "VC AI valuations"?
- Can Atlas Search handle our domain-specific terminology better?
- What's the migration path from basic text index to Atlas Search?

### 3. Query Strategy
- Best practices for balancing precision vs recall in text search?
- How to boost important terms without requiring exact phrase matches?
- Recommendations for handling domain-specific synonyms (VC = venture capitalist)?

### 4. Performance at Scale
- Currently 823K documents, adding 500+ episodes weekly
- Text search taking 7.5s even with M30 cluster
- How to optimize for sub-2 second response times?

### 5. Hybrid Search Architecture
- Is our vector + text combination approach optimal?
- Should we consider different merge strategies?
- Any MongoDB-specific features we're not leveraging?

## Current Architecture Context
- **Cluster**: M30 (recently upgraded from M10)
- **Collections**: 823K documents in transcripts collection
- **Indexes**: Basic text index on 'text' field
- **Use Case**: Natural language queries for VC/startup podcast content
- **Performance Target**: <2 second response time

## Business Context
- Pre-revenue B2B SaaS targeting VCs
- Search quality directly impacts £99/month value proposition
- Need production-ready solution that can scale
- Building with AI assistance (Claude Code), need clear patterns
