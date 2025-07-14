"""Standardized embedding utilities"""
import logging
from typing import List, Optional, Tuple, Union
from .embeddings_768d_modal import get_embedder

logger = logging.getLogger(__name__)

async def embed_query(text: str, session_id: Optional[str] = None,
                     return_timing: bool = False) -> Union[Optional[List[float]], Optional[Tuple[List[float], float]]]:
    """
    Standardized function to embed text.
    Always normalizes the query before embedding.

    Args:
        text: Raw query text
        session_id: Optional session ID for tracking
        return_timing: If True, returns (embedding, elapsed_time) tuple

    Returns:
        768-dimensional embedding vector or None if error
        If return_timing=True, returns (embedding, elapsed_time) tuple or None
    """
    # Always normalize
    clean_text = text.strip().lower()

    # Log for debugging
    logger.info(f"Embedding query: '{clean_text}'")

    # Get embedder and directly call async method with retry
    embedder = get_embedder()
    result = await embedder._encode_query_async_with_retry(clean_text, session_id=session_id, return_timing=return_timing)

    if return_timing:
        # Result is (embedding, elapsed_time) or None
        if result and isinstance(result, tuple):
            embedding, elapsed = result
            if embedding and len(embedding) == 768:
                return embedding, elapsed
            else:
                logger.error(f"Invalid embedding: length={len(embedding) if embedding else 0}")
                return None
        return None
    else:
        # Result is embedding or None
        embedding = result
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
