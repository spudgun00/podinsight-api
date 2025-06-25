"""Warmup function to pre-establish connections"""
import logging
from .mongodb_vector_search import get_vector_search_handler
from .embeddings_768d_modal import get_embedder

logger = logging.getLogger(__name__)

async def warmup_connections():
    """Pre-establish connections to avoid cold start issues"""
    try:
        # Warm up MongoDB connection
        logger.info("Warming up MongoDB connection...")
        vector_handler = await get_vector_search_handler()
        
        # Test the connection with a simple query
        if vector_handler.collection:
            count = await vector_handler.collection.count_documents({}, limit=1)
            logger.info(f"MongoDB warmup successful, collection accessible")
        
        # Warm up Modal embedder
        logger.info("Warming up Modal embedder...")
        embedder = get_embedder()
        
        # Test with a simple embedding
        test_embedding = embedder.encode_query("test")
        if test_embedding and len(test_embedding) == 768:
            logger.info("Modal embedder warmup successful")
        
        logger.info("All connections warmed up successfully")
        return True
        
    except Exception as e:
        logger.error(f"Warmup failed: {e}")
        return False