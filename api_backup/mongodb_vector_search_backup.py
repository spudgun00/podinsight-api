#!/usr/bin/env python3
"""
MongoDB Atlas Vector Search for 768D embeddings
Provides semantic search with Instructor-XL embeddings
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
import asyncio
from collections import OrderedDict

logger = logging.getLogger(__name__)

class MongoVectorSearchHandler:
    """Handles vector similarity search using MongoDB Atlas"""
    
    def __init__(self, mongodb_uri: Optional[str] = None):
        """Initialize MongoDB connection for vector search"""
        self.mongodb_uri = mongodb_uri or os.getenv('MONGODB_URI')
        if not self.mongodb_uri:
            logger.warning("MONGODB_URI not set - vector search will not work!")
            self.client = None
            self.db = None
        else:
            self.client = MongoClient(
                self.mongodb_uri,
                maxPoolSize=10,
                minPoolSize=2,
                serverSelectionTimeoutMS=5000
            )
            self.db = self.client['podinsight']
            self.collection = self.db['transcript_chunks_768d']
        
        # Simple in-memory cache (LRU with max 100 entries)
        self.cache = OrderedDict()
        self.cache_ttl = 300  # 5 minutes
        self.max_cache_size = 100
        
    async def vector_search(
        self, 
        query_embedding: List[float], 
        limit: int = 10,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search using MongoDB Atlas
        
        Args:
            query_embedding: 768D embedding vector
            limit: Maximum number of results
            min_score: Minimum similarity score threshold
            
        Returns:
            List of matching chunks with metadata
        """
        if self.db is None:
            logger.error("MongoDB not connected")
            return []
            
        # Check cache first
        cache_key = f"{hash(str(query_embedding))}:{limit}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info("Cache hit for vector search")
            return cached_result
            
        try:
            start_time = time.time()
            
            # MongoDB Atlas Vector Search pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index_768d",
                        "path": "embedding_768d",
                        "queryVector": query_embedding,
                        "numCandidates": limit * 10,  # Cast wider net
                        "limit": limit
                    }
                },
                {
                    "$addFields": {
                        "score": {"$meta": "vectorSearchScore"}
                    }
                },
                {
                    "$match": {
                        "score": {"$gte": min_score}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
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
            
            # Execute search
            results = list(self.collection.aggregate(pipeline))
            
            elapsed = time.time() - start_time
            logger.info(f"Vector search took {elapsed:.2f}s, found {len(results)} results")
            
            # Enrich results with episode metadata
            enriched_results = await self._enrich_with_metadata(results)
            
            # Cache the results
            self._add_to_cache(cache_key, enriched_results)
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    async def _enrich_with_metadata(self, chunks: List[Dict]) -> List[Dict[str, Any]]:
        """
        Enrich chunk results with episode metadata from transcripts collection
        """
        if not chunks:
            return []
            
        # Get unique episode IDs
        episode_ids = list(set(chunk['episode_id'] for chunk in chunks))
        
        # Fetch episode metadata
        transcripts_collection = self.db['transcripts']
        episodes = {}
        
        for episode in transcripts_collection.find(
            {'episode_id': {'$in': episode_ids}},
            {
                'episode_id': 1,
                'podcast_name': 1,
                'episode_title': 1,
                'published_at': 1,
                'topics': 1
            }
        ):
            episodes[episode['episode_id']] = episode
        
        # Enrich chunks
        enriched = []
        for chunk in chunks:
            episode_id = chunk['episode_id']
            if episode_id in episodes:
                episode = episodes[episode_id]
                enriched_chunk = {
                    **chunk,
                    'podcast_name': episode.get('podcast_name', 'Unknown'),
                    'episode_title': episode.get('episode_title', 'Unknown Episode'),
                    'published_at': episode.get('published_at'),
                    'topics': episode.get('topics', [])
                }
                enriched.append(enriched_chunk)
            else:
                # Include chunk even if episode metadata not found
                enriched_chunk = {
                    **chunk,
                    'podcast_name': chunk.get('feed_slug', 'Unknown'),
                    'episode_title': 'Unknown Episode',
                    'published_at': None,
                    'topics': []
                }
                enriched.append(enriched_chunk)
        
        return enriched
    
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
        if self.client:
            self.client.close()

# Create singleton instance
_vector_search_handler = None

async def get_vector_search_handler() -> MongoVectorSearchHandler:
    """Get or create singleton vector search handler"""
    global _vector_search_handler
    if _vector_search_handler is None:
        _vector_search_handler = MongoVectorSearchHandler()
    return _vector_search_handler