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
import time
import json

# Configure logging
from lib import aws_search

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/audio_clips", tags=["audio"])

# Environment variables
LAMBDA_FUNCTION_URL = os.environ.get("AUDIO_LAMBDA_URL")
LAMBDA_API_KEY = os.environ.get("AUDIO_LAMBDA_API_KEY")

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
        "index": aws_search.INDEX,
        "region": aws_search.REGION,
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
        episode_id: episode guid, resolved against the AWS search index
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
        # Phase 2, 2026-08-27: every id is treated as an opaque GUID and
        # resolved against the AWS index. The old code had a special branch for
        # 24-hex ids, converting them from a MongoDB ObjectId to a guid - which
        # broke the one legitimate episode whose guid is itself 24 hex
        # characters (SOURCE_OF_TRUTH 6.3). Resolving against the index has no
        # such ambiguity: an id either has chunks or it does not.
        guid = episode_id

        # Validate parameters
        if start_time_ms < 0:
            raise HTTPException(status_code=400, detail="Start time must be non-negative")
        if duration_ms <= 0 or duration_ms > 60000:  # Max 60 seconds
            raise HTTPException(status_code=400, detail="Duration must be between 1 and 60000 milliseconds")

        # feed_slug from the AWS index. The Lambda needs it to build the S3 key.
        logger.info(f"Resolving feed_slug for {guid} from the AWS index")
        try:
            hit = aws_search.client().search(
                index=aws_search.INDEX,
                body={"size": 1, "_source": ["feed_slug", "episode_title"],
                      "query": {"term": {"episode_id": guid}}})["hits"]["hits"]
        except Exception as e:  # noqa: BLE001
            logger.error(f"Index lookup failed for {guid}: {e}")
            raise HTTPException(status_code=503, detail="Search index unavailable")

        if not hit:
            logger.warning(f"GUID {guid} has no indexed transcript")
            raise HTTPException(status_code=422, detail="Episode does not have transcript data available")

        feed_slug = hit[0]["_source"].get("feed_slug")
        if not feed_slug:
            logger.error(f"Could not determine feed_slug for GUID {guid}")
            raise HTTPException(status_code=500, detail="Could not determine podcast feed")

        # Check if Lambda URL is configured
        if not LAMBDA_FUNCTION_URL:
            logger.error("AUDIO_LAMBDA_URL not configured")
            raise HTTPException(status_code=503, detail="Audio service not configured")

        # 8 Sep 2026, RULED BY JAMES: playability is a tolerance, not a gate.
        # A located timestamp can be a few seconds LATE - the publisher-transcript
        # defect measured a median +3.5s, with 85 of 88 under ten seconds - which
        # used to open a clip after the quote had begun. Every clip now starts a
        # 5-second PRE-ROLL earlier, and the window is lengthened by exactly the
        # amount actually shifted so the original span is never truncated.
        # Applied here because this is the single choke point every clip in the
        # product passes through: briefs, search citations and the watcher alike.
        PRE_ROLL_MS = 5000
        shift = min(PRE_ROLL_MS, start_time_ms)          # never before 0
        clip_start_ms = start_time_ms - shift
        clip_duration_ms = min(60000, duration_ms + shift)

        # Prepare Lambda request payload
        lambda_payload = {
            "feed_slug": feed_slug,
            "guid": guid,
            "start_time_ms": clip_start_ms,
            "duration_ms": clip_duration_ms
        }

        logger.info(f"Invoking Lambda for {feed_slug}/{guid} at {clip_start_ms}ms "
                    f"({shift}ms pre-roll from {start_time_ms}ms, {clip_duration_ms}ms)")

        # Call Lambda function with API key authentication
        headers = {}
        if LAMBDA_API_KEY:
            headers["x-api-key"] = LAMBDA_API_KEY

        # 25s was not enough for long episodes: a 5-hour Acquired episode times
        # out while the Lambda fetches and seeks the source audio.
        async with httpx.AsyncClient(timeout=55.0) as client:
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
            start_time_ms=clip_start_ms,
            duration_ms=clip_duration_ms,
            generation_time_ms=generation_time_ms
        )

    except HTTPException:
        raise
    except httpx.TimeoutException:
        logger.error("Lambda timeout after 55 seconds")
        raise HTTPException(status_code=504, detail="Audio generation timed out")
    except Exception as e:
        logger.error(f"Unexpected error in audio clip generation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
