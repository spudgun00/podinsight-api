"""Theme series for the Narrative Pulse, in the shape the chart already reads.

Narrative Pulse v2, 2026-08-28. Per NARRATIVE_PULSE_VISION.md: themes are the
stable top layer over the discovered narratives.

`series` is emitted in EXACTLY the /api/topic-mentions shape - bucket, mentions,
episodes, mentions_per_episode, partial - so the chart plots a theme with the
code that plots a tracked topic, and SyntheaTrend applies the same floor to
both. A second plotting path would be a second set of rules.

The unit is PASSAGES. `mentions` carries them because that is the key the chart
reads; every response says `unit: "passages"` and the UI labels them as such.

Per-month episode counts are DISTINCT episodes, aggregated from
discovered_topic_episodes - an episode appearing in two of a theme's narratives
counts once. That is why normalisation cannot use the theme document's
`episodes_summed`, which is an upper bound.

Every response is cross-checked against the indexed theme totals and fails loudly
rather than serving a series that disagrees with its own drilldown.
"""
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search
from lib import window as W

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/themes", tags=["themes"])

THEMES_INDEX = "discovered_themes"
TOPIC_EPISODES = "discovered_topic_episodes"
NARRATIVES_INDEX = "discovered_topics"

# Partial-bucket logic lives in lib/window.partial_buckets - one place, and
# it replaced two hardcoded rules that were both wrong at corpus v3.

METHOD = ("Themes are a versioned map over the discovered narratives, not a list "
          "chosen in advance: a theme renders only where qualifying narratives "
          "exist under it. Sponsor, unlabelled and low-confidence clusters roll "
          "up nowhere. A theme's volume is the sum of its narratives'.")


class SeriesPoint(BaseModel):
    bucket: str
    mentions: int                  # passages; the key the chart reads
    episodes: int
    mentions_per_episode: float
    partial: bool = False


class Member(BaseModel):
    cluster_id: int
    label: str
    chunks: int
    episodes: int
    podcasts: int
    carried_by_few_shows: bool = False


class Theme(BaseModel):
    theme_key: str
    topic: str                     # the chart keys series by `topic`
    label: str
    why: str = ""
    narrative_count: int
    total_mentions: int            # passages
    episodes_with_mentions: int    # distinct across the whole period
    has_data: bool = True
    change_pct: Optional[float] = None
    series: List[SeriesPoint] = []
    members: List[Member] = []


class ThemesResponse(BaseModel):
    themes: List[Theme]
    buckets: List[str]
    unit: str = "passages"
    method: str = METHOD
    episodes_scanned: int
    range_from: Optional[str] = None
    range_to: Optional[str] = None
    theme_map_version: Optional[int] = None
    k: Optional[int] = None
    reconciled: bool = True
    window: Optional[dict] = None
    source: str = "opensearch"


def _theme_docs(client) -> List[Dict[str, Any]]:
    r = client.search(index=THEMES_INDEX, body={"size": 50})
    return [h["_source"] for h in r["hits"]["hits"]]


def _month_stats(client, cluster_ids: List[int], w=None) -> Dict[str, Dict[str, int]]:
    """Passages and DISTINCT episodes per month for a set of clusters."""
    if not cluster_ids:
        return {}
    body = {
        "size": 0, "query": {"terms": {"cluster_id": cluster_ids}},
        "aggs": {"m": {"date_histogram": {"field": "published_at",
                                          "calendar_interval": "month",
                                          "format": "yyyy-MM"},
                       "aggs": {"passages": {"sum": {"field": "chunk_count"}},
                                "eps": {"cardinality": {"field": "episode_id",
                                                        "precision_threshold": 4000}}}}}}
    if w is not None:
        W.apply(body, w)
    r = client.search(index=TOPIC_EPISODES, body=body)
    out = {}
    for b in r["aggregations"]["m"]["buckets"]:
        out[b["key_as_string"]] = {"mentions": int(b["passages"]["value"]),
                                   "episodes": int(b["eps"]["value"])}
    return out


def _change_pct(series: List[SeriesPoint]) -> Optional[float]:
    """Against the previous COMPLETE month, as /api/topic-mentions does."""
    full = [p for p in series if not p.partial]
    if len(full) < 2 or full[-2].mentions <= 0:
        return None
    return round(100.0 * (full[-1].mentions - full[-2].mentions) / full[-2].mentions, 1)


@router.get("", response_model=ThemesResponse)
def themes(limit: int = Query(6, ge=1, le=12),
           window: str = Query(W.DEFAULT, description="30d | 90d | 12m | all")
           ) -> ThemesResponse:
    w = W.resolve(window)
    try:
        client = aws_search.client()
        docs = _theme_docs(client)
    except Exception as e:                                   # noqa: BLE001
        logger.error("themes failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Themes unavailable: {e}")
    if not docs:
        raise HTTPException(status_code=404, detail="No themes have been built")

    try:
        _rng_body = {"size": 0, "aggs": {
            "first": {"min": {"field": "published_at"}},
            "last": {"max": {"field": "published_at"}},
            "eps": {"cardinality": {"field": "episode_id",
                                    "precision_threshold": 4000}}}}
        W.apply(_rng_body, w)
        rng = client.search(index=aws_search.INDEX, body=_rng_body)["aggregations"]
    except Exception as e:                                   # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Themes unavailable: {e}")

    # Buckets inside the window only. The indexed `monthly` map spans the whole
    # library; a 30-day window must plot one month, not twenty with nineteen zeros.
    mr = W.month_range(w)
    buckets = sorted({b for d in docs for b in (d.get("monthly") or {})})
    if mr:
        buckets = [b for b in buckets if mr[0] <= b <= mr[1]]
    partials = W.partial_buckets(w)
    docs.sort(key=lambda d: -d.get("chunks", 0))

    out, reconciled = [], True
    for d in docs[:limit]:
        members = d.get("members") or []
        ids = [m["cluster_id"] for m in members]
        stats = _month_stats(client, ids, w)

        series = []
        for b in buckets:
            s = stats.get(b, {"mentions": 0, "episodes": 0})
            eps = s["episodes"]
            series.append(SeriesPoint(
                bucket=b, mentions=s["mentions"], episodes=eps,
                mentions_per_episode=round(s["mentions"] / eps, 2) if eps else 0.0,
                partial=(b in partials)))

        # The series must add up to the indexed theme total, or the chart would
        # sit above a drilldown that contradicts it. Inside a window the series
        # is a SUBSET of the indexed monthly map, so the check runs bucket by
        # bucket over the windowed buckets only - which is still the guarantee
        # that matters: every plotted point equals what the index holds for it.
        indexed = d.get("monthly") or {}
        for p in series:
            if p.partial:
                continue        # a half month cannot equal a whole-month total
            if p.mentions != int(indexed.get(p.bucket, 0)):
                reconciled = False
                logger.error("theme %s bucket %s: series %s vs indexed %s",
                             d.get("theme_key"), p.bucket, p.mentions,
                             indexed.get(p.bucket))

        total_eps = 0
        if ids:
            _te_body = {
                "size": 0, "query": {"terms": {"cluster_id": ids}},
                "aggs": {"eps": {"cardinality": {"field": "episode_id",
                                                 "precision_threshold": 4000}}}}
            W.apply(_te_body, w)
            total_eps = client.search(index=TOPIC_EPISODES, body=_te_body
                                      )["aggregations"]["eps"]["value"]

        out.append(Theme(
            theme_key=d["theme_key"], topic=d["label"], label=d["label"],
            why=d.get("why", ""), narrative_count=d.get("narrative_count", 0),
            total_mentions=(sum(p.mentions for p in series) if not w.get("is_all")
                            else d.get("chunks", 0)),
            episodes_with_mentions=total_eps,
            has_data=bool(sum(p.mentions for p in series) if not w.get("is_all")
                          else d.get("chunks")),
            change_pct=_change_pct(series),
            series=series,
            members=[Member(cluster_id=m["cluster_id"], label=m["label"],
                            chunks=m["chunks"], episodes=m["episodes"],
                            podcasts=m["podcasts"],
                            carried_by_few_shows=bool(m.get("carried_by_few_shows")))
                     for m in members]))

    if not reconciled:
        raise HTTPException(
            status_code=503,
            detail="Theme series do not reconcile with the indexed theme totals")

    first = docs[0]
    return ThemesResponse(
        themes=out, buckets=buckets, window=w,
        episodes_scanned=rng["eps"]["value"],
        range_from=(rng["first"].get("value_as_string") or "")[:10],
        range_to=(rng["last"].get("value_as_string") or "")[:10],
        theme_map_version=first.get("theme_map_version"), k=first.get("k"))
