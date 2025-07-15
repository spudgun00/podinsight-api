# Production MongoDB Performance Monitoring Guide

## What We Fixed

1. **MongoDB Connection Timeouts**: Changed from dynamic (7-10ms) to fixed 10s timeout
2. **Connection Pooling**: Increased pool size and added connection warming
3. **Text Search Performance**:
   - Created index on `episode_metadata.episode_id`
   - Reduced MAX_SEARCH_TERMS from 12 to 6
   - Fixed text search from 24.64s to ~7.79s

## Expected Performance Metrics

### Before Optimizations
- Connection establishment: 15-20s (causing timeouts)
- Text search: 24.64s
- Total search time: 27.56s
- Frequent "remainingTimeMS: 7" errors

### After Optimizations
- Connection establishment: <1s (with warming)
- Text search: ~7-10s
- Total search time: ~10-12s
- No timeout errors

## Key Metrics to Monitor

### 1. Connection Times
Look for these log entries:
```
[MONGODB_CONNECTION] Connected in X.XXs
```
- Should be <1s with connection warming
- >5s indicates connection issues

### 2. Search Performance
```
[TEXT_SEARCH] Execution time: X.XXs
[VECTOR_SEARCH] Execution time: X.XXs
[HYBRID_LATENCY] Search completed in XXXXms
```
- Text search: Should be <10s (was 24.64s)
- Vector search: Should remain ~0.67s
- Total hybrid search: Should be <12s (was 27.56s)

### 3. Timeout Warnings
Watch for:
```
remainingTimeMS: X
```
- Should NOT see values <1000ms
- Previously saw "remainingTimeMS: 7"

## Monitoring Commands

### 1. Check Recent Logs
```bash
# View recent search performance
grep -E "(TEXT_SEARCH|VECTOR_SEARCH|HYBRID_LATENCY)" /path/to/logs | tail -20

# Check for timeout warnings
grep "remainingTimeMS" /path/to/logs | tail -10

# Monitor connection times
grep "MONGODB_CONNECTION" /path/to/logs | tail -10
```

### 2. Real-time Monitoring
```bash
# Watch search performance in real-time
tail -f /path/to/logs | grep -E "(SEARCH|LATENCY|remainingTimeMS)"
```

### 3. Performance Statistics
```bash
# Calculate average search times from logs
grep "HYBRID_LATENCY" /path/to/logs | \
  awk -F'in |ms' '{print $(NF-1)}' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count, "ms"}'
```

## Alerts to Set Up

1. **Search Timeout Alert**
   - Trigger: HYBRID_LATENCY > 20000ms
   - Action: Check MongoDB connection and indexes

2. **Connection Warning**
   - Trigger: MONGODB_CONNECTION > 5000ms
   - Action: Check replica set health

3. **Low remainingTimeMS Alert**
   - Trigger: remainingTimeMS < 1000
   - Action: Investigate slow queries

## Verification Steps

### 1. Initial Deployment (First Hour)
- [ ] Monitor logs for first 10-20 searches
- [ ] Verify text search <10s
- [ ] Confirm no remainingTimeMS warnings
- [ ] Check connection warming is working

### 2. Load Testing
- [ ] Run multiple concurrent searches
- [ ] Monitor connection pool usage
- [ ] Verify no connection timeouts under load

### 3. Daily Checks
- [ ] Review average search times
- [ ] Check for any timeout patterns
- [ ] Monitor index usage statistics

## Troubleshooting

### If Search is Still Slow (>15s)

1. **Verify Index Usage**
   ```bash
   python scripts/check_text_index_safe.py
   ```

2. **Check Episode Metadata Index**
   ```bash
   python scripts/fix_episode_metadata_index.py
   ```

3. **Monitor Query Complexity**
   - Check if searches have >6 terms
   - Look for complex regex patterns

### If Timeouts Return

1. **Check MongoDB Status**
   - Verify replica set health
   - Check for ongoing elections
   - Monitor Atlas metrics

2. **Review Connection Pool**
   - Check if pool is exhausted
   - Monitor connection churn

3. **Verify Warming Endpoint**
   - Ensure /api/prewarm is being called
   - Check warming frequency

## Success Criteria

The optimizations are successful if:
- ✅ No "remainingTimeMS < 1000" warnings
- ✅ Average search time <12s
- ✅ 95th percentile search time <15s
- ✅ No connection timeout errors
- ✅ Stable performance under load

## Next Optimization Opportunities

If further improvements needed:
1. Denormalize episode metadata into chunks
2. Implement caching layer for frequent searches
3. Use MongoDB Atlas Search instead of text indexes
4. Optimize vector similarity threshold
