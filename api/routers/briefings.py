"""Priority Briefings, served from pre-generated episode briefs.

Phase D, 2026-08-27. The mock ranked episodes by an invented "Score: 97", framed
everything as "3h ago", and labelled stances (CONSENSUS FORMING, DIVERGENCE)
that nothing in the corpus measures. All of that is gone.

Briefs are generated once by podinsight-aws-pilot/generate_briefs.py and read
from the episode_briefs index. Nothing is generated per view.

Every number on a card is an input to the ranking, not an output of it:
mentions, words, and the density derived from them.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search
from lib import window as W

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["briefings"])

BRIEFS_INDEX = "episode_briefs"

RANKING_SENTENCE = (
    "Ranked by how densely each episode discusses the five tracked topics — "
    "mentions per 1,000 words — over episodes of at least 5,000 words, with at "
    "most two per podcast."
)


class Claim(BaseModel):
    claim: str
    quote: str
    start_seconds: Optional[float] = None
    timestamp: Optional[str] = None
    located: bool = False


class EntityMention(BaseModel):
    name: str
    count: int


class Speaker(BaseModel):
    """Role and affiliation only where the transcript stated them.

    Empty strings are meaningful here: they mean the episode never said, and a
    wrong affiliation is worse than a missing one.
    """
    name: str
    role: str = ""
    affiliation: str = ""


class Brief(BaseModel):
    episode_id: str
    podcast_name: str
    episode_title: str
    published_at: Optional[str] = None
    summary: str
    # One line, at most ~15 words, for the card. The long summary stays in the
    # full brief.
    hook: str = ""
    duration_minutes: Optional[int] = None
    # Tags and entity counts come from the corpus, not from the model: tags are
    # the tracked topics the episode actually mentions, entities are counted
    # from the 2025 extraction under the same filter and stoplist as
    # /api/entities.
    topic_tags: List[str] = []
    top_entities: List[EntityMention] = []
    speakers: List[Speaker] = []
    no_playable_claims: bool = False
    claims: List[Claim]
    guests: List[str] = []
    rank_position: int
    rank_mentions: int
    rank_words: int
    rank_density: float


class BriefingsResponse(BaseModel):
    briefs: List[Brief]
    count: int
    ranking: str
    period: str
    window: Optional[dict] = None
    prompt_version: Optional[int] = None
    validation_rules: Optional[str] = None
    generated_by: Optional[str] = None
    source: str = "opensearch"


def _to_brief(s: Dict[str, Any]) -> Brief:
    return Brief(
        episode_id=s["episode_id"], podcast_name=s.get("podcast_name") or "Unknown Podcast",
        episode_title=s.get("episode_title") or "(Untitled episode)",
        published_at=s.get("published_at"), summary=s.get("summary") or "",
        hook=s.get("hook") or "", duration_minutes=s.get("duration_minutes"),
        topic_tags=s.get("topic_tags") or [],
        top_entities=[EntityMention(**e) for e in (s.get("top_entities") or [])],
        speakers=[Speaker(**sp) for sp in (s.get("speakers") or [])],
        no_playable_claims=bool(s.get("no_playable_claims")),
        claims=[Claim(**c) for c in (s.get("claims") or [])],
        guests=s.get("guests") or [], rank_position=s.get("rank_position", 0),
        rank_mentions=s.get("rank_mentions", 0), rank_words=s.get("rank_words", 0),
        rank_density=s.get("rank_density", 0.0))


@router.get("/briefings", response_model=BriefingsResponse)
def briefings(limit: int = Query(12, ge=1, le=100),
              window: str = Query(W.DEFAULT, description="30d | 90d | 12m | all")
              ) -> BriefingsResponse:
    # This endpoint took the window parameter without using it: the page sent
    # `window=90d`, FastAPI ignored an unknown query field, and the panel printed
    # "Jan 2025 - Aug 2026" under a ninety-day control. Found by reading the
    # rendered label for truth rather than for presence.
    w = W.resolve(window)
    try:
        os_ = aws_search.client()
        _body = {"size": limit, "sort": [{"rank_position": "asc"}]}
        W.apply(_body, w)
        r = os_.search(index=BRIEFS_INDEX, body=_body)
        _rng = {"size": 0, "aggs": {
            "min": {"min": {"field": "published_at"}},
            "max": {"max": {"field": "published_at"}}}}
        W.apply(_rng, w)
        rng = os_.search(index=aws_search.INDEX, body=_rng)["aggregations"]
    except Exception as e:                                   # noqa: BLE001
        logger.error("briefings failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Briefings unavailable: {e}")

    hits = r["hits"]["hits"]
    first = (rng["min"].get("value_as_string") or "")[:10]
    last = (rng["max"].get("value_as_string") or "")[:10]
    return BriefingsResponse(
        briefs=[_to_brief(h["_source"]) for h in hits],
        count=r["hits"]["total"]["value"] if isinstance(r["hits"]["total"], dict) else len(hits),
        ranking=RANKING_SENTENCE,
        period=f"{first} to {last}", window=w,
        generated_by=(hits[0]["_source"].get("model") if hits else None),
        prompt_version=(hits[0]["_source"].get("prompt_version") if hits else None),
        validation_rules=(hits[0]["_source"].get("validation_rules") if hits else None))


@router.get("/briefings/{episode_id}", response_model=Brief)
def briefing(episode_id: str) -> Brief:
    try:
        r = aws_search.client().search(index=BRIEFS_INDEX, body={
            "size": 1, "query": {"term": {"episode_id": episode_id}}})
    except Exception as e:                                   # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Briefing unavailable: {e}")
    hits = r["hits"]["hits"]
    if not hits:
        raise HTTPException(status_code=404, detail="No brief for this episode")
    return _to_brief(hits[0]["_source"])
