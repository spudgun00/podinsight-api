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
    Synchronous endpoint to warm up Modal.
    Waits for Modal to actually warm up before returning.
    """
    import time
    start_time = time.time()

    try:
        # Import here to avoid circular imports
        from ..search_lightweight_768d import generate_embedding_768d_local

        # Log prewarm initiation
        logger.info("🔥 Modal pre-warming initiated")

        # Use a simple test query that Modal can cache
        test_query = "warm"

        # Wait for Modal to actually warm up
        embedding_start = time.time()
        result = await generate_embedding_768d_local(test_query)
        embedding_time = time.time() - embedding_start

        if result:
            total_time = time.time() - start_time
            logger.info(f"✅ Modal pre-warm successful! Total time: {total_time:.2f}s, Embedding time: {embedding_time:.2f}s")

            # Log if it was a cold start vs warm instance
            if embedding_time > 5.0:
                logger.info(f"🥶 Modal cold start detected (took {embedding_time:.2f}s)")
                return {"status": "warmed", "message": "Modal warmed from cold start", "time": embedding_time}
            else:
                logger.info(f"🔥 Modal already warm (took {embedding_time:.2f}s)")
                return {"status": "already_warm", "message": "Modal was already warm", "time": embedding_time}
        else:
            logger.warning("⚠️ Modal pre-warm returned no result")
            return {"status": "failed", "message": "Pre-warming failed - no result"}

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"❌ Modal pre-warm failed after {total_time:.2f}s: {e}", exc_info=True)
        # Don't fail hard - pre-warming is optional
        return {"status": "error", "message": f"Pre-warming error: {str(e)}", "time": total_time}

# Export router for inclusion in main app
# Note: The handler export is not needed when using router pattern
