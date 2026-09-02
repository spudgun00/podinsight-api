"""Topic co-occurrence, served from the AWS rollup index.

Phase 2, 2026-08-27. Replaces the MongoDB implementation. Two topics
"co-occur" when both are mentioned in the same episode.

A pair is only meaningful when both topics clear a floor: with DePIN present in
2 episodes of 1,236, any overlap it has is noise, and reporting a Jaccard score
for it would dress a coincidence up as a signal.
"""
import logging
import threading
from itertools import combinations
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search
from lib import snapshots as _S

def _S_key(w):
    """The snapshot key for a window argument, which may be a raw string."""
    try:
        from lib import window as _W
        return (_W.resolve(w) or {}).get("key", "all") if isinstance(w, str) else "all"
    except Exception:                                         # noqa: BLE001
        return "all"


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["topic-correlations"])

ROLLUP_INDEX = "topic_mentions"
MIN_EPISODES = 5

_cache: Optional["CorrelationsResponse"] = None
# Handlers run in FastAPI's threadpool (they are sync, because their work is
# blocking I/O). Two first-callers could otherwise build this cache at the
# same time and each pay the full scan.
_lock = threading.Lock()


class TopicPair(BaseModel):
    topic_a: str
    topic_b: str
    episodes_a: int
    episodes_b: int
    both: int
    either: int
    jaccard: float
    expected_if_unrelated: float
    meaningful: bool


class CorrelationsResponse(BaseModel):
    pairs: List[TopicPair]
    topic_episode_counts: Dict[str, int]
    episodes_scanned: int
    meaningful_pairs: int
    note: str
    source: str = "opensearch"


def _build() -> CorrelationsResponse:
    os_ = aws_search.client()
    sets: Dict[str, set] = {}
    after = None
    episodes = set()
    while True:
        body = {"size": 5000, "sort": [{"_doc": "asc"}],
                "_source": ["episode_id", "topic", "mention_count"]}
        if after:
            body["search_after"] = after
        hits = os_.search(index=ROLLUP_INDEX, body=body)["hits"]["hits"]
        if not hits:
            break
        for h in hits:
            s = h["_source"]
            episodes.add(s["episode_id"])
            if s.get("mention_count", 0) > 0:
                sets.setdefault(s["topic"], set()).add(s["episode_id"])
        after = hits[-1]["sort"]

    counts = {t: len(v) for t, v in sets.items()}
    total = len(episodes) or 1
    pairs = []
    for a, b in combinations(sorted(sets), 2):
        both = len(sets[a] & sets[b])
        either = len(sets[a] | sets[b])
        meaningful = counts[a] >= MIN_EPISODES and counts[b] >= MIN_EPISODES
        pairs.append(TopicPair(
            topic_a=a, topic_b=b, episodes_a=counts[a], episodes_b=counts[b],
            both=both, either=either,
            jaccard=round(both / either, 4) if either else 0.0,
            # What the overlap would be if the two topics were independent.
            expected_if_unrelated=round(counts[a] * counts[b] / total, 1),
            meaningful=meaningful))
    pairs.sort(key=lambda p: (p.meaningful, p.jaccard), reverse=True)
    n_meaningful = sum(1 for p in pairs if p.meaningful)
    return CorrelationsResponse(
        pairs=pairs, topic_episode_counts=counts, episodes_scanned=len(episodes),
        meaningful_pairs=n_meaningful,
        note=(f"A pair is meaningful when both topics appear in at least "
              f"{MIN_EPISODES} episodes. {n_meaningful} of {len(pairs)} pairs qualify; "
              f"the rest involve a topic too sparse in this corpus to correlate."))


@router.get("/topic-correlations", response_model=CorrelationsResponse)
def topic_correlations(refresh: bool = Query(False)) -> CorrelationsResponse:
    # Finding 5: serve the prebuilt snapshot when there is one. This path
    # touches OpenSearch NOT AT ALL, which is the point - the engine scales to
    # zero and waking it cost the front page 13 to 30 seconds. A missing or
    # failed snapshot returns None and the live path below runs unchanged.
    _snap = _S.panel(_S_key("all"), "topic-correlations")
    if _snap is not None:
        return CorrelationsResponse(**_snap)

    global _cache
    try:
        if _cache is None or refresh:
            with _lock:
                if _cache is None or refresh:
                    _cache = _build()
    except Exception as e:                                   # noqa: BLE001
        logger.error("topic-correlations failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Topic correlations unavailable: {e}")
    return _cache
