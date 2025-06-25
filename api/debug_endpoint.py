"""Debug endpoint for troubleshooting search issues"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
import os
from .embeddings_768d_modal import get_embedder
from .mongodb_vector_search import get_vector_search_handler

router = APIRouter()

# Simple auth check
DEBUG_KEY = os.getenv("DEBUG_API_KEY", "debug-key-123")

@router.get("/api/debug")
async def debug_search(
    q: str,
    x_admin_key: Optional[str] = Header(None)
):
    """Debug endpoint to test search pipeline"""
    
    # Check auth
    if x_admin_key != DEBUG_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    try:
        # 1. Normalize query
        clean_query = q.strip().lower()
        
        # 2. Generate embedding
        embedder = get_embedder()
        embedding = embedder.encode_query(clean_query)
        
        # 3. Get vector handler
        vector_handler = await get_vector_search_handler()
        
        debug_info = {
            "original_query": q,
            "clean_query": clean_query,
            "embedding_length": len(embedding) if embedding else 0,
            "embedding_first_5": embedding[:5] if embedding else None,
            "mongodb_connected": vector_handler.db is not None,
            "collection_name": vector_handler.collection.name if vector_handler.collection else None
        }
        
        # 4. Try vector search
        if embedding and vector_handler.db:
            results = await vector_handler.vector_search(
                embedding,
                limit=5,
                min_score=0.0
            )
            
            debug_info["vector_search_count"] = len(results)
            debug_info["first_result"] = {
                "score": results[0].get("score") if results else None,
                "text_preview": results[0].get("text", "")[:100] if results else None
            }
        else:
            debug_info["vector_search_error"] = "No embedding or DB connection"
        
        return debug_info
        
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        }