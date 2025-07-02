# API Data Inconsistency Report - Topic Velocity Endpoint

**Date**: 2025-07-02
**Reported By**: Dashboard Team
**Severity**: High - Data Integrity Issue
**Affected Endpoint**: `/api/topic-velocity`

## Executive Summary

The Topic Velocity API endpoint returns different mention counts for the same week depending on the `weeks` parameter value. This causes users to see conflicting data when switching between different time views in the dashboard.

## Issue Description

When requesting data from the Topic Velocity API with different time ranges, the same week returns different mention counts. For example:
- Week 2025-W15 shows **0 mentions** for DePIN when requesting 12 weeks of data
- Week 2025-W15 shows **1 mention** for DePIN when requesting 52 weeks of data

This inconsistency affects approximately **40% of weeks** in our testing.

## Evidence

### Test Methodology
We made parallel API calls with different `weeks` parameters and compared the mention counts for identical weeks:

```javascript
// Parallel API calls made by the dashboard
fetchTopicVelocity(12, DEFAULT_TOPICS)  // 3-month view
fetchTopicVelocity(52, DEFAULT_TOPICS)  // Year view (used for quarterly filtering)
```

### Results
Comparison of DePIN topic mentions for overlapping weeks:

| Week | 12-Week Request | 52-Week Request | Status |
|------|-----------------|-----------------|---------|
| 2025-W15 | 0 mentions | 1 mention | ❌ MISMATCH |
| 2025-W16 | 1 mention | 1 mention | ✅ Consistent |
| 2025-W17 | 1 mention | 1 mention | ✅ Consistent |
| 2025-W18 | 3 mentions | 2 mentions | ❌ MISMATCH |
| 2025-W19 | 1 mention | 0 mentions | ❌ MISMATCH |
| 2025-W20 | 2 mentions | 1 mention | ❌ MISMATCH |
| 2025-W21 | 1 mention | 1 mention | ✅ Consistent |
| 2025-W22 | 2 mentions | 2 mentions | ✅ Consistent |
| 2025-W23 | 0 mentions | 0 mentions | ✅ Consistent |
| 2025-W24 | 3 mentions | 3 mentions | ✅ Consistent |

**Inconsistency Rate**: 4 out of 10 weeks (40%)

## How to Reproduce

1. Make two API calls:
   ```bash
   # Request 1: Get 12 weeks of data
   GET /api/topic-velocity?weeks=12&topics=DePIN

   # Request 2: Get 52 weeks of data
   GET /api/topic-velocity?weeks=52&topics=DePIN
   ```

2. Find weeks that appear in both responses (e.g., 2025-W15)

3. Compare the mention counts for the same week across both responses

4. Expected: Identical mention counts for the same week
   Actual: Different mention counts

## Expected Behavior

A specific week (e.g., 2025-W15) should have identical data regardless of the requested time window:
- The mention count for Week X should be the same whether requesting 4, 12, 24, or 52 weeks
- Historical data should be immutable - past weeks shouldn't change based on query parameters

## Impact

1. **User Trust**: Users lose confidence when the same time period shows different values
2. **Data Analysis**: Incorrect insights and decisions based on inconsistent data
3. **UI Confusion**: Dashboard shows conflicting information in different views

## Potential Root Causes

Based on the pattern, the issue could be:

1. **Different Data Sources**: Different time ranges might query different databases or tables
2. **Aggregation Logic**: The API might apply different calculation methods based on the time window
3. **Caching Issues**: Different cache layers for different time ranges with stale data
4. **Query Optimization**: Database queries might use different logic/joins for different time windows
5. **Sampling**: The API might sample data differently for larger time windows

## Verification Steps for Fix

Once fixed, verify by:

1. **Automated Test**: Create a test that:
   ```javascript
   // Pseudo-code for verification test
   const results = await Promise.all([
     fetchTopicVelocity(4),
     fetchTopicVelocity(12),
     fetchTopicVelocity(24),
     fetchTopicVelocity(52)
   ]);

   // Find overlapping weeks
   const commonWeeks = findCommonWeeks(results);

   // Verify each common week has identical data across all requests
   commonWeeks.forEach(week => {
     const values = results.map(r => getWeekValue(r, week));
     assert(allValuesEqual(values), `Week ${week} has inconsistent data`);
   });
   ```

2. **Manual Verification**:
   - Load dashboard with debug logging enabled
   - Check console for "MISMATCH" entries - there should be none
   - Switch between time views (1M, 3M, 6M) and quarterly views
   - Verify the same week shows consistent values across all views

3. **Regression Testing**:
   - Test with different topics (not just DePIN)
   - Test with different time periods
   - Verify data consistency over multiple days

## Debug Code

To enable debug logging in the dashboard:

```javascript
// This code is already in components/dashboard/topic-velocity-chart-full-v0.tsx
// It logs data inconsistencies to the browser console
```

Look for console output starting with "🔍 DEBUG" and any lines marked with "❌ MISMATCH"

## Contact

For questions about this report or assistance with reproduction:
- Dashboard Team
- Debug logs and evidence collected on 2025-07-02

## Appendix: Raw Data Sample

<details>
<summary>Sample API Response Comparison</summary>

12-week request for DePIN (partial):
```json
{
  "data": {
    "DePIN": [
      {"week": "2025-W15", "mentions": 0, "date": "2025-04-07"},
      {"week": "2025-W18", "mentions": 3, "date": "2025-04-28"},
      {"week": "2025-W19", "mentions": 1, "date": "2025-05-05"},
      {"week": "2025-W20", "mentions": 2, "date": "2025-05-12"}
    ]
  }
}
```

52-week request for DePIN (partial):
```json
{
  "data": {
    "DePIN": [
      {"week": "2025-W15", "mentions": 1, "date": "2025-04-07"},
      {"week": "2025-W18", "mentions": 2, "date": "2025-04-28"},
      {"week": "2025-W19", "mentions": 0, "date": "2025-05-05"},
      {"week": "2025-W20", "mentions": 1, "date": "2025-05-12"}
    ]
  }
}
```
</details>
