"""
Lightweight Search API for Vercel deployment
Uses external embedding service instead of local model
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
import numpy as np
from .database import get_pool

# Configure logging
logger = logging.getLogger(__name__)

# Request/Response models (same as before)
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


async def generate_embedding_api(text: str) -> List[float]:
    """
    Generate embedding using Hugging Face API (free tier)
    Using same model: sentence-transformers/all-MiniLM-L6-v2
    """
    api_url = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
    api_key = os.environ.get("HUGGINGFACE_API_KEY")
    
    if not api_key:
        # Fallback to a mock embedding for testing
        logger.warning("No HUGGINGFACE_API_KEY found, using mock embedding")
        mock_embedding = [0.1] * 384
        return mock_embedding
    
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
                    # The API returns embeddings directly
                    embedding = result
                    
                    # Normalize to unit length
                    norm = np.linalg.norm(embedding)
                    if norm > 0:
                        embedding = (np.array(embedding) / norm).tolist()
                    
                    return embedding
                else:
                    error_text = await response.text()
                    logger.error(f"Embedding API error: {response.status} - {error_text}")
                    # Return mock embedding as fallback
                    return [0.1] * 384
                    
    except Exception as e:
        logger.error(f"Error calling embedding API: {str(e)}")
        # Return mock embedding as fallback
        return [0.1] * 384


# Import other functions from original search.py
from .search import (
    check_query_cache,
    store_query_cache,
    search_episodes,
    SearchRequest,
    SearchResponse,
    SearchResult
)


async def search_handler_lightweight(request: SearchRequest) -> SearchResponse:
    """
    Lightweight search handler using external embedding API
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
        # Generate new embedding using API
        logger.info(f"Generating embedding via API for query: {request.query}")
        embedding = await generate_embedding_api(request.query)
        
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