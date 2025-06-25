from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import traceback
import time

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
async def diagnostic_root():
    """Basic diagnostic check"""
    start = time.time()
    try:
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DATABASE", "podinsight")
        
        logger.info(f"[diagnostic] Connecting to MongoDB...")
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
        col = client[db_name]["transcript_chunks_768d"]
        
        count = await col.estimated_document_count()
        connect_time = time.time() - start
        logger.info(f"[diagnostic] ⏱️  mongo connect ok ({connect_time*1000:.0f} ms)")
        
        return {
            "status": "ok",
            "db": db_name,
            "count": count,
            "connect_time_ms": round(connect_time * 1000),
            "env": {
                "MONGODB_URI": bool(os.getenv("MONGODB_URI")),
                "MONGODB_DATABASE": bool(os.getenv("MONGODB_DATABASE")),
                "MODAL_EMBEDDING_URL": bool(os.getenv("MODAL_EMBEDDING_URL"))
            }
        }
    except Exception as e:
        logger.error(f"[diagnostic] Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc().split('\n')
        }

@app.get("/vc")
async def diagnostic_vc():
    """Test venture capital vector search"""
    try:
        # Import here to avoid circular imports
        from .embedding_utils import embed_query
        
        # 1. Test embedding
        embed_start = time.time()
        vec = embed_query("venture capital")
        embed_time = time.time() - embed_start
        logger.info(f"[diagnostic] ⏱️  embed_query ok ({embed_time*1000:.0f} ms)")
        
        if not vec or len(vec) != 768:
            return {
                "error": "embedding failed",
                "vec_length": len(vec) if vec else 0
            }
        
        logger.info(f"[diagnostic] Embedding first 5: {vec[:5]}")
        
        # 2. Connect to MongoDB
        connect_start = time.time()
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DATABASE", "podinsight")
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
        col = client[db_name]["transcript_chunks_768d"]
        connect_time = time.time() - connect_start
        logger.info(f"[diagnostic] ⏱️  mongo connect ok ({connect_time*1000:.0f} ms)")
        
        # 3. Vector search
        search_start = time.time()
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index_768d",
                    "path": "embedding_768d",
                    "queryVector": vec,
                    "numCandidates": 100,
                    "limit": 3
                }
            },
            {
                "$project": {
                    "score": {"$meta": "vectorSearchScore"},
                    "text": {"$substr": ["$text", 0, 80]},
                    "_id": 0
                }
            }
        ]
        
        results = await col.aggregate(pipeline).to_list(3)
        search_time = time.time() - search_start
        logger.info(f"[diagnostic] ⏱️  vector search ok ({search_time*1000:.0f} ms)")
        
        return {
            "status": "ok",
            "hits": len(results),
            "results": results,
            "timings": {
                "embed_ms": round(embed_time * 1000),
                "connect_ms": round(connect_time * 1000),
                "search_ms": round(search_time * 1000)
            }
        }
        
    except Exception as e:
        logger.error(f"[diagnostic] VC Error: {traceback.format_exc()}")
        return {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

# Handler for Vercel - use the app directly
app = app