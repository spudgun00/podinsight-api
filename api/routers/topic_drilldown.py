"""The episodes behind a topic-mentions number.

Phase D, 2026-08-27. Narrative Pulse and Velocity Tracking show a count per
topic per month; this returns the episodes that make up that count, so a number
on the chart can be opened and checked.

Reads the same `topic_mentions` rollup the chart reads, so the drilldown total
always reconciles with the bar it came from - it is the same documents,
unaggregated.

No volume floor applies here. A floor is right for a *rate of change*, where a
small denominator makes the percentage unstable; a count of episodes is a fact.
DePIN drills down to its two episodes, and that is the honest answer rather than
a suppressed one.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["topic-drilldown"])

ROLLUP_INDEX = "topic_mentions"


class DrilldownEpisode(BaseModel):
    episode_id: str
    episode_title: str
    podcast_name: str
    published_at: Optional[str] = None
    mention_count: int
    chunks_scanned: int
    feed_slug: Optional[str] = None


class DrilldownResponse(BaseModel):
    topic: str
    month: Optional[str] = None
    scope: str
    episodes: List[DrilldownEpisode]
    episode_count: int
    total_mentions: int
    truncated: bool = False
    source: str = "opensearch"


@router.get("/topic-drilldown", response_model=DrilldownResponse)
def topic_drilldown(
    topic: str = Query(..., min_length=1, max_length=64),
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    limit: int = Query(200, ge=1, le=1000),
) -> DrilldownResponse:
    must = [{"term": {"topic": topic}},
            {"range": {"mention_count": {"gt": 0}}}]
    if month:
        must.append({"term": {"month": month}})

    try:
        os_ = aws_search.client()
        r = os_.search(index=ROLLUP_INDEX, body={
            "size": limit,
            "query": {"bool": {"must": must}},
            # Count first, then most recent, so the biggest contributors lead.
            "sort": [{"mention_count": "desc"}, {"published_at": "desc"}],
            "aggs": {"total": {"sum": {"field": "mention_count"}},
                     "eps": {"cardinality": {"field": "episode_id",
                                             "precision_threshold": 4000}}}})
    except Exception as e:                                   # noqa: BLE001
        logger.error("topic-drilldown failed for %r/%r: %s", topic, month, e)
        raise HTTPException(status_code=503, detail=f"Drilldown unavailable: {e}")

    hits = r["hits"]["hits"]
    total_eps = r["aggregations"]["eps"]["value"]
    return DrilldownResponse(
        topic=topic, month=month,
        scope=month or "whole period",
        episodes=[DrilldownEpisode(
            episode_id=h["_source"]["episode_id"],
            episode_title=h["_source"].get("episode_title") or "(Untitled episode)",
            podcast_name=h["_source"].get("podcast_name") or "Unknown Podcast",
            published_at=h["_source"].get("published_at"),
            mention_count=h["_source"].get("mention_count", 0),
            chunks_scanned=h["_source"].get("chunks_scanned", 0),
            feed_slug=h["_source"].get("feed_slug")) for h in hits],
        episode_count=total_eps,
        total_mentions=int(r["aggregations"]["total"]["value"]),
        truncated=len(hits) < total_eps)
