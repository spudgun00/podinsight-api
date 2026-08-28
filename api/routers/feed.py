"""Narrative Feed, served from the pre-generated episode briefs.

Phase D, 2026-08-27. The mock feed was six hand-written items: a synthesised
event line ("consensus forming across 8 sources"), a relative timestamp against
a corpus that ends 23 June 2025, and a stance pill - CONSENSUS, DIVERGENCE,
TREND, LP INTEL, PATTERN - that nothing in the stack measures. Stance needs
claim matching and stance detection; retrieval does not produce it.

What replaces it is the one thing the brief store can honestly support: every
episode's brief, newest first. The ordering is a fact about the corpus, not a
judgement about it, so the panel can state its rule in a sentence and the
reader can check it.

Same store as /api/briefings, different question. /api/briefings ranks a
shortlist by tracked-topic density; this returns all 1,236 in date order with
an optional filter on the five tracked topics.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["feed"])

BRIEFS_INDEX = "episode_briefs"

# Stated on the panel, verbatim. If this sentence stops being true of the query
# below, one of the two is wrong.
ORDERING_SENTENCE = "Every episode's brief, newest first."

# from + size against AOSS is bounded by index.max_result_window (10,000). The
# corpus is 1,236 briefs, so this ceiling is unreachable through the UI; it
# exists so a hand-made request gets a clear answer instead of a 500.
MAX_OFFSET = 9_000

# Only the card's fields, plus claims - which is mapped `enabled: false`, so it
# rides along in _source but is never indexed. It is counted here and dropped:
# the feed shows how many quotes an episode has, and the brief panel fetches
# the quotes themselves from /api/briefings/{episode_id} when a card is opened.
_CARD_FIELDS = ["episode_id", "podcast_name", "episode_title", "published_at",
                "hook", "topic_tags", "duration_minutes", "claims"]


class FeedItem(BaseModel):
    episode_id: str
    podcast_name: str
    episode_title: str
    published_at: Optional[str] = None
    hook: str = ""
    topic_tags: List[str] = []
    claim_count: int = 0
    duration_minutes: Optional[int] = None


class TopicCount(BaseModel):
    name: str
    count: int


class FeedResponse(BaseModel):
    items: List[FeedItem]
    # `total` is the count under the active filter; `corpus_total` is every
    # brief. The panel needs both: one drives "showing 30 of 489", the other
    # the All chip.
    total: int
    corpus_total: int
    offset: int
    limit: int
    has_more: bool
    topic: Optional[str] = None
    # Facet counts over the whole store, never over the filtered slice, so the
    # chips do not change their numbers as you click between them.
    topics: List[TopicCount] = []
    untagged: int = 0
    period: str
    ordering: str = ORDERING_SENTENCE
    source: str = "opensearch"


def _to_item(s: Dict[str, Any]) -> FeedItem:
    return FeedItem(
        episode_id=s["episode_id"],
        podcast_name=s.get("podcast_name") or "Unknown Podcast",
        episode_title=s.get("episode_title") or "(Untitled episode)",
        published_at=(s.get("published_at") or "")[:10] or None,
        hook=s.get("hook") or "",
        topic_tags=s.get("topic_tags") or [],
        claim_count=len(s.get("claims") or []),
        duration_minutes=s.get("duration_minutes"))


def _facets(client) -> Dict[str, Any]:
    """Tracked-topic counts and the corpus date range, over every brief.

    Separate from the page query so the numbers are the store's, not the
    filtered slice's.
    """
    r = client.search(index=BRIEFS_INDEX, body={"size": 0, "aggs": {
        "topics": {"terms": {"field": "topic_tags.keyword", "size": 50,
                             "order": {"_key": "asc"}}},
        "untagged": {"missing": {"field": "topic_tags.keyword"}},
        "first": {"min": {"field": "published_at"}},
        "last": {"max": {"field": "published_at"}},
    }})
    a = r["aggregations"]
    total = r["hits"]["total"]
    return {
        "topics": [TopicCount(name=b["key"], count=b["doc_count"])
                   for b in a["topics"]["buckets"]],
        "untagged": a["untagged"]["doc_count"],
        "first": (a["first"]["value_as_string"] or "")[:10],
        "last": (a["last"]["value_as_string"] or "")[:10],
        "corpus_total": total["value"] if isinstance(total, dict) else total,
    }


@router.get("/feed", response_model=FeedResponse)
def feed(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0, le=MAX_OFFSET),
    topic: Optional[str] = Query(None, description="One of the tracked topics"),
) -> FeedResponse:
    try:
        client = aws_search.client()
        facets = _facets(client)
    except Exception as e:                                   # noqa: BLE001
        logger.error("feed facets failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Feed unavailable: {e}")

    known = {t.name for t in facets["topics"]}
    if topic is not None and topic not in known:
        # The chips are built from the facet above, so the UI cannot ask for a
        # topic that is not here. A hand-made request gets told, rather than an
        # empty feed it would have to interpret.
        raise HTTPException(
            status_code=400,
            detail=f"Unknown topic. Tracked topics: {', '.join(sorted(known))}")

    body: Dict[str, Any] = {
        "size": limit,
        "from": offset,
        # published_at is day-granular and many episodes share a date, so the
        # sort needs a second, unique key. Without it a document can appear on
        # two pages, or on none, as ties are broken differently per request.
        "sort": [{"published_at": "desc"}, {"episode_id": "asc"}],
        "_source": _CARD_FIELDS,
    }
    if topic is not None:
        body["query"] = {"term": {"topic_tags.keyword": topic}}

    try:
        r = client.search(index=BRIEFS_INDEX, body=body)
    except Exception as e:                                   # noqa: BLE001
        logger.error("feed page failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Feed unavailable: {e}")

    hits = r["hits"]["hits"]
    total_h = r["hits"]["total"]
    total = total_h["value"] if isinstance(total_h, dict) else total_h
    return FeedResponse(
        items=[_to_item(h["_source"]) for h in hits],
        total=total,
        corpus_total=facets["corpus_total"],
        offset=offset,
        limit=limit,
        has_more=(offset + len(hits)) < total,
        topic=topic,
        topics=facets["topics"],
        untagged=facets["untagged"],
        period=f"{facets['first']} to {facets['last']}")
