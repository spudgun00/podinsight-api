"""Market Narratives, from the discovered_topics index.

Phase E part B, 2026-08-28. The mock card read "67 narrative shifts detected,
up 24 from last week" - two invented numbers over a week that does not exist.
This serves the 23 clusters the discovery engine found and its three rules let
through.

Two shapes matter here.

`series` is emitted in EXACTLY the shape /api/topic-mentions emits, down to the
`partial` flag on the last bucket, so the browser can hand a narrative straight
to SyntheaTrend.format. The floor and the colours then live in one place for
tracked topics and discovered ones alike, and the two cannot disagree.

The unit is CHUNKS, not mentions. A chunk is a passage of transcript, and one
episode contributes several, which is why chunks_per_episode is on every
document and why the breadth floor counts episodes and podcasts rather than
chunks. Callers are told the unit rather than left to assume.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from lib import aws_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/narratives", tags=["narratives"])

INDEX = "discovered_topics"
EPISODES_INDEX = "discovered_topic_episodes"

# 23 June 2025 is the last day in the corpus, so June is 23 of 30 days. The
# chart already draws it dashed and trend.js already refuses to use a partial
# bucket as a baseline; this flag is what tells them.
LAST_DAY = 23
DAYS_IN_JUNE = 30

RANKING = ("Ranked by breadth: distinct podcasts first, then distinct episodes. "
           "Breadth, not volume - a cluster one show talks about constantly is "
           "that show's preoccupation, not a narrative across the archive.")

METHOD = ("Discovered by clustering all 54,284 stored chunk embeddings, not by a "
          "hand-written topic list. Labels are written by Claude Sonnet 4.5 from "
          "the passages nearest each cluster centre, and ship only where it "
          "rated the label high confidence. Sponsor read-outs, clusters below a "
          "breadth floor of 8 podcasts and 40 episodes, and anything not "
          "confidently a single topic are excluded.")


class SeriesPoint(BaseModel):
    bucket: str
    mentions: int          # chunks; the key name matches /api/topic-mentions
    partial: bool = False


class Narrative(BaseModel):
    cluster_id: int
    topic: str
    total_mentions: int    # chunks, named to match the trend formatter's input
    chunks: int
    episodes: int
    podcasts: int
    chunks_per_episode: float
    change_pct: Optional[float] = None
    has_data: bool = True
    series: List[SeriesPoint] = []


class NarrativesResponse(BaseModel):
    narratives: List[Narrative]
    count: int
    unit: str = "chunks"
    ranking: str = RANKING
    method: str = METHOD
    excluded_count: int
    k: Optional[int] = None
    engine_version: Optional[int] = None
    labelling_model: Optional[str] = None
    generated_at: Optional[str] = None
    source: str = "opensearch"


class NarrativeEpisode(BaseModel):
    episode_id: str
    episode_title: str
    podcast_name: str
    published_at: Optional[str] = None
    chunk_count: int


class NarrativeDetail(BaseModel):
    cluster_id: int
    topic: str
    chunks: int
    episodes: int
    podcasts: int
    episodes_listed: List[NarrativeEpisode]
    truncated: bool = False
    samples: List[Dict[str, Any]] = []
    unit: str = "chunks"
    source: str = "opensearch"


def _series(monthly: Dict[str, int]) -> List[SeriesPoint]:
    out = []
    for b in sorted(monthly):
        out.append(SeriesPoint(bucket=b, mentions=int(monthly[b]),
                               partial=b.endswith("-06")))
    return out


def _change_pct(series: List[SeriesPoint]) -> Optional[float]:
    """Against the previous COMPLETE month, the same rule /api/topic-mentions
    uses. A partial bucket is never a baseline and never the compared value."""
    full = [p for p in series if not p.partial]
    if len(full) < 2:
        return None
    prev, last = full[-2].mentions, full[-1].mentions
    if prev <= 0:
        return None
    return round(100.0 * (last - prev) / prev, 1)


def _docs(client) -> List[Dict[str, Any]]:
    r = client.search(index=INDEX, body={"size": 200})
    return [h["_source"] for h in r["hits"]["hits"]]


@router.get("", response_model=NarrativesResponse)
async def narratives(limit: int = Query(12, ge=1, le=50)) -> NarrativesResponse:
    try:
        docs = _docs(aws_search.client())
    except Exception as e:                                   # noqa: BLE001
        logger.error("narratives failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Narratives unavailable: {e}")
    if not docs:
        raise HTTPException(status_code=404, detail="No discovered topics have been built")

    live = [d for d in docs if d.get("is_narrative")]
    live.sort(key=lambda d: (-d.get("podcasts", 0), -d.get("episodes", 0)))
    first = docs[0]
    out = []
    for d in live[:limit]:
        s = _series(d.get("monthly") or {})
        out.append(Narrative(
            cluster_id=d["cluster_id"], topic=d.get("label") or "(unlabelled)",
            total_mentions=d.get("chunks", 0), chunks=d.get("chunks", 0),
            episodes=d.get("episodes", 0), podcasts=d.get("podcasts", 0),
            chunks_per_episode=d.get("chunks_per_episode", 0.0),
            change_pct=_change_pct(s), has_data=bool(d.get("chunks")), series=s))
    return NarrativesResponse(
        narratives=out, count=len(live), excluded_count=len(docs) - len(live),
        k=first.get("k"), engine_version=first.get("engine_version"),
        labelling_model=first.get("labelling_model"),
        generated_at=first.get("generated_at"))


@router.get("/{cluster_id}", response_model=NarrativeDetail)
async def narrative(
    cluster_id: int = Path(...),
    limit: int = Query(300, ge=1, le=1000),
) -> NarrativeDetail:
    """The episodes behind a narrative, so the number can be opened and checked.

    Membership comes from `discovered_topic_episodes`, one document per (cluster,
    episode), which reconciles chunk-for-chunk and episode-for-episode against
    the cluster document. The cluster document's eight samples justify the label;
    they are not the episode list, and showing eight of 499 as if they were would
    be worse than showing none.

    Ordered the way the topic drilldown orders: biggest contributor first, most
    recent breaking ties.
    """
    try:
        client = aws_search.client()
        r = client.search(index=INDEX, body={
            "size": 1, "query": {"term": {"cluster_id": cluster_id}}})
    except Exception as e:                                   # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Narrative unavailable: {e}")
    hits = r["hits"]["hits"]
    if not hits:
        raise HTTPException(status_code=404, detail="No such narrative")
    d = hits[0]["_source"]
    if not d.get("is_narrative"):
        # Sponsor, filler, below the breadth floor, or not confidently one
        # topic. It has an id and counts, but it is not a narrative and does not
        # get a narrative's drilldown.
        raise HTTPException(status_code=404,
                            detail="That cluster is not a narrative: " + str(d.get("excluded_reason")))

    try:
        ep = client.search(index=EPISODES_INDEX, body={
            "size": limit, "query": {"term": {"cluster_id": cluster_id}},
            "sort": [{"chunk_count": "desc"}, {"published_at": "desc"}],
            "aggs": {"eps": {"cardinality": {"field": "episode_id",
                                             "precision_threshold": 4000}}}})
    except Exception as e:                                   # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Narrative unavailable: {e}")

    total_eps = ep["aggregations"]["eps"]["value"]
    listed = [NarrativeEpisode(
        episode_id=h["_source"]["episode_id"],
        episode_title=h["_source"].get("episode_title") or "(Untitled episode)",
        podcast_name=h["_source"].get("podcast_name") or "Unknown Podcast",
        published_at=(h["_source"].get("published_at") or "")[:10] or None,
        chunk_count=h["_source"].get("chunk_count", 0)) for h in ep["hits"]["hits"]]

    return NarrativeDetail(
        cluster_id=cluster_id, topic=d.get("label") or "(unlabelled)",
        chunks=d.get("chunks", 0), episodes=total_eps,
        podcasts=d.get("podcasts", 0), episodes_listed=listed,
        truncated=len(listed) < total_eps,
        samples=d.get("samples") or [])
