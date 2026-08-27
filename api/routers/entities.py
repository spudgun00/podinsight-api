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
    entities: List[Entity]
    count_basis: str
    total_entities: int
    episodes_covered: int
    labels: List[str]
    curated: bool = True
    filter_version: Optional[int] = None
    stoplist_version: Optional[int] = None
    curation_note: str
    source: str = "opensearch"


@router.get("/entities", response_model=EntitiesResponse)
async def entities(
    limit: int = Query(10, ge=1, le=200),
    min_episodes: int = Query(2, ge=1),
    q: Optional[str] = Query(None, description="prefix filter on the entity name"),
) -> EntitiesResponse:
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
        eps = os_.search(index=aws_search.INDEX, body={"size": 0, "aggs": {
            "e": {"cardinality": {"field": "episode_id", "precision_threshold": 4000}}}}
            )["aggregations"]["e"]["value"]
    except Exception as e:                                   # noqa: BLE001
        logger.error("entities failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Entities unavailable: {e}")

    return EntitiesResponse(
        entities=[Entity(text=h["_source"]["display"],
                         labels=h["_source"].get("labels") or [h["_source"]["label"]],
                         episode_count=h["_source"]["episode_count"],
                         podcast_count=h["_source"]["podcast_count"],
                         occurrences=h["_source"].get("occurrences", 0))
                  for h in r["hits"]["hits"]],
        count_basis="distinct episodes an entity appears in",
        total_entities=total, episodes_covered=eps, labels=KEEP_LABELS,
        filter_version=first.get("filter_version"),
        stoplist_version=first.get("stoplist_version"),
        curation_note=(
            "Curated list. Kept spaCy labels: PERSON, ORG, PRODUCT, GPE. Numeric and "
            "temporal labels are excluded because they are 48% of raw occurrences and "
            "dominate any frequency ranking. A versioned stoplist removes terms that "
            "carry a kept label but are not entities. Entities are merged across "
            "labels. spaCy's labels are the 2025 extraction's and contain known errors."))
