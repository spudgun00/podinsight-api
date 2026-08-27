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
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from lib import aws_search

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
    claims_total = 0
    minutes = 0
    episodes = 0
    podcasts = set()
    first = last = ""
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
            episodes += 1
            podcasts.add(s.get("podcast_name"))
            minutes += s.get("duration_minutes") or 0
            pub = (s.get("published_at") or "")[:10]
            if pub:
                first = pub if not first or pub < first else first
                last = pub if not last or pub > last else last
            for i, c in enumerate(s.get("claims") or []):
                claims_total += 1
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
    return {"period": f"{first} to {last}" if first and last else "",
            "episodes": episodes, "podcasts": len(podcasts - {None}),
            "hours": round(minutes / 60), "verified_claims": claims_total,
            "figures_count": len(figures), "figures": figures}


@router.get("/signals", response_model=SignalsResponse)
async def signals(limit: int = Query(60, ge=1, le=500)) -> SignalsResponse:
    global _cache
    if _cache is None:
        try:
            _cache = _scan(aws_search.client())
        except Exception as e:                               # noqa: BLE001
            logger.error("signals scan failed: %s", e)
            raise HTTPException(status_code=503, detail=f"Signals unavailable: {e}")
    d = dict(_cache)
    d["figures"] = d["figures"][:limit]
    return SignalsResponse(**d)
