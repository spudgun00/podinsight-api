# Topic Velocity Regression Fix - Deployment Log

**Date**: 2025-07-02
**Time**: ~4:00 PM PST
**Deployed Commit**: 56a8af2

## Summary

Fixed critical regression in Topic Velocity API where it was returning fewer weeks than requested, breaking dashboard functionality.

## Problem
- API returned only 1 week for 1M view (expected 4)
- API returned only 9 weeks for 3M view (expected 12)
- Dashboard charts appeared broken with insufficient data

## Root Cause
The data consistency fix (removing date filters from query) inadvertently broke the week generation logic. The API was only returning weeks that had data, not the full requested range.

## Solution
Modified `/api/topic_velocity.py` to:
1. Generate ALL weeks in the requested range (lines 236-252)
2. Include empty weeks (0 mentions) for dates without data
3. Properly calculate weeks counting backwards from current date

## Code Changes
```python
# Generate ALL weeks in the requested range (including empty weeks)
all_weeks_in_range = []
current_date = end_date

while current_date >= start_date:
    iso_year, iso_week, _ = current_date.isocalendar()
    week_key = f"{iso_year}-W{str(iso_week).zfill(2)}"
    all_weeks_in_range.append(week_key)
    current_date -= timedelta(weeks=1)

all_weeks_in_range.reverse()  # Sort chronologically
```

## Verification
Created test script `scripts/test_topic_velocity_regression.py` to verify:
- 1M view returns exactly 4 weeks
- 3M view returns exactly 12 weeks
- 6M view returns exactly 24 weeks
- 1Y view returns exactly 52 weeks

## Deployment
- Committed: "fix: Fix topic velocity regression - return all requested weeks"
- Pushed to GitHub at ~4:00 PM PST
- Vercel auto-deployment triggered
- Dashboard team unblocked

## Impact
- Dashboard now shows correct number of weeks for all time ranges
- Data consistency maintained (no date filtering in query)
- Empty weeks included with 0 mentions for complete visualization