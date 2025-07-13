"""
Modal Pre-warming Endpoint
Triggers a lightweight embedding request to warm up the Modal endpoint
"""

import asyncio
import logging
from fastapi import APIRouter

# Ensure correct environment loading
from lib.env_loader import load_env_safely
load_env_safely()

logger = logging.getLogger(__name__)

# Create router for prewarm endpoint
router = APIRouter(prefix="/api", tags=["prewarm"])

@router.post("/prewarm")
async def prewarm_modal():
    """
    Fire-and-forget endpoint to warm up Modal.
    Sends a simple test embedding request that Modal can cache.
    """
    try:
        # Import here to avoid circular imports
        from ..search_lightweight_768d import generate_embedding_768d_local

        # Log prewarm initiation
        logger.info("🔥 Modal pre-warming initiated")

        # Create a background task to warm Modal
        # Using a simple, cacheable query
        asyncio.create_task(_warm_modal())

        return {"status": "warming", "message": "Modal pre-warming initiated"}
    except Exception as e:
        logger.error(f"Pre-warming failed to start: {e}", exc_info=True)
        # Don't fail the request - pre-warming is optional
        return {"status": "skipped", "message": f"Pre-warming unavailable: {str(e)}"}

async def _warm_modal():
    """Background task to actually warm Modal"""
    import time
    start_time = time.time()

    try:
        from ..search_lightweight_768d import generate_embedding_768d_local

        # Use a simple test query that Modal can cache
        test_query = "warm"
        logger.info("🚀 Starting Modal pre-warm with test query")

        # This will trigger Modal to load the model
        embedding_start = time.time()
        result = await generate_embedding_768d_local(test_query)
        embedding_time = time.time() - embedding_start

        if result:
            total_time = time.time() - start_time
            logger.info(f"✅ Modal pre-warm successful! Total time: {total_time:.2f}s, Embedding time: {embedding_time:.2f}s")

            # Log if it was a cold start vs warm instance
            if embedding_time > 5.0:
                logger.info(f"🥶 Modal cold start detected (took {embedding_time:.2f}s)")
            else:
                logger.info(f"🔥 Modal warm instance (took {embedding_time:.2f}s)")
        else:
            logger.warning("⚠️ Modal pre-warm returned no result")

    except Exception as e:
        # Log but don't raise - this is a best-effort operation
        total_time = time.time() - start_time
        logger.error(f"❌ Modal pre-warm failed after {total_time:.2f}s: {e}", exc_info=True)

# Export router for inclusion in main app
# Note: The handler export is not needed when using router pattern
