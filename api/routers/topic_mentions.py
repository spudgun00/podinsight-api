"""Topic mentions, served from the AWS rollup index.

Phase 2, 2026-08-27. Replaces the MongoDB topic_mentions collection with the
OpenSearch index of the same name, built by
podinsight-aws-pilot/build_topic_mentions_aws.py from all 1,236 episodes.

Two things the caller needs to know and the old endpoint could not tell it:

  has_data      DePIN has 2 mentions in 2 episodes across the whole corpus and
                4 of 6 months empty. It is returned with its real zeros and
                has_data false. It is not plotted and it is not padded.
  partial       The corpus ends 2025-06-23, so June covers 23 of 30 days and
                thins sharply after the 13th. The final bucket is flagged so
                the chart can render it distinctly rather than showing a
                truncated month as a decline.
"""
import calendar
import logging
from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["topic-mentions"])

ROLLUP_INDEX = "topic_mentions"
TOPICS = ["AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS", "Crypto/Web3"]
# A topic needs a real presence before a line through it means anything.
MIN_EPISODES_TO_PLOT = 5

_cache: Optional["TopicMentionsResponse"] = None


class BucketPoint(BaseModel):
    bucket: str
    mentions: int
    episodes: int
    mentions_per_episode: float
    partial: bool = False
    days_covered: Optional[int] = None
    days_in_bucket: Optional[int] = None


class TopicSeries(BaseModel):
    topic: str
    total_mentions: int
    episodes_with_mentions: int
    has_data: bool
    change_pct: Optional[float] = None
    series: List[BucketPoint]


class TopicMentionsResponse(BaseModel):
    bucket: str
    buckets: List[str]
    topics: List[TopicSeries]
    episodes_scanned: int
    range_from: Optional[str] = None
    range_to: Optional[str] = None
    terms_version: Optional[int] = None
    source: str = "opensearch"


def _build() -> TopicMentionsResponse:
    os_ = aws_search.client()

    rng = os_.search(index=aws_search.INDEX, body={"size": 0, "aggs": {
        "min": {"min": {"field": "published_at"}},
        "max": {"max": {"field": "published_at"}}}})["aggregations"]
    first = (rng["min"]["value_as_string"] or "")[:10]
    last = (rng["max"]["value_as_string"] or "")[:10]

    episodes = os_.search(index=ROLLUP_INDEX, body={"size": 0, "aggs": {
        "e": {"cardinality": {"field": "episode_id", "precision_threshold": 4000}}}}
        )["aggregations"]["e"]["value"]

    r = os_.search(index=ROLLUP_INDEX, body={"size": 0, "aggs": {
        "t": {"terms": {"field": "topic", "size": 20}, "aggs": {
            "m": {"terms": {"field": "month", "size": 36, "order": {"_key": "asc"}},
                  "aggs": {"mentions": {"sum": {"field": "mention_count"}},
                           "eps": {"filter": {"range": {"mention_count": {"gt": 0}}}}}},
            "total": {"sum": {"field": "mention_count"}},
            "eps_any": {"filter": {"range": {"mention_count": {"gt": 0}}}}}}}})

    by_topic = {b["key"]: b for b in r["aggregations"]["t"]["buckets"]}
    months = sorted({m["key"] for b in by_topic.values() for m in b["m"]["buckets"] if m["key"]})

    def coverage(month: str):
        """How much of this calendar month the corpus actually covers."""
        y, mo = int(month[:4]), int(month[5:7])
        in_month = calendar.monthrange(y, mo)[1]
        f, l = date.fromisoformat(first), date.fromisoformat(last)
        start = max(date(y, mo, 1), f)
        end = min(date(y, mo, in_month), l)
        covered = (end - start).days + 1 if end >= start else 0
        return covered, in_month

    series_out = []
    for topic in TOPICS:
        b = by_topic.get(topic)
        buckets = {m["key"]: m for m in (b["m"]["buckets"] if b else [])}
        pts = []
        for month in months:
            mb = buckets.get(month)
            mentions = int(mb["mentions"]["value"]) if mb else 0
            eps = mb["eps"]["doc_count"] if mb else 0
            cov, in_month = coverage(month)
            pts.append(BucketPoint(
                bucket=month, mentions=mentions, episodes=eps,
                mentions_per_episode=round(mentions / eps, 2) if eps else 0.0,
                partial=cov < in_month, days_covered=cov, days_in_bucket=in_month))
        total = int(b["total"]["value"]) if b else 0
        eps_any = b["eps_any"]["doc_count"] if b else 0

        # Change is computed on complete buckets only. Measuring the last full
        # month against a 23-day one would report a fall that is an artefact of
        # where the corpus stops.
        full = [p for p in pts if not p.partial]
        change = None
        if len(full) >= 2 and full[-2].mentions:
            change = round((full[-1].mentions - full[-2].mentions) / full[-2].mentions * 100, 1)

        series_out.append(TopicSeries(
            topic=topic, total_mentions=total, episodes_with_mentions=eps_any,
            has_data=eps_any >= MIN_EPISODES_TO_PLOT, change_pct=change, series=pts))

    return TopicMentionsResponse(
        bucket="month", buckets=months, topics=series_out,
        episodes_scanned=episodes, range_from=first, range_to=last, terms_version=1)


@router.get("/topic-mentions", response_model=TopicMentionsResponse)
async def topic_mentions(refresh: bool = Query(False)) -> TopicMentionsResponse:
    global _cache
    try:
        if _cache is None or refresh:
            _cache = _build()
    except Exception as e:                                   # noqa: BLE001
        logger.error("topic-mentions failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Topic mentions unavailable: {e}")
    return _cache
