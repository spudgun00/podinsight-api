"""
Fixed MongoDB Vector Search with Supabase metadata integration
"""
import os
import time
import logging
import hashlib
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from collections import OrderedDict
from supabase import create_client

logger = logging.getLogger(__name__)


class MongoVectorSearchHandler:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.supabase = None
        self.cache = OrderedDict()
        self.max_cache_size = 100
        self.cache_ttl = 300  # 5 minutes
        self._connect()
    
    def _connect(self):
        """Initialize MongoDB and Supabase connections"""
        try:
            # MongoDB connection
            mongo_uri = os.getenv("MONGODB_URI")
            if not mongo_uri:
                logger.warning("MONGODB_URI not set, vector search disabled")
                return
            
            logger.info("Attempting MongoDB connection...")
            self.client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
            # Use the database name directly since it's in the URI
            self.db = self.client.podinsight
            self.collection = self.db.transcript_chunks_768d
            logger.info("MongoDB client created successfully")
            
            # Supabase connection
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
            
            if supabase_url and supabase_key:
                self.supabase = create_client(supabase_url, supabase_key)
                logger.info("Connected to Supabase for episode metadata")
            else:
                logger.warning("Supabase credentials not set, episode metadata will be limited")
            
            logger.info("MongoDB Vector Search Handler initialized")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
    
    async def vector_search(self, 
                          embedding: List[float], 
                          limit: int = 10,
                          min_score: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform vector search using MongoDB Atlas Vector Search
        """
        if self.collection is None:
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
            
            # Perform vector search using the correct field name
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index_768d",
                        "path": "embedding_768d",  # This is the correct field name
                        "queryVector": embedding,
                        "numCandidates": min(limit * 10, 1000),  # Cap candidates to prevent full scan
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
                        "score": {"$exists": True, "$ne": None}  # Filter out null scores
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
            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(None)
            
            elapsed = time.time() - start_time
            logger.info(f"Vector search took {elapsed:.2f}s, found {len(results)} results")
            
            # Debug log the raw results
            if results:
                logger.info(f"First result score: {results[0].get('score', 'No score')}")
                logger.info(f"First result episode_id: {results[0].get('episode_id', 'No episode_id')}")
            else:
                logger.warning("Vector search returned no results from MongoDB")
            
            # Enrich results with episode metadata from Supabase
            enriched_results = await self._enrich_with_metadata(results)
            
            logger.info(f"After enrichment: {len(enriched_results)} results")
            
            # Cache the results
            self._add_to_cache(cache_key, enriched_results)
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    async def _enrich_with_metadata(self, chunks: List[Dict]) -> List[Dict[str, Any]]:
        """
        Enrich chunk results with episode metadata from Supabase
        """
        if not chunks:
            return []
            
        # Get unique episode IDs (these are GUIDs)
        episode_guids = list(set(chunk['episode_id'] for chunk in chunks))
        
        # If no Supabase connection, return chunks with minimal metadata
        if not self.supabase:
            enriched = []
            for chunk in chunks:
                enriched_chunk = {
                    **chunk,
                    'podcast_name': chunk.get('feed_slug', 'Unknown'),
                    'episode_title': 'Unknown Episode',
                    'published_at': None,
                    'topics': []
                }
                enriched.append(enriched_chunk)
            return enriched
        
        # Fetch episode metadata from MongoDB using guid field
        try:
            # Query MongoDB for all episodes with matching guids
            logger.info(f"Looking up {len(episode_guids)} episode GUIDs in MongoDB episode_metadata")
            logger.info(f"First 3 GUIDs: {episode_guids[:3]}")
            
            # MongoDB query - MUST use async/await with motor
            cursor = self.db.episode_metadata.find({"guid": {"$in": episode_guids}})
            metadata_docs = await cursor.to_list(None)
            logger.info(f"MongoDB returned {len(metadata_docs)} episodes")
            
            # Create lookup dict by guid
            episodes = {}
            for doc in metadata_docs:
                episodes[doc['guid']] = doc
            
            # Enrich chunks
            enriched = []
            for chunk in chunks:
                episode_guid = chunk['episode_id']
                if episode_guid in episodes:
                    doc = episodes[episode_guid]
                    
                    # Extract metadata from the nested structure
                    raw_feed = doc.get('raw_entry_original_feed', {})
                    
                    # Get episode title from nested structure first, fallback to root
                    episode_title = raw_feed.get('episode_title') or doc.get('episode_title') or 'Unknown Episode'
                    
                    # Get podcast name from nested structure first, fallback to root
                    podcast_name = raw_feed.get('podcast_title') or doc.get('podcast_title') or chunk.get('feed_slug', 'Unknown')
                    
                    # Get published date
                    published_at = raw_feed.get('published_date_iso') or doc.get('published_at')
                    
                    # Get guests information
                    guests = doc.get('guests', [])
                    guest_names = [guest.get('name', '') for guest in guests if guest.get('name')]
                    
                    enriched_chunk = {
                        **chunk,
                        'podcast_name': podcast_name,
                        'episode_title': episode_title,
                        'published_at': published_at,
                        'topics': [],  # Topics might be in different field
                        's3_audio_path': doc.get('s3_audio_path') or raw_feed.get('s3_audio_path_raw'),
                        'duration_seconds': doc.get('duration_seconds', 0),
                        'guests': guest_names,
                        'segment_count': doc.get('segment_count', 0)
                    }
                    enriched.append(enriched_chunk)
                else:
                    # Include chunk even if episode metadata not found
                    logger.warning(f"Episode metadata not found for guid: {episode_guid}")
                    enriched_chunk = {
                        **chunk,
                        'podcast_name': chunk.get('feed_slug', 'Unknown'),
                        'episode_title': 'Unknown Episode',
                        'published_at': None,
                        'topics': [],
                        'guests': [],
                        'segment_count': 0
                    }
                    enriched.append(enriched_chunk)
            
            logger.info(f"Enriched {len(enriched)} chunks with MongoDB metadata")
            return enriched
            
        except Exception as e:
            logger.error(f"Failed to fetch MongoDB metadata: {e}")
            # Return chunks without enrichment on error
            enriched = []
            for chunk in chunks:
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