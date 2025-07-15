# URGENT: MongoDB Connection Timeout Fix

## Problem
MongoDB operations are timing out during initial connection from Vercel, causing 15-20 second delays.

## Root Cause
The MongoDB driver's serverSelectionTimeoutMS is too short (appears to be ~10ms based on logs showing "remainingTimeMS: 7"). The driver can't discover the replica set topology in time.

## Immediate Fix

### 1. Update MongoDB Connection Configuration

Find where you create the MongoDB client and add these timeout settings:

```python
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=30000,  # 30 seconds (was ~10ms!)
    connectTimeoutMS=30000,          # 30 seconds
    socketTimeoutMS=30000,           # 30 seconds
    maxPoolSize=100,                 # Increase pool size
    minPoolSize=10,                  # Keep connections warm
    maxIdleTimeMS=60000,             # Keep connections for 1 minute
    retryWrites=True,
    retryReads=True,
    w='majority'
)
```

### 2. Add Connection Warming

Add this to your app startup:

```python
async def warm_mongodb_connection():
    """Warm up MongoDB connection on startup"""
    try:
        # Ping to establish connection
        await client.admin.command('ping')

        # Do a simple query to warm up the connection pool
        db = client.podinsight
        await db.transcript_chunks_768d.find_one()

        print("✅ MongoDB connection warmed up")
    except Exception as e:
        print(f"⚠️ MongoDB warmup failed: {e}")

# Call this on app startup
```

### 3. Update improved_hybrid_search.py

Look for where MongoDB client is created (around line where it says "Creating MongoDB client for hybrid search"):

```python
# OLD
client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=timeout_ms)

# NEW
client = AsyncIOMotorClient(
    uri,
    serverSelectionTimeoutMS=30000,  # 30s instead of 8s
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
    maxPoolSize=50,
    minPoolSize=5,
    maxIdleTimeMS=60000
)
```

### 4. Add Retry Logic

Wrap MongoDB operations with retry:

```python
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def with_retry(operation, max_retries=3):
    """Retry MongoDB operations with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = (2 ** attempt) * 1  # 1s, 2s, 4s
            print(f"MongoDB retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
            await asyncio.sleep(wait_time)
```

## Why This Works

1. **Longer Timeouts**: Gives MongoDB driver time to discover all replica set members
2. **Connection Pooling**: Reuses established connections instead of creating new ones
3. **Connection Warming**: Establishes connections before first user request
4. **Retry Logic**: Handles transient network issues

## Expected Results

- Initial connection: May take 2-5s (one time)
- Subsequent queries: <1s for vector search, <0.5s for text search
- No more ReplicaSetNoPrimary errors
- No more Vercel timeouts

## Deploy This Fix ASAP

This should resolve the 15-20 second delays you're seeing in production!
