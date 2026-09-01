"""The global date window. One resolver, one anchor, no hardcoded dates.

James's ruling, 1 Sep 2026: twenty months of library makes unbounded panels
unreadable, so one control governs every surface. Four choices, default 90 days.

**The anchor is the newest episode in the library, never today's calendar date.**
That is the whole point. The forward machine is unbuilt, so the library's newest
episode is 28 Aug 2026 and will stay there until someone runs an ingestion. A
window counted back from *today* would slide forward on its own and quietly empty
the page - "last 30 days" would show nothing at all by October, with no error and
no explanation. Counted back from the library, "last 30 days" always means the
last 30 days the library actually has.

Every window is resolved server-side and every endpoint filters on
`published_at`. Nothing is hidden client-side: a row absent from a response is
absent from the data for that window, so counts, floors and drilldowns all agree
by construction.
"""
from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from lib import aws_search

# The four choices, in the order the control shows them. `days=None` means "all".
WINDOWS = {
    "30d": {"label": "Last 30 days", "days": 30},
    "90d": {"label": "Last 90 days", "days": 90},
    "12m": {"label": "Last 12 months", "months": 12},
    "all": {"label": "All time", "days": None},
}
DEFAULT = "90d"

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_anchor_cache: Dict[str, Any] = {}
_lock = threading.Lock()
_TTL = 300          # seconds; the anchor only moves when ingestion runs


def anchor(refresh: bool = False) -> Dict[str, Any]:
    """The library's own date range. Measured, never written down."""
    with _lock:
        c = _anchor_cache.get("v")
        if c and not refresh and time.time() - c["_at"] < _TTL:
            return c
    r = aws_search.client().search(index=aws_search.INDEX, body={"size": 0, "aggs": {
        "newest": {"max": {"field": "published_at"}},
        "oldest": {"min": {"field": "published_at"}}}})["aggregations"]
    newest = (r["newest"].get("value_as_string") or "")[:10] or None
    oldest = (r["oldest"].get("value_as_string") or "")[:10] or None
    out = {"newest": newest, "oldest": oldest, "_at": time.time()}
    with _lock:
        _anchor_cache["v"] = out
    return out


def _minus_months(d: date, n: int) -> date:
    """n calendar months back, clamped to the end of a shorter month."""
    y, m = d.year, d.month - n
    while m <= 0:
        m += 12
        y -= 1
    day = d.day
    while True:
        try:
            return date(y, m, day)
        except ValueError:
            day -= 1          # 31 Mar minus 1 month -> 28/29 Feb


def pretty(iso: Optional[str]) -> str:
    """2026-08-28 -> 28 Aug 2026. The label a person reads."""
    if not iso:
        return ""
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def resolve(key: Optional[str] = None, refresh: bool = False) -> Dict[str, Any]:
    """Turn a window key into real dates, from the library.

    Returns `from_` and `to` as inclusive ISO dates, plus the label the control
    shows. An unknown key falls back to the default rather than erroring: a
    stale bookmark should show the default view, not a 422.
    """
    k = (key or DEFAULT).lower().strip()
    if k not in WINDOWS:
        k = DEFAULT
    a = anchor(refresh=refresh)
    newest, oldest = a["newest"], a["oldest"]
    spec = WINDOWS[k]

    if k == "all" or not newest:
        from_ = oldest
        label = spec["label"]
        span = f"{pretty(oldest)} to {pretty(newest)}" if oldest and newest else ""
    else:
        end = date.fromisoformat(newest)
        if spec.get("months"):
            start = _minus_months(end, spec["months"])
        else:
            # Inclusive of the anchor day: "last 30 days" is 30 days of library,
            # the newest one included.
            start = end - timedelta(days=spec["days"] - 1)
        if oldest and start < date.fromisoformat(oldest):
            start = date.fromisoformat(oldest)
        from_ = start.isoformat()
        span = f"{pretty(from_)} to {pretty(newest)}"
        label = spec["label"]

    return {
        "key": k,
        "label": label,
        # "Last 90 days: 31 May to 28 Aug 2026" - the control says what it covers
        "label_full": f"{label}: {span}" if span and k != "all" else
                      (f"{label}: {span}" if span else label),
        "from": from_,
        "to": newest,
        "span": span,
        "anchor": newest,
        "anchor_note": "counted back from the newest episode in the library, "
                       "not from today's date",
        "corpus_from": oldest,
        "corpus_to": newest,
        "is_all": k == "all",
    }


def filter_clause(w: Dict[str, Any], field: str = "published_at") -> Optional[Dict]:
    """The OpenSearch range clause for a resolved window, or None for all-time.

    None is deliberate: 'All time' must add no clause at all, so it restores
    exactly the pre-window behaviour rather than a range that merely looks total.
    """
    if w.get("is_all") or not w.get("from"):
        return None
    return {"range": {field: {"gte": w["from"], "lte": w["to"]}}}


def apply(body: Dict[str, Any], w: Dict[str, Any], field: str = "published_at") -> Dict[str, Any]:
    """Add the window clause to an OpenSearch body, whatever query it already has."""
    clause = filter_clause(w, field)
    if clause is None:
        return body
    q = body.get("query")
    if q is None:
        body["query"] = {"bool": {"filter": [clause]}}
    elif "bool" in q:
        q["bool"].setdefault("filter", [])
        if isinstance(q["bool"]["filter"], dict):
            q["bool"]["filter"] = [q["bool"]["filter"]]
        q["bool"]["filter"].append(clause)
    else:
        body["query"] = {"bool": {"must": [q], "filter": [clause]}}
    return body


def in_window(published_at: Optional[str], w: Dict[str, Any]) -> bool:
    """Python-side test, for rollups already held in memory.

    Used only where the rows were fetched for another reason and filtering them
    again in OpenSearch would be a second round trip - never to hide rows from a
    response the client already has.
    """
    if w.get("is_all") or not w.get("from"):
        return True
    if not published_at:
        return False
    d = published_at[:10]
    return w["from"] <= d <= w["to"]


def month_range(w: Dict[str, Any]) -> Optional[tuple]:
    """('2026-05', '2026-08') for month-bucketed surfaces, or None for all-time."""
    if w.get("is_all") or not w.get("from"):
        return None
    return (w["from"][:7], w["to"][:7])


def partial_buckets(w: Dict[str, Any]) -> set:
    """Month buckets the window only partly covers, for dashing.

    Two ways a month can be partial, and both must be dashed or the chart
    overstates a dip that is only a short month:

      * **the end** - the library's newest episode is 28 Aug 2026, so 2026-08
        holds 28 of 31 days whatever the window;
      * **the start** - "last 90 days" begins on 31 May, so 2026-05 holds one
        day of library, not thirty-one.

    This replaces two hardcoded rules that were wrong at corpus v3:
    `PARTIAL_BUCKET = "2025-06"` in themes.py, frozen at the corpus-v1 end date,
    and `partial = b.endswith("-06")` in narratives.py, which marked **every
    June** partial.
    """
    import calendar
    out = set()
    to = w.get("to")
    if to:
        d = date.fromisoformat(to[:10])
        if d.day < calendar.monthrange(d.year, d.month)[1]:
            out.add(f"{d.year:04d}-{d.month:02d}")
    frm = w.get("from")
    if frm and not w.get("is_all"):
        f = date.fromisoformat(frm[:10])
        if f.day > 1:
            out.add(f"{f.year:04d}-{f.month:02d}")
    return out
