"""
MongoDB Vector Search with lazy connection initialization to fix event loop issues
"""
import os
import time
import logging
import hashlib
import asyncio
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from collections import OrderedDict
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)

# Global instance to reuse connections
_handler_instance = None


class MongoVectorSearchHandler:
    # Class-level client to share across instances
    _client = None
    
    def __init__(self):
        self.cache = OrderedDict()
        self.max_cache_size = 100
        self.cache_ttl = 300  # 5 minutes
    
    def _get_collection(self):
        """Always return a collection bound to *this* event loop."""
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DATABASE", "podinsight")
        
        if not uri:
            logger.warning("MONGODB_URI not set, vector search disabled")
            return None
            
        # Create client once at class level
        if MongoVectorSearchHandler._client is None:
            logger.info("Creating MongoDB client (class-level)")
            MongoVectorSearchHandler._client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=10,
                retryWrites=True
            )
        
        # Always get fresh collection reference for current event loop
        db = MongoVectorSearchHandler._client[db_name]
        return db["transcript_chunks_768d"]
    
    async def vector_search(self, 
                          embedding: List[float], 
                          limit: int = 10,
                          min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Perform vector search using MongoDB Atlas Vector Search
        """
        # Get fresh collection for this request
        collection = self._get_collection()
        if collection is None:
            logger.warning("MongoDB not connected for vector search")
            return []
            
        logger.info(
            "[VECTOR_SEARCH_ENTER] db=%s col=%s dim=%d",
            os.getenv("MONGODB_DATABASE", "podinsight"),
            "transcript_chunks_768d",
            len(embedding)
        )
        
        try:
            
            # Create cache key from embedding
            embedding_str = str(embedding[:10])  # Use first 10 values for cache key
            cache_key = hashlib.md5(f"{embedding_str}_{limit}_{min_score}".encode()).hexdigest()
            
            # Check cache
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                logger.info(f"Vector search cache hit")
                return cached_result
            
            start_time = time.time()
            
            # Perform vector search
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index_768d",
                        "path": "embedding_768d",
                        "queryVector": embedding,
                        "numCandidates": min(limit * 50, 2000),
                        "limit": limit
                    }
                },
                {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
                {"$match": {"score": {"$gte": min_score}}},
                {"$limit": limit}
            ]
            
            # Execute search
            try:
                results = await collection.aggregate(pipeline).to_list(limit)
            except Exception:
                logger.exception("[VECTOR_SEARCH] Mongo aggregate failed")
                return []
            
            logger.info("[VECTOR_SEARCH] got %d hits", len(results))
            
            elapsed = time.time() - start_time
            logger.info(f"Vector search took {elapsed:.2f}s")
            
            # Cache the results
            self._add_to_cache(cache_key, results)
            
            return results
        
        except OperationFailure as e:
            logger.error("[VECTOR_SEARCH_OPFAIL] code=%s  msg=%s", e.code, e.details)
            return []
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    def _get_from_cache(self, key: str) -> Optional[List[Dict]]:
        """Get item from cache if not expired"""
        if key in self.cache:
            item = self.cache[key]
            if time.time() - item['timestamp'] < self.cache_ttl:
                # Move to end (LRU)
                self.cache.move_to_end(key)
                return item['data']
            else:
                # Expired
                del self.cache[key]
        return None
    
    def _add_to_cache(self, key: str, data: List[Dict]):
        """Add item to cache with LRU eviction"""
        # Remove oldest if at capacity
        if len(self.cache) >= self.max_cache_size:
            self.cache.popitem(last=False)
            
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    async def close(self):
        """Close MongoDB connection"""
        if MongoVectorSearchHandler._client:
            MongoVectorSearchHandler._client.close()
            MongoVectorSearchHandler._client = None

# Use global instance for connection pooling
async def get_vector_search_handler() -> MongoVectorSearchHandler:
    """Get or create singleton vector search handler"""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = MongoVectorSearchHandler()
    return _handler_instance