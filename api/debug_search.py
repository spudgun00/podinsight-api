"""
Debug endpoint to diagnose search issues
"""
from fastapi import APIRouter
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/debug/search")
async def debug_search():
    """Check search configuration and connections"""
    
    # Check environment variables
    env_vars = {
        "MONGODB_URI": "SET" if os.getenv("MONGODB_URI") else "NOT SET",
        "MODAL_EMBEDDING_URL": os.getenv("MODAL_EMBEDDING_URL", "using default"),
        "SUPABASE_URL": "SET" if os.getenv("SUPABASE_URL") else "NOT SET",
        "SUPABASE_KEY": "SET" if os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") else "NOT SET"
    }
    
    # Try to import and check handlers
    handler_status = {}
    
    try:
        from .mongodb_vector_search import get_vector_search_handler
        handler = await get_vector_search_handler()
        
        # Try to actually use the connection
        test_query = None
        if handler.collection is not None:
            try:
                # Try a simple count
                test_query = await handler.collection.count_documents({}, limit=1)
                test_query = "Connection successful"
            except Exception as e:
                test_query = f"Query failed: {str(e)}"
        
        handler_status["vector_search_handler"] = {
            "initialized": handler.client is not None,
            "db_connected": handler.db is not None,
            "collection_set": handler.collection is not None,
            "connection_test": test_query
        }
    except Exception as e:
        handler_status["vector_search_handler"] = {"error": str(e)}
    
    try:
        from .embeddings_768d_modal import get_embedder
        embedder = get_embedder()
        handler_status["modal_embedder"] = {
            "initialized": True,
            "modal_url": embedder.modal_url
        }
    except Exception as e:
        handler_status["modal_embedder"] = {"error": str(e)}
    
    # Test a simple embedding
    embedding_test = {}
    try:
        test_embedding = await embedder._encode_query_async("test")
        embedding_test = {
            "success": test_embedding is not None,
            "dimensions": len(test_embedding) if test_embedding else 0
        }
    except Exception as e:
        embedding_test = {"error": str(e)}
    
    return {
        "environment_variables": env_vars,
        "handlers": handler_status,
        "embedding_test": embedding_test,
        "debug_info": "Check if MONGODB_URI is set in Vercel environment variables"
    }