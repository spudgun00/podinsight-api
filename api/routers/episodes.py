"""Episode catalogue, derived from the AWS search index.

Phase 1 switchover, 2026-08-27. This used to read MongoDB's episode_metadata
collection (50 episodes) and count chunks from transcript_chunks_768d. It now
aggregates the OpenSearch index, which carries all 1,236 episodes.

Field derivation, since the index stores chunks rather than episodes:
  episode_title / podcast_name / published_at -> identical on every chunk
  total_chunks     -> the bucket's doc count
  duration_seconds -> max(end_time) across the episode's chunks
  word_count       -> sum(word_count) across the episode's chunks

main.js gates the whole Priority Briefings feature on this endpoint returning
successfully, so it fails loudly rather than returning a partial list.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["episodes"])

_cache: Optional[List["Episode"]] = None


class Episode(BaseModel):
    episode_id: str
    podcast_name: str
    episode_title: str
    published_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    word_count: Optional[int] = None
    total_chunks: int = 0


class EpisodesResponse(BaseModel):
    episodes: List[Episode]
    total: int
    source: str = "opensearch"


def _load() -> List[Episode]:
    """One composite aggregation, paged. 1,236 episodes over ~2 requests."""
    client = aws_search.client()
    out, after = [], None
    while True:
        comp = {"size": 1000, "sources": [{"e": {"terms": {"field": "episode_id"}}}]}
        if after:
            comp["after"] = after
        body = {"size": 0, "aggs": {"eps": {"composite": comp, "aggs": {
            "dur": {"max": {"field": "end_time"}},
            "words": {"sum": {"field": "word_count"}},
            "meta": {"top_hits": {"size": 1, "_source": [
                "podcast_name", "episode_title", "published_at"]}},
        }}}}
        r = client.search(index=aws_search.INDEX, body=body)
        agg = r["aggregations"]["eps"]
        for b in agg["buckets"]:
            src = b["meta"]["hits"]["hits"][0]["_source"]
            out.append(Episode(
                episode_id=b["key"]["e"],
                podcast_name=src.get("podcast_name") or "Unknown Podcast",
                episode_title=src.get("episode_title") or "(Untitled episode)",
                published_at=src.get("published_at"),
                duration_seconds=int(b["dur"]["value"] or 0),
                word_count=int(b["words"]["value"] or 0),
                total_chunks=b["doc_count"]))
        after = agg.get("after_key")
        if not after or not agg["buckets"]:
            break
    out.sort(key=lambda e: (e.published_at or ""), reverse=True)
    return out


@router.get("/episodes", response_model=EpisodesResponse)
async def list_episodes(
    limit: int = Query(2000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    refresh: bool = Query(False, description="Bypass the in-process cache"),
) -> EpisodesResponse:
    global _cache
    try:
        if _cache is None or refresh:
            _cache = _load()
            logger.info("Loaded %d episodes from the AWS index", len(_cache))
    except Exception as e:                                   # noqa: BLE001
        logger.error("Episode aggregation failed: %s", e)
        raise HTTPException(status_code=503,
                            detail=f"Episode catalogue unavailable: {e}")
    return EpisodesResponse(episodes=_cache[offset:offset + limit], total=len(_cache))
