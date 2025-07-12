"""Standardized embedding utilities"""
import logging
from typing import List, Optional
from .embeddings_768d_modal import get_embedder

logger = logging.getLogger(__name__)

async def embed_query(text: str) -> Optional[List[float]]:
    """
    Standardized function to embed text.
    Always normalizes the query before embedding.

    Args:
        text: Raw query text

    Returns:
        768-dimensional embedding vector or None if error
    """
    # Always normalize
    clean_text = text.strip().lower()

    # Log for debugging
    logger.info(f"Embedding query: '{clean_text}'")

    # Get embedder and directly call async method with retry
    embedder = get_embedder()
    embedding = await embedder._encode_query_async_with_retry(clean_text)

    # Validate
    if embedding and len(embedding) == 768:
        return embedding
    else:
        logger.error(f"Invalid embedding: length={len(embedding) if embedding else 0}")
        return None

def validate_embedding(embedding: List[float]) -> bool:
    """
    Validate that an embedding meets our invariants

    Returns:
        True if valid, False otherwise
    """
    if not embedding:
        return False

    # Check length
    if len(embedding) != 768:
        logger.error(f"Invalid embedding length: {len(embedding)}")
        return False

    # Check values are numeric
    try:
        sum(embedding)  # Will fail if non-numeric
    except:
        logger.error("Embedding contains non-numeric values")
        return False

    return True
