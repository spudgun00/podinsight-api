"""Named entities, served from the AWS rollup index.

Phase 2, 2026-08-27. Replaces the MongoDB episode_entities collection. Built by
podinsight-aws-pilot/build_entities_aws.py from the cleaned_entities artefacts
already in S3 for all 1,236 episodes - no NER pass was needed.

The list is CURATED, and the response says so. Raw spaCy output is truthful but
useless as a ranking: 48% of the 268,263 occurrences carry numeric or temporal
labels, and ranking by frequency returns "one", "first", "today", "two". Two
versioned filters are applied and both versions are returned so a consumer can
tell the list has been shaped:

  filter_version    which spaCy labels are kept
  stoplist_version  which terms are excluded despite carrying a kept label

Entities are merged across labels. spaCy tags "Trump" as ORG in 441 episodes
and PERSON in 285; they are one entity.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search
from lib import snapshots as _S
from lib import window as W
from lib.entity_coverage import coverage as entity_coverage

def _S_key(w):
    """The snapshot key for a window argument, which may be a raw string."""
    try:
        from lib import window as _W
        return (_W.resolve(w) or {}).get("key", "all") if isinstance(w, str) else "all"
    except Exception:                                         # noqa: BLE001
        return "all"


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["entities"])

ROLLUP_INDEX = "entities"
KEEP_LABELS = ["PERSON", "ORG", "PRODUCT", "GPE"]


class Entity(BaseModel):
    text: str
    labels: List[str]
    episode_count: int
    podcast_count: int
    occurrences: int


class EntitiesResponse(BaseModel):
    entity_coverage: Optional[dict] = None
    entities: List[Entity]
    count_basis: str
    total_entities: int
    episodes_covered: int
    labels: List[str]
    curated: bool = True
    filter_version: Optional[int] = None
    stoplist_version: Optional[int] = None
    curation_note: str
    window: Optional[dict] = None
    source: str = "opensearch"


def _windowed(limit: int, min_episodes: int, q, w) -> "EntitiesResponse":
    """Ranked entities inside a window, from `entity_episodes`.

    The `entities` rollup is pre-aggregated over all time and carries no dates,
    so it cannot answer a windowed question at all. `entity_episodes` holds one
    document per (entity, episode) WITH a date, which makes the arithmetic exact
    rather than approximate: the bucket's `doc_count` IS the entity's episode
    count for the window, because there is exactly one row per pair. No
    cardinality estimate is involved.
    """
    os_ = aws_search.client()
    filters = [W.filter_clause(w)]
    if q:
        filters.append({"prefix": {"entity": q.lower()}})
    body = {"size": 0, "query": {"bool": {"filter": filters}}, "aggs": {
        "e": {"terms": {"field": "entity",
                        # Well above `limit` so the top slice is stable; the
                        # ordering key is doc_count, which is exact per shard.
                        "size": max(limit * 10, 300),
                        "order": {"_count": "desc"}},
              "aggs": {"mentions": {"sum": {"field": "mention_count"}},
                       "pods": {"cardinality": {"field": "podcast_name"}},
                       "top": {"top_hits": {"size": 1, "_source": ["display", "kind"]}}}},
        "total": {"cardinality": {"field": "entity", "precision_threshold": 40000}},
        "eps": {"cardinality": {"field": "episode_id", "precision_threshold": 40000}}}}
    try:
        r = os_.search(index="entity_episodes", body=body)
    except Exception as e:                                   # noqa: BLE001
        logger.error("windowed entities failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Entities unavailable: {e}")
    a = r["aggregations"]
    rows = [b for b in a["e"]["buckets"] if b["doc_count"] >= min_episodes][:limit]
    ents = []
    for b in rows:
        src = (b["top"]["hits"]["hits"] or [{}])[0].get("_source", {})
        ents.append(Entity(
            text=src.get("display") or b["key"],
            labels=[src.get("kind")] if src.get("kind") else [],
            episode_count=b["doc_count"],
            podcast_count=int(b["pods"]["value"]),
            occurrences=int(b["mentions"]["value"])))
    return EntitiesResponse(
        entity_coverage=entity_coverage(), entities=ents,
        count_basis="distinct episodes an entity appears in, within the window",
        total_entities=int(a["total"]["value"]),
        episodes_covered=int(a["eps"]["value"]),
        labels=KEEP_LABELS, window=w,
        filter_version=None, stoplist_version=None,
        curation_note=("Ranked from entity_episodes inside the window, so the "
                       "counts are exact for the period rather than a slice of "
                       "an all-time rollup. Same curation as the rollup: entity "
                       "v2, stoplist v2, aliases proposed but not applied."))


@router.get("/entities", response_model=EntitiesResponse)
def entities(
    limit: int = Query(10, ge=1, le=200),
    min_episodes: int = Query(2, ge=1),
    q: Optional[str] = Query(None, description="prefix filter on the entity name"),
    window: str = Query(W.DEFAULT, description="30d | 90d | 12m | all"),
) -> EntitiesResponse:
    # Finding 5: serve the prebuilt snapshot when there is one. This path
    # touches OpenSearch NOT AT ALL, which is the point - the engine scales to
    # zero and waking it cost the front page 13 to 30 seconds. A missing or
    # failed snapshot returns None and the live path below runs unchanged.
    _snap = _S.panel(_S_key(window), "entities")
    if _snap is not None:
        return EntitiesResponse(**_snap)

    w = W.resolve(window)
    if not w.get("is_all"):
        return _windowed(limit, min_episodes, q, w)
    try:
        os_ = aws_search.client()
        must = [{"range": {"episode_count": {"gte": min_episodes}}}]
        if q:
            must.append({"prefix": {"entity": q.lower()}})
        r = os_.search(index=ROLLUP_INDEX, body={
            "size": limit, "query": {"bool": {"must": must}},
            "sort": [{"episode_count": "desc"}, {"occurrences": "desc"}]})
        total = os_.count(index=ROLLUP_INDEX, body={
            "query": {"bool": {"must": must}}})["count"]
        first = r["hits"]["hits"][0]["_source"] if r["hits"]["hits"] else {}
        # Episodes that actually HAVE entities, not episodes in the corpus.
        # These diverged when the 28 Aug 2026 backfill quadrupled the corpus
        # while entity extraction stayed at the pre-backfill episodes: the
        # surface was reading "of 4471" for counts drawn from 1,235.
        eps = os_.search(index="entity_episodes", body={"size": 0, "aggs": {
            "e": {"cardinality": {"field": "episode_id", "precision_threshold": 40000}}}}
            )["aggregations"]["e"]["value"]
    except Exception as e:                                   # noqa: BLE001
        logger.error("entities failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Entities unavailable: {e}")

    return EntitiesResponse(
        entity_coverage=entity_coverage(),
        entities=[Entity(text=h["_source"]["display"],
                         labels=h["_source"].get("labels") or [h["_source"]["label"]],
                         episode_count=h["_source"]["episode_count"],
                         podcast_count=h["_source"]["podcast_count"],
                         occurrences=h["_source"].get("occurrences", 0))
                  for h in r["hits"]["hits"]],
        count_basis="distinct episodes an entity appears in",
        total_entities=total, episodes_covered=eps, labels=KEEP_LABELS, window=w,
        filter_version=first.get("filter_version"),
        stoplist_version=first.get("stoplist_version"),
        curation_note=(
            "Curated list. Kept spaCy labels: PERSON, ORG, PRODUCT, GPE. Numeric and "
            "temporal labels are excluded because they are 48% of raw occurrences and "
            "dominate any frequency ranking. A versioned stoplist removes terms that "
            "carry a kept label but are not entities. Entities are merged across "
            "labels. spaCy's labels are the 2025 extraction's and contain known errors."))
