"""
Modal Pre-warming Endpoint
Triggers a lightweight embedding request to warm up the Modal endpoint
"""

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure correct environment loading
from lib.env_loader import load_env_safely
load_env_safely()

logger = logging.getLogger(__name__)

# Create FastAPI app for Vercel
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/prewarm")
async def prewarm_modal():
    """
    Fire-and-forget endpoint to warm up Modal.
    Sends a simple test embedding request that Modal can cache.
    """
    try:
        # Import here to avoid circular imports
        from api.search_lightweight_768d import generate_embedding_768d_local

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
    try:
        from api.search_lightweight_768d import generate_embedding_768d_local

        # Use a simple test query that Modal can cache
        test_query = "warm"
        logger.info("Starting Modal pre-warm with test query")

        # This will trigger Modal to load the model
        result = await generate_embedding_768d_local(test_query)

        if result:
            logger.info("Modal pre-warm successful")
        else:
            logger.warning("Modal pre-warm returned no result")

    except Exception as e:
        # Log but don't raise - this is a best-effort operation
        logger.error(f"Modal pre-warm failed: {e}", exc_info=True)

# Export handler for Vercel
handler = app
