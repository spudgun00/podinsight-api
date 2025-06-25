# PodInsight Complete Code Appendix
*All scripts and code as of June 25, 2025*

## Table of Contents
1. [Core API Files](#core-api-files)
   - [search_lightweight_768d.py](#searchlightweight768dpy)
   - [mongodb_vector_search.py](#mongodbvectorsearchpy)
   - [embeddings_768d_modal.py](#embeddings768dmodalpy)
   - [database.py](#databasepy)
   - [mongodb_search.py](#mongodbsearchpy)
2. [Modal.com Scripts](#modalcom-scripts)
   - [modal_web_endpoint_simple.py](#modalwebendpointsimplepy)
   - [modal_embeddings_simple.py](#modalembeddingssimplepy)
3. [Testing Scripts](#testing-scripts)
   - [test_data_quality.py](#testdataqualitypy)
   - [test_e2e_production.py](#teste2eproductionpy)
   - [debug_vector_search.py](#debugvectorsearchpy)
   - [check_orphan_episodes.py](#checkorphanepisodespy)
   - [test_embedding_instruction.py](#testembeddinginstructionpy)
4. [Utility Scripts](#utility-scripts)
   - [analyze_182_chunk_episode.py](#analyze182chunkepisodepy)
   - [test_embedder_direct.py](#testembedderdirectpy)

---

## Core API Files

### search_lightweight_768d.py
Location: `/api/search_lightweight_768d.py`

```python
"""
Lightweight Search API with 768D Vector Search
Primary: MongoDB Atlas Vector Search (768D)
Secondary: MongoDB Text Search
Tertiary: Supabase pgvector (384D)
"""
from fastapi import HTTPException
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import logging
import hashlib
import json
import asyncio
import aiohttp
from pydantic import BaseModel, Field, validator
from .database import get_pool
from .mongodb_search import get_search_handler
from .mongodb_vector_search import get_vector_search_handler
from .embeddings_768d_modal import get_embedder

# Configure logging
logger = logging.getLogger(__name__)

# Use same request/response models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    
    @validator('query')
    def query_not_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Query cannot be empty")
        return v.strip()

class SearchResult(BaseModel):
    episode_id: str
    podcast_name: str
    episode_title: str
    published_at: str
    published_date: str  # Human-readable date
    similarity_score: float
    excerpt: str
    word_count: int
    duration_seconds: int
    topics: List[str]
    s3_audio_path: Optional[str]
    timestamp: Optional[Dict[str, float]]  # start_time, end_time for playback

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int
    cache_hit: bool
    search_id: str
    query: str
    limit: int
    offset: int
    search_method: str  # "vector_768d", "text", or "vector_384d"


async def generate_embedding_768d_local(text: str) -> List[float]:
    """
    Generate 768D embedding using local Instructor-XL model
    """
    try:
        embedder = get_embedder()
        return embedder.encode_query(text)
    except Exception as e:
        logger.error(f"Error generating 768D embedding: {e}")
        return None


async def generate_embedding_384d_api(text: str) -> List[float]:
    """
    Generate 384D embedding using Hugging Face API (existing fallback)
    """
    api_url = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
    api_key = os.environ.get("HUGGINGFACE_API_KEY")
    
    if not api_key:
        logger.error("HUGGINGFACE_API_KEY not found")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": text,
        "options": {"wait_for_model": True}
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    embedding = result
                    
                    # Normalize to unit length
                    norm = sum(x**2 for x in embedding) ** 0.5
                    if norm > 0:
                        embedding = [x / norm for x in embedding]
                    
                    return embedding
                else:
                    logger.error(f"Embedding API error: {response.status}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error calling embedding API: {str(e)}")
        return None


# TODO: Implement MongoDB caching instead of Supabase
# async def check_query_cache_768d(query_hash: str) -> Optional[List[float]]:
#     """Check if 768D query embedding exists in cache"""
#     pool = get_pool()
#     
#     try:
#         def get_cache(client):
#             return client.table("query_cache_768d") \
#                 .select("embedding_768d") \
#                 .eq("query_hash", query_hash) \
#                 .execute()
#         
#         result = await pool.execute_with_retry(get_cache)
#         
#         if result.data and len(result.data) > 0:
#             embedding = result.data[0]["embedding_768d"]
#             if isinstance(embedding, str):
#                 embedding = json.loads(embedding)
#             return embedding
#         
#         return None
#         
#     except Exception as e:
#         logger.warning(f"768D cache check failed: {str(e)}")
#         return None


# TODO: Implement MongoDB caching instead of Supabase
# async def store_query_cache_768d(query: str, query_hash: str, embedding: List[float]) -> None:
#     """Store 768D query embedding in cache"""
#     pool = get_pool()
#     
#     try:
#         embedding_str = json.dumps(embedding)
#         
#         def insert_cache(client):
#             return client.table("query_cache_768d") \
#                 .upsert({
#                     "query_hash": query_hash,
#                     "query_text": query[:500],
#                     "embedding_768d": embedding_str,
#                     "created_at": datetime.now().isoformat()
#                 }) \
#                 .execute()
#         
#         await pool.execute_with_retry(insert_cache)
#         logger.info(f"Cached 768D embedding for query: {query[:50]}...")
#         
#     except Exception as e:
#         logger.warning(f"Failed to cache 768D query: {str(e)}")


async def expand_chunk_context(chunk: Dict[str, Any], context_seconds: float = 20.0) -> str:
    """
    Expand a single chunk by fetching surrounding chunks for context
    
    Args:
        chunk: The chunk hit from vector search
        context_seconds: How many seconds before/after to include (default ±20s)
    
    Returns:
        Expanded text with context
    """
    try:
        # Get MongoDB connection
        from .mongodb_vector_search import get_vector_search_handler
        vector_handler = await get_vector_search_handler()
        
        if vector_handler.db is None:
            return chunk.get("text", "")
        
        # Calculate time window
        start_window = chunk.get("start_time", 0) - context_seconds
        end_window = chunk.get("end_time", 0) + context_seconds
        
        # Fetch surrounding chunks from same episode
        # Use simpler logic: get all chunks where start_time is within our window
        cursor = vector_handler.db.transcript_chunks_768d.find({
            "episode_id": chunk["episode_id"],
            "start_time": {"$gte": start_window, "$lte": end_window}
        }).sort("start_time", 1)
        surrounding_chunks = await cursor.to_list(None)
        
        # Concatenate texts
        texts = []
        for c in surrounding_chunks:
            texts.append(c.get("text", "").strip())
        
        # Join with spaces and clean up
        expanded_text = " ".join(texts)
        expanded_text = " ".join(expanded_text.split())  # Normalize whitespace
        
        # If we got good context, return it
        if len(expanded_text) > len(chunk.get("text", "")):
            logger.info(f"Expanded chunk from {len(chunk.get('text', ''))} to {len(expanded_text)} chars")
            return expanded_text
        else:
            # Fallback to original if expansion failed
            return chunk.get("text", "")
            
    except Exception as e:
        logger.warning(f"Context expansion failed: {e}")
        return chunk.get("text", "")


async def search_handler_lightweight_768d(request: SearchRequest) -> SearchResponse:
    """
    Enhanced search handler with 768D vector search
    Fallback chain: 768D Vector → Text Search → 384D Vector
    """
    # Generate query hash for caching
    query_hash = hashlib.sha256(request.query.encode()).hexdigest()
    search_id = f"search_{query_hash[:8]}_{datetime.now().timestamp()}"
    
    # Try 768D Vector Search first
    try:
        # Check cache for 768D embedding
        # TODO: Implement MongoDB caching instead of Supabase
        # embedding_768d = await check_query_cache_768d(query_hash)
        # cache_hit = bool(embedding_768d)
        embedding_768d = None
        cache_hit = False
        
        if not embedding_768d:
            # Generate new 768D embedding
            logger.info(f"Generating 768D embedding for: {request.query}")
            embedding_768d = await generate_embedding_768d_local(request.query)
            
            # TODO: Cache to MongoDB instead of Supabase
            # if embedding_768d:
            #     # Cache it asynchronously
            #     asyncio.create_task(store_query_cache_768d(request.query, query_hash, embedding_768d))
        
        if embedding_768d:
            # Get MongoDB vector search handler
            vector_handler = await get_vector_search_handler()
            
            if vector_handler.db is not None:
                logger.info(f"Using MongoDB 768D vector search: {request.query}")
                
                # Perform vector search
                logger.info(f"Calling vector search with limit={request.limit + request.offset}, min_score=0.0")
                vector_results = await vector_handler.vector_search(
                    embedding_768d,
                    limit=request.limit + request.offset,
                    min_score=0.0  # Lowered threshold to debug - was 0.7
                )
                logger.info(f"Vector search returned {len(vector_results)} results")
                
                # Apply offset
                paginated_results = vector_results[request.offset:request.offset + request.limit]
                logger.info(f"After pagination: {len(paginated_results)} results (offset={request.offset}, limit={request.limit})")
                
                # Convert to API format with expanded context
                formatted_results = []
                for result in paginated_results:
                    # Expand context for better readability
                    expanded_text = await expand_chunk_context(result, context_seconds=20.0)
                    
                    # Vector search provides chunks with timestamps
                    # Handle published_at - it comes as string from Supabase
                    published_at_str = result.get("published_at")
                    if published_at_str:
                        try:
                            from dateutil import parser
                            published_dt = parser.parse(published_at_str)
                            published_at_iso = published_dt.isoformat()
                            published_date = published_dt.strftime('%B %d, %Y')
                        except:
                            published_at_iso = published_at_str
                            published_date = "Unknown date"
                    else:
                        published_at_iso = datetime.now().isoformat()
                        published_date = "Unknown date"
                    
                    formatted_results.append(SearchResult(
                        episode_id=result["episode_id"],
                        podcast_name=result["podcast_name"],
                        episode_title=result["episode_title"],
                        published_at=published_at_iso,
                        published_date=published_date,
                        similarity_score=float(result.get("score", 0.0)) if result.get("score") is not None else 0.0,
                        excerpt=expanded_text,  # Use expanded text instead of single chunk
                        word_count=len(expanded_text.split()),
                        duration_seconds=result.get("duration_seconds", 0),
                        topics=result.get("topics", []),
                        s3_audio_path=result.get("s3_audio_path"),
                        timestamp={
                            "start_time": result.get("start_time", 0),  # Keep original timestamp for audio sync
                            "end_time": result.get("end_time", 0)
                        }
                    ))
                
                # Audio paths and durations are now included in vector search results
                # from the fixed mongodb_vector_search.py enrichment
                for result, vector_result in zip(formatted_results, paginated_results):
                    result.s3_audio_path = vector_result.get("s3_audio_path")
                    result.duration_seconds = vector_result.get("duration_seconds", 0)
                
                logger.info(f"Returning {len(formatted_results)} formatted results")
                return SearchResponse(
                    results=formatted_results,
                    total_results=len(vector_results),
                    cache_hit=cache_hit,
                    search_id=search_id,
                    query=request.query,
                    limit=request.limit,
                    offset=request.offset,
                    search_method="vector_768d"
                )
    
    except Exception as e:
        logger.error(f"768D vector search failed for query '{request.query}': {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
    
    # Fallback to MongoDB text search
    try:
        mongo_handler = await get_search_handler()
        
        if mongo_handler.db is not None:
            logger.info(f"Falling back to MongoDB text search: {request.query}")
            
            mongo_results = await mongo_handler.search_transcripts(
                request.query, 
                limit=request.limit + request.offset
            )
            
            # Apply offset
            paginated_results = mongo_results[request.offset:request.offset + request.limit]
            
            # Convert MongoDB results to API format
            formatted_results = []
            for result in paginated_results:
                formatted_results.append(SearchResult(
                    episode_id=result["episode_id"],
                    podcast_name=result["podcast_name"],
                    episode_title=result["episode_title"],
                    published_at=result["published_at"],
                    published_date=result.get("published_date", "Unknown date"),
                    similarity_score=float(result.get("relevance_score", 0.0)) if result.get("relevance_score") is not None else 0.0,
                    excerpt=result["excerpt"],
                    word_count=result.get("word_count", 0),
                    duration_seconds=0,
                    topics=result.get("topics", []),
                    s3_audio_path=None,
                    timestamp=result.get("timestamp")
                ))
            
            # Get audio data from Supabase (same as above)
            if formatted_results:
                pool = get_pool()
                episode_ids = [r.episode_id for r in formatted_results]
                
                def get_audio_paths(client):
                    return client.table("episodes") \
                        .select("id, s3_audio_path, duration_seconds") \
                        .in_("id", episode_ids) \
                        .execute()
                
                audio_data = await pool.execute_with_retry(get_audio_paths)
                
                audio_by_id = {
                    ep["id"]: {
                        "s3_audio_path": ep.get("s3_audio_path"),
                        "duration_seconds": ep.get("duration_seconds", 0)
                    }
                    for ep in audio_data.data
                }
                
                for result in formatted_results:
                    if result.episode_id in audio_by_id:
                        result.s3_audio_path = audio_by_id[result.episode_id]["s3_audio_path"]
                        result.duration_seconds = audio_by_id[result.episode_id]["duration_seconds"]
            
            return SearchResponse(
                results=formatted_results,
                total_results=len(mongo_results),
                cache_hit=False,
                search_id=search_id,
                query=request.query,
                limit=request.limit,
                offset=request.offset,
                search_method="text"
            )
    
    except Exception as e:
        logger.warning(f"MongoDB text search failed: {str(e)}")
    
    # No more fallbacks - return empty results
    logger.info(f"All search methods failed for: {request.query}")
    
    return SearchResponse(
        results=[],
        total_results=0,
        cache_hit=False,
        search_id=search_id,
        query=request.query,
        limit=request.limit,
        offset=request.offset,
        search_method="none"
    )
```

### mongodb_vector_search.py
Location: `/api/mongodb_vector_search.py`

```python
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
            logger.info(f"Executing vector search with index: vector_index_768d")
            logger.info(f"Collection name: {self.collection.name}")
            logger.info(f"Database name: {self.db.name}")
            logger.info(f"Embedding length: {len(embedding)}")
            
            try:
                cursor = self.collection.aggregate(pipeline)
                results = await cursor.to_list(None)
            except Exception as e:
                logger.error(f"MongoDB aggregate error: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                # Try to get more details about the error
                if hasattr(e, 'details'):
                    logger.error(f"Error details: {e.details}")
                results = []
            
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
```

### embeddings_768d_modal.py
Location: `/api/embeddings_768d_modal.py`

```python
"""
768D Embeddings using Modal.com hosted Instructor-XL
Replaces local model with Modal serverless function
"""

import os
import logging
import aiohttp
from typing import List, Optional
import asyncio

logger = logging.getLogger(__name__)

class ModalInstructorXLEmbedder:
    """Handles 768D embeddings via Modal.com"""
    
    def __init__(self):
        """Initialize Modal configuration"""
        # Get from environment or Modal dashboard
        self.modal_url = os.getenv('MODAL_EMBEDDING_URL', 'https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run')
        self.modal_token = None  # Public endpoint, no auth needed
    
    def encode_query(self, query: str) -> Optional[List[float]]:
        """
        Encode search query to 768D vector using Modal (synchronous wrapper)
        
        Args:
            query: Search query text
            
        Returns:
            List of 768 float values or None if error
        """
        # Check if there's already an event loop running
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._encode_query_async(query))
                return future.result()
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._encode_query_async(query))
    
    async def _encode_query_async(self, query: str) -> Optional[List[float]]:
        """
        Async method to encode search query to 768D vector using Modal
        
        Args:
            query: Search query text
            
        Returns:
            List of 768 float values or None if error
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json"
                }
                # No auth header since it's a public endpoint
                
                payload = {"text": query}
                
                # Use the correct endpoint (no /embed suffix)
                embed_url = self.modal_url
                
                async with session.post(
                    embed_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)  # Increased timeout for cold starts
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        embedding = data.get("embedding", data)  # Handle different response formats
                        logger.info(f"Generated 768D embedding via Modal for: {query[:50]}...")
                        return embedding
                    else:
                        error_text = await response.text()
                        logger.error(f"Modal API error {response.status}: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Modal API timeout - function may be cold starting (30s timeout)")
            return None
        except Exception as e:
            logger.error(f"Modal embedding error: {e}")
            return None
    
    async def encode_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Encode multiple texts to 768D vectors
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors or None if error
        """
        # No auth needed for public endpoint
            
        try:
            # Use the batch endpoint
            batch_url = f"{self.modal_url}/embed_batch"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json"
                }
                # No auth header since it's a public endpoint
                
                payload = {"texts": texts}
                
                async with session.post(
                    batch_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)  # Longer timeout for batch
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        embeddings = data.get("embeddings", data)
                        logger.info(f"Generated {len(embeddings)} embeddings via Modal")
                        return embeddings
                    else:
                        # Fallback to individual requests
                        logger.warning("Batch endpoint failed, falling back to individual requests")
                        results = []
                        for text in texts:
                            embedding = await self._encode_query_async(text)
                            if embedding:
                                results.append(embedding)
                            else:
                                return None  # Fail if any request fails
                        return results
                        
        except Exception as e:
            logger.error(f"Modal batch embedding error: {e}")
            return None

# Singleton instance
_embedder = None

def get_embedder() -> ModalInstructorXLEmbedder:
    """Get or create singleton embedder instance"""
    global _embedder
    if _embedder is None:
        _embedder = ModalInstructorXLEmbedder()
    return _embedder
```

### database.py
Location: `/api/database.py`

```python
"""
Database connection management for Supabase
"""
import os
import time
import asyncio
import logging
from typing import Optional, Callable, Any
from functools import wraps
from supabase import create_client, Client
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class SupabaseConnectionPool:
    """Manages Supabase connections with retry logic"""
    
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
        self.client: Optional[Client] = None
        self.last_error_time = 0
        self.error_count = 0
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self._connect()
        
        # Track connection metrics
        self.total_requests = 0
        self.connection_errors = 0
        self.created_at = time.time()
        
    def _connect(self):
        """Initialize Supabase client"""
        if not self.url or not self.key:
            logger.error("Supabase credentials not found in environment")
            return
            
        try:
            self.client = create_client(self.url, self.key)
            logger.info("Supabase client initialized successfully")
            self.error_count = 0
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None
            self.last_error_time = time.time()
            
    def get_client(self) -> Optional[Client]:
        """Get Supabase client with automatic reconnection"""
        self.total_requests += 1
        
        if self.client is None:
            # Try to reconnect if enough time has passed
            if time.time() - self.last_error_time > 30:  # 30 second cooldown
                logger.info("Attempting to reconnect to Supabase...")
                self._connect()
        
        return self.client
        
    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries):
            client = self.get_client()
            if client is None:
                self.connection_errors += 1
                raise Exception("Supabase client not available")
                
            try:
                # Execute the operation
                result = operation(client, *args, **kwargs)
                
                # If it's a coroutine, await it
                if asyncio.iscoroutine(result):
                    result = await result
                    
                return result
                
            except Exception as e:
                last_error = e
                self.error_count += 1
                self.connection_errors += 1
                logger.warning(f"Database operation failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    
                # Check if we need to reconnect
                if "connection" in str(e).lower() or "timeout" in str(e).lower():
                    self.client = None
                    self.last_error_time = time.time()
        
        # All retries failed
        raise last_error or Exception("Operation failed after all retries")
        
    def get_stats(self) -> dict:
        """Get connection pool statistics"""
        uptime = time.time() - self.created_at
        return {
            "active_connections": 1 if self.client else 0,
            "max_connections": 1,  # Supabase uses a single client
            "total_requests": self.total_requests,
            "connection_errors": self.connection_errors,
            "error_rate": self.connection_errors / max(1, self.total_requests),
            "uptime_seconds": uptime,
            "status": "healthy" if self.client else "disconnected"
        }

# Global connection pool
_pool: Optional[SupabaseConnectionPool] = None

def get_pool() -> SupabaseConnectionPool:
    """Get or create the global connection pool"""
    global _pool
    if _pool is None:
        _pool = SupabaseConnectionPool()
    return _pool

def close_pool():
    """Close the connection pool"""
    global _pool
    if _pool:
        _pool = None
        logger.info("Connection pool closed")

# For backward compatibility
def get_supabase_client() -> Optional[Client]:
    """Get Supabase client (deprecated, use get_pool instead)"""
    pool = get_pool()
    return pool.get_client()
```

### mongodb_search.py
Location: `/api/mongodb_search.py`

```python
"""
MongoDB text search implementation for fallback when vector search fails
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class MongoSearchHandler:
    def __init__(self):
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Initialize MongoDB connection"""
        try:
            mongo_uri = os.getenv("MONGODB_URI")
            if not mongo_uri:
                logger.warning("MONGODB_URI not set, text search disabled")
                return
                
            self.client = AsyncIOMotorClient(mongo_uri)
            self.db = self.client.podinsight
            logger.info("MongoDB text search handler initialized")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
    
    async def search_transcripts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform text search on episode transcripts
        """
        if self.db is None:
            logger.warning("MongoDB not connected for text search")
            return []
            
        try:
            # Use text search on the episode_transcripts collection
            results = []
            
            # First try text search if index exists
            cursor = self.db.episode_transcripts.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            async for doc in cursor:
                # Get episode metadata
                metadata = await self.db.episode_metadata.find_one(
                    {"guid": doc.get("episode_id")}
                )
                
                if metadata:
                    raw_feed = metadata.get('raw_entry_original_feed', {})
                    
                    result = {
                        "episode_id": doc.get("episode_id"),
                        "podcast_name": raw_feed.get('podcast_title', 'Unknown'),
                        "episode_title": raw_feed.get('episode_title', 'Unknown Episode'),
                        "published_at": raw_feed.get('published_date_iso'),
                        "published_date": self._format_date(raw_feed.get('published_date_iso')),
                        "relevance_score": doc.get("score", 0),
                        "excerpt": self._extract_excerpt(doc.get("transcript", ""), query, 200),
                        "word_count": doc.get("word_count", 0),
                        "topics": []
                    }
                    results.append(result)
            
            logger.info(f"Text search found {len(results)} results for '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Text search error: {e}")
            # Fallback to regex search if text index doesn't exist
            return await self._regex_search(query, limit)
    
    async def _regex_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Fallback regex search when text index is not available
        """
        try:
            # Case-insensitive regex search
            cursor = self.db.episode_transcripts.find(
                {"transcript": {"$regex": query, "$options": "i"}}
            ).limit(limit)
            
            results = []
            async for doc in cursor:
                # Get episode metadata
                metadata = await self.db.episode_metadata.find_one(
                    {"guid": doc.get("episode_id")}
                )
                
                if metadata:
                    raw_feed = metadata.get('raw_entry_original_feed', {})
                    
                    result = {
                        "episode_id": doc.get("episode_id"),
                        "podcast_name": raw_feed.get('podcast_title', 'Unknown'),
                        "episode_title": raw_feed.get('episode_title', 'Unknown Episode'),
                        "published_at": raw_feed.get('published_date_iso'),
                        "published_date": self._format_date(raw_feed.get('published_date_iso')),
                        "relevance_score": 1.0,  # No scoring for regex
                        "excerpt": self._extract_excerpt(doc.get("transcript", ""), query, 200),
                        "word_count": doc.get("word_count", 0),
                        "topics": []
                    }
                    results.append(result)
            
            logger.info(f"Regex search found {len(results)} results for '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Regex search error: {e}")
            return []
    
    def _extract_excerpt(self, text: str, query: str, context_length: int = 200) -> str:
        """
        Extract relevant excerpt around the query match
        """
        if not text:
            return ""
            
        # Find the query in the text (case-insensitive)
        lower_text = text.lower()
        lower_query = query.lower()
        
        pos = lower_text.find(lower_query)
        if pos == -1:
            # If exact match not found, return beginning of text
            return text[:context_length] + "..." if len(text) > context_length else text
        
        # Calculate excerpt boundaries
        start = max(0, pos - context_length // 2)
        end = min(len(text), pos + len(query) + context_length // 2)
        
        # Adjust to word boundaries
        if start > 0:
            while start < len(text) and text[start] not in ' \n\t':
                start += 1
        
        if end < len(text):
            while end > 0 and text[end-1] not in ' \n\t':
                end -= 1
        
        excerpt = text[start:end].strip()
        
        # Add ellipsis if needed
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(text):
            excerpt = excerpt + "..."
            
        return excerpt
    
    def _format_date(self, date_str: str) -> str:
        """Format ISO date string to human-readable format"""
        if not date_str:
            return "Unknown date"
            
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%B %d, %Y')
        except:
            return date_str

# Create singleton instance
_search_handler = None

async def get_search_handler() -> MongoSearchHandler:
    """Get or create singleton search handler"""
    global _search_handler
    if _search_handler is None:
        _search_handler = MongoSearchHandler()
    return _search_handler
```

---

## Modal.com Scripts

### modal_web_endpoint_simple.py
Location: `/scripts/modal_web_endpoint_simple.py`
**CRITICAL FILE - Controls embedding behavior**

```python
"""
Simple Modal.com endpoint for PodInsight embeddings
Simplified version to fix the endpoint issues
"""

import modal
from typing import List, Dict
import time
from pydantic import BaseModel

# These imports only work inside Modal containers
try:
    import torch
    import numpy as np
    from sentence_transformers import SentenceTransformer
except ImportError:
    # Not available locally, will be available in Modal container
    pass

# Create Modal app
app = modal.App("podinsight-embeddings-simple")

# Build image with updated dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "numpy>=1.26.0,<2.0",
        "torch==2.6.0",  # Updated to address CVE-2025-32434 security vulnerability
        "sentence-transformers==2.7.0",  # Tested version
        "fastapi",
        "pydantic",
        extra_index_url="https://download.pytorch.org/whl/cu121"
    )
)

# Create persistent volume for model weights
volume = modal.Volume.from_name("podinsight-hf-cache", create_if_missing=True)

# Embedding instruction - set to empty string to match how chunks were likely indexed
# Can be changed to "Represent the venture capital podcast discussion:" if needed
INSTRUCTION = ""

# Global model cache to avoid reloading
MODEL = None

# Request model for web endpoint
class EmbeddingRequest(BaseModel):
    text: str

def get_model():
    """Get or load the model (cached globally)"""
    global MODEL
    if MODEL is None:
        print("📥 Loading model to cache...")
        start = time.time()
        
        # Load model - try without trust_remote_code first
        try:
            MODEL = SentenceTransformer('hkunlp/instructor-xl')
            print("✅ Loaded without trust_remote_code")
        except Exception as e:
            print(f"⚠️ Loading without trust_remote_code failed: {e}")
            MODEL = SentenceTransformer('hkunlp/instructor-xl', trust_remote_code=True)
            print("✅ Loaded with trust_remote_code")
        
        # Move to GPU if available
        if torch.cuda.is_available():
            print(f"🖥️  Moving model to GPU: {torch.cuda.get_device_name(0)}")
            MODEL.to('cuda')
            
            # Pre-compile CUDA kernels with dummy encode
            print("🔥 Pre-compiling CUDA kernels...")
            try:
                # Do a real encode to trigger kernel compilation
                dummy_texts = [
                    ["Represent the sentence:", "warmup test"],
                    ["Represent the sentence:", "hello world"]
                ]
                _ = MODEL.encode(dummy_texts, convert_to_tensor=False)
                print("✅ CUDA kernels pre-compiled")
            except Exception as e:
                print(f"⚠️  Warmup failed: {e}")
        else:
            print("⚠️  No GPU available, using CPU")
            
        load_time = time.time() - start
        print(f"✅ Model loaded and cached in {load_time:.2f}s")
    
    return MODEL

@app.function(
    image=image,
    gpu="A10G",
    volumes={"/root/.cache/huggingface": volume},
    scaledown_window=600,
    enable_memory_snapshot=True,  # Re-enabled - Modal fixed the bug
    max_containers=10,  # Concurrency guard-rail
    # min_containers=1,  # Uncomment to keep 1 container always warm (zero cold boots)
)
@modal.fastapi_endpoint(method="POST")
def generate_embedding(request: EmbeddingRequest) -> Dict:
    """Generate embedding for a single text"""
    return _generate_embedding(request.text)

def _generate_embedding(text: str) -> Dict:
    """Internal function to generate embedding"""
    print(f"🔄 Generating embedding for: {text[:50]}...")
    start = time.time()
    
    try:
        # Get cached model (fast for warm requests)
        model_start = time.time()
        model = get_model()
        model_load_time = time.time() - model_start
        
        # Check GPU status
        gpu_available = torch.cuda.is_available()
        
        # Generate embedding
        embed_start = time.time()
        
        # Handle empty instruction case
        if INSTRUCTION:
            # Use instructor format with instruction
            formatted_input = [[INSTRUCTION, text]]
            print(f"   Using instructor format with: '{INSTRUCTION}'")
        else:
            # Use simple text format when no instruction
            formatted_input = text
            print(f"   Using simple text format (no instruction)")
        
        try:
            embedding = model.encode(
                formatted_input,
                normalize_embeddings=True,
                convert_to_tensor=False,
                show_progress_bar=False
            )
            
            # Handle output based on format
            if INSTRUCTION and isinstance(embedding, list):
                embedding = embedding[0]
            
            print(f"   ✅ Embedding generated successfully")
        except Exception as e:
            print(f"   ❌ Embedding failed: {e}")
            raise e
        
        embed_time = time.time() - embed_start
        total_time = time.time() - start
        
        print(f"✅ Embedding generated in {embed_time:.2f}s (total: {total_time:.2f}s)")
        
        # Debug: Check embedding
        print(f"   Embedding type: {type(embedding)}")
        print(f"   Embedding shape: {embedding.shape if hasattr(embedding, 'shape') else 'N/A'}")
        
        # Convert to list properly
        if isinstance(embedding, np.ndarray):
            embedding_list = embedding.tolist()
        elif hasattr(embedding, 'cpu'):  # PyTorch tensor
            embedding_list = embedding.cpu().numpy().tolist()
        else:
            embedding_list = list(embedding)
        
        print(f"   First 5 values: {embedding_list[:5] if len(embedding_list) > 5 else embedding_list}")
        print(f"   Valid embedding: {isinstance(embedding_list[0], (int, float)) if embedding_list else False}")
        
        return {
            "embedding": embedding_list,
            "dimension": len(embedding),
            "model": "instructor-xl",
            "gpu_available": gpu_available,
            "inference_time_ms": round(embed_time * 1000, 2),
            "total_time_ms": round(total_time * 1000, 2),
            "model_load_time_ms": round(model_load_time * 1000, 2)
        }
        
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return {
            "error": str(e),
            "embedding": None,
            "dimension": 0,
            "model": "instructor-xl",
            "gpu_available": False,
            "inference_time_ms": 0
        }

@app.function(
    image=image,
    gpu="A10G",
    volumes={"/root/.cache/huggingface": volume},
    scaledown_window=600,
)
@modal.fastapi_endpoint(method="GET")
def health_check() -> dict:
    """Simple health check"""
    try:
        gpu_available = torch.cuda.is_available()
        return {
            "status": "healthy",
            "model": "instructor-xl",
            "gpu_available": gpu_available,
            "gpu_name": torch.cuda.get_device_name(0) if gpu_available else None,
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda if gpu_available else None,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.function(
    image=image,
    gpu="A10G",
    volumes={"/root/.cache/huggingface": volume},
    scaledown_window=600,
    enable_memory_snapshot=True,
)
def test_embedding(text: str = "test embedding generation") -> None:
    """Test function for modal run"""
    result = _generate_embedding(text)
    print(f"\n📊 Test Results:")
    print(f"   Embedding dimension: {result.get('dimension', 0)}")
    print(f"   GPU available: {result.get('gpu_available', False)}")
    print(f"   Inference time: {result.get('inference_time_ms', 0)}ms")
    print(f"   Total time: {result.get('total_time_ms', 0)}ms")
    print(f"   Model load time: {result.get('model_load_time_ms', 0)}ms")

if __name__ == "__main__":
    print("Deploy this with: modal deploy scripts/modal_web_endpoint_simple.py")
    print("\nAfter deployment, test with:")
    print("  modal run scripts/modal_web_endpoint_simple.py::test_embedding --text 'your text here'")
```

### modal_embeddings_simple.py
Location: `/scripts/modal_embeddings_simple.py`

```python
"""
Simple Modal function for testing embeddings
"""

import modal
import time

# Create the Modal app
app = modal.App("test-embeddings-simple")

# Simple image with minimal dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "numpy",
        "torch",
        "sentence-transformers",
    )
)

@app.function(image=image, gpu="T4")
def test_simple_embedding(text: str = "test"):
    """Simple test function"""
    import torch
    from sentence_transformers import SentenceTransformer
    
    print(f"GPU available: {torch.cuda.is_available()}")
    
    # Load a small model for testing
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Generate embedding
    start = time.time()
    embedding = model.encode(text)
    duration = time.time() - start
    
    print(f"Generated embedding in {duration:.2f}s")
    print(f"Embedding shape: {embedding.shape}")
    print(f"First 5 values: {embedding[:5]}")
    
    return {
        "text": text,
        "embedding_size": len(embedding),
        "duration_seconds": duration,
        "gpu_available": torch.cuda.is_available()
    }

if __name__ == "__main__":
    print("Run with: modal run scripts/modal_embeddings_simple.py::test_simple_embedding --text 'your text'")
```

---

## Testing Scripts

### test_data_quality.py
Location: `/scripts/test_data_quality.py`

```python
#!/usr/bin/env python3
"""
Data Quality Test Suite for PodInsight

Tests the production API to ensure data quality standards are met.
Focuses on search result quality, response times, and error handling.
"""

import requests
import time
import json
import statistics
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from urllib.parse import urljoin

# Configuration
VERCEL_BASE = os.getenv("VERCEL_URL", "https://podinsight-api.vercel.app")
TIMEOUT = 15  # seconds

# Test result tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0
}

def log_test(test_name: str, passed: bool, message: str = "", warning: bool = False):
    """Log test result"""
    if warning:
        test_results["warnings"] += 1
        print(f"   ⚠️  {message}")
    elif passed:
        test_results["passed"] += 1
        print(f"   ✅ {message}")
    else:
        test_results["failed"] += 1
        print(f"   ❌ {message}")

def test_health_endpoint():
    """Test the health check endpoint"""
    print("🏥 Testing health endpoint...")
    
    try:
        start = time.time()
        response = requests.get(f"{VERCEL_BASE}/api/health", timeout=TIMEOUT)
        latency = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"Non-200 status: {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Unhealthy status: {data.get('status')}"
        
        log_test("health", True, f"Health OK ({latency:.0f}ms)")
        return True
        
    except Exception as e:
        log_test("health", False, f"Health check failed: {str(e)}")
        return False

def validate_search_result(result: Dict[str, Any], query: str) -> List[str]:
    """Validate a single search result for data quality"""
    issues = []
    
    # Required fields
    required_fields = [
        "episode_id", "podcast_name", "episode_title", 
        "published_at", "similarity_score", "excerpt"
    ]
    
    for field in required_fields:
        if field not in result:
            issues.append(f"Missing required field: {field}")
        elif result[field] is None:
            issues.append(f"Null value for required field: {field}")
    
    # Validate similarity score
    if "similarity_score" in result:
        score = result["similarity_score"]
        if not isinstance(score, (int, float)):
            issues.append(f"Invalid similarity_score type: {type(score)}")
        elif not 0 <= score <= 1:
            issues.append(f"Similarity score out of range: {score}")
    
    # Validate excerpt
    if "excerpt" in result and result["excerpt"]:
        excerpt = result["excerpt"]
        if len(excerpt) < 10:
            issues.append(f"Excerpt too short: {len(excerpt)} chars")
        if len(excerpt) > 10000:
            issues.append(f"Excerpt too long: {len(excerpt)} chars")
    
    # Validate episode_id format
    if "episode_id" in result and result["episode_id"]:
        episode_id = result["episode_id"]
        if not isinstance(episode_id, str):
            issues.append(f"Invalid episode_id type: {type(episode_id)}")
    
    return issues

def test_known_queries():
    """Test queries that should return meaningful results"""
    print("🔍 Testing known high-recall queries...")
    
    # High-recall queries that should find content
    test_queries = [
        "openai",
        "sequoia capital", 
        "founder burnout",
        "artificial intelligence",
        "venture capital"
    ]
    
    all_passed = True
    
    for query in test_queries:
        print(f"   Testing: '{query}'")
        
        try:
            start = time.time()
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json={"query": query, "limit": 5},
                timeout=15
            )
            latency = (time.time() - start) * 1000
            
            # Basic response validation
            assert response.status_code == 200, f"Non-200 status: {response.status_code}"
            
            data = response.json()
            results = data.get("results", [])
            
            # Check for results
            assert len(results) >= 1, f"No results for high-recall query '{query}'"
            
            # Validate each result
            total_issues = []
            for i, result in enumerate(results):
                issues = validate_search_result(result, query)
                if issues:
                    total_issues.extend([f"Result {i+1}: {issue}" for issue in issues])
            
            if total_issues:
                print(f"      ❌ Data quality issues:")
                for issue in total_issues[:5]:  # Show first 5 issues
                    print(f"         - {issue}")
                all_passed = False
            else:
                print(f"      ✅ {len(results)} valid results ({latency:.0f}ms)")
                
        except AssertionError as e:
            print(f"      ❌ {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"      ❌ Exception: {str(e)}")
            all_passed = False
    
    log_test("known_queries", all_passed, 
             "Known queries passed" if all_passed else "Known queries failed")
    return all_passed

def test_warm_latency():
    """Test response times for warm requests"""
    print("⚡ Testing warm request latency...")
    
    # Warm up with one request
    try:
        requests.post(
            f"{VERCEL_BASE}/api/search",
            json={"query": "test warmup", "limit": 3},
            timeout=30
        )
    except:
        pass  # Ignore warmup errors
    
    # Test actual latencies
    latencies = []
    query = "artificial intelligence"
    
    for i in range(3):
        try:
            start = time.time()
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json={"query": query, "limit": 5},
                timeout=TIMEOUT
            )
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                latencies.append(latency)
                
        except Exception as e:
            print(f"      ⚠️  Request {i+1} failed: {str(e)}")
    
    if latencies:
        median = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
        
        print(f"   Latencies: {[f'{l:.0f}ms' for l in latencies]}")
        print(f"   Median: {median:.0f}ms, P95: {p95:.0f}ms")
        
        # Pass if median < 1s and P95 < 2s
        passed = median < 1000 and p95 < 2000
        log_test("warm_latency", passed, 
                 "Warm latency acceptable" if passed else f"Warm latency too high")
        return passed
    else:
        log_test("warm_latency", False, "All latency tests failed")
        return False

def test_bad_inputs():
    """Test handling of invalid inputs"""
    print("🛡️  Testing bad input handling...")
    
    bad_inputs = [
        {"query": "", "expected_status": 422, "name": "Empty string"},
        {"query": "a", "expected_status": 200, "name": "Single character"},
        {"query": "🚀" * 100, "expected_status": 200, "name": "Long emoji string"},
        {"query": "x" * 501, "expected_status": 422, "name": "Very long string"},
    ]
    
    all_passed = True
    
    for test_case in bad_inputs:
        try:
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json={"query": test_case["query"], "limit": 5},
                timeout=TIMEOUT
            )
            
            if response.status_code == test_case["expected_status"]:
                print(f"   ✅ {test_case['name']}: {response.status_code}")
            else:
                print(f"   ❌ {test_case['name']}: got {response.status_code}, expected {test_case['expected_status']}")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ {test_case['name']}: Exception {str(e)}")
            all_passed = False
    
    log_test("bad_inputs", all_passed, 
             "Bad input handling passed" if all_passed else "Bad input handling failed")
    return all_passed

def test_concurrent_load():
    """Test handling of concurrent requests"""
    print("🔄 Testing concurrent load...")
    
    queries = [
        "machine learning",
        "startup funding", 
        "product market fit",
        "venture capital",
        "artificial intelligence",
        "founder advice",
        "growth strategy",
        "tech innovation",
        "market analysis", 
        "investment thesis"
    ]
    
    success_count = 0
    error_count = 0
    latencies = []
    
    def make_request(query):
        try:
            start = time.time()
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json={"query": query, "limit": 3},
                timeout=30
            )
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                return True, latency
            else:
                return False, latency
                
        except Exception as e:
            return False, 30000  # Timeout
    
    # Execute concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_query = {executor.submit(make_request, q): q for q in queries}
        
        for future in as_completed(future_to_query):
            query = future_to_query[future]
            success, latency = future.result()
            
            if success:
                success_count += 1
                latencies.append(latency)
            else:
                error_count += 1
    
    success_rate = success_count / len(queries)
    max_latency = max(latencies) if latencies else 0
    
    print(f"   Success rate: {success_count}/{len(queries)}")
    print(f"   Max latency: {max_latency:.0f}ms")
    
    # Pass if >80% success rate and max latency < 10s
    passed = success_rate >= 0.8 and max_latency < 10000
    log_test("concurrent_load", passed,
             "Concurrent load handled" if passed else "Concurrent load issues")
    return passed

def main():
    """Run all data quality tests"""
    print("🧪 Data Quality Test Suite")
    print(f"Testing: {VERCEL_BASE}")
    print(f"Started: {datetime.now()}")
    print("=" * 60)
    print()
    
    # Run tests
    tests = [
        ("Health Check", test_health_endpoint),
        ("Known Queries", test_known_queries),
        ("Warm Latency", test_warm_latency),
        ("Bad Inputs", test_bad_inputs),
        ("Concurrent Load", test_concurrent_load),
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
        print()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for p in results.values() if p)
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("✨ All data quality tests passed!")
        return 0
    else:
        print("💥 Data quality tests FAILED - system not ready for production")
        return 1

if __name__ == "__main__":
    exit(main())
```

### test_e2e_production.py
Location: `/scripts/test_e2e_production.py`

```python
#!/usr/bin/env python3
"""
End-to-End Production Tests for PodInsight

Comprehensive test suite that validates the entire search pipeline
from query to results, including edge cases and performance.
"""

import requests
import time
import json
import statistics
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os

# Configuration
API_BASE = os.getenv("API_URL", "https://podinsight-api.vercel.app")
TIMEOUT = 30  # seconds for each request

class TestResult:
    """Track test results"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.duration = 0
        self.details = {}

class E2ETestSuite:
    def __init__(self):
        self.results: List[TestResult] = []
        self.api_base = API_BASE
        
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️ "
        }.get(level, "")
        print(f"[{timestamp}] {prefix} {message}")
    
    def add_result(self, result: TestResult):
        """Add test result"""
        self.results.append(result)
        status = "✅ PASS" if result.passed else "❌ FAIL"
        self.log(f"{status} {result.name} ({result.duration:.2f}s)", 
                 "SUCCESS" if result.passed else "ERROR")
        if result.message:
            print(f"         {result.message}")
    
    def test_health_check(self) -> TestResult:
        """Test 1: Basic health check"""
        result = TestResult("Health Check")
        start = time.time()
        
        try:
            response = requests.get(f"{self.api_base}/api/health", timeout=10)
            result.duration = time.time() - start
            
            assert response.status_code == 200, f"Status {response.status_code}"
            data = response.json()
            assert data.get("status") == "healthy", "Not healthy"
            
            result.passed = True
            result.message = f"API healthy, version: {data.get('version', 'unknown')}"
            result.details = data
            
        except Exception as e:
            result.duration = time.time() - start
            result.message = str(e)
            
        return result
    
    def test_basic_search(self) -> TestResult:
        """Test 2: Basic search functionality"""
        result = TestResult("Basic Search")
        start = time.time()
        
        try:
            # Test a simple query
            response = requests.post(
                f"{self.api_base}/api/search",
                json={"query": "artificial intelligence", "limit": 5},
                timeout=TIMEOUT
            )
            result.duration = time.time() - start
            
            assert response.status_code == 200, f"Status {response.status_code}"
            data = response.json()
            
            # Validate response structure
            assert "results" in data, "Missing results field"
            assert "total_results" in data, "Missing total_results"
            assert "search_method" in data, "Missing search_method"
            
            results = data["results"]
            assert isinstance(results, list), "Results not a list"
            
            if len(results) > 0:
                # Validate first result structure
                first = results[0]
                required_fields = [
                    "episode_id", "podcast_name", "episode_title",
                    "similarity_score", "excerpt"
                ]
                for field in required_fields:
                    assert field in first, f"Missing field: {field}"
                
                result.passed = True
                result.message = f"Found {len(results)} results via {data['search_method']}"
            else:
                result.passed = False
                result.message = "No results returned for test query"
                
            result.details = {"count": len(results), "method": data.get("search_method")}
            
        except Exception as e:
            result.duration = time.time() - start
            result.message = str(e)
            
        return result
    
    def test_pagination(self) -> TestResult:
        """Test 3: Pagination functionality"""
        result = TestResult("Pagination")
        start = time.time()
        
        try:
            # Get first page
            response1 = requests.post(
                f"{self.api_base}/api/search",
                json={"query": "startup", "limit": 5, "offset": 0},
                timeout=TIMEOUT
            )
            data1 = response1.json()
            
            # Get second page
            response2 = requests.post(
                f"{self.api_base}/api/search",
                json={"query": "startup", "limit": 5, "offset": 5},
                timeout=TIMEOUT
            )
            data2 = response2.json()
            
            result.duration = time.time() - start
            
            # Verify different results
            if data1["results"] and data2["results"]:
                ids1 = {r["episode_id"] for r in data1["results"]}
                ids2 = {r["episode_id"] for r in data2["results"]}
                
                overlap = ids1.intersection(ids2)
                assert len(overlap) == 0, f"Pages overlap: {len(overlap)} common results"
                
                result.passed = True
                result.message = "Pagination working correctly"
            else:
                result.passed = False
                result.message = "Insufficient results to test pagination"
                
        except Exception as e:
            result.duration = time.time() - start
            result.message = str(e)
            
        return result
    
    def test_relevance_ranking(self) -> TestResult:
        """Test 4: Relevance ranking"""
        result = TestResult("Relevance Ranking")
        start = time.time()
        
        try:
            response = requests.post(
                f"{self.api_base}/api/search",
                json={"query": "openai gpt", "limit": 10},
                timeout=TIMEOUT
            )
            data = response.json()
            results = data.get("results", [])
            
            result.duration = time.time() - start
            
            if len(results) >= 2:
                # Check that scores are descending
                scores = [r["similarity_score"] for r in results]
                
                is_descending = all(scores[i] >= scores[i+1] 
                                  for i in range(len(scores)-1))
                
                assert is_descending, "Results not sorted by relevance"
                
                # Check score range
                assert all(0 <= s <= 1 for s in scores), "Scores out of range"
                
                result.passed = True
                result.message = f"Scores properly ranked: {scores[0]:.3f} to {scores[-1]:.3f}"
            else:
                result.passed = False
                result.message = "Insufficient results to test ranking"
                
        except Exception as e:
            result.duration = time.time() - start
            result.message = str(e)
            
        return result
    
    def test_special_characters(self) -> TestResult:
        """Test 5: Special character handling"""
        result = TestResult("Special Characters")
        start = time.time()
        
        test_queries = [
            "a16z",  # Alphanumeric
            "founder's journey",  # Apostrophe
            "series-a funding",  # Hyphen
            "AI/ML engineer",  # Slash
        ]
        
        all_passed = True
        
        try:
            for query in test_queries:
                response = requests.post(
                    f"{self.api_base}/api/search",
                    json={"query": query, "limit": 3},
                    timeout=TIMEOUT
                )
                
                if response.status_code != 200:
                    all_passed = False
                    result.message = f"Failed on '{query}': status {response.status_code}"
                    break
                    
            result.duration = time.time() - start
            
            if all_passed:
                result.passed = True
                result.message = "All special character queries handled correctly"
            
        except Exception as e:
            result.duration = time.time() - start
            result.message = str(e)
            
        return result
    
    def test_concurrent_requests(self) -> TestResult:
        """Test 6: Concurrent request handling"""
        result = TestResult("Concurrent Requests")
        start = time.time()
        
        queries = [
            "machine learning", "blockchain", "cloud computing",
            "cybersecurity", "data science", "devops",
            "microservices", "kubernetes", "react", "python"
        ]
        
        def search(query):
            try:
                response = requests.post(
                    f"{self.api_base}/api/search",
                    json={"query": query, "limit": 3},
                    timeout=TIMEOUT
                )
                return response.status_code == 200, response.elapsed.total_seconds()
            except:
                return False, TIMEOUT
        
        try:
            successes = 0
            latencies = []
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(search, q): q for q in queries}
                
                for future in as_completed(futures):
                    success, latency = future.result()
                    if success:
                        successes += 1
                        latencies.append(latency)
            
            result.duration = time.time() - start
            
            success_rate = successes / len(queries)
            avg_latency = statistics.mean(latencies) if latencies else 0
            
            assert success_rate >= 0.9, f"Low success rate: {success_rate:.1%}"
            
            result.passed = True
            result.message = f"Success rate: {success_rate:.0%}, Avg latency: {avg_latency:.2f}s"
            result.details = {"success_rate": success_rate, "avg_latency": avg_latency}
            
        except Exception as e:
            result.duration = time.time() - start
            result.message = str(e)
            
        return result
    
    def test_error_handling(self) -> TestResult:
        """Test 7: Error handling"""
        result = TestResult("Error Handling")
        start = time.time()
        
        error_cases = [
            {"payload": {}, "name": "Missing query"},
            {"payload": {"query": ""}, "name": "Empty query"},
            {"payload": {"query": "test", "limit": -1}, "name": "Negative limit"},
            {"payload": {"query": "test", "limit": 1000}, "name": "Excessive limit"},
            {"payload": {"query": "x" * 501}, "name": "Query too long"},
        ]
        
        all_passed = True
        
        try:
            for case in error_cases:
                response = requests.post(
                    f"{self.api_base}/api/search",
                    json=case["payload"],
                    timeout=TIMEOUT
                )
                
                # Should return 4xx error
                if not (400 <= response.status_code < 500):
                    all_passed = False
                    result.message = f"{case['name']}: Expected 4xx, got {response.status_code}"
                    break
            
            result.duration = time.time() - start
            
            if all_passed:
                result.passed = True
                result.message = "All error cases handled correctly"
                
        except Exception as e:
            result.duration = time.time() - start
            result.message = str(e)
            
        return result
    
    def test_response_times(self) -> TestResult:
        """Test 8: Response time performance"""
        result = TestResult("Response Times")
        start = time.time()
        
        # Warm up
        requests.post(
            f"{self.api_base}/api/search",
            json={"query": "warmup", "limit": 1},
            timeout=TIMEOUT
        )
        
        queries = [
            "ai", "machine learning", "startup funding",
            "product development", "venture capital"
        ]
        
        latencies = []
        
        try:
            for query in queries:
                req_start = time.time()
                response = requests.post(
                    f"{self.api_base}/api/search",
                    json={"query": query, "limit": 5},
                    timeout=TIMEOUT
                )
                latency = time.time() - req_start
                
                if response.status_code == 200:
                    latencies.append(latency)
            
            result.duration = time.time() - start
            
            if latencies:
                p50 = statistics.median(latencies)
                p95 = sorted(latencies)[int(len(latencies) * 0.95)]
                
                # Performance thresholds
                assert p50 < 1.0, f"P50 too high: {p50:.2f}s"
                assert p95 < 2.0, f"P95 too high: {p95:.2f}s"
                
                result.passed = True
                result.message = f"P50: {p50:.2f}s, P95: {p95:.2f}s"
                result.details = {"p50": p50, "p95": p95, "samples": len(latencies)}
            else:
                result.message = "No successful requests to measure"
                
        except Exception as e:
            result.duration = time.time() - start
            result.message = str(e)
            
        return result
    
    def test_metadata_quality(self) -> TestResult:
        """Test 9: Metadata quality"""
        result = TestResult("Metadata Quality")
        start = time.time()
        
        try:
            response = requests.post(
                f"{self.api_base}/api/search",
                json={"query": "technology trends", "limit": 10},
                timeout=TIMEOUT
            )
            data = response.json()
            results = data.get("results", [])
            
            result.duration = time.time() - start
            
            if results:
                issues = []
                
                for i, res in enumerate(results):
                    # Check for placeholder data
                    if "Unknown" in res.get("podcast_name", ""):
                        issues.append(f"Result {i}: Unknown podcast name")
                    if "Episode" in res.get("episode_title", "") and "Unknown" in res.get("episode_title", ""):
                        issues.append(f"Result {i}: Placeholder episode title")
                    if not res.get("published_at"):
                        issues.append(f"Result {i}: Missing published date")
                    if res.get("excerpt", "").strip() == "":
                        issues.append(f"Result {i}: Empty excerpt")
                
                if not issues:
                    result.passed = True
                    result.message = "All metadata complete and valid"
                else:
                    result.passed = False
                    result.message = f"Found {len(issues)} metadata issues"
                    result.details = {"issues": issues[:5]}  # First 5 issues
            else:
                result.message = "No results to validate"
                
        except Exception as e:
            result.duration = time.time() - start
            result.message = str(e)
            
        return result
    
    def test_search_methods(self) -> TestResult:
        """Test 10: Different search methods"""
        result = TestResult("Search Methods")
        start = time.time()
        
        # Queries likely to trigger different search methods
        test_cases = [
            {"query": "artificial intelligence", "expected": "vector_768d"},
            {"query": "the", "expected": ["text", "none"]},  # Common word might fail vector
        ]
        
        methods_used = set()
        
        try:
            for case in test_cases:
                response = requests.post(
                    f"{self.api_base}/api/search",
                    json={"query": case["query"], "limit": 5},
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    data = response.json()
                    method = data.get("search_method", "unknown")
                    methods_used.add(method)
            
            result.duration = time.time() - start
            
            # We should see at least vector search working
            if "vector_768d" in methods_used:
                result.passed = True
                result.message = f"Search methods tested: {', '.join(methods_used)}"
            else:
                result.passed = False
                result.message = "Vector search not working"
                
            result.details = {"methods": list(methods_used)}
            
        except Exception as e:
            result.duration = time.time() - start
            result.message = str(e)
            
        return result
    
    def run_all_tests(self):
        """Run all E2E tests"""
        self.log("Starting E2E Test Suite", "INFO")
        self.log(f"API Base: {self.api_base}", "INFO")
        print("=" * 80)
        
        # Define all tests
        tests = [
            self.test_health_check,
            self.test_basic_search,
            self.test_pagination,
            self.test_relevance_ranking,
            self.test_special_characters,
            self.test_concurrent_requests,
            self.test_error_handling,
            self.test_response_times,
            self.test_metadata_quality,
            self.test_search_methods,
        ]
        
        # Run each test
        for test_func in tests:
            print()  # Blank line between tests
            try:
                result = test_func()
                self.add_result(result)
            except Exception as e:
                # Catch any unexpected errors
                result = TestResult(test_func.__name__.replace("test_", "").title())
                result.message = f"Unexpected error: {str(e)}"
                self.add_result(result)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("E2E TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        # Individual results
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} {result.name}")
            if not result.passed and result.message:
                print(f"     ↳ {result.message}")
        
        # Overall stats
        print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
        total_time = sum(r.duration for r in self.results)
        print(f"Duration: {total_time:.1f}s")
        
        # Performance summary
        response_times = next((r for r in self.results if r.name == "Response Times"), None)
        if response_times and response_times.details:
            print(f"\nPerformance:")
            print(f"  P50 latency: {response_times.details.get('p50', 0):.2f}s")
            print(f"  P95 latency: {response_times.details.get('p95', 0):.2f}s")
        
        # Exit code
        if passed == total:
            print("\n✨ All E2E tests passed! System is production ready.")
            return 0
        else:
            print(f"\n💥 {total - passed} tests failed. System needs attention.")
            return 1

def main():
    """Run the E2E test suite"""
    suite = E2ETestSuite()
    return suite.run_all_tests()

if __name__ == "__main__":
    exit(main())
```

### debug_vector_search.py
Location: `/scripts/debug_vector_search.py`

```python
#!/usr/bin/env python3
"""
Debug script for MongoDB vector search issues
"""

import os
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import aiohttp
import numpy as np

# Load environment variables
load_dotenv()

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
MODAL_URL = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

async def main():
    """Debug vector search functionality"""
    print("🔍 Debugging Vector Search...")
    print("=" * 60)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.podinsight
    chunks_collection = db.transcript_chunks_768d
    
    # 1. Check if chunks have embeddings
    print("\n1. Checking if chunks have embeddings:")
    sample_chunk = await chunks_collection.find_one({})
    if sample_chunk and "embedding_768d" in sample_chunk:
        embedding = sample_chunk["embedding_768d"]
        print(f"  ✅ Chunks have embeddings (length: {len(embedding)})")
        print(f"  First 10 values: {embedding[:10]}")
        
        # Check embedding statistics
        embedding_array = np.array(embedding)
        print(f"  Min: {embedding_array.min()}, Max: {embedding_array.max()}")
        print(f"  Mean: {embedding_array.mean():.4f}")
        print(f"  Norm: {np.linalg.norm(embedding_array):.4f}")
    else:
        print("  ❌ No embeddings found in chunks!")
        return
    
    # 2. Test Modal endpoint
    print("\n2. Generating test embedding from Modal:")
    test_query = "openai"
    
    async with aiohttp.ClientSession() as session:
        payload = {"text": test_query}
        async with session.post(MODAL_URL, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                test_embedding = data.get("embedding", [])
                print(f"  ✅ Got embedding (length: {len(test_embedding)})")
                print(f"  First 10 values: {test_embedding[:10]}")
                
                # Check norm
                test_array = np.array(test_embedding)
                print(f"  Norm: {np.linalg.norm(test_array):.4f}")
            else:
                print(f"  ❌ Modal error: {response.status}")
                return
    
    # 3. Check if any chunks contain our test query
    print(f"\n3. Checking if any chunks contain '{test_query}' text:")
    text_search_cursor = chunks_collection.find(
        {"text": {"$regex": test_query, "$options": "i"}}
    ).limit(5)
    
    text_matches = await text_search_cursor.to_list(None)
    print(f"  Found {len(text_matches)} chunks containing '{test_query}'")
    
    if text_matches:
        sample = text_matches[0]
        print(f"  Sample episode_id: {sample.get('episode_id')}")
        print(f"  Sample text: {sample.get('text', '')[:100]}...")
        
        # Check if this chunk has an embedding
        if "embedding_768d" in sample:
            print(f"  ✅ This chunk has embedding (length: {len(sample['embedding_768d'])})")
            
            # Calculate similarity manually
            chunk_embedding = np.array(sample["embedding_768d"])
            test_embedding_array = np.array(test_embedding)
            
            # Cosine similarity
            similarity = np.dot(chunk_embedding, test_embedding_array) / (
                np.linalg.norm(chunk_embedding) * np.linalg.norm(test_embedding_array)
            )
            print(f"  Manual similarity score: {similarity:.4f}")
    
    # 4. Check MongoDB indexes
    print("\n4. Checking MongoDB vector index:")
    indexes = await chunks_collection.list_indexes().to_list(None)
    for idx in indexes:
        print(f"  Index: {idx.get('name')}")
    
    # 5. Try a manual vector search
    print("\n5. Attempting manual vector search:")
    
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": test_embedding,
                "numCandidates": 100,
                "limit": 5
            }
        },
        {
            "$limit": 5
        },
        {
            "$addFields": {
                "score": {"$meta": "vectorSearchScore"}
            }
        },
        {
            "$project": {
                "text": {"$substr": ["$text", 0, 100]},
                "score": 1,
                "episode_id": 1
            }
        }
    ]
    
    try:
        cursor = chunks_collection.aggregate(pipeline)
        results = await cursor.to_list(None)
        
        print(f"  Found {len(results)} results")
        for i, result in enumerate(results, 1):
            print(f"  {i}. Score: {result.get('score', 0):.4f}")
            print(f"     Text: {result.get('text', '')}...")
            
    except Exception as e:
        print(f"  ❌ Vector search error: {e}")
        print(f"     Error type: {type(e).__name__}")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### check_orphan_episodes.py
Location: `/scripts/check_orphan_episodes.py`

```python
#!/usr/bin/env python3
"""
Check for orphan episodes - chunks without corresponding metadata
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_orphans():
    """Find chunks that don't have corresponding episode metadata"""
    
    # MongoDB connection
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("❌ MONGODB_URI not set")
        return
    
    print("🔍 Checking for orphan episodes...")
    print("=" * 60)
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client.podinsight
    
    # Get all unique episode IDs from chunks
    print("\n1. Getting unique episode IDs from chunks...")
    pipeline = [
        {"$group": {"_id": "$episode_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    cursor = db.transcript_chunks_768d.aggregate(pipeline)
    chunk_episodes = await cursor.to_list(None)
    
    chunk_episode_ids = {doc["_id"] for doc in chunk_episodes}
    chunk_counts = {doc["_id"]: doc["count"] for doc in chunk_episodes}
    
    print(f"   Found {len(chunk_episode_ids)} unique episodes in chunks")
    print(f"   Total chunks: {sum(chunk_counts.values())}")
    
    # Get all episode metadata GUIDs
    print("\n2. Getting episode metadata GUIDs...")
    cursor = db.episode_metadata.find({}, {"guid": 1})
    metadata_docs = await cursor.to_list(None)
    metadata_guids = {doc["guid"] for doc in metadata_docs}
    
    print(f"   Found {len(metadata_guids)} episodes with metadata")
    
    # Find orphans
    print("\n3. Finding orphan episodes...")
    orphan_ids = chunk_episode_ids - metadata_guids
    
    if orphan_ids:
        print(f"   ❌ Found {len(orphan_ids)} orphan episodes!")
        
        # Show details of orphans
        print("\n   Orphan Episodes (chunks without metadata):")
        orphan_chunk_total = 0
        
        # Sort by chunk count
        sorted_orphans = sorted(orphan_ids, key=lambda x: chunk_counts.get(x, 0), reverse=True)
        
        for i, episode_id in enumerate(sorted_orphans[:10], 1):
            chunk_count = chunk_counts.get(episode_id, 0)
            orphan_chunk_total += chunk_count
            
            # Get sample chunk to see feed_slug
            sample_chunk = await db.transcript_chunks_768d.find_one({"episode_id": episode_id})
            feed_slug = sample_chunk.get("feed_slug", "unknown") if sample_chunk else "unknown"
            
            print(f"   {i}. {episode_id}")
            print(f"      Feed: {feed_slug}")
            print(f"      Chunks: {chunk_count}")
        
        if len(orphan_ids) > 10:
            print(f"   ... and {len(orphan_ids) - 10} more orphan episodes")
        
        total_orphan_chunks = sum(chunk_counts.get(eid, 0) for eid in orphan_ids)
        print(f"\n   Total orphan chunks: {total_orphan_chunks}")
        print(f"   Percentage of chunks that are orphans: {total_orphan_chunks / sum(chunk_counts.values()) * 100:.1f}%")
    else:
        print("   ✅ No orphan episodes found! All chunks have metadata.")
    
    # Find metadata without chunks (less critical)
    print("\n4. Finding metadata without chunks...")
    metadata_without_chunks = metadata_guids - chunk_episode_ids
    
    if metadata_without_chunks:
        print(f"   Found {len(metadata_without_chunks)} episodes with metadata but no chunks")
        print("   (This is less critical - might be episodes that weren't chunked)")
    else:
        print("   ✅ All metadata episodes have corresponding chunks")
    
    # Summary statistics
    print("\n5. Summary Statistics:")
    print(f"   Total unique episodes in chunks: {len(chunk_episode_ids)}")
    print(f"   Total episodes with metadata: {len(metadata_guids)}")
    print(f"   Episodes with both chunks and metadata: {len(chunk_episode_ids & metadata_guids)}")
    print(f"   Coverage: {len(chunk_episode_ids & metadata_guids) / len(chunk_episode_ids) * 100:.1f}%")
    
    # Check data consistency
    print("\n6. Checking data consistency...")
    
    # Sample a few episodes that have both
    matched_episodes = list((chunk_episode_ids & metadata_guids))[:5]
    
    for episode_id in matched_episodes:
        # Get metadata
        metadata = await db.episode_metadata.find_one({"guid": episode_id})
        
        # Get a sample chunk
        chunk = await db.transcript_chunks_768d.find_one({"episode_id": episode_id})
        
        if metadata and chunk:
            # Check feed slug consistency
            chunk_feed = chunk.get("feed_slug", "")
            meta_feed = metadata.get("raw_entry_original_feed", {}).get("podcast_slug", "")
            
            if chunk_feed and meta_feed and chunk_feed != meta_feed:
                print(f"   ⚠️  Feed mismatch for {episode_id}:")
                print(f"      Chunk feed: {chunk_feed}")
                print(f"      Meta feed: {meta_feed}")
    
    print("\n✅ Orphan check complete!")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(check_orphans())
```

### test_embedding_instruction.py
Location: `/scripts/test_embedding_instruction.py`
**Created during debugging session**

```python
#!/usr/bin/env python3
"""
Test different embedding instructions to find the right match
"""

import asyncio
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MODAL_URL = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

async def generate_embedding(text: str, instruction: str = None) -> list:
    """Generate embedding with specific instruction"""
    async with aiohttp.ClientSession() as session:
        # If instruction is provided, format as instructor model expects
        if instruction:
            payload = {"text": f"{instruction} {text}"}
        else:
            payload = {"text": text}
        
        async with session.post(MODAL_URL, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("embedding", [])
    return None

async def test_instructions():
    """Test different instruction formats"""
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client.podinsight
    
    # Test queries
    test_queries = [
        "openai",
        "artificial intelligence",
        "sequoia capital"
    ]
    
    # Different instruction formats to test
    instructions = [
        None,  # No instruction
        "Represent the venture capital podcast discussion:",
        "Represent this document for retrieval:",
        "Represent the document:",
        "",  # Empty instruction
        "query:",
        "passage:",
    ]
    
    print("Testing different embedding instructions...")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        for instruction in instructions:
            # Generate embedding
            if instruction is None:
                print(f"Testing: No instruction")
                embedding = await generate_embedding(query)
            else:
                print(f"Testing: '{instruction}'")
                embedding = await generate_embedding(query, instruction)
            
            if not embedding:
                print("  ❌ Failed to generate embedding")
                continue
            
            # Search with this embedding
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index_768d",
                        "path": "embedding_768d",
                        "queryVector": embedding,
                        "numCandidates": 100,
                        "limit": 5
                    }
                },
                {
                    "$limit": 5
                },
                {
                    "$addFields": {
                        "score": {"$meta": "vectorSearchScore"}
                    }
                },
                {
                    "$project": {
                        "text": {"$substr": ["$text", 0, 50]},
                        "score": 1
                    }
                }
            ]
            
            cursor = db.transcript_chunks_768d.aggregate(pipeline)
            results = await cursor.to_list(None)
            
            if results:
                print(f"  ✅ Found {len(results)} results")
                print(f"     Top score: {results[0]['score']:.4f}")
                print(f"     Text preview: {results[0]['text']}...")
            else:
                print(f"  ❌ No results found")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(test_instructions())
```

---

## Utility Scripts

### analyze_182_chunk_episode.py
Location: `/scripts/analyze_182_chunk_episode.py`

```python
#!/usr/bin/env python3
"""
Analyze the episode with 182 chunks to understand chunking patterns
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

async def analyze_large_episode():
    """Analyze episode with many chunks"""
    
    # MongoDB connection
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client.podinsight
    
    # The episode with 182 chunks
    episode_id = "0117f268-e54e-4cf8-b641-8987e1ca2a38"
    
    print(f"🔍 Analyzing episode: {episode_id}")
    print("=" * 80)
    
    # Get episode metadata
    print("\n1. Episode Metadata:")
    metadata = await db.episode_metadata.find_one({"guid": episode_id})
    
    if metadata:
        raw_feed = metadata.get("raw_entry_original_feed", {})
        print(f"   Podcast: {raw_feed.get('podcast_title', 'Unknown')}")
        print(f"   Episode: {raw_feed.get('episode_title', 'Unknown')}")
        print(f"   Published: {raw_feed.get('published_date_iso', 'Unknown')}")
        print(f"   Feed URL: {raw_feed.get('feed_url', 'Unknown')}")
        
        # Check segment count
        segment_count = metadata.get("segment_count", 0)
        print(f"   Segment count: {segment_count}")
    else:
        print("   ❌ No metadata found for this episode!")
    
    # Get all chunks for this episode
    print("\n2. Chunk Analysis:")
    cursor = db.transcript_chunks_768d.find(
        {"episode_id": episode_id}
    ).sort("chunk_index", 1)
    
    chunks = await cursor.to_list(None)
    print(f"   Total chunks: {len(chunks)}")
    
    if chunks:
        # Analyze chunk distribution
        chunk_lengths = [len(chunk.get("text", "")) for chunk in chunks]
        avg_length = sum(chunk_lengths) / len(chunk_lengths)
        
        print(f"   Average chunk length: {avg_length:.0f} characters")
        print(f"   Min chunk length: {min(chunk_lengths)} characters")
        print(f"   Max chunk length: {max(chunk_lengths)} characters")
        
        # Check time coverage
        first_chunk = chunks[0]
        last_chunk = chunks[-1]
        
        duration = last_chunk.get("end_time", 0) - first_chunk.get("start_time", 0)
        print(f"   Time coverage: {duration:.0f} seconds ({duration/60:.1f} minutes)")
        
        # Check for gaps or overlaps
        print("\n3. Checking chunk continuity:")
        gaps = []
        overlaps = []
        
        for i in range(1, len(chunks)):
            prev_end = chunks[i-1].get("end_time", 0)
            curr_start = chunks[i].get("start_time", 0)
            
            diff = curr_start - prev_end
            if diff > 0.1:  # Gap larger than 0.1 seconds
                gaps.append((i, diff))
            elif diff < -0.1:  # Overlap larger than 0.1 seconds
                overlaps.append((i, -diff))
        
        print(f"   Gaps found: {len(gaps)}")
        if gaps:
            print("   Largest gaps:")
            for idx, gap_size in sorted(gaps, key=lambda x: x[1], reverse=True)[:5]:
                print(f"     Between chunks {idx-1} and {idx}: {gap_size:.1f} seconds")
        
        print(f"   Overlaps found: {len(overlaps)}")
        
        # Sample some chunk texts
        print("\n4. Sample chunk texts:")
        sample_indices = [0, len(chunks)//4, len(chunks)//2, 3*len(chunks)//4, len(chunks)-1]
        
        for idx in sample_indices:
            if idx < len(chunks):
                chunk = chunks[idx]
                text_preview = chunk.get("text", "")[:100]
                print(f"\n   Chunk {idx} (index {chunk.get('chunk_index')}):")
                print(f"   Time: {chunk.get('start_time', 0):.1f}s - {chunk.get('end_time', 0):.1f}s")
                print(f"   Text: {text_preview}...")
        
        # Check embedding presence
        print("\n5. Embedding check:")
        chunks_with_embeddings = sum(1 for c in chunks if "embedding_768d" in c and c["embedding_768d"])
        print(f"   Chunks with embeddings: {chunks_with_embeddings}/{len(chunks)}")
        
        if chunks_with_embeddings < len(chunks):
            print("   ⚠️  Some chunks are missing embeddings!")
    
    # Check if this pattern is common
    print("\n6. Checking other episodes with many chunks:")
    pipeline = [
        {"$group": {"_id": "$episode_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 100}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    cursor = db.transcript_chunks_768d.aggregate(pipeline)
    high_chunk_episodes = await cursor.to_list(None)
    
    print(f"   Found {len(high_chunk_episodes)} episodes with 100+ chunks:")
    for doc in high_chunk_episodes:
        print(f"   - {doc['_id']}: {doc['count']} chunks")
    
    # Close connection
    client.close()
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    asyncio.run(analyze_large_episode())
```

### test_embedder_direct.py
Location: `/scripts/test_embedder_direct.py`

```python
#!/usr/bin/env python3
"""
Test the embedder directly without going through the API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.embeddings_768d_modal import get_embedder
import asyncio
import time

async def test_embedder():
    """Test embedding generation"""
    print("🧪 Testing Modal Embedder Directly")
    print("=" * 60)
    
    embedder = get_embedder()
    print(f"Modal URL: {embedder.modal_url}")
    
    # Test queries
    test_queries = [
        "artificial intelligence",
        "openai",
        "venture capital",
        "startup funding",
        "machine learning",
    ]
    
    print("\n1. Testing single embeddings:")
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        start = time.time()
        
        # Test synchronous method
        embedding = embedder.encode_query(query)
        
        if embedding:
            duration = time.time() - start
            print(f"   ✅ Success! Length: {len(embedding)}, Time: {duration:.2f}s")
            print(f"   First 5 values: {embedding[:5]}")
            
            # Check if normalized
            import math
            norm = math.sqrt(sum(x**2 for x in embedding))
            print(f"   Norm: {norm:.4f}")
        else:
            print(f"   ❌ Failed to generate embedding")
    
    # Test batch if available
    print("\n2. Testing batch embeddings:")
    try:
        batch_start = time.time()
        embeddings = await embedder.encode_batch(test_queries[:3])
        
        if embeddings:
            batch_duration = time.time() - batch_start
            print(f"   ✅ Batch success! Generated {len(embeddings)} embeddings")
            print(f"   Total time: {batch_duration:.2f}s ({batch_duration/len(embeddings):.2f}s per embedding)")
        else:
            print(f"   ❌ Batch endpoint not available or failed")
    except Exception as e:
        print(f"   ❌ Batch error: {e}")
    
    # Test error handling
    print("\n3. Testing error cases:")
    
    # Empty string
    empty_result = embedder.encode_query("")
    print(f"   Empty string: {'✅ Handled' if empty_result else '❌ Failed'}")
    
    # Very long text
    long_text = "test " * 1000
    long_result = embedder.encode_query(long_text)
    print(f"   Long text: {'✅ Handled' if long_result else '❌ Failed'}")
    
    print("\n✅ Embedder tests complete!")

if __name__ == "__main__":
    asyncio.run(test_embedder())
```

---

## Notes

1. **Critical File**: `modal_web_endpoint_simple.py` controls the embedding behavior. The `INSTRUCTION` variable was changed from `"Represent the venture capital podcast discussion:"` to `""` (empty string) on June 25, 2025.

2. **Virtual Environment**: Always activate with `source venv/bin/activate` before running scripts or deploying.

3. **Deployment Commands**:
   - API: `git push origin main` (auto-deploys via Vercel)
   - Modal: `modal deploy scripts/modal_web_endpoint_simple.py`

4. **Environment Variables**: Required in `.env` file for local development and in Vercel/Modal dashboards for production.

5. **Testing**: Run tests after any changes to verify system functionality.

This appendix contains all the code referenced in the main documentation. Each file is complete and can be copied directly.