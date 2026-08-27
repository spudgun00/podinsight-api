"""/api/search served from the AWS stack.

Phase 1 of the switchover. Same request and response shape the demo already
consumes, plus one addition: `no_matches`.

`no_matches` is the point of the change. The old path could not say "I don't
know" - it returned five weak results and a hardcoded 95% confidence for a
carbonara recipe. Retrieval now applies a calibrated cutoff, and when nothing
clears it the API says so explicitly, so the front end can render that as a
result rather than as a failure.
"""
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from lib import aws_search
from lib.bedrock_synthesis import synthesize

logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=50)
    offset: int = Field(0, ge=0)

    @validator("query")
    def query_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class Citation(BaseModel):
    index: int
    episode_id: str
    episode_title: str
    podcast_name: str
    timestamp: str
    start_seconds: float
    chunk_index: int
    chunk_text: str
    similarity_score: float = 0.0
    published_date: Optional[str] = None


class AnswerObject(BaseModel):
    text: str
    citations: List[Citation]
    confidence: Optional[float] = None


class SearchResult(BaseModel):
    episode_id: str
    podcast_name: str
    episode_title: str
    published_at: Optional[str] = None
    published_date: Optional[str] = None
    similarity_score: float
    excerpt: str
    word_count: int
    duration_seconds: int
    topics: List[str] = []
    s3_audio_path: Optional[str] = None
    timestamp: Optional[Dict[str, float]] = None


class SearchResponse(BaseModel):
    answer: Optional[AnswerObject] = None
    results: List[SearchResult]
    total_results: int
    cache_hit: bool = False
    search_id: str
    query: str
    limit: int
    offset: int
    search_method: str
    processing_time_ms: Optional[int] = None
    raw_chunks: Optional[List[Dict[str, Any]]] = None
    # --- new in phase 1 ---
    no_matches: bool = False
    no_matches_reason: Optional[str] = None
    top_score: Optional[float] = None
    cutoff: Optional[float] = None


def _to_result(h: Dict[str, Any]) -> SearchResult:
    pub = h.get("published_at")
    return SearchResult(
        episode_id=h.get("episode_id", ""),
        podcast_name=h.get("podcast_name", "Unknown Podcast"),
        episode_title=h.get("episode_title", "(Untitled episode)"),
        published_at=pub,
        published_date=(pub or "")[:10] or None,
        similarity_score=float(h.get("rerank_score", 0.0)),
        excerpt=h.get("text", "")[:500],
        word_count=int(h.get("word_count", 0)),
        duration_seconds=int(round(float(h.get("end_time", 0)) - float(h.get("start_time", 0)))),
        topics=[],
        s3_audio_path=None,
        timestamp={"start_time": float(h.get("start_time", 0.0)),
                   "end_time": float(h.get("end_time", 0.0))},
    )


async def search_handler_aws(request: SearchRequest) -> SearchResponse:
    t0 = time.time()
    search_id = f"search_{uuid.uuid4().hex[:8]}"
    top_n = max(request.limit, 10)

    try:
        found = aws_search.search(request.query, top_n=top_n)
    except Exception as e:                                   # noqa: BLE001
        logger.error("[%s] AWS retrieval failed: %s", search_id, e)
        raise

    hits = found["results"]

    # Nothing cleared the cutoff. Say so; do not synthesise from what was
    # rejected, and do not dress weak results up as an answer.
    if found["no_matches"]:
        logger.info("[%s] no strong matches for %r (top %.6g < %.6g)",
                    search_id, request.query, found["top_score"], found["cutoff"])
        return SearchResponse(
            answer=None, results=[], total_results=0, search_id=search_id,
            query=request.query, limit=request.limit, offset=request.offset,
            search_method="aws_hybrid_rerank",
            processing_time_ms=int((time.time() - t0) * 1000),
            no_matches=True,
            no_matches_reason="Nothing in the library scored above the relevance floor.",
            top_score=found["top_score"], cutoff=found["cutoff"])

    answer, meta = synthesize(request.query, hits)

    # Retrieval found something but synthesis declined: the passages were on
    # topic without answering. That is still an honest "no", not an error.
    if answer is None and meta.get("declined"):
        logger.info("[%s] synthesis declined: %s", search_id, meta.get("reason"))
        window = hits[request.offset:request.offset + request.limit]
        return SearchResponse(
            answer=None, results=[_to_result(h) for h in window],
            total_results=len(hits), search_id=search_id, query=request.query,
            limit=request.limit, offset=request.offset,
            search_method="aws_hybrid_rerank",
            processing_time_ms=int((time.time() - t0) * 1000),
            no_matches=True,
            no_matches_reason="Passages were retrieved, but none of them answered the question.",
            top_score=found["top_score"], cutoff=found["cutoff"])

    window = hits[request.offset:request.offset + request.limit]
    return SearchResponse(
        answer=AnswerObject(**answer) if answer else None,
        results=[_to_result(h) for h in window],
        total_results=len(hits), search_id=search_id, query=request.query,
        limit=request.limit, offset=request.offset,
        search_method="aws_hybrid_rerank",
        processing_time_ms=int((time.time() - t0) * 1000),
        no_matches=False, top_score=found["top_score"], cutoff=found["cutoff"])
