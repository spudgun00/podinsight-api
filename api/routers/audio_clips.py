"""
Audio clip generation API endpoint for on-demand clip extraction.
This handles requests from the frontend and invokes AWS Lambda for clip generation.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import logging
from bson import ObjectId
from pymongo import MongoClient
import time
import json

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/audio_clips", tags=["audio"])

# Environment variables
LAMBDA_FUNCTION_URL = os.environ.get("AUDIO_LAMBDA_URL")
LAMBDA_API_KEY = os.environ.get("AUDIO_LAMBDA_API_KEY")
MONGODB_URI = os.environ.get("MONGODB_URI")

# Response models
class AudioClipResponse(BaseModel):
    clip_url: str
    expires_at: str
    cache_hit: bool
    episode_id: str
    start_time_ms: int
    duration_ms: int
    generation_time_ms: int

@router.get("/health")
async def health_check():
    """Health check endpoint for audio service"""
    return {
        "status": "healthy",
        "service": "audio_clips",
        "lambda_configured": bool(LAMBDA_FUNCTION_URL),
        "mongodb_configured": bool(MONGODB_URI)
    }

@router.get("/{episode_id}")
async def get_audio_clip(
    episode_id: str,
    start_time_ms: int = Query(..., description="Start time in milliseconds"),
    duration_ms: int = Query(30000, description="Duration in milliseconds (default: 30 seconds)")
) -> AudioClipResponse:
    """
    Generate or retrieve an audio clip for a specific episode.

    Args:
        episode_id: MongoDB ObjectId of the episode
        start_time_ms: Start time of the clip in milliseconds
        duration_ms: Duration of the clip in milliseconds (default: 30000)

    Returns:
        AudioClipResponse with pre-signed URL and metadata
    """
    start_time = time.time()

    try:
        # Validate ID format - support multiple formats
        import re
        guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'

        # Check if it's a standard GUID
        if re.match(guid_pattern, episode_id):
            guid = episode_id
        # Check if it's a special format (substack:, flightcast:, etc)
        elif ':' in episode_id and (episode_id.startswith('substack:') or episode_id.startswith('flightcast:')):
            # These are valid GUIDs in our system
            guid = episode_id
            logger.info(f"Using special format ID: {guid}")
        # For backward compatibility, check if it's an ObjectId and convert
        elif len(episode_id) == 24:
            try:
                ObjectId(episode_id)
                # It's an ObjectId - need to look up the GUID
                if not MONGODB_URI:
                    logger.error("MONGODB_URI not configured")
                    raise HTTPException(status_code=503, detail="Database service not configured")

                client = MongoClient(MONGODB_URI)
                db = client.podinsight

                episode = db.episode_metadata.find_one(
                    {"_id": ObjectId(episode_id)},
                    {"guid": 1}
                )

                if not episode or not episode.get("guid"):
                    raise HTTPException(status_code=404, detail="Episode not found or missing GUID")

                # Use the GUID from here on
                guid = episode["guid"]
                logger.info(f"Converted ObjectId {episode_id} to GUID {guid}")
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid episode ID format")
        else:
            raise HTTPException(status_code=400, detail="Invalid episode ID format - must be GUID, ObjectId, or special format (substack:, flightcast:)")

        # Validate parameters
        if start_time_ms < 0:
            raise HTTPException(status_code=400, detail="Start time must be non-negative")
        if duration_ms <= 0 or duration_ms > 60000:  # Max 60 seconds
            raise HTTPException(status_code=400, detail="Duration must be between 1 and 60000 milliseconds")

        # Look up feed_slug from MongoDB using GUID
        logger.info(f"Looking up GUID {guid} in MongoDB")

        if not MONGODB_URI:
            logger.error("MONGODB_URI not configured")
            raise HTTPException(status_code=503, detail="Database service not configured")

        client = MongoClient(MONGODB_URI)
        db = client.podinsight

        # Find feed_slug from transcript_chunks using GUID
        chunk = db.transcript_chunks_768d.find_one(
            {"episode_id": guid},
            {"feed_slug": 1}
        )

        if not chunk:
            logger.warning(f"GUID {guid} has no transcript data")
            raise HTTPException(status_code=422, detail="Episode does not have transcript data available")

        if not chunk.get("feed_slug"):
            logger.error(f"Could not find feed_slug for GUID {guid}")
            raise HTTPException(status_code=500, detail="Could not determine podcast feed")

        feed_slug = chunk["feed_slug"]

        # Check if Lambda URL is configured
        if not LAMBDA_FUNCTION_URL:
            logger.error("AUDIO_LAMBDA_URL not configured")
            raise HTTPException(status_code=503, detail="Audio service not configured")

        # Prepare Lambda request payload
        lambda_payload = {
            "feed_slug": feed_slug,
            "guid": guid,
            "start_time_ms": start_time_ms,
            "duration_ms": duration_ms
        }

        logger.info(f"Invoking Lambda for {feed_slug}/{guid} at {start_time_ms}ms")

        # Call Lambda function with API key authentication
        headers = {}
        if LAMBDA_API_KEY:
            headers["x-api-key"] = LAMBDA_API_KEY

        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                LAMBDA_FUNCTION_URL,
                json=lambda_payload,
                headers=headers
            )

        if response.status_code != 200:
            logger.error(f"Lambda returned {response.status_code}: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Audio generation failed: {response.text}"
            )

        # Parse Lambda response
        lambda_result = response.json()

        # Calculate generation time
        generation_time_ms = int((time.time() - start_time) * 1000)

        # Return response matching the expected format
        return AudioClipResponse(
            clip_url=lambda_result.get("clip_url"),
            expires_at=lambda_result.get("expires_at", ""),
            cache_hit=lambda_result.get("cache_hit", False),
            episode_id=episode_id,
            start_time_ms=start_time_ms,
            duration_ms=duration_ms,
            generation_time_ms=generation_time_ms
        )

    except HTTPException:
        raise
    except httpx.TimeoutException:
        logger.error("Lambda timeout after 25 seconds")
        raise HTTPException(status_code=504, detail="Audio generation timed out")
    except Exception as e:
        logger.error(f"Unexpected error in audio clip generation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
