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
        surrounding_chunks = list(vector_handler.db.transcript_chunks_768d.find({
            "episode_id": chunk["episode_id"],
            "start_time": {"$gte": start_window, "$lte": end_window}
        }).sort("start_time", 1))
        
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
                vector_results = await vector_handler.vector_search(
                    embedding_768d,
                    limit=request.limit + request.offset,
                    min_score=0.7  # Adjust threshold as needed
                )
                
                # Apply offset
                paginated_results = vector_results[request.offset:request.offset + request.limit]
                
                # Convert to API format with expanded context
                formatted_results = []
                for result in paginated_results:
                    # Expand context for better readability
                    expanded_text = await expand_chunk_context(result, context_seconds=20.0)
                    
                    # Vector search provides chunks with timestamps
                    formatted_results.append(SearchResult(
                        episode_id=result["episode_id"],
                        podcast_name=result["podcast_name"],
                        episode_title=result["episode_title"],
                        published_at=result["published_at"].isoformat() if result.get("published_at") else datetime.now().isoformat(),
                        published_date=result["published_at"].strftime('%B %d, %Y') if result.get("published_at") else "Unknown date",
                        similarity_score=result["score"],
                        excerpt=expanded_text,  # Use expanded text instead of single chunk
                        word_count=len(expanded_text.split()),
                        duration_seconds=0,  # Will be filled from Supabase
                        topics=result.get("topics", []),
                        s3_audio_path=None,  # Will be filled from Supabase
                        timestamp={
                            "start_time": result.get("start_time", 0),  # Keep original timestamp for audio sync
                            "end_time": result.get("end_time", 0)
                        }
                    ))
                
                # Get audio paths and durations from Supabase
                if formatted_results:
                    pool = get_pool()
                    episode_ids = list(set(r.episode_id for r in formatted_results))
                    
                    def get_audio_data(client):
                        return client.table("episodes") \
                            .select("id, s3_audio_path, duration_seconds") \
                            .in_("id", episode_ids) \
                            .execute()
                    
                    audio_data = await pool.execute_with_retry(get_audio_data)
                    
                    # Create lookup dict
                    audio_by_id = {
                        ep["id"]: {
                            "s3_audio_path": ep.get("s3_audio_path"),
                            "duration_seconds": ep.get("duration_seconds", 0)
                        }
                        for ep in audio_data.data
                    }
                    
                    # Update results
                    for result in formatted_results:
                        if result.episode_id in audio_by_id:
                            result.s3_audio_path = audio_by_id[result.episode_id]["s3_audio_path"]
                            result.duration_seconds = audio_by_id[result.episode_id]["duration_seconds"]
                
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
        logger.warning(f"768D vector search failed: {str(e)}")
    
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
                    similarity_score=result["relevance_score"],
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
    
    # Final fallback to 384D pgvector
    logger.info(f"Final fallback to 384D pgvector: {request.query}")
    
    # Import existing functions from search_lightweight
    from .search_lightweight import (
        check_query_cache,
        store_query_cache,
        search_episodes
    )
    
    # Check 384D cache
    cache_hit = False
    embedding_384d = await check_query_cache(query_hash)
    
    if embedding_384d:
        cache_hit = True
    else:
        # Generate 384D embedding
        embedding_384d = await generate_embedding_384d_api(request.query)
        
        if embedding_384d:
            asyncio.create_task(store_query_cache(request.query, query_hash, embedding_384d))
        else:
            # Last resort - return empty results
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
    
    # Search with 384D embeddings
    search_results = await search_episodes(embedding_384d, request.limit, request.offset)
    
    # Format results (existing logic)
    formatted_results = []
    for result in search_results["results"]:
        episode_topics = search_results["topics_by_episode"].get(result["episode_id"], [])
        
        topics_str = ', '.join(episode_topics) if episode_topics else 'various topics'
        excerpt = (
            f"{result['episode_title'][:150]}... "
            f"This episode from {result['podcast_name']} covers {topics_str}. "
            f"Published on {result['published_at'][:10]}. "
            f"Match score: {result['similarity']:.1%}"
        )
        
        # Parse the published_at string to datetime
        try:
            published_dt = datetime.fromisoformat(result["published_at"].replace('Z', '+00:00'))
            published_date = published_dt.strftime('%B %d, %Y')
        except:
            published_date = "Unknown date"
        
        formatted_results.append(SearchResult(
            episode_id=result["episode_id"],
            podcast_name=result["podcast_name"],
            episode_title=result["episode_title"],
            published_at=result["published_at"],
            published_date=published_date,
            similarity_score=result["similarity"],
            excerpt=excerpt,
            word_count=result.get("word_count", 0),
            duration_seconds=result.get("duration_seconds", 0),
            topics=episode_topics,
            s3_audio_path=result.get("s3_audio_path"),
            timestamp=None  # No timestamps in pgvector search
        ))
    
    return SearchResponse(
        results=formatted_results,
        total_results=search_results["total"],
        cache_hit=cache_hit,
        search_id=search_id,
        query=request.query,
        limit=request.limit,
        offset=request.offset,
        search_method="vector_384d"
    )