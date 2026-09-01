"""The Intelligence Brief: one cached document for the whole period.

Phase E, 2026-08-28. Serves the single document written by
podinsight-aws-pilot/build_intelligence_brief.py. Nothing is generated per
view, and nothing is computed here - this router is a reader.

The mock was a *weekly* brief with Consensus Forming, Contrarian Signals and
Emerging Blindspots. All three need claim matching across episodes, which is
the same wall Consensus Monitor was dropped for. The document says so in its
own absence note rather than leaving the reader to notice the gap.

Citations are returned resolved. A caller never has to look a claim up: every
id cited in the prose is a key in `citations`, whose value carries the claim,
its verbatim quote, its timestamp and whether the timestamp was located well
enough to play a clip from it.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search
from lib import window as W

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["intelligence-brief"])

INDEX = "intelligence_brief"


class Citation(BaseModel):
    id: str
    episode_id: str
    claim_index: int
    claim: str
    quote: str
    start_seconds: Optional[float] = None
    timestamp: Optional[str] = None
    located: bool = False
    episode_title: Optional[str] = None
    podcast_name: Optional[str] = None
    published_at: Optional[str] = None


class Sentence(BaseModel):
    text: str
    claim_ids: List[str]


class TopicParagraph(BaseModel):
    topic: str
    sentences: List[Sentence]


class ExcludedTopic(BaseModel):
    topic: str
    mentions: int
    reason: str


class NotableClaim(Citation):
    rank_position: Optional[int] = None


class BriefResponse(BaseModel):
    title: str
    generated_at: Optional[str] = None
    model: Optional[str] = None
    doc_version: Optional[int] = None
    facts: Dict[str, Any]
    window: Optional[dict] = None
    honours_window: bool = True
    window_note: Optional[str] = None
    dominated: List[TopicParagraph]
    dominated_excluded: List[ExcludedTopic] = []
    citations: Dict[str, Citation]
    notable_claims: List[NotableClaim] = []
    notable_rule: str = ""
    absence_note: str = ""
    validation_rules: str = ""
    sentences_dropped: List[Dict[str, Any]] = []
    generation_calls: Optional[int] = None
    cost_usd: Optional[float] = None
    source: str = "opensearch"


@router.get("/intelligence-brief", response_model=BriefResponse)
def intelligence_brief(
    window: str = Query(W.DEFAULT, description="30d | 90d | 12m | all"),
) -> BriefResponse:
    """The brief is a GENERATED document and cannot honour a window.

    Its prose is written once by Sonnet with every sentence citing claim ids,
    and the quote check has already passed over it. Filtering it to a window
    would leave sentences citing claims that are no longer shown - prose making
    a case from evidence the reader cannot see - which is worse than a brief
    that plainly states the period it covers.

    So it reports its own period and says it does not follow the control. The
    panel renders that in plain words rather than silently ignoring the window.
    Regenerating per window is a spend decision, not a rendering one.
    """
    w = W.resolve(window)
    try:
        r = aws_search.client().search(index=INDEX, body={
            "size": 1, "sort": [{"generated_at": "desc"}]})
    except Exception as e:                                   # noqa: BLE001
        logger.error("intelligence brief failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Brief unavailable: {e}")

    hits = r["hits"]["hits"]
    if not hits:
        raise HTTPException(status_code=404, detail="No brief has been generated")
    src = hits[0]["_source"]
    facts = src.get("facts") or {}
    doc_period = f"{facts.get('period_start','')} to {facts.get('period_end','')}".strip(" to ")
    return BriefResponse(
        **src,
        window=w,
        honours_window=w.get("is_all", False),
        window_note=(None if w.get("is_all") else
                     f"This brief covers {W.pretty(facts.get('period_start'))} to "
                     f"{W.pretty(facts.get('period_end'))}, the whole library. It is a "
                     f"written document with every sentence citing a verified claim, so "
                     f"it is not narrowed to {w['label'].lower()} - the prose would cite "
                     f"evidence the page no longer shows."))
