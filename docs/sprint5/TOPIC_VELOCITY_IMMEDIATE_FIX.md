# Topic Velocity API - Immediate Fix Guide

**Date**: 2025-01-13
**Issue**: `/api/topic-velocity` timing out in Vercel (500 errors)
**Root Cause**: Multiple sequential Supabase queries + not using connection pooler

## 🚨 Quick Fix: Use Supabase Connection Pooler

The most immediate fix is to update the `SUPABASE_URL` in Vercel to use the pooler endpoint.

### Step 1: Get Pooler URL from Supabase

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Navigate to **Settings → Database**
4. Find the **Connection Pooler** section
5. Copy the **Connection string** for "Transaction" mode
6. It should look like: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`

### Step 2: Update Vercel Environment Variable

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select `podinsight-api` project
3. Go to **Settings → Environment Variables**
4. Update `SUPABASE_URL` to use the pooler:

**Current (Direct Connection):**
```
https://ydbtuijwsvwwcxkgogtb.supabase.co
```

**Change to (Pooler Connection):**
```
https://ydbtuijwsvwwcxkgogtb.pooler.supabase.com
```

Note: Simply add `.pooler` before `.supabase.com`

### Step 3: Redeploy

The change should trigger an automatic redeployment.

## 🔧 Why This Helps

1. **Connection Pooling**: PgBouncer on port 6543 multiplexes connections
2. **Serverless Friendly**: Prevents "too many connections" errors
3. **Reduced Latency**: Reuses existing connections instead of creating new ones

## 📊 Expected Improvement

- **Before**: 4 queries × cold start connection time = timeout
- **After**: 4 queries × pooled connection = faster response

## 🚀 Long-term Fix (Next Sprint)

The queries should be combined into a single database function:

```sql
CREATE OR REPLACE FUNCTION get_topic_velocity_data(
    p_topics text[],
    p_weeks integer
)
RETURNS json AS $$
DECLARE
    result json;
BEGIN
    -- Combine all 4 queries into one
    SELECT json_build_object(
        'topic_data', (
            SELECT json_agg(row_to_json(t))
            FROM (
                SELECT tm.*, e.published_at
                FROM topic_mentions tm
                JOIN episodes e ON tm.episode_id = e.id
                WHERE tm.topic_name = ANY(p_topics)
            ) t
        ),
        'total_episodes', (SELECT COUNT(*) FROM episodes),
        'date_range', json_build_object(
            'start', (SELECT MIN(published_at) FROM episodes),
            'end', (SELECT MAX(published_at) FROM episodes)
        )
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;
```

Then call it with:
```python
result = await supabase.rpc('get_topic_velocity_data', {
    'p_topics': topics,
    'p_weeks': weeks
}).execute()
```

This would reduce 4 network round trips to just 1.

## 📝 Testing After Fix

```bash
# Test the endpoint
curl "https://podinsight-api.vercel.app/api/topic-velocity?weeks=4"

# Should return data within 5-10 seconds
```

## ⚠️ If Still Failing

Check Vercel logs for specific errors:
- "too many connections" → Pooler not working
- "timeout" → Queries still too slow
- "permission denied" → RLS issue (unlikely based on local tests)
