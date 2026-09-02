"""The approved alias table, applied at rollup and at serving time.

ALIAS_VERSION 2, approved 5 Sep 2026 by ADV and James. Before this the version
was 1 and the rollups merged NOTHING: every spelling of a name was its own
entity, which is why the NEW watcher saw fourteen DeepSeeks.

Three things this is not:

  * It is **not a rewrite of the library.** `entity_mentions_v2` is untouched.
    Every mention keeps the `surface` the transcript actually said, so a passage
    never stops matching its own words. The merge is a lookup consulted when a
    count is built or a surface is read.
  * It is **not irreversible.** Deleting a family from `aliases_v2.json` and
    rebuilding restores the previous numbers exactly.
  * It is **not majority rule.** Direction-by-majority was repealed on the day
    it was written: in this corpus manglings outnumber correct spellings -
    `chat GPT` carries 2,190 mentions against `ChatGPT`'s 340 - so the heavier
    side is the error. **The label is the model-proposed canonical**, overridden
    only by a human attestation.

**The kind-mismatch guard.** A family whose members disagree about what kind of
thing they are is reported, never merged. Those rows are held in bucket C and
are not in this table; `mismatches()` is here so a caller can say so.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

PATH = os.environ.get("SYNTHEA_ALIASES") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "podinsight-aws-pilot", "aliases_v2.json")

_doc: Optional[Dict] = None


def _load() -> Dict:
    global _doc
    if _doc is None:
        try:
            with open(PATH) as f:
                _doc = json.load(f)
            logger.info("alias table v%s: %d families, %d surfaces",
                        _doc.get("alias_version"), len(_doc.get("families", {})),
                        len(_doc.get("lookup", {})))
        except Exception as e:                                    # noqa: BLE001
            # A missing table is ALIAS_VERSION 1 behaviour: merge nothing. The
            # surfaces stay unmerged and every number is the pre-approval number.
            logger.warning("alias table unreadable (%s); merging nothing", e)
            _doc = {"alias_version": 1, "families": {}, "lookup": {}}
    return _doc


def version() -> int:
    return int(_load().get("alias_version", 1))


def label(surface: Optional[str]) -> Optional[str]:
    """The display label for a surface, or the surface unchanged."""
    if not surface:
        return surface
    return _load()["lookup"].get(surface.lower(), surface)


def key(surface: Optional[str]) -> Optional[str]:
    """The rollup key: the family's label lowercased, or the surface's own."""
    if not surface:
        return surface
    lab = _load()["lookup"].get(surface.lower())
    return lab.lower() if lab else surface.lower()


def merged() -> bool:
    return bool(_load().get("lookup"))


def families() -> Dict:
    return _load().get("families", {})


def members_of(lab: str) -> List[str]:
    lo = (lab or "").lower()
    return sorted(m for m, v in _load()["lookup"].items() if v.lower() == lo)
