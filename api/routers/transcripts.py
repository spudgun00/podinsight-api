"""
Transcript retrieval endpoint
"""
import os
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from async_lru import alru_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/transcript", tags=["transcripts"])

class TranscriptChunk(BaseModel):
    text: str
    start_time: float
    end_time: float
    chunk_index: int
    speaker: Optional[str] = None

class TranscriptResponse(BaseModel):
    episode_id: str
    podcast_name: str
    episode_title: str
    published_at: str
    full_text: str
    chunks: List[TranscriptChunk]
    duration_seconds: int
    word_count: int
    total_chunks: int

def get_mongodb_client():
    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        raise ValueError("MONGODB_URI not configured")
    return AsyncIOMotorClient(mongo_uri)

@alru_cache(maxsize=100)
async def get_transcript_cached(episode_id: str) -> TranscriptResponse:
    """Get full transcript for an episode (cached)"""
    try:
        # Get MongoDB client
        mongo_client = get_mongodb_client()
        db = mongo_client["podinsight"]

        # Fetch metadata from MongoDB episode_metadata collection
        metadata_collection = db["episode_metadata"]
        metadata = await metadata_collection.find_one({"episode_id": episode_id})

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

        # Fetch transcript chunks from MongoDB
        chunks_collection = db["transcript_chunks_768d"]

        cursor = chunks_collection.find(
            {"episode_id": episode_id}
        ).sort("chunk_index", 1).limit(5000)

        chunks_list = await cursor.to_list(length=5000)
        if not chunks_list:
            raise HTTPException(status_code=404, detail=f"No transcript found")

        # Build response
        transcript_chunks = [
            TranscriptChunk(
                text=chunk.get("text", ""),
                start_time=chunk.get("start_time", 0.0),
                end_time=chunk.get("end_time", 0.0),
                chunk_index=chunk.get("chunk_index", 0),
                speaker=chunk.get("speaker")
            )
            for chunk in chunks_list
        ]

        full_text = "\n\n".join(chunk.text for chunk in transcript_chunks)
        word_count = sum(len(chunk.text.split()) for chunk in transcript_chunks)
        duration_seconds = int(transcript_chunks[-1].end_time) if transcript_chunks else 0

        # Extract nested metadata fields
        raw_entry = metadata.get("raw_entry_original_feed", {})

        return TranscriptResponse(
            episode_id=episode_id,
            podcast_name=metadata.get("podcast_title", "Unknown"),
            episode_title=raw_entry.get("episode_title", "Unknown Episode"),
            published_at=raw_entry.get("published_date_iso", ""),
            full_text=full_text,
            chunks=transcript_chunks,
            duration_seconds=duration_seconds,
            word_count=word_count,
            total_chunks=len(transcript_chunks)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transcript: {e}", exc_info=True)
        # Return more detailed error for debugging
        error_detail = f"Failed to fetch transcript: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/{episode_id}", response_model=TranscriptResponse)
async def get_transcript(episode_id: str):
    """Get full transcript for an episode"""
    return await get_transcript_cached(episode_id)
