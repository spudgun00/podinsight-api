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
    Synchronous endpoint to warm up Modal and MongoDB.
    Waits for both services to actually warm up before returning.
    """
    import time
    start_time = time.time()
    results = {}

    # Warm MongoDB connection first (in parallel with Modal)
    try:
        from ..improved_hybrid_search import warm_mongodb_connection

        logger.info("🔥 MongoDB connection warming initiated")
        mongodb_start = time.time()

        # Run MongoDB warming in background
        mongodb_task = asyncio.create_task(warm_mongodb_connection())

    except Exception as e:
        logger.warning(f"⚠️ MongoDB warming setup failed: {e}")
        mongodb_task = None

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
            modal_time = time.time() - embedding_start
            logger.info(f"✅ Modal pre-warm successful! Embedding time: {modal_time:.2f}s")

            # Log if it was a cold start vs warm instance
            if embedding_time > 5.0:
                logger.info(f"🥶 Modal cold start detected (took {embedding_time:.2f}s)")
                results["modal"] = {"status": "warmed", "message": "Modal warmed from cold start", "time": embedding_time}
            else:
                logger.info(f"🔥 Modal already warm (took {embedding_time:.2f}s)")
                results["modal"] = {"status": "already_warm", "message": "Modal was already warm", "time": embedding_time}
        else:
            logger.warning("⚠️ Modal pre-warm returned no result")
            results["modal"] = {"status": "failed", "message": "Pre-warming failed - no result"}

    except Exception as e:
        modal_time = time.time() - start_time
        logger.error(f"❌ Modal pre-warm failed after {modal_time:.2f}s: {e}", exc_info=True)
        results["modal"] = {"status": "error", "message": f"Pre-warming error: {str(e)}", "time": modal_time}

    # Wait for MongoDB warming to complete
    if mongodb_task:
        try:
            await mongodb_task
            mongodb_time = time.time() - mongodb_start
            results["mongodb"] = {"status": "warmed", "message": "MongoDB connection warmed", "time": mongodb_time}
        except Exception as e:
            mongodb_time = time.time() - mongodb_start
            logger.error(f"❌ MongoDB warm failed after {mongodb_time:.2f}s: {e}")
            results["mongodb"] = {"status": "error", "message": f"MongoDB warming error: {str(e)}", "time": mongodb_time}
    else:
        results["mongodb"] = {"status": "skipped", "message": "MongoDB warming not attempted"}

    # Calculate total time
    total_time = time.time() - start_time

    # Return combined results
    return {
        "status": "completed",
        "total_time": total_time,
        "services": results,
        "message": f"Pre-warming completed in {total_time:.2f}s"
    }

# Export router for inclusion in main app
# Note: The handler export is not needed when using router pattern
