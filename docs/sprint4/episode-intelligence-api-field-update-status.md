# Episode Intelligence API - Field Update Status

## Update Summary
Based on your confirmation that `episode_id` now contains GUID values in the `episode_metadata` collection, I've updated the Episode Intelligence API to use this field.

## Changes Made (Commit: f119a2d)

### 1. Updated Dashboard Endpoint (`/api/intelligence/dashboard`)
- Now checks `episode_id` field first, then falls back to `guid` field
- Uses `episode_id` to lookup data in `episode_intelligence` collection

### 2. Updated Brief Endpoint (`/api/intelligence/brief/{episode_id}`)
- Checks `episode_id` field first for intelligence lookups
- Maintains backward compatibility with `guid` field

### 3. Updated Helper Functions
- `get_episode_signals()`: Uses episode_id to find matching intelligence data
- `calculate_relevance_score()`: Queries using episode_id first, then guid

### 4. Enhanced Debug Endpoints
- `/api/intelligence/debug`: Now shows both guid and episode_id fields
- `/api/intelligence/test-match`: Enhanced to check episode_id field and show match status

## Testing Results

### Current Status
The API code has been updated and pushed to GitHub. However, the deployment to Vercel may take some time to complete.

### Test Endpoints
1. **Debug Endpoint**: `https://podinsight-api.vercel.app/api/intelligence/debug`
   - Shows collection counts and sample documents

2. **Test Match Endpoint**: `https://podinsight-api.vercel.app/api/intelligence/test-match`
   - Checks if episode_id values match between collections

3. **Dashboard Endpoint**: `https://podinsight-api.vercel.app/api/intelligence/dashboard`
   - Should return real episode data once deployment completes

## Next Steps

1. **Wait for Deployment**: Vercel deployment typically takes 2-5 minutes
2. **Verify Real Data**: Once deployed, the dashboard should return real episodes instead of mock data
3. **Check Field Matching**: The test-match endpoint should show `intelligence_match_found: true`

## How to Verify Success

Run this command to check if real data is being returned:
```bash
curl -X GET "https://podinsight-api.vercel.app/api/intelligence/dashboard?limit=1" | jq '.episodes[0] | {episode_id, title, signals: (.signals | length)}'
```

Success indicators:
- `episode_id` will NOT start with "mock-"
- `title` will be a real episode title
- `signals` count will be greater than 1

## Troubleshooting

If the API still returns mock data after deployment:
1. Check if `episode_metadata.episode_id` truly contains the same values as `episode_intelligence.episode_id`
2. Verify that the ETL script copied the GUID values correctly
3. Check the test-match endpoint to see field comparison

## Code Fallback Logic

The API now uses this priority order:
1. Check `episode_metadata.episode_id` field
2. Fall back to `episode_metadata.guid` field
3. Use the provided episode_id parameter as last resort

This ensures backward compatibility while supporting the new field structure.
