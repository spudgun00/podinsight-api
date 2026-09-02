"""Wake the search engine, and report what the snapshots hold.

Finding 5, 2 Sep 2026. The front page renders from prebuilt snapshots and no
longer touches OpenSearch, which is why it is fast. But the engine still has to
be awake for the thing snapshots must never answer: a question.

So the page fires one wake call on load, in the background, and the engine warms
while the reader is still looking at the page. By the time a question is typed
it is usually ready. Anyone who outruns the wake still sees the warming bar -
that bar is not removed, it is simply made rare.

The wake is the cheapest query that forces the collection to serve: a count. It
is fire-and-forget from the page's point of view and nothing renders from it.
"""
import logging
import time

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional

from lib import aws_search
from lib import snapshots as _S

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["wake"])


class WakeResponse(BaseModel):
    ready: bool
    elapsed_ms: int
    # Was the engine already awake? A fast wake means it was; a slow one means
    # this call paid the cost the reader would otherwise have paid at the
    # moment they asked a question.
    was_cold: Optional[bool] = None
    error: Optional[str] = None


@router.get("/wake", response_model=WakeResponse)
def wake() -> WakeResponse:
    t0 = time.time()
    try:
        aws_search.client().count(index=aws_search.INDEX)
        ms = int((time.time() - t0) * 1000)
        return WakeResponse(ready=True, elapsed_ms=ms, was_cold=ms > 2000)
    except Exception as e:                                    # noqa: BLE001
        logger.error("wake failed: %s", e)
        return WakeResponse(ready=False, elapsed_ms=int((time.time() - t0) * 1000),
                            error=str(e)[:200])


class SnapshotStatus(BaseModel):
    snapshots: Dict[str, Any]
    library_newest: Optional[str] = None
    stale: list = []


@router.get("/snapshots", response_model=SnapshotStatus)
def snapshot_status() -> SnapshotStatus:
    """What each snapshot holds and whether it still matches the library.

    The weekly self-check reads this: a snapshot whose `library_newest` is
    behind the library's own newest episode is stale, and stale is a fact to be
    reported rather than a state to be guessed at.

    Asking the library its newest date is one cheap query, and this endpoint is
    not on the page's load path - it is for the self-check and for a person.
    """
    st = _S.status()
    newest = None
    try:
        from lib import window as W
        newest = W.anchor(refresh=True).get("newest")
    except Exception as e:                                    # noqa: BLE001
        logger.error("snapshot status could not read the library: %s", e)
    stale = [k for k, v in st.items()
             if newest and v and v.get("library_newest") != newest]
    return SnapshotStatus(snapshots=st, library_newest=newest, stale=stale)
