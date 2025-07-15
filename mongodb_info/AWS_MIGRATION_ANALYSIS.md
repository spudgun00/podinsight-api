# MongoDB Atlas to AWS Migration Analysis

**Date**: 2025-01-14
**Current Crisis**: MongoDB M20 tier (4GB RAM) with 8.4GB data causing timeouts
**Available Credits**: $300 MongoDB, $5,000 AWS

---

## 🎯 Executive Summary

### Key Discovery: MongoDB Atlas on AWS Marketplace
You can potentially pay for MongoDB Atlas through AWS Marketplace, using your AWS credits. This changes everything - you could have 18+ months of runway instead of 4 months.

### Recommended Strategy
1. **Immediate**: Check AWS Marketplace for MongoDB Atlas billing
2. **Short-term**: Upgrade to M30 tier to fix performance
3. **Long-term**: Plan migration to PostgreSQL + pgvector for better cost efficiency

---

## 💰 Financial Analysis

### Current MongoDB Path
- M30: $370/month → With $300 credit = 4 months runway
- M40: $700/month → With $300 credit = <1 month runway

### AWS Credits Usage
- PostgreSQL option: $330/month = 15 months runway
- MongoDB via AWS: $370/month = 13.5 months runway
- Best of both: Use AWS credits for MongoDB now, migrate later

---

## 🔍 AWS Alternatives Deep Dive

### 1. AWS DocumentDB ❌ (Not Viable)
**Marketing**: "MongoDB-compatible"
**Reality**:
- Based on MongoDB 3.6/4.0 API
- **NO text search support** ($text, $search operators)
- No Atlas Search compatibility
- Would require complete search rewrite

**Verdict**: Despite "compatibility" claims, would break your core functionality

### 2. Amazon OpenSearch 🤔 (Possible but Complex)
**Pros**:
- Excellent text search (Lucene-based)
- Scalable and managed
- Good for analytics

**Cons**:
- Not optimized for 768-dim vectors
- Completely different API/query language
- Would need separate storage for non-search data
- 6-8 week migration effort

**Cost**: ~$350-500/month for your data size

### 3. PostgreSQL + pgvector ✅ (Recommended Long-term)
**Pros**:
- Native full-text search
- pgvector for 768-dim embeddings
- Single database for all data
- Mature, reliable, SQL standard
- Rich ecosystem and tooling

**Cons**:
- Paradigm shift (document → relational)
- Complete code rewrite needed
- 4-6 week migration effort

**Cost**: ~$330/month (db.m5.xlarge with 16GB RAM)

### 4. DynamoDB + OpenSearch ⚠️ (Over-engineered)
**Pros**:
- DynamoDB for data, OpenSearch for search
- Highly scalable

**Cons**:
- Two services to manage
- Complex data synchronization
- Higher cost (~$600/month)
- Most complex migration

---

## 🛠️ Migration Complexity Analysis

### Staying with MongoDB (1 day)
```python
# No code changes needed
# Just upgrade tier in Atlas console
```

### PostgreSQL Migration (4-6 weeks)
```python
# Current MongoDB
pipeline = [
    {"$search": {
        "text": {
            "query": query_text,
            "path": "text"
        }
    }},
    {"$limit": 100}
]
results = await collection.aggregate(pipeline).to_list()

# New PostgreSQL
query = """
    SELECT *,
           ts_rank(to_tsvector('english', text),
                  websearch_to_tsquery($1)) as text_score,
           1 - (embedding_768d <=> $2) as vector_score
    FROM transcript_chunks_768d
    WHERE to_tsvector('english', text) @@ websearch_to_tsquery($1)
       OR embedding_768d <=> $2 < 0.5
    ORDER BY (text_score + vector_score) DESC
    LIMIT 100
"""
results = await conn.fetch(query, query_text, query_vector)
```

---

## 📋 Phased Migration Plan

### Phase 1: Stop the Bleeding (Week 1)
1. **Check AWS Marketplace** for MongoDB Atlas
   - Contact: AWS account manager or support
   - Ask: "Can we pay for MongoDB Atlas through AWS Marketplace?"

2. **If YES**:
   - Route MongoDB bills through AWS
   - Upgrade to M30 immediately
   - You now have 18+ months runway!

3. **If NO**:
   - Still upgrade to M30 (using MongoDB credits)
   - Begin immediate PostgreSQL migration planning

### Phase 2: Strategic Migration (Months 2-4)
Only if you want long-term cost optimization:

1. **Infrastructure Setup**
   ```sql
   -- PostgreSQL schema
   CREATE TABLE transcript_chunks_768d (
       id UUID PRIMARY KEY,
       episode_id UUID NOT NULL,
       chunk_index INTEGER NOT NULL,
       text TEXT NOT NULL,
       embedding_768d vector(768),
       start_time FLOAT,
       end_time FLOAT,
       feed_slug VARCHAR(255),
       created_at TIMESTAMP DEFAULT NOW()
   );

   -- Indexes
   CREATE INDEX idx_text_fts ON transcript_chunks_768d
   USING GIN (to_tsvector('english', text));

   CREATE INDEX idx_embedding ON transcript_chunks_768d
   USING ivfflat (embedding_768d vector_cosine_ops);
   ```

2. **Dual-Write Strategy**
   ```python
   # Write to both databases during transition
   async def save_transcript_chunk(data):
       # Write to MongoDB (existing)
       await mongo_collection.insert_one(data)

       # Also write to PostgreSQL (new)
       await pg_conn.execute("""
           INSERT INTO transcript_chunks_768d
           (id, episode_id, text, embedding_768d, ...)
           VALUES ($1, $2, $3, $4, ...)
       """, data['_id'], data['episode_id'], ...)
   ```

3. **Gradual Cutover**
   - Week 1-2: Dual writes + backfill historical data
   - Week 3-4: A/B test search results
   - Week 5-6: Gradual traffic migration
   - Week 7-8: Full cutover + MongoDB decommission

---

## 🎯 Decision Matrix

| Factor | Stay with MongoDB | Migrate to PostgreSQL |
|--------|-------------------|----------------------|
| **Time to Fix** | 1 day | 4-6 weeks |
| **Risk** | None | Medium-High |
| **Monthly Cost** | $370-700 | $330 |
| **Credits Runway** | 4 months (or 18 via AWS) | 15 months |
| **Code Changes** | None | Complete rewrite |
| **Team Learning** | None | PostgreSQL + pgvector |
| **Long-term Flexibility** | Vendor lock-in | SQL standard |
| **Search Performance** | Good | Excellent (more control) |

---

## 🚀 Recommended Action Plan

### This Week (Critical):
1. **Call AWS Support**: Ask about MongoDB Atlas on AWS Marketplace
2. **Upgrade MongoDB**: M20 → M30 regardless of credits situation
3. **Deploy query optimizations**: Limit results to reduce load

### Next Month (If AWS Marketplace works):
1. Relax - you have 18 months runway
2. Plan PostgreSQL migration at a comfortable pace
3. Build proof-of-concept without time pressure

### Next Month (If AWS Marketplace doesn't work):
1. Start PostgreSQL migration immediately
2. Set up dual-write infrastructure
3. Target 2-month migration timeline

---

## 💡 Key Insights

1. **AWS Marketplace could solve everything** - This should be your #1 priority
2. **PostgreSQL + pgvector is the best technical solution** - But migration risk is high
3. **DocumentDB is a trap** - "MongoDB-compatible" doesn't include search features
4. **Credits create artificial urgency** - Don't let them force a bad decision

## 📞 Next Steps

1. **Today**: Contact AWS about MongoDB Atlas Marketplace billing
2. **Tomorrow**: Upgrade MongoDB tier regardless
3. **This Week**: Make migration go/no-go decision based on AWS response

Remember: A working system on expensive infrastructure beats a broken system on cheap infrastructure. Fix the immediate problem first, optimize costs second.
