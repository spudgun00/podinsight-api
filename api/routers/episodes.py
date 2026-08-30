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
import threading
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["episodes"])

_cache: Optional[List["Episode"]] = None
# Handlers run in FastAPI's threadpool (they are sync, because their work is
# blocking I/O). Two first-callers could otherwise build this cache at the
# same time and each pay the full scan.
_lock = threading.Lock()


class Episode(BaseModel):
    episode_id: str
    podcast_name: str
    episode_title: str
    published_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    word_count: Optional[int] = None
    total_chunks: int = 0


class EpisodesResponse(BaseModel):
    # Totals over the WHOLE catalogue, not the page. The header used to sum the
    # page and divide, which was right while the corpus was smaller than the
    # default limit of 2,000 and silently wrong the moment the backfill passed
    # it - the page reported 28 podcasts and 1,838 hours for a corpus holding
    # 29 and 4,080.
    podcast_count: Optional[int] = None
    total_hours: Optional[int] = None
    episodes: List[Episode]
    total: int
    source: str = "opensearch"


ROLLUP_INDEX = "episodes_catalogue"


def _from_rollup(client) -> Optional[List["Episode"]]:
    """Read the precomputed catalogue. Milliseconds, and flat in corpus size.

    Returns None when the rollup has not been built, so the caller falls back to
    deriving it live rather than serving an empty catalogue.
    """
    if not client.indices.exists(index=ROLLUP_INDEX):
        return None
    out, after = [], None
    while True:
        body = {"size": 1000, "sort": [{"episode_id": "asc"}]}
        if after:
            body["search_after"] = after
        hits = client.search(index=ROLLUP_INDEX, body=body)["hits"]["hits"]
        if not hits:
            break
        for h in hits:
            out.append(Episode(**{k: v for k, v in h["_source"].items()
                                  if k != "rollup_version"}))
        after = hits[-1]["sort"]
    return out or None


def _load() -> List[Episode]:
    """The episode catalogue, from the rollup when there is one.

    Deriving this live is a paged composite aggregation with a top_hits per
    episode: 7.4s against a warm engine, ~38s against one waking from idle,
    which was long enough to render three components on the demo as failures.
    It is derived data over a corpus that only moves when a load runs, so it is
    precomputed by podinsight-aws-pilot/build_episodes_rollup.py.

    The aggregation below stays as the fallback. It is what built the rollup, so
    an unbuilt rollup is slow rather than broken.
    """
    client = aws_search.client()
    rolled = _from_rollup(client)
    if rolled is not None:
        rolled.sort(key=lambda e: (e.published_at or ""), reverse=True)
        logger.info("Episode catalogue served from the %s rollup (%d episodes)",
                    ROLLUP_INDEX, len(rolled))
        return rolled
    logger.warning("%s not built; deriving the catalogue live. Run "
                   "build_episodes_rollup.py", ROLLUP_INDEX)
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
def list_episodes(
    limit: int = Query(2000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    refresh: bool = Query(False, description="Bypass the in-process cache"),
) -> EpisodesResponse:
    global _cache
    try:
        if _cache is None or refresh:
            with _lock:
                if _cache is None or refresh:
                    _cache = _load()
                    logger.info("Loaded %d episodes from the AWS index", len(_cache))
    except Exception as e:                                   # noqa: BLE001
        logger.error("Episode aggregation failed: %s", e)
        raise HTTPException(status_code=503,
                            detail=f"Episode catalogue unavailable: {e}")
    return EpisodesResponse(
        episodes=_cache[offset:offset + limit], total=len(_cache),
        podcast_count=len({e.podcast_name for e in _cache}),
        total_hours=round(sum(e.duration_seconds or 0 for e in _cache) / 3600))
