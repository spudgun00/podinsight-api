# Code Appendix - All Modified Files

## 1. api/search_lightweight_768d.py

### Key Changes:
- Added query normalization: `clean_query = request.query.strip().lower()`
- Fixed offset/limit math
- Added DEBUG_MODE logging
- Added fallback when vector search returns 0 results

```python
# Lines 230-237: Query normalization
# Normalize query for consistent processing
clean_query = request.query.strip().lower()

# Debug logging
if DEBUG_MODE:
    logger.info(f"[DEBUG] Original query: '{request.query}'")
    logger.info(f"[DEBUG] Clean query: '{clean_query}'")
    logger.info(f"[DEBUG] Offset: {request.offset}, Limit: {request.limit}")

# Lines 261-273: Fixed pagination
# Perform vector search - fetch enough results for pagination
num_to_fetch = request.limit + request.offset
logger.info(f"Calling vector search with limit={num_to_fetch}, min_score=0.0")
vector_results = await vector_handler.vector_search(
    embedding_768d,
    limit=num_to_fetch,
    min_score=0.0  # Lowered threshold to debug - was 0.7
)
logger.info(f"Vector search returned {len(vector_results)} results")

# Apply offset - slice from offset to end, not offset+limit
paginated_results = vector_results[request.offset:]
if len(paginated_results) > request.limit:
    paginated_results = paginated_results[:request.limit]

# Lines 336-349: Fallback logic
# Only return vector results if we actually got some
if len(formatted_results) > 0:
    logger.info(f"Returning {len(formatted_results)} formatted results")
    return SearchResponse(...)
else:
    logger.warning(f"Vector search returned 0 results, falling back to text search")
```

## 2. api/embeddings_768d_modal.py

### Key Changes:
- Added nested array detection and flattening
- Added dimension logging

```python
# Lines 73-83: Array flattening
if response.status == 200:
    data = await response.json()
    embedding = data.get("embedding", data)

    # Un-nest accidental double list
    if isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
        logger.warning(f"Detected nested embedding array, flattening...")
        embedding = embedding[0]

    logger.info(f"Generated 768D embedding via Modal for: {query[:50]}... (dim: {len(embedding) if embedding else 0})")
    return embedding
```

## 3. api/mongodb_vector_search.py

### Key Changes:
- Increased timeouts from 5s to 10s
- Added retry logic with exponential backoff
- Implemented singleton pattern
- Added environment variable for database name

```python
# Lines 37-45: Connection improvements
self.client = AsyncIOMotorClient(
    mongo_uri,
    serverSelectionTimeoutMS=10000,  # Increased from 5000
    connectTimeoutMS=10000,
    socketTimeoutMS=10000,
    maxPoolSize=10,
    retryWrites=True
)

# Get database name from environment or use default
db_name = os.getenv("MONGODB_DATABASE", "podinsight")
logger.info(f"Using MongoDB database: {db_name}")

# Lines 154-173: Retry logic
for attempt in range(3):
    try:
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(None)
        if attempt > 0:
            logger.info(f"Vector search succeeded on attempt {attempt + 1}")
        break
    except Exception as e:
        last_error = e
        if attempt < 2:  # Not the last attempt
            wait_time = (attempt + 1) * 2  # 2, 4 seconds
            logger.warning(f"Vector search attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            await asyncio.sleep(wait_time)
        else:
            logger.error(f"MongoDB aggregate error after 3 attempts: {e}")
            results = []

# Lines 339-344: Singleton pattern
async def get_vector_search_handler() -> MongoVectorSearchHandler:
    """Get or create singleton vector search handler"""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = MongoVectorSearchHandler()
    return _handler_instance
```

## 4. api/warmup.py (New File)

```python
"""Warmup function to pre-establish connections"""
import logging
from .mongodb_vector_search import get_vector_search_handler
from .embeddings_768d_modal import get_embedder

logger = logging.getLogger(__name__)

async def warmup_connections():
    """Pre-establish connections to avoid cold start issues"""
    try:
        # Warm up MongoDB connection
        logger.info("Warming up MongoDB connection...")
        vector_handler = await get_vector_search_handler()

        # Test the connection with a simple query
        if vector_handler.collection:
            count = await vector_handler.collection.count_documents({}, limit=1)
            logger.info(f"MongoDB warmup successful, collection accessible")

        # Warm up Modal embedder
        logger.info("Warming up Modal embedder...")
        embedder = get_embedder()

        # Test with a simple embedding
        test_embedding = embedder.encode_query("test")
        if test_embedding and len(test_embedding) == 768:
            logger.info("Modal embedder warmup successful")

        logger.info("All connections warmed up successfully")
        return True

    except Exception as e:
        logger.error(f"Warmup failed: {e}")
        return False
```

## 5. api/topic_velocity.py

### Key Changes:
- Added startup event for warmup

```python
# Lines 41-48: Startup warmup
from .warmup import warmup_connections

@app.on_event("startup")
async def startup_event():
    """Run warmup on startup"""
    logger.info("Starting API warmup...")
    await warmup_connections()
```

## Test Scripts Created

### scripts/test_phase1_fixes.py
- Tests query normalization (case sensitivity)
- Tests offset/limit pagination
- Tests various queries for success rate

### scripts/monitor_system_health.py
- Comprehensive health monitoring
- Tests Modal endpoint, API health, and critical queries
- Outputs JSON report with pass/fail status

### scripts/test_api_debug.py
- Debug helper for testing different query formats
- Shows which queries work with which parameters

## Git Commits

### Commit 1: Critical API search fixes
```
fix: Critical API search fixes per advisor recommendations

Phase 1 fixes implemented:
- Add query normalization (lowercase, trim) for consistent results
- Fix offset/limit math bug that was causing failures
- Handle nested array issue in Modal embeddings
- Add DEBUG_MODE environment variable for troubleshooting
```

### Commit 2: MongoDB configuration fix
```
fix: Add MongoDB database name from env and better error handling

- Use MONGODB_DATABASE env var for database name flexibility
- Add connection verification and detailed logging
- Improve error messages for debugging connection issues
```

### Commit 3: Reliability improvements
```
fix: Add connection pooling, retry logic, and warmup for reliability

- Increase MongoDB timeouts from 5s to 10s
- Add retry logic with exponential backoff (3 attempts)
- Implement connection pooling with singleton pattern
- Add warmup function to pre-establish connections
- Fall back to text search if vector search returns 0 results
```
