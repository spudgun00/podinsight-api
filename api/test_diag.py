from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
async def test_root():
    """Simplest possible test"""
    return {
        "status": "ok",
        "message": "Diagnostic endpoint is working",
        "env_vars_present": {
            "MONGODB_URI": bool(os.getenv("MONGODB_URI")),
            "MONGODB_DATABASE": bool(os.getenv("MONGODB_DATABASE")),
            "MODAL_EMBEDDING_URL": bool(os.getenv("MODAL_EMBEDDING_URL"))
        }
    }

# Handler for Vercel
handler = app