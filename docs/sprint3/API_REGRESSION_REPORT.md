# CRITICAL API REGRESSION - Incorrect Week Count Returned

**Date**: 2025-07-02
**Severity**: CRITICAL - Dashboard is broken
**Regression Introduced**: After data consistency fix deployment

## Executive Summary

The Topic Velocity API is returning significantly fewer weeks than requested, breaking the dashboard functionality. This is a regression introduced by the recent data consistency fix.

## Evidence

### Test Results (July 2, 2025 - Week 27)

| Time Range | Weeks Requested | Weeks Returned | Actual Weeks | Missing Data |
|------------|-----------------|----------------|--------------|--------------|
| 1 Month | 4 weeks | 1 week | [2025-W24] | 75% missing |
| 3 Months | 12 weeks | 9 weeks | [2025-W16 to 2025-W24] | 25% missing |

### Expected Behavior

For today's date (July 2, 2025 - ISO Week 27):
- **1M view** should return: W24, W25, W26, W27 (4 weeks)
- **3M view** should return approximately: W15-W27 (12-13 weeks)

### Actual Behavior
- **1M view** returns: Only W24 (1 week)
- **3M view** returns: W16-W24 (9 weeks)

## Impact

1. **1M View Unusable**: Shows only a single data point instead of a trend
2. **3M View Incomplete**: Missing 3 weeks of historical data
3. **User Experience**: Charts appear broken with insufficient data
4. **Data Analysis**: Impossible to analyze trends with missing data

## Root Cause Analysis

The recent fix that removed date filtering from the database query appears to have broken the logic that:
1. Calculates the correct date range based on the `weeks` parameter
2. Returns the appropriate number of weeks counting backwards from today

## Reproduction Steps

```bash
# These API calls demonstrate the issue:
GET /api/topic-velocity?weeks=4&topics=AI%20Agents,Capital%20Efficiency,DePIN,B2B%20SaaS,Crypto/Web3
# Expected: 4 weeks of data
# Actual: 1 week of data

GET /api/topic-velocity?weeks=12&topics=AI%20Agents,Capital%20Efficiency,DePIN,B2B%20SaaS,Crypto/Web3
# Expected: 12 weeks of data
# Actual: 9 weeks of data
```

## Debug Output from Dashboard

```javascript
📅 API Response Analysis:
Today's date: 2025-07-02T15:59:33.786Z
1M: Requested 4 weeks, got 1 weeks: ['2025-W24']
3M: Requested 12 weeks, got 9 weeks: ['2025-W16', '2025-W17', '2025-W18', '2025-W19', '2025-W20', '2025-W21', '2025-W22', '2025-W23', '2025-W24']
```

## Recommended Fix

1. **Immediate**: Revert to the previous version of the API if possible
2. **Proper Fix**:
   - Ensure the API correctly calculates the date range based on current date
   - Return exactly the number of weeks requested
   - Maintain the data consistency fix while properly filtering by date

## Verification Test

Once fixed, this query should return true:
```javascript
// For any API response
const response = await fetch('/api/topic-velocity?weeks=N');
const data = await response.json();

// Verify correct number of weeks
const actualWeeks = new Set();
Object.values(data.data).forEach(topicData => {
  topicData.forEach(item => actualWeeks.add(item.week));
});

console.assert(actualWeeks.size === N, `Expected ${N} weeks, got ${actualWeeks.size}`);
```

## Contact

Dashboard team is blocked until this is resolved. The dashboard is currently showing incorrect and incomplete data to users.
