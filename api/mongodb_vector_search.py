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
    def __init__(self):
        self._client = None
        self._collection = None
        self.cache = OrderedDict()
        self.max_cache_size = 100
        self.cache_ttl = 300  # 5 minutes
    
    def _get_collection(self):
        """Get MongoDB collection, creating client if needed within current event loop"""
        # Always create a new collection reference for the current event loop
        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            logger.warning("MONGODB_URI not set, vector search disabled")
            return None
        
        # Create client if needed
        if self._client is None:
            logger.info("Creating MongoDB client...")
            self._client = AsyncIOMotorClient(
                mongo_uri, 
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=10,
                retryWrites=True
            )
        
        # Always get fresh collection reference for current event loop
        db_name = os.getenv("MONGODB_DATABASE", "podinsight")
        collection = self._client[db_name]["transcript_chunks_768d"]
        logger.info(f"MongoDB collection obtained for current request: {collection.full_name}")
        
        return collection
    
    async def vector_search(self, 
                          embedding: List[float], 
                          limit: int = 10,
                          min_score: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform vector search using MongoDB Atlas Vector Search
        """
        collection = self._get_collection()
        logger.warning("[VECTOR_SEARCH_ENTER] path=%s idx=%s  len=%d",
                       collection.full_name if collection is not None else "None", "vector_index_768d", len(embedding))
        logger.warning(f"[VECTOR_SEARCH_START] Called with limit={limit}, min_score={min_score}, embedding_len={len(embedding) if embedding else 0}")
        
        if collection is None:
            logger.warning("MongoDB not connected for vector search")
            return []
        
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
            
            # Log search parameters
            logger.info(f"Vector search - embedding dim: {len(embedding)}, limit: {limit}, min_score: {min_score}")
            
            # Perform vector search using the correct field name
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index_768d",
                        "path": "embedding_768d",  # This is the correct field name
                        "queryVector": embedding,
                        "numCandidates": min(limit * 50, 2000),  # Higher recall with one DB round-trip
                        "limit": limit,
                        "filter": {}
                    }
                },
                {
                    "$limit": limit  # Critical: Add $limit right after $vectorSearch
                },
                {
                    "$addFields": {
                        "score": {"$meta": "vectorSearchScore"}
                    }
                },
                {
                    "$match": {
                        "score": {"$gte": 0}  # Explicit score check to avoid null/NaN issues
                    }
                },
                {
                    "$project": {
                        "episode_id": 1,
                        "feed_slug": 1,
                        "chunk_index": 1,
                        "text": 1,
                        "start_time": 1,
                        "end_time": 1,
                        "speaker": 1,
                        "score": 1
                    }
                }
            ]
            
            # Execute search (async)
            logger.info(f"Executing vector search with index: vector_index_768d")
            logger.info(f"Collection name: {collection.name}")
            logger.info(f"Embedding length: {len(embedding)}")
            
            # Since we fixed the event loop issue, no need for retry logic
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(None)
            logger.info(f"[VECTOR_SEARCH] Returned {len(results)} results")
            logger.info(f"[DEBUG] raw vector hits: {results[:3] if results else 'EMPTY'}")
            
            elapsed = time.time() - start_time
            logger.info(f"Vector search took {elapsed:.2f}s, found {len(results)} results")
            
            # Log top scores for debugging
            if results:
                top_scores = [r.get("score", 0) for r in results[:3]]
                logger.info(f"Top 3 scores: {top_scores}")
            
            # Debug log the raw results
            if results:
                logger.info(f"First result score: {results[0].get('score', 'No score')}")
                logger.info(f"First result episode_id: {results[0].get('episode_id', 'No episode_id')}")
            else:
                logger.warning("Vector search returned no results from MongoDB")
            
            # Return results directly without Supabase enrichment
            logger.info(f"Returning {len(results)} results without Supabase enrichment")
            
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
        if self._client:
            self._client.close()

# Use global instance for connection pooling
async def get_vector_search_handler() -> MongoVectorSearchHandler:
    """Get or create singleton vector search handler"""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = MongoVectorSearchHandler()
    return _handler_instance