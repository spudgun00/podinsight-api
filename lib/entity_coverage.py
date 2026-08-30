"""How far the entity extraction actually reaches.

The 28 Aug 2026 backfill took the corpus to 4,471 episodes, but entity
extraction reads precomputed NER artefacts that exist only for the original
1,236. So the entity surfaces are correct and incomplete at the same time, and
the only honest thing is for them to say through when they are complete.

Derived from entity_episodes itself, never written down, so the label
disappears on its own the moment extraction catches up.
"""
from typing import Optional, Dict, Any

from lib import aws_search

_cache: Optional[Dict[str, Any]] = None


def coverage(refresh: bool = False) -> Dict[str, Any]:
    global _cache
    if _cache is not None and not refresh:
        return _cache
    c = aws_search.client()
    ent = c.search(index="entity_episodes", body={"size": 0, "aggs": {
        "max": {"max": {"field": "published_at"}},
        "eps": {"cardinality": {"field": "episode_id",
                                "precision_threshold": 40000}}}})["aggregations"]
    corp = c.search(index=aws_search.INDEX, body={"size": 0, "aggs": {
        "max": {"max": {"field": "published_at"}},
        "eps": {"cardinality": {"field": "episode_id",
                                "precision_threshold": 40000}}}})["aggregations"]
    through = (ent["max"]["value_as_string"] or "")[:10] or None
    corpus_to = (corp["max"]["value_as_string"] or "")[:10] or None
    covered, total = ent["eps"]["value"], corp["eps"]["value"]
    _cache = {
        "entity_coverage_through": through,
        "corpus_through": corpus_to,
        "episodes_with_entities": covered,
        "episodes_in_corpus": total,
        # complete is the switch the front end reads: when extraction catches
        # up this goes true and the label stops rendering, with no deploy.
        "complete": bool(through and corpus_to and through >= corpus_to),
    }
    return _cache
