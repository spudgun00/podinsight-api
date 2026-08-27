"""Transcript retrieval, served from the AWS search index.

Phase 2, 2026-08-27. Previously read episode_metadata and
transcript_chunks_768d from MongoDB. The AWS index holds both the chunk text
and the original Whisper segments nested inside each chunk, so a transcript
reassembles from it directly.

One shape change worth knowing about: chunks are now ~300-word passages rather
than the old ~18-word fragments, so `chunks` is roughly 15x shorter per episode.
The finer granularity has not been lost - it is in `segments` on each chunk,
which is what the citation timestamps resolve against.
"""
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lib import aws_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/transcript", tags=["transcripts"])


class TranscriptSegment(BaseModel):
    text: str
    start_time: float


class TranscriptChunk(BaseModel):
    text: str
    start_time: float
    end_time: float
    chunk_index: int
    speaker: Optional[str] = None       # never populated; no diarisation in the corpus
    segments: List[TranscriptSegment] = []


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
    source: str = "opensearch"


@router.get("/{episode_id}", response_model=TranscriptResponse)
async def get_transcript(episode_id: str) -> TranscriptResponse:
    try:
        os_ = aws_search.client()
        hits, after = [], None
        while True:
            body = {"size": 1000, "sort": [{"chunk_index": "asc"}],
                    "_source": {"excludes": ["embedding"]},
                    "query": {"term": {"episode_id": episode_id}}}
            if after:
                body["search_after"] = after
            page = os_.search(index=aws_search.INDEX, body=body)["hits"]["hits"]
            if not page:
                break
            hits.extend(page)
            after = page[-1]["sort"]
    except HTTPException:
        raise
    except Exception as e:                                   # noqa: BLE001
        logger.error("transcript lookup failed for %s: %s", episode_id, e)
        raise HTTPException(status_code=503, detail=f"Transcript unavailable: {e}")

    if not hits:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

    src = [h["_source"] for h in hits]
    first = src[0]
    chunks = [TranscriptChunk(
        text=c.get("text", ""), start_time=float(c.get("start_time", 0.0)),
        end_time=float(c.get("end_time", 0.0)), chunk_index=int(c.get("chunk_index", 0)),
        segments=[TranscriptSegment(text=s.get("text", ""), start_time=float(s.get("t", 0.0)))
                  for s in (c.get("segments") or [])]) for c in src]

    return TranscriptResponse(
        episode_id=episode_id,
        podcast_name=first.get("podcast_name") or "Unknown Podcast",
        episode_title=first.get("episode_title") or "(Untitled episode)",
        published_at=first.get("published_at") or "",
        full_text=" ".join(c.text for c in chunks),
        chunks=chunks,
        duration_seconds=int(max((c.end_time for c in chunks), default=0)),
        word_count=sum(int(c.get("word_count", 0)) for c in src),
        total_chunks=len(chunks))
