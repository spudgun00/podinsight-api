# api/diag/index.py
import os, requests, logging, json, traceback, time
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api.embedding_utils import embed_query

router = APIRouter()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("diag")

@router.get("/")
async def root():
    """Basic diagnostic check"""
    start = time.time()
    try:
        uri = os.getenv("MONGODB_URI")
        db  = os.getenv("MONGODB_DATABASE", "podinsight")
        
        log.info(f"[diag] Connecting to MongoDB...")
        c   = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
        col = c[db]["transcript_chunks_768d"]
        
        count = await col.estimated_document_count()
        connect_time = time.time() - start
        log.info(f"[diag] ⏱️  mongo connect ok ({connect_time*1000:.0f} ms)")
        
        return {
            "db": db,
            "count": count,
            "env": {k: bool(os.getenv(k)) for k in
                    ("MONGODB_URI","MONGODB_DATABASE","MODAL_EMBEDDING_URL")}
        }
    except Exception as e:
        log.error(f"[diag] Error in root: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vc")
async def vc():
    """Test venture capital query end-to-end"""
    try:
        # 1. Test embedding generation
        embed_start = time.time()
        vec = embed_query("venture capital")
        embed_time = time.time() - embed_start
        log.info(f"[diag] ⏱️  embed_query ok ({embed_time*1000:.0f} ms)")
        
        if not vec or len(vec) != 768:
            log.error(f"[diag] Bad embedding: length={len(vec) if vec else 0}")
            return {"error": "embedding failed", "vec_length": len(vec) if vec else 0}
        
        log.info(f"[diag] Embedding first 5 values: {vec[:5]}")
        
        # 2. Connect to MongoDB
        connect_start = time.time()
        uri = os.getenv("MONGODB_URI")
        db = os.getenv("MONGODB_DATABASE", "podinsight")
        c   = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
        col = c[db]["transcript_chunks_768d"]
        connect_time = time.time() - connect_start
        log.info(f"[diag] ⏱️  mongo connect ok ({connect_time*1000:.0f} ms)")
        
        # 3. Run vector search
        search_start = time.time()
        pipe = [
            {"$vectorSearch":{
                "index":"vector_index_768d",
                "path":"embedding_768d",
                "queryVector":vec,
                "numCandidates":100,
                "limit":3}},
            {"$project":{"score":{"$meta":"vectorSearchScore"},
                        "text":{"$substr":["$text",0,80]}}}]
        
        hits = await col.aggregate(pipe).to_list(3)
        search_time = time.time() - search_start
        log.info(f"[diag] ⏱️  vector search ok ({search_time*1000:.0f} ms)")
        
        return {"hits": len(hits), "top": hits}
        
    except Exception as e:
        log.error(f"[diag] Error in vc: {traceback.format_exc()}")
        return {"error": str(e), "traceback": traceback.format_exc()}

# Import and mount on existing app
from api.topic_velocity import app
app.include_router(router, prefix="/diag")