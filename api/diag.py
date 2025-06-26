# api/diag.py
# Each file under /api is an **independent** Vercel serverless fn.
# Expose ONE ASGI app right here; no need to import the main API.
import os, time, traceback, logging, requests, math
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    """Basic MongoDB connectivity check."""
    try:
        t0 = time.perf_counter()

        uri      = os.getenv("MONGODB_URI")
        db_name  = os.getenv("MONGODB_DATABASE", "podinsight")
        client   = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
        col      = client[db_name]["transcript_chunks_768d"]
        count    = await col.estimated_document_count()
        dur      = round((time.perf_counter() - t0) * 1000)

        return {
            "db"       : db_name,
            "count"    : count,
            "latencyMs": dur,
            "env"      : {k: bool(os.getenv(k)) for k in
                          ("MONGODB_URI","MONGODB_DATABASE","MODAL_EMBEDDING_URL")},
        }

    except Exception as e:
        logging.exception("diag root failed")
        return {"error": str(e), "trace": traceback.format_exc()[:500]}

@app.get("/vc")
async def diag_vc():
    """Full Modal->Atlas vector round-trip for the query 'venture capital'."""
    try:
        t0 = time.perf_counter()

        # ---------- 1. get embedding ----------
        modal = os.getenv("MODAL_EMBEDDING_URL")
        q     = "venture capital"
        r     = requests.post(modal, json={"text": q}, timeout=30)
        r.raise_for_status()
        vec   = r.json()["embedding"]
        vec_norm = math.sqrt(sum(x*x for x in vec))

        # ---------- 2. vector search ----------
        client   = AsyncIOMotorClient(os.getenv("MONGODB_URI"), serverSelectionTimeoutMS=8000)
        col      = client[os.getenv("MONGODB_DATABASE","podinsight")]["transcript_chunks_768d"]

        pipe = [
            {"$vectorSearch": {
                "index"       : "vector_index_768d",
                "path"        : "embedding_768d",
                "queryVector" : vec,
                "numCandidates": 100,
                "limit"       : 5,
            }},
            {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
            {"$project":   {"score": 1, "text": {"$substr": ["$text",0,80]}}},
        ]

        hits   = await col.aggregate(pipe).to_list(length=5)
        dur_ms = round((time.perf_counter() - t0) * 1000)

        return {
            "hits"        : len(hits),
            "top"         : hits,
            "embedNorm"   : round(vec_norm,4),
            "totalMs"     : dur_ms,
        }

    except Exception as e:
        logging.exception("diag vc failed")
        return {"error": str(e), "trace": traceback.format_exc()[:500]}

@app.get("/test")
async def test_route():
    """Simple test to verify routing works"""
    return {"status": "ok", "message": "diag file reached"}

# Vercel expects the app to be exported
handler = app