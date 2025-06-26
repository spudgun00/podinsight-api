# Diagnostics

This folder contains investigation scripts and tools for diagnosing and fixing issues with the PodInsight API.

## Current Issue: Sentiment API Timeout

The sentiment analysis API is timing out after 300 seconds when processing the MongoDB `transcript_chunks_768d` collection.

### Problem Analysis
- API is finding chunks (logs show "No chunks found for X in week Y")
- Vercel timeout after 300 seconds (5 minute limit)
- Collection likely has 1200+ chunks to process
- Current approach is too slow for production use

### Investigation Scripts
- `mongodb_query_analyzer.py` - Analyze MongoDB query performance
- `sentiment_performance_test.py` - Test sentiment analysis with different optimization strategies
- `chunk_distribution_analysis.py` - Understand data distribution for optimization

### Optimization Strategies to Test
1. **Pagination** - Process data in smaller batches
2. **Indexing** - Ensure proper MongoDB indexes on `published_at` and `text` fields
3. **Sampling** - Use statistical sampling instead of processing all chunks
4. **Caching** - Cache results for common queries
5. **Aggregation** - Use MongoDB aggregation pipeline for better performance
