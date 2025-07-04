"""Simple test endpoint to verify audio API basics"""
from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/api/test_audio")
async def test_audio():
    """Test endpoint to verify environment and basic functionality"""
    return {
        "status": "ok",
        "lambda_url_configured": bool(os.environ.get("AUDIO_LAMBDA_URL")),
        "lambda_api_key_configured": bool(os.environ.get("AUDIO_LAMBDA_API_KEY")),
        "mongodb_configured": bool(os.environ.get("MONGODB_URI")),
        "environment": {
            "has_audio_lambda_url": "AUDIO_LAMBDA_URL" in os.environ,
            "has_audio_lambda_api_key": "AUDIO_LAMBDA_API_KEY" in os.environ,  # pragma: allowlist secret
            "has_mongodb_uri": "MONGODB_URI" in os.environ
        }
    }
