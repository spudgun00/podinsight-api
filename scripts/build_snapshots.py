#!/usr/bin/env python3
"""Prebuild the front page, one JSON snapshot per window.

Finding 5, 2 Sep 2026. The front page was paying the search engine's wake-up
tax: 13 to 30 seconds on a cold load, because every panel asked OpenSearch a
question at request time and the collection scales to zero OCU when idle. That
price is the honest cost of scale-to-zero for a *question*. It is not the honest
cost of a front page over a library that changes once a week.

So the panels stop asking. Every front-page endpoint's answer is computed here,
ahead of time, four times - once per window - and written to disk. The API loads
those files at start-up and serves them from memory, so rendering the front page
touches OpenSearch **not at all** and is independent of whether the engine is
awake.

**Why files and not an index.** The episodes-catalogue pattern this follows puts
its rollup in OpenSearch, and that is right for a rollup a query needs to join
against. It is wrong here: reading a snapshot out of OpenSearch would still wake
OpenSearch, which is the entire cost being removed. The files are a few hundred
kilobytes, they sit beside the code, they cost nothing to store, and they load in
milliseconds.

**What still goes to the engine, and must.** Search, drilldowns and the
watchlist. A question has to reach the whole library, and a snapshot must never
answer one - the honest decline that took this project weeks to earn depends on
search seeing everything.

Every snapshot is stamped with when it was built and with the library's newest
episode, so a stale snapshot can be *seen* to be stale rather than trusted.

    python scripts/build_snapshots.py            # all four windows
    python scripts/build_snapshots.py --window 90d
"""
import argparse
import json
import os

# Set BEFORE any router is imported: the routes short-circuit to a snapshot, and
# a builder that reads its own output writes a snapshot that never changes.
os.environ["SNAPSHOT_BUILD"] = "1"
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import aws_search, window as W          # noqa: E402

SNAPSHOT_VERSION = 1
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "snapshots")

# Each entry: the key the API serves it under, and a callable returning the
# payload. The callables are the ROUTE FUNCTIONS THEMSELVES, imported and
# called directly, so a snapshot cannot drift from what the live endpoint would
# have returned - there is no second implementation to keep in step.
def _panels():
    from api.routers import (signals, themes, narratives, feed, entities,
                             episodes, briefings, topic_mentions,
                             topic_correlations, intelligence_brief)
    return [
        ("signals",             lambda w: signals.signals(limit=60, window=w)),
        ("themes",              lambda w: themes.themes(limit=6, window=w)),
        ("narratives",          lambda w: narratives.narratives(limit=12, window=w)),
        ("feed",                lambda w: feed.feed(limit=10, offset=0, topic=None, window=w)),
        ("entities",            lambda w: entities.entities(limit=10, min_episodes=2,
                                                            q=None, window=w)),
        ("episodes",            lambda w: episodes.list_episodes(limit=2000, offset=0,
                                                                 refresh=False, window=w)),
        ("briefings",           lambda w: briefings.briefings(limit=12, window=w)),
        # These two take no `window` argument: they were not windowed in
        # finding 1 and still are not, so their snapshot is IDENTICAL in all
        # four windows. Recorded rather than hidden - Topic Movement is a
        # front-page card showing the same numbers whichever period is
        # selected, which is a finding-1 gap and belongs in the report.
        ("topic-mentions",      lambda w: topic_mentions.topic_mentions(refresh=False)),
        ("topic-correlations",  lambda w: topic_correlations.topic_correlations(refresh=False)),
        ("intelligence-brief",  lambda w: intelligence_brief.intelligence_brief(window=w)),
    ]


def jsonable(v):
    """Pydantic model or plain value -> plain JSON."""
    if hasattr(v, "model_dump"):
        return v.model_dump(mode="json")
    if hasattr(v, "dict"):
        return v.dict()
    return v


def build(window_key):
    anchor = W.anchor(refresh=True)
    started = time.time()
    panels, failed = {}, []
    for name, fn in _panels():
        t0 = time.time()
        try:
            panels[name] = {"payload": jsonable(fn(window_key)),
                            "built_in_s": round(time.time() - t0, 2)}
            print(f"    {name:22} {panels[name]['built_in_s']:>6.2f}s")
        except Exception as e:                                # noqa: BLE001
            # A panel that cannot be built is RECORDED as missing, never written
            # as an empty payload. The API falls back to the live endpoint for
            # it, so a failure here degrades to today's behaviour rather than to
            # a panel that silently shows nothing.
            failed.append({"panel": name, "error": f"{type(e).__name__}: {e}"[:300]})
            print(f"    {name:22}  FAILED  {type(e).__name__}: {str(e)[:90]}")
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "window": window_key,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "library_newest": anchor["newest"],
        "library_oldest": anchor["oldest"],
        "build_seconds": round(time.time() - started, 2),
        "panels": panels,
        "failed": failed,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", choices=sorted(W.WINDOWS), action="append")
    a = ap.parse_args()
    keys = a.window or list(W.WINDOWS)
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"library newest: {W.anchor(refresh=True)['newest']}")
    any_failed = False
    for k in keys:
        print(f"\n== {k}")
        snap = build(k)
        path = os.path.join(OUT_DIR, f"front-page-{k}.json")
        with open(path, "w") as f:
            json.dump(snap, f, separators=(",", ":"))
        size = os.path.getsize(path) / 1024
        print(f"  wrote {path}  {size:,.0f} KB  in {snap['build_seconds']}s"
              + (f"  ({len(snap['failed'])} panels FAILED)" if snap["failed"] else ""))
        any_failed |= bool(snap["failed"])
    if any_failed:
        sys.exit("one or more panels failed to build; those will fall back to live")


if __name__ == "__main__":
    main()
