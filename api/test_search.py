"""
Test endpoint to verify MongoDB vector search is working
Bypasses Modal embedding generation for faster testing
"""
from fastapi import HTTPException
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pydantic import BaseModel
from .mongodb_vector_search import get_vector_search_handler

logger = logging.getLogger(__name__)

class TestSearchRequest(BaseModel):
    limit: int = 10

class TestSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_results: int
    message: str

async def test_search_handler(request: TestSearchRequest) -> TestSearchResponse:
    """
    Test search using a pre-computed embedding from an existing document
    """
    try:
        # Get MongoDB vector search handler
        vector_handler = await get_vector_search_handler()
        
        if vector_handler.db is None:
            return TestSearchResponse(
                results=[],
                total_results=0,
                message="MongoDB not connected"
            )
        
        # First, get a sample document with an embedding
        sample_doc = await vector_handler.db.transcript_chunks_768d.find_one(
            {"embedding_768d": {"$exists": True}},
            {"embedding_768d": 1, "text": 1}
        )
        
        if not sample_doc or "embedding_768d" not in sample_doc:
            return TestSearchResponse(
                results=[],
                total_results=0,
                message="No documents with embeddings found"
            )
        
        # Use the existing embedding to search
        test_embedding = sample_doc["embedding_768d"]
        sample_text = sample_doc.get("text", "Unknown")[:100]
        
        logger.info(f"Using embedding from document: {sample_text}...")
        
        # Perform vector search with the existing embedding
        results = await vector_handler.vector_search(
            test_embedding,
            limit=request.limit,
            min_score=0.0  # No threshold
        )
        
        # Format results
        formatted_results = []
        for result in results[:5]:  # Limit to 5 for testing
            formatted_results.append({
                "episode_id": result.get("episode_id"),
                "text": result.get("text", "")[:200] + "...",
                "score": result.get("score", 0),
                "podcast_name": result.get("podcast_name", "Unknown"),
                "episode_title": result.get("episode_title", "Unknown")
            })
        
        return TestSearchResponse(
            results=formatted_results,
            total_results=len(results),
            message=f"Success! Found {len(results)} results using embedding from: {sample_text}"
        )
        
    except Exception as e:
        logger.error(f"Test search error: {str(e)}")
        return TestSearchResponse(
            results=[],
            total_results=0,
            message=f"Error: {str(e)}"
        )