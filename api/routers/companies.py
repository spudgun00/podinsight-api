"""Company Tracking v1: a watchlist over the filtered entity index.

Phase E, 2026-08-28. The mock Company Tracking invented everything it showed -
mention counts, a sentiment percentage, a "last insight" line, and a badge that
cycled 1 -> 2 -> 3 every five minutes. None of it came from the corpus.

What is real, and all this serves:

  * which companies the corpus names at all      -> the `entities` rollup
  * which episodes name a given company, and how
    often in each                                -> the `entity_episodes` index

Both are built from the same S3 cleaned_entities artefacts under the same
curation - the same kept spaCy labels, the same versioned stoplist, the same
alias table - so a company that is searchable here is always openable, and the
two never disagree about what it is called. Every response carries those three
version numbers, because a caller should be able to tell the list has been
shaped.

Counts only. There are no percentages anywhere in this module: the one number a
percentage would express - a share of episodes - is unstable at the low end,
where most watchlist companies live, and the project's volume floor exists to
suppress exactly that. A count of episodes is a fact at any size, so DePIN's two
episodes and Openai's 446 are reported the same way.

Nothing here is alerting. There is no "new since last visit" and no unread
count: the corpus is six fixed months ending 23 June 2025, so nothing is new,
and until forward ingestion exists nothing can be.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/companies", tags=["companies"])

ROLLUP_INDEX = "entities"
PAIRS_INDEX = "entity_episodes"

EXTRACTION_NOTE = (
    "Mentions come from automated entity extraction over the transcripts, not "
    "from a curated company list. Spelling variants, ticker symbols and "
    "abbreviations are counted separately unless an explicit alias folds them "
    "together, so a count is a floor rather than an exact total.")


class CompanyMatch(BaseModel):
    name: str
    episode_count: int
    podcast_count: int
    occurrences: int
    labels: List[str] = []


class SearchResponse(BaseModel):
    query: str
    matches: List[CompanyMatch]
    extraction_note: str = EXTRACTION_NOTE
    filter_version: Optional[int] = None
    stoplist_version: Optional[int] = None
    alias_version: Optional[int] = None
    source: str = "opensearch"


class CompanyEpisode(BaseModel):
    episode_id: str
    episode_title: str
    podcast_name: str
    published_at: Optional[str] = None
    mention_count: int


class CompanyResponse(BaseModel):
    name: str
    episode_count: int
    total_mentions: int
    podcast_count: int
    period: str
    episodes: List[CompanyEpisode]
    truncated: bool = False
    extraction_note: str = EXTRACTION_NOTE
    filter_version: Optional[int] = None
    stoplist_version: Optional[int] = None
    alias_version: Optional[int] = None
    source: str = "opensearch"


class EpisodeMention(BaseModel):
    name: str
    mention_count: int


class EpisodeMentionsResponse(BaseModel):
    episode_id: str
    # Only the names that are actually mentioned. A caller passing ten
    # watchlist names and getting two back knows the other eight are absent;
    # returning zeros would invite them to be rendered.
    mentioned: List[EpisodeMention]
    checked: int
    extraction_note: str = EXTRACTION_NOTE
    source: str = "opensearch"


def _norm(name: str) -> str:
    return name.strip().lower()


def _versions(*sources: Dict[str, Any]) -> Dict[str, Any]:
    """First non-null wins, across the documents we happened to read.

    The `entities` rollup predates the alias table being versioned in its
    documents and carries no alias_version, while `entity_episodes` does. Rather
    than report null for a version that exists, take each number from whichever
    index actually records it.
    """
    out = {"filter_version": None, "stoplist_version": None, "alias_version": None}
    for src in sources:
        for k in out:
            if out[k] is None and src.get(k) is not None:
                out[k] = src[k]
    return out


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(8, ge=1, le=25),
) -> SearchResponse:
    """Typeahead over the curated entity index.

    Prefix only, and only over names that survived the filter, the stoplist and
    the alias table. A user can therefore pick a canonical name or nothing -
    which is the point: a free-text watchlist would accumulate spellings the
    corpus never uses and quietly report zero for all of them.
    """
    try:
        os_ = aws_search.client()
        r = os_.search(index=ROLLUP_INDEX, body={
            "size": limit,
            "query": {"prefix": {"entity": _norm(q)}},
            "sort": [{"episode_count": "desc"}, {"occurrences": "desc"}]})
    except Exception as e:                                   # noqa: BLE001
        logger.error("company search failed for %r: %s", q, e)
        raise HTTPException(status_code=503, detail=f"Company search unavailable: {e}")

    hits = r["hits"]["hits"]
    first = hits[0]["_source"] if hits else {}
    pair = {}
    if first:
        try:
            pr = os_.search(index=PAIRS_INDEX, body={
                "size": 1, "query": {"term": {"entity": first["entity"]}}})
            pair = pr["hits"]["hits"][0]["_source"] if pr["hits"]["hits"] else {}
        except Exception:                                    # noqa: BLE001
            pair = {}          # versions are provenance, not the answer
    return SearchResponse(
        query=q,
        matches=[CompanyMatch(
            name=h["_source"]["display"],
            episode_count=h["_source"]["episode_count"],
            podcast_count=h["_source"]["podcast_count"],
            occurrences=h["_source"].get("occurrences", 0),
            labels=h["_source"].get("labels") or []) for h in hits],
        **_versions(first, pair))


@router.get("/mentions", response_model=EpisodeMentionsResponse)
async def episode_mentions(
    episode_id: str = Query(..., min_length=1),
    name: List[str] = Query(default_factory=list),
) -> EpisodeMentionsResponse:
    """Which of these companies does this episode mention, and how often.

    Serves the brief panel's watchlist tile. Empty `name` list is a valid
    request and returns nothing mentioned - that is the "no companies
    configured" case, and it should not be an error.
    """
    names = [n for n in (name or []) if n and n.strip()]
    if not names:
        return EpisodeMentionsResponse(episode_id=episode_id, mentioned=[], checked=0)
    if len(names) > 100:
        raise HTTPException(status_code=400, detail="At most 100 names per request")

    try:
        r = aws_search.client().search(index=PAIRS_INDEX, body={
            "size": len(names),
            "query": {"bool": {
                "filter": [{"term": {"episode_id": episode_id}},
                           {"terms": {"entity": [_norm(n) for n in names]}}]},
            },
            "sort": [{"mention_count": "desc"}]})
    except Exception as e:                                   # noqa: BLE001
        logger.error("episode mentions failed for %r: %s", episode_id, e)
        raise HTTPException(status_code=503, detail=f"Mentions unavailable: {e}")

    return EpisodeMentionsResponse(
        episode_id=episode_id,
        mentioned=[EpisodeMention(name=h["_source"]["display"],
                                  mention_count=h["_source"].get("mention_count", 0))
                   for h in r["hits"]["hits"]],
        checked=len(names))


@router.get("/{name}", response_model=CompanyResponse)
async def company(
    name: str,
    limit: int = Query(200, ge=1, le=1000),
) -> CompanyResponse:
    """One company: its totals, and the episodes behind them.

    404 when the corpus never names it. The UI turns that into "no mentions
    found in the library for that name" rather than adding it to the watchlist
    silently, so a watchlist never contains a row that can only ever read zero.
    """
    key = _norm(name)
    try:
        os_ = aws_search.client()
        roll = os_.search(index=ROLLUP_INDEX, body={
            "size": 1, "query": {"term": {"entity": key}}})
    except Exception as e:                                   # noqa: BLE001
        logger.error("company lookup failed for %r: %s", name, e)
        raise HTTPException(status_code=503, detail=f"Company unavailable: {e}")

    hits = roll["hits"]["hits"]
    if not hits:
        raise HTTPException(status_code=404, detail="No mentions in the library for that name")
    src = hits[0]["_source"]

    try:
        r = os_.search(index=PAIRS_INDEX, body={
            "size": limit,
            "query": {"term": {"entity": key}},
            # The drilldown's order, for the same reason: biggest contributors
            # first, most recent breaking ties.
            "sort": [{"mention_count": "desc"}, {"published_at": "desc"}],
            "aggs": {"total": {"sum": {"field": "mention_count"}},
                     "eps": {"cardinality": {"field": "episode_id",
                                             "precision_threshold": 4000}},
                     "first": {"min": {"field": "published_at"}},
                     "last": {"max": {"field": "published_at"}}}})
    except Exception as e:                                   # noqa: BLE001
        logger.error("company episodes failed for %r: %s", name, e)
        raise HTTPException(status_code=503, detail=f"Company unavailable: {e}")

    a = r["aggregations"]
    eps = a["eps"]["value"]
    first = (a["first"]["value_as_string"] or "")[:10]
    last = (a["last"]["value_as_string"] or "")[:10]
    return CompanyResponse(
        name=src["display"],
        episode_count=eps,
        total_mentions=int(a["total"]["value"]),
        podcast_count=src.get("podcast_count", 0),
        period=f"{first} to {last}" if first and last else "",
        episodes=[CompanyEpisode(
            episode_id=h["_source"]["episode_id"],
            episode_title=h["_source"].get("episode_title") or "(Untitled episode)",
            podcast_name=h["_source"].get("podcast_name") or "Unknown Podcast",
            published_at=(h["_source"].get("published_at") or "")[:10] or None,
            mention_count=h["_source"].get("mention_count", 0))
            for h in r["hits"]["hits"]],
        truncated=len(r["hits"]["hits"]) < eps,
        **_versions(src, r["hits"]["hits"][0]["_source"] if r["hits"]["hits"] else {}))
