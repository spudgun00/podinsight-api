"""
Simple endpoint to test basic functionality
"""
from fastapi import APIRouter
import os

router = APIRouter()

@router.get("/api/simple-test")
async def simple_test():
    """Test environment variables and basic setup"""
    
    # Check what environment variables are available
    mongo_uri = os.getenv("MONGODB_URI")
    
    # Basic response
    response = {
        "status": "ok",
        "mongodb_uri_set": bool(mongo_uri),
        "mongodb_uri_starts_with": mongo_uri[:30] + "..." if mongo_uri else "Not set",
        "python_version": os.environ.get("PYTHON_VERSION", "unknown"),
        "vercel_env": os.environ.get("VERCEL_ENV", "unknown"),
        "node_env": os.environ.get("NODE_ENV", "unknown")
    }
    
    # Try a simple import test
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        response["motor_import"] = "success"
        
        # Try to create a client (but don't connect)
        if mongo_uri:
            client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=1000)
            response["client_created"] = "success"
            client.close()
        else:
            response["client_created"] = "no uri"
            
    except ImportError as e:
        response["motor_import"] = f"import error: {str(e)}"
    except Exception as e:
        response["motor_error"] = str(e)
    
    return response