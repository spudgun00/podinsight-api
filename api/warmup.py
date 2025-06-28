"""
Warmup endpoint to prevent cold starts
"""
import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class WarmupResponse(BaseModel):
    status: str
    message: str

@router.get("/api/warmup")
async def warmup() -> WarmupResponse:
    """
    Simple endpoint to keep the function warm
    """
    logger.info("[WARMUP] Warmup request received")

    # Import modules to warm them up
    try:
        # These imports will trigger module initialization
        from .embeddings_768d_modal import get_embedder
        from .mongodb_vector_search import get_vector_search_handler
        from .synthesis import get_openai_client

        logger.info("[WARMUP] Modules imported successfully")

        # Initialize the embedder (but don't actually embed anything)
        embedder = get_embedder()
        logger.info("[WARMUP] Embedder initialized")

        # Initialize OpenAI client
        client = get_openai_client()
        logger.info("[WARMUP] OpenAI client initialized")

        return WarmupResponse(
            status="success",
            message="Function warmed up successfully"
        )
    except Exception as e:
        logger.error(f"[WARMUP] Error during warmup: {e}")
        return WarmupResponse(
            status="error",
            message=f"Warmup failed: {str(e)}"
        )
