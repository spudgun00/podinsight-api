"""
Search API endpoints for PodInsightHQ
Implements semantic search using embeddings and pgvector
"""
from fastapi import HTTPException
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import logging
import hashlib
import json
import asyncio
from pydantic import BaseModel, Field, validator
from sentence_transformers import SentenceTransformer
import numpy as np
from .database import get_pool

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the embedding model (same as used in ETL)
# This is a lightweight model that loads quickly
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Request/Response models
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
    similarity_score: float
    excerpt: str
    word_count: int
    duration_seconds: int
    topics: List[str]
    s3_audio_path: Optional[str]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int
    cache_hit: bool
    search_id: str
    query: str
    limit: int
    offset: int


async def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for search query using the same model as ETL
    
    Args:
        text: Query text to embed
        
    Returns:
        384-dimensional embedding vector
    """
    try:
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, model.encode, text)
        
        # Normalize to unit length (same as ETL process)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embedding: {str(e)}"
        )


async def check_query_cache(query_hash: str) -> Optional[List[float]]:
    """
    Check if we have a cached embedding for this query
    
    Args:
        query_hash: SHA256 hash of the query
        
    Returns:
        Cached embedding if found, None otherwise
    """
    pool = get_pool()
    
    try:
        def query_cache(client):
            return client.table("query_cache") \
                .select("embedding") \
                .eq("query_hash", query_hash) \
                .execute()
        
        result = await pool.execute_with_retry(query_cache)
        
        if result.data and len(result.data) > 0:
            # Parse the embedding from string format
            embedding_str = result.data[0].get("embedding")
            if embedding_str:
                # Remove the brackets and split by comma
                embedding_str = embedding_str.strip("[]")
                return [float(x) for x in embedding_str.split(",")]
        
        return None
    except Exception as e:
        # Cache miss is not an error
        logger.debug(f"Cache miss for query hash: {query_hash}")
        return None


async def store_query_cache(query: str, query_hash: str, embedding: List[float]):
    """
    Store query and embedding in cache for future use
    
    Args:
        query: Original query text
        query_hash: SHA256 hash of the query
        embedding: 384D embedding vector
    """
    pool = get_pool()
    
    try:
        # Convert embedding to PostgreSQL array format
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        
        def insert_cache(client):
            return client.table("query_cache") \
                .upsert({
                    "query_hash": query_hash,
                    "query_text": query,
                    "embedding": embedding_str,
                    "created_at": datetime.now().isoformat()
                }, on_conflict="query_hash") \
                .execute()
        
        await pool.execute_with_retry(insert_cache)
        logger.info(f"Cached embedding for query: {query[:50]}...")
    except Exception as e:
        # Cache storage failure is not critical
        logger.warning(f"Failed to cache query embedding: {str(e)}")


async def search_episodes(embedding: List[float], limit: int, offset: int) -> Dict[str, Any]:
    """
    Search episodes using pgvector similarity search
    
    Args:
        embedding: Query embedding vector
        limit: Number of results to return
        offset: Offset for pagination
        
    Returns:
        Search results with episode metadata
    """
    pool = get_pool()
    
    try:
        # Convert embedding to PostgreSQL array format
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        
        # Use the similarity_search_ranked function from our migration
        def search_query(client):
            # Call the database function directly using RPC
            return client.rpc(
                "similarity_search_ranked",
                {
                    "query_embedding": embedding_str,
                    "match_count": limit + offset  # Get extra for offset
                }
            ).execute()
        
        results = await pool.execute_with_retry(search_query)
        
        # Apply offset manually since the function doesn't support it
        paginated_results = results.data[offset:offset + limit] if results.data else []
        
        # Get topic mentions for the found episodes
        if paginated_results:
            episode_ids = [r["episode_id"] for r in paginated_results]
            
            def get_topics(client):
                return client.table("topic_mentions") \
                    .select("episode_id, topic_name") \
                    .in_("episode_id", episode_ids) \
                    .execute()
            
            topics_result = await pool.execute_with_retry(get_topics)
            
            # Group topics by episode
            topics_by_episode = {}
            for topic in topics_result.data:
                ep_id = topic["episode_id"]
                if ep_id not in topics_by_episode:
                    topics_by_episode[ep_id] = []
                topics_by_episode[ep_id].append(topic["topic_name"])
        else:
            topics_by_episode = {}
        
        return {
            "results": paginated_results,
            "topics_by_episode": topics_by_episode,
            "total": len(results.data) if results.data else 0
        }
        
    except Exception as e:
        logger.error(f"Error searching episodes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search episodes: {str(e)}"
        )


def extract_excerpt(transcript: str, query: str, max_length: int = 200) -> str:
    """
    Extract relevant excerpt from transcript around query terms
    
    Args:
        transcript: Full transcript text
        query: Search query
        max_length: Maximum excerpt length in words
        
    Returns:
        Relevant excerpt with context
    """
    if not transcript:
        return "No transcript available."
    
    # Simple approach: find first occurrence of any query word
    query_words = query.lower().split()
    transcript_lower = transcript.lower()
    words = transcript.split()
    
    best_position = -1
    best_score = 0
    
    # Find position with most query words nearby
    for i, word in enumerate(words):
        if i + max_length > len(words):
            break
            
        # Count query words in window
        window = " ".join(words[i:i+max_length]).lower()
        score = sum(1 for qw in query_words if qw in window)
        
        if score > best_score:
            best_score = score
            best_position = i
    
    # If no good match, just return beginning
    if best_position == -1:
        excerpt_words = words[:max_length]
    else:
        # Get window around best position
        start = max(0, best_position - 50)
        end = min(len(words), start + max_length)
        excerpt_words = words[start:end]
    
    excerpt = " ".join(excerpt_words)
    
    # Add ellipsis if truncated
    if len(words) > max_length:
        if best_position > 50:
            excerpt = "..." + excerpt
        if best_position + max_length < len(words):
            excerpt = excerpt + "..."
    
    return excerpt


async def search_handler(request: SearchRequest) -> SearchResponse:
    """
    Main search handler that orchestrates the search process
    
    Args:
        request: Search request with query and parameters
        
    Returns:
        Search response with results and metadata
    """
    # Generate query hash for caching
    query_hash = hashlib.sha256(request.query.encode()).hexdigest()
    search_id = f"search_{query_hash[:8]}_{datetime.now().timestamp()}"
    
    # Check cache first
    cache_hit = False
    embedding = await check_query_cache(query_hash)
    
    if embedding:
        cache_hit = True
        logger.info(f"Cache hit for query: {request.query}")
    else:
        # Generate new embedding
        logger.info(f"Generating embedding for query: {request.query}")
        embedding = await generate_embedding(request.query)
        
        # Store in cache (async, don't wait)
        asyncio.create_task(store_query_cache(request.query, query_hash, embedding))
    
    # Search episodes
    search_results = await search_episodes(embedding, request.limit, request.offset)
    
    # Format results
    formatted_results = []
    for result in search_results["results"]:
        # Get topics for this episode
        episode_topics = search_results["topics_by_episode"].get(result["episode_id"], [])
        
        # Create a meaningful excerpt from available data
        topics_str = ', '.join(episode_topics) if episode_topics else 'various topics'
        excerpt = (
            f"{result['episode_title'][:150]}... "
            f"This episode from {result['podcast_name']} covers {topics_str}. "
            f"Published on {result['published_at'][:10]}. "
            f"Match score: {result['similarity']:.1%}"
        )
        
        formatted_results.append(SearchResult(
            episode_id=result["episode_id"],
            podcast_name=result["podcast_name"],
            episode_title=result["episode_title"],
            published_at=result["published_at"],
            similarity_score=result["similarity"],
            excerpt=excerpt,
            word_count=result.get("word_count", 0),
            duration_seconds=result.get("duration_seconds", 0),
            topics=episode_topics,
            s3_audio_path=result.get("s3_audio_path")
        ))
    
    return SearchResponse(
        results=formatted_results,
        total_results=search_results["total"],
        cache_hit=cache_hit,
        search_id=search_id,
        query=request.query,
        limit=request.limit,
        offset=request.offset
    )