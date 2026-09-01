"""Notable Signals, honest v1.

Phase E, 2026-08-28. The mock strip carried five cards of invented arithmetic:
"67 narrative shifts detected, up 24 from last week", confidence percentages,
sentiment counts, and per-card totals of 23, 14, 31, 12, 34 and 28 that nothing
produced. None of it survives.

Two of the four honest cards are served from here. The other two are not, and
deliberately: Watchlist Mentions reads the browser's own watchlist, and Topic
Movement reuses /api/topic-mentions through the shared trend formatter, so the
same topic cannot report a percentage on one surface and "low volume" on
another.

  * Notable Figures  claims that cite a monetary figure at or above $1bn,
                     counted from the brief store. The rule is printed on the
                     card, and the list opens to the claims themselves.
  * Library          episodes, hours, verified claims - the three totals the
                     corpus can state without qualification.

The Market Narratives slot is absent, not empty. It needs topics the corpus
discovers for itself, which is the parked topic-discovery engine.
"""
import logging
import re
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search
from lib import window as W

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["signals"])

BRIEFS = "episode_briefs"

# One billion, in the forms transcripts actually use. Deliberately narrow:
# only an explicit currency amount with an explicit billion/trillion scale
# counts. "$500 million" does not qualify, "3.5 billion users" is not money,
# and a bare "2 billion" with no currency marker is not counted either - a
# figure has to be unambiguously monetary to be called a monetary figure.
BILLION_RE = re.compile(
    r"""(?:\$|£|€|usd\s*)\s?(\d[\d,]*(?:\.\d+)?)\s*(billion|trillion|bn|tn)\b"""
    r"""|(\d[\d,]*(?:\.\d+)?)\s*(billion|trillion)\s+(?:dollars|pounds|euros)\b""",
    re.I)

THRESHOLD_USD = 1_000_000_000

FIGURES_RULE = (
    "Claims that cite a monetary figure of $1bn or more. Counted from the "
    "verified claims in the brief store, not from the transcripts: every claim "
    "here carries a quote that was checked word for word against its episode. "
    "Only explicit currency amounts at billion or trillion scale are counted, "
    "so a figure in millions, or a large number that is not money, is not.")

_cache: Optional[Dict[str, Any]] = None
# Handlers run in FastAPI's threadpool (they are sync, because their work is
# blocking I/O). Two first-callers could otherwise build this cache at the
# same time and each pay the full scan.
_lock = threading.Lock()


class FigureClaim(BaseModel):
    id: str
    episode_id: str
    claim_index: int
    claim: str
    quote: str
    figure: str
    amount_usd: float
    start_seconds: Optional[float] = None
    timestamp: Optional[str] = None
    located: bool = False
    episode_title: Optional[str] = None
    podcast_name: Optional[str] = None
    published_at: Optional[str] = None


class SignalsResponse(BaseModel):
    period: str
    # Library
    episodes: int
    podcasts: int
    hours: int
    verified_claims: int
    # Notable figures
    figures_count: int
    window: Optional[dict] = None
    figures_rule: str = FIGURES_RULE
    figures: List[FigureClaim] = []
    source: str = "opensearch"


def _amount(m: re.Match) -> Optional[float]:
    num = m.group(1) or m.group(3)
    scale = (m.group(2) or m.group(4) or "").lower()
    if not num:
        return None
    try:
        v = float(num.replace(",", ""))
    except ValueError:
        return None
    mult = 1_000_000_000_000 if scale in ("trillion", "tn") else 1_000_000_000
    return v * mult


def _scan(client) -> Dict[str, Any]:
    """One pass over the brief store. Claims are mapped `enabled: false`, so
    they ride in _source and cannot be queried - the scan is the only way, and
    it is why this is cached rather than computed per request."""
    figures: List[FigureClaim] = []
    ep_rows: List[Dict[str, Any]] = []
    after = None
    while True:
        body: Dict[str, Any] = {"size": 500, "sort": [{"episode_id": "asc"}],
                                "_source": ["episode_id", "episode_title", "podcast_name",
                                            "published_at", "duration_minutes", "claims"]}
        if after:
            body["search_after"] = after
        hits = client.search(index=BRIEFS, body=body)["hits"]["hits"]
        if not hits:
            break
        for h in hits:
            s = h["_source"]
            pub = (s.get("published_at") or "")[:10]
            n_claims = len(s.get("claims") or [])
            ep_rows.append({"published_at": pub,
                            "podcast_name": s.get("podcast_name"),
                            "duration_minutes": s.get("duration_minutes") or 0,
                            "claims": n_claims})
            for i, c in enumerate(s.get("claims") or []):
                text = f"{c.get('claim','')} {c.get('quote','')}"
                best = None
                for m in BILLION_RE.finditer(text):
                    amt = _amount(m)
                    if amt and amt >= THRESHOLD_USD and (best is None or amt > best[0]):
                        best = (amt, m.group(0).strip())
                if best:
                    figures.append(FigureClaim(
                        id=f"{s['episode_id']}#{i}", episode_id=s["episode_id"],
                        claim_index=i, claim=c.get("claim", ""), quote=c.get("quote", ""),
                        figure=best[1], amount_usd=best[0],
                        start_seconds=c.get("start_seconds"), timestamp=c.get("timestamp"),
                        located=bool(c.get("located")), episode_title=s.get("episode_title"),
                        podcast_name=s.get("podcast_name"), published_at=pub))
        after = hits[-1]["sort"]

    figures.sort(key=lambda f: -f.amount_usd)
    # Raw rows, not totals. The scan is expensive and cached once; the window
    # then aggregates from these in memory. Pre-aggregating here would mean one
    # full scan per window, four times the work for the same answer.
    return {"figures": figures, "episodes": ep_rows}


def _aggregate(cache: Dict[str, Any], w) -> Dict[str, Any]:
    """Period figures for one window, from the cached scan."""
    eps = [e for e in cache["episodes"] if W.in_window(e["published_at"], w)]
    figs = [f for f in cache["figures"] if W.in_window(f.published_at, w)]
    dates = [e["published_at"] for e in eps if e["published_at"]]
    return {
        "period": f"{min(dates)} to {max(dates)}" if dates else "",
        "episodes": len(eps),
        "podcasts": len({e["podcast_name"] for e in eps} - {None}),
        "hours": round(sum(e["duration_minutes"] or 0 for e in eps) / 60),
        "verified_claims": sum(e["claims"] for e in eps),
        "figures_count": len(figs),
        "figures": figs,
    }


@router.get("/signals", response_model=SignalsResponse)
def signals(limit: int = Query(60, ge=1, le=500),
            window: str = Query(W.DEFAULT, description="30d | 90d | 12m | all")
            ) -> SignalsResponse:
    global _cache
    w = W.resolve(window)
    if _cache is None:
        try:
            with _lock:
                if _cache is None:
                    _cache = _scan(aws_search.client())
        except Exception as e:                               # noqa: BLE001
            logger.error("signals scan failed: %s", e)
            raise HTTPException(status_code=503, detail=f"Signals unavailable: {e}")
    d = _aggregate(_cache, w)
    d["figures"] = d["figures"][:limit]
    d["window"] = w
    return SignalsResponse(**d)
