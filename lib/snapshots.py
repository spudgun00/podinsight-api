"""Prebuilt front-page snapshots, served from memory.

Finding 5, 2 Sep 2026. The front page used to ask OpenSearch ten questions on
every load, and OpenSearch scales to zero OCU when idle, so a cold load cost 13
to 30 seconds. Those answers are now computed ahead of time by
`scripts/build_snapshots.py` and read from disk once, at import.

**Serving a snapshot touches OpenSearch not at all.** That is the whole point:
if the snapshot lived in the engine, reading it would wake the engine and the
tax would still be paid.

Three properties this must keep:

  * **A snapshot never answers a question.** Search, drilldowns and the
    watchlist go to the live engine, always. A question has to reach the whole
    library.
  * **A missing snapshot is not an error.** Every endpoint falls back to its
    live path, so an unbuilt or failed panel degrades to the old behaviour
    rather than to an empty panel.
  * **Staleness is visible, not assumed.** Each snapshot carries the time it was
    built and the library's newest episode at that moment, and both are served
    to the page so a reader can see what they are looking at.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "snapshots")

_cache: Dict[str, Any] = {}
_lock = threading.Lock()
_loaded = False

# The builder calls the route functions to compute payloads. Those routes now
# short-circuit to a snapshot, so without this the builder would read its own
# previous output and write it back - a snapshot that refreshes its timestamp
# forever while its numbers never move. Caught when a rebuild of the 90-day
# window "took" 0.01 seconds.
BYPASS = os.environ.get("SNAPSHOT_BUILD") == "1"


def _load() -> None:
    global _loaded
    with _lock:
        if _loaded:
            return
        for name in os.listdir(DIR) if os.path.isdir(DIR) else []:
            if not name.startswith("front-page-") or not name.endswith(".json"):
                continue
            key = name[len("front-page-"):-len(".json")]
            try:
                with open(os.path.join(DIR, name)) as f:
                    _cache[key] = json.load(f)
            except Exception as e:                            # noqa: BLE001
                logger.error("snapshot %s unreadable: %s", name, e)
        _loaded = True
        if _cache:
            logger.info("loaded %d front-page snapshots: %s",
                        len(_cache), ", ".join(sorted(_cache)))
        else:
            logger.warning("no front-page snapshots found in %s; every panel "
                           "will serve live", DIR)


def reload() -> int:
    """Re-read from disk. For a build session that has just rebuilt them."""
    global _loaded
    with _lock:
        _cache.clear()
        _loaded = False
    _load()
    return len(_cache)


def panel(window_key: str, name: str) -> Optional[Dict[str, Any]]:
    """One panel's prebuilt payload, or None to serve live.

    None is returned for a missing window, a missing panel, a panel the build
    recorded as failed, or a build in progress - all mean the same thing to a
    caller: there is no snapshot, use the engine.
    """
    if BYPASS:
        return None
    _load()
    snap = _cache.get(window_key)
    if not snap:
        return None
    p = (snap.get("panels") or {}).get(name)
    if not p or "payload" not in p:
        return None
    return p["payload"]


def stamp(window_key: str) -> Optional[Dict[str, Any]]:
    """When this window's snapshot was built, and against which library."""
    _load()
    snap = _cache.get(window_key)
    if not snap:
        return None
    return {
        "generated_at": snap.get("generated_at"),
        "library_newest": snap.get("library_newest"),
        "snapshot_version": snap.get("snapshot_version"),
        "build_seconds": snap.get("build_seconds"),
        "panels": sorted((snap.get("panels") or {})),
        "failed": [f["panel"] for f in (snap.get("failed") or [])],
    }


def status() -> Dict[str, Any]:
    """Every snapshot's stamp, for the self-check and for /api/snapshots."""
    _load()
    return {k: stamp(k) for k in sorted(_cache)}
