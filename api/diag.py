from fastapi import FastAPI
from pymongo import MongoClient
import os, json

app = FastAPI()

@app.get("/diag")
@app.get("/api/diag")
async def diag():
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DATABASE", "podinsight")
    c = MongoClient(uri, serverSelectionTimeoutMS=3000)
    col = c[db_name]["transcript_chunks_768d"]

    msg = {
        "db": db_name,
        "count": col.estimated_document_count(),
        "vector_index_seen": True,   # Atlas Search indexes never appear in list_indexes()
        "env": {k: bool(os.getenv(k)) for k in
                ["MONGODB_URI","MONGODB_DATABASE","MODAL_EMBEDDING_URL"]}
    }
    return msg

@app.get("/diag/vc")
@app.get("/api/diag/vc")
async def diag_vc():
    from pymongo import MongoClient
    import requests, os
    uri = os.getenv("MONGODB_URI")
    db = MongoClient(uri).podinsight

    # 1) embed the query *inside* the λ
    modal = os.getenv("MODAL_EMBEDDING_URL")
    vec = requests.post(modal, json={"text": "venture capital"}, timeout=30).json()["embedding"]

    # 2) run the identical pipeline
    pipe = [{"$vectorSearch":{
                "index":"vector_index_768d",
                "path":"embedding_768d",
                "queryVector":vec,
                "numCandidates":100,
                "limit":3}},
            {"$addFields":{"score":{"$meta":"vectorSearchScore"}}},
            {"$project":{"text":{"$substr":["$text",0,80]},"score":1}}]

    out = list(db.transcript_chunks_768d.aggregate(pipe))
    return {"hits":len(out), "top":out[:3]}

# Handler for Vercel
handler = app