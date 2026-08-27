"""Retrieval against the AWS stack: OpenSearch Serverless + Bedrock.

Phase 1 of the switchover. Replaces the MongoDB + Modal + instructor-xl path
for /api/search only. Topic mentions, correlations and entities still read
MongoDB and are untouched.

Shape is the pilot's, unchanged:
  Cohere Embed v4 (input_type=search_query)
    -> hybrid BM25 + kNN through the normalisation search pipeline
    -> Amazon Rerank 1.0, 50 candidates down to 10
    -> honest cutoff; below it the API says so rather than guessing.

Settings come from the environment so the region or index can move without a
code change. Defaults are the values the full corpus was loaded with.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

logger = logging.getLogger(__name__)

REGION = os.getenv("AWS_SEARCH_REGION", "eu-central-1")
COLLECTION = os.getenv("AOSS_COLLECTION", "podinsight-pilot")
INDEX = os.getenv("AOSS_INDEX", "chunks_full")
SEARCH_PIPELINE = os.getenv("AOSS_SEARCH_PIPELINE", "hybrid-pipeline")

EMBED_MODEL = os.getenv("BEDROCK_EMBED_MODEL", "eu.cohere.embed-v4:0")
EMBED_DIMS = int(os.getenv("BEDROCK_EMBED_DIMS", "1024"))
RERANK_MODEL = os.getenv("BEDROCK_RERANK_MODEL", "amazon.rerank-v1:0")

RETRIEVE_K = int(os.getenv("SEARCH_RETRIEVE_K", "50"))
RERANK_K = int(os.getenv("SEARCH_RERANK_K", "10"))

# Calibrated on 24 throwaway queries, never on the frozen scorecard. See
# podinsight-aws-pilot/calibrate_full.py and out/calibration.json. Amazon
# Rerank 1.0 scores are very small in absolute terms; this is not a typo.
CUTOFF = float(os.getenv("SEARCH_RERANK_CUTOFF", "0.00113"))

_BOTO = Config(retries={"max_attempts": 5, "mode": "adaptive"}, read_timeout=25,
               connect_timeout=5)
_bedrock = None
_agent = None
_os_client = None
_endpoint = None


def _bedrock_runtime():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client("bedrock-runtime", region_name=REGION, config=_BOTO)
    return _bedrock


def _bedrock_agent():
    global _agent
    if _agent is None:
        _agent = boto3.client("bedrock-agent-runtime", region_name=REGION, config=_BOTO)
    return _agent


def collection_endpoint() -> str:
    global _endpoint
    if _endpoint is None:
        env = os.getenv("AOSS_ENDPOINT")
        if env:
            _endpoint = env
        else:
            aoss = boto3.client("opensearchserverless", region_name=REGION, config=_BOTO)
            d = aoss.batch_get_collection(names=[COLLECTION])["collectionDetails"]
            if not d:
                raise RuntimeError(f"collection {COLLECTION} not found in {REGION}")
            _endpoint = d[0]["collectionEndpoint"]
    return _endpoint


def client() -> OpenSearch:
    global _os_client
    if _os_client is None:
        creds = boto3.Session().get_credentials().get_frozen_credentials()
        host = collection_endpoint().replace("https://", "")
        _os_client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=AWS4Auth(creds.access_key, creds.secret_key, REGION, "aoss",
                               session_token=creds.token),
            use_ssl=True, verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=25, max_retries=2, retry_on_timeout=True, pool_maxsize=20)
    return _os_client


def embed_query(text: str) -> List[float]:
    """Cohere needs input_type=search_query here.

    Index time used search_document. Getting this wrong does not raise - it
    quietly returns a vector from the wrong space and degrades every result.
    """
    r = _bedrock_runtime().invoke_model(modelId=EMBED_MODEL, body=json.dumps({
        "texts": [text[:8000]], "input_type": "search_query",
        "embedding_types": ["float"], "output_dimension": EMBED_DIMS}))
    e = json.loads(r["body"].read())["embeddings"]
    return (e["float"] if isinstance(e, dict) else e)[0]


def hybrid(query: str, k: int = RETRIEVE_K) -> List[Dict[str, Any]]:
    """Keyword and vector, fused by the normalisation processor in the pipeline."""
    body = {
        "size": k,
        "_source": {"excludes": ["embedding"]},
        "query": {"hybrid": {"queries": [
            {"multi_match": {"query": query, "fields": ["text^1.0", "context^0.5"]}},
            {"knn": {"embedding": {"vector": embed_query(query), "k": k}}},
        ]}},
    }
    r = client().search(index=INDEX, body=body,
                        params={"search_pipeline": SEARCH_PIPELINE})
    return [{**h["_source"], "hybrid_score": h["_score"]} for h in r["hits"]["hits"]]


def rerank(query: str, hits: List[Dict[str, Any]], top_n: int = RERANK_K):
    """Bedrock rerank reads query and passage together and rescores.

    The passage includes the generated context sentence. Measured on the pilot,
    showing it to the reranker lifts genuine answers substantially while leaving
    off-domain text near zero.
    """
    if not hits:
        return []
    arn = f"arn:aws:bedrock:{REGION}::foundation-model/{RERANK_MODEL}"
    sources = [{"type": "INLINE", "inlineDocumentSource": {"type": "TEXT", "textDocument":
                {"text": f'{h.get("context", "")}\n\n{h["text"][:9000]}'}}} for h in hits]
    out = []
    for i in range(0, len(sources), 100):     # rerank takes 100 documents per query
        batch = sources[i:i + 100]
        r = _bedrock_agent().rerank(
            queries=[{"type": "TEXT", "textQuery": {"text": query[:2000]}}],
            sources=batch,
            rerankingConfiguration={"type": "BEDROCK_RERANKING_MODEL",
                "bedrockRerankingConfiguration": {
                    "numberOfResults": min(top_n, len(batch)),
                    "modelConfiguration": {"modelArn": arn}}})
        for res in r["results"]:
            h = dict(hits[i + res["index"]])
            h["rerank_score"] = res["relevanceScore"]
            out.append(h)
    out.sort(key=lambda h: h["rerank_score"], reverse=True)
    return out[:top_n]


def _norm(s: str) -> str:
    """Normalise for comparison, keeping CJK.

    The character class must not be [a-z0-9 ] alone: that strips every Chinese,
    Japanese and Korean character, so a CJK quote normalises to the empty
    string. An empty string is a substring of everything, which made the brief
    generator's verbatim and playable checks pass without checking anything and
    sent locate_quote straight to the chunk start.
    """
    return re.sub(r"[^a-z0-9 \u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]",
                  "", (s or "").lower())


def locate_quote(hit: Dict[str, Any], quote: str) -> float:
    """Recover the second at which a quote STARTS, from the nested segments.

    Resolution order, most reliable first:
      1. a segment containing the whole quote
      2. the segment containing the quote's opening words - a quote often spans
         two or three segments, and the place to play from is where it begins,
         not the longest segment somewhere inside it
      3. the earliest segment contained in the quote and long enough to be
         distinctive

    The length floor on (3) matters: without it a segment of "100%." normalises
    to "100", a substring of "...that's a 10,000X", so a two-word fragment won
    the match and Play clip landed half an hour from the sentence quoted.
    """
    MIN_SEGMENT_CHARS = 20
    q = _norm(quote)
    if not q:
        return float(hit.get("start_time", 0.0))
    segs = sorted((hit.get("segments") or []), key=lambda s: float(s.get("t", 0)))

    for seg in segs:                                   # 1. whole quote inside a segment
        if q in _norm(seg.get("text", "")):
            return float(seg["t"])

    words = q.split()
    for n in (8, 6, 4):                                # 2. where the quote starts
        head = " ".join(words[:n])
        if len(head) < MIN_SEGMENT_CHARS:
            continue
        for seg in segs:
            if head in _norm(seg.get("text", "")):
                return float(seg["t"])

    for seg in segs:                                   # 3. earliest distinctive overlap
        s = _norm(seg.get("text", ""))
        if s and len(s) >= MIN_SEGMENT_CHARS and s in q:
            return float(seg["t"])

    return float(hit.get("start_time", 0.0))


def search(query: str, top_n: int = RERANK_K, cutoff: float = None) -> Dict[str, Any]:
    """Full query path. `no_matches` is a first-class outcome, not an error."""
    cutoff = CUTOFF if cutoff is None else cutoff
    ranked = rerank(query, hybrid(query), top_n=top_n)
    kept = [h for h in ranked if h["rerank_score"] >= cutoff]
    return {
        "results": kept,
        "no_matches": not kept,
        "top_score": ranked[0]["rerank_score"] if ranked else 0.0,
        "considered": len(ranked),
        "cutoff": cutoff,
    }


def health() -> Dict[str, Any]:
    try:
        n = client().count(index=INDEX)["count"]
        return {"ok": True, "region": REGION, "index": INDEX, "chunks": n}
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "region": REGION, "index": INDEX, "error": str(e)}
