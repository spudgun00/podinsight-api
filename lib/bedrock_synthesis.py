"""Answer synthesis on Bedrock Claude, replacing OpenAI gpt-4o-mini.

Two things differ from lib/synthesis.py beyond the provider swap.

1. It can decline. The old prompt was explicitly told "ALWAYS synthesize the
   content - NEVER say 'no data found'", which is the behaviour the scorecard
   scored 0/3 on. Here, retrieval has an honest cutoff, so synthesis is never
   asked to invent an answer from nothing; and the prompt is additionally
   allowed to return `answered: false` when the passages it was given do not
   actually answer the question.

2. Citations carry a verbatim quote, and the timestamp is resolved by matching
   that quote back to the chunk's nested Whisper segments. The chunk start can
   be half a minute earlier than the sentence being quoted, which sends Play
   clip to the wrong moment.
"""
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.config import Config

from lib.aws_search import locate_quote

logger = logging.getLogger(__name__)

REGION = os.getenv("AWS_SEARCH_REGION", "eu-central-1")
# EU regions require the eu.* inference profile; the bare anthropic.* id fails
# with ValidationException pointing at inference profiles.
MODEL = os.getenv("BEDROCK_SYNTHESIS_MODEL",
                  "eu.anthropic.claude-sonnet-4-5-20250929-v1:0")
MAX_TOKENS = int(os.getenv("BEDROCK_SYNTHESIS_MAX_TOKENS", "700"))
MAX_SOURCES = int(os.getenv("BEDROCK_SYNTHESIS_MAX_SOURCES", "6"))
MAX_PER_EPISODE = int(os.getenv("BEDROCK_SYNTHESIS_MAX_PER_EPISODE", "2"))

_client = None


def _bedrock():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=REGION,
                               config=Config(retries={"max_attempts": 4, "mode": "adaptive"},
                                             read_timeout=45, connect_timeout=5))
    return _client


SYSTEM = """You summarise what podcast guests actually said, for an investor audience.

You are given numbered passages retrieved for a question. A separate retrieval
step has already discarded weak matches, so the passages are plausible.

Answer whenever the passages support an answer, even a partial one. Passages are
transcript excerpts: they are conversational, they may start mid-sentence, and
the person speaking is named in the passage's Context line rather than in the
words themselves. Use the Context line to attribute a quote. A passage that
makes the point in different words still answers the question.

Decline ONLY when no passage bears on the question at all - a different subject,
a different year, a different company or person from the one asked about. In
that case set "answered" to false and leave "bullets" empty. Do not pad, do not
pivot to a related topic, and do not apologise. Declining is a correct answer
when it is earned, but answering from thin material is the more useful default.

Other rules:
- Use ONLY the passages. Never add outside knowledge and never state a fact that
  is not in them.
- Each bullet cites exactly one passage by its number.
- Each bullet carries a "quote": a span copied VERBATIM from that passage, 4 to
  25 words, that the bullet is drawn from. Copy it character for character. Do
  not paraphrase, reformat, or join separate sentences.

Reply with JSON only, no prose around it:
{"answered": true|false,
 "bullets": [{"text": "...", "source": 1, "quote": "..."}]}

Aim for 2 to 4 bullets. Each bullet one sentence, specific, no preamble."""


def _dedupe(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Cap sources per episode so one episode cannot fill the citation list."""
    seen, out = {}, []
    for h in hits:
        eid = h.get("episode_id")
        if seen.get(eid, 0) >= MAX_PER_EPISODE:
            continue
        seen[eid] = seen.get(eid, 0) + 1
        out.append(h)
        if len(out) >= MAX_SOURCES:
            break
    return out


def _format(hits: List[Dict[str, Any]], query: str) -> str:
    parts = [f"Question: {query}\n"]
    for i, h in enumerate(hits, 1):
        parts.append(
            f"[{i}] {h.get('podcast_name', '')} - {h.get('episode_title', '')}\n"
            f"Context: {h.get('context', '')}\n"
            f"Passage: {h.get('text', '')}\n")
    return "\n".join(parts)


def _parse(raw: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _hhmm(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


def synthesize(query: str, hits: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Returns (answer_or_None, meta). answer is None when nothing is answerable."""
    meta = {"model": MODEL, "sources_offered": 0, "declined": False, "ms": 0}
    if os.getenv("ANSWER_SYNTHESIS_ENABLED", "true").lower() != "true":
        return None, {**meta, "disabled": True}
    if not hits:
        return None, {**meta, "declined": True, "reason": "no passages above cutoff"}

    sources = _dedupe(hits)
    meta["sources_offered"] = len(sources)
    t0 = time.time()
    try:
        r = _bedrock().converse(
            modelId=MODEL,
            system=[{"text": SYSTEM}],
            messages=[{"role": "user", "content": [{"text": _format(sources, query)}]}],
            inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0.0})
        raw = r["output"]["message"]["content"][0]["text"]
        meta["usage"] = r.get("usage", {})
    except Exception as e:                                   # noqa: BLE001
        logger.error("Bedrock synthesis failed: %s", e)
        return None, {**meta, "error": str(e), "ms": int((time.time() - t0) * 1000)}
    meta["ms"] = int((time.time() - t0) * 1000)

    parsed = _parse(raw)
    if not parsed or not parsed.get("answered") or not parsed.get("bullets"):
        logger.info("Synthesis declined for %r", query)
        return None, {**meta, "declined": True,
                      "reason": "model judged the passages did not answer"}

    lines, citations, used = [], [], {}
    for b in parsed["bullets"]:
        idx = b.get("source")
        if not isinstance(idx, int) or not (1 <= idx <= len(sources)):
            continue
        hit = sources[idx - 1]
        if idx not in used:
            used[idx] = len(used) + 1
            quote = (b.get("quote") or "").strip() or hit.get("text", "")[:160]
            start = locate_quote(hit, quote)          # exact second, not chunk start
            citations.append({
                "index": used[idx],
                "episode_id": hit.get("episode_id", ""),
                "episode_title": hit.get("episode_title", ""),
                "podcast_name": hit.get("podcast_name", ""),
                "timestamp": _hhmm(start),
                "start_seconds": float(start),
                "chunk_index": int(hit.get("chunk_index", 0)),
                "chunk_text": quote,
                "similarity_score": float(hit.get("rerank_score", 0.0)),
                "published_date": hit.get("published_at"),
            })
        lines.append(f"• {b.get('text', '').strip()} [{used[idx]}]")

    if not lines:
        return None, {**meta, "declined": True, "reason": "no valid citations"}
    return {"text": "\n".join(lines), "citations": citations}, meta
