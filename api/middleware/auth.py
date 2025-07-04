"""
Authentication middleware for PodInsightHQ API
Implements JWT-based authentication using Supabase Auth
"""
import os
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
import jwt
from datetime import datetime

logger = logging.getLogger(__name__)

# Security scheme for FastAPI docs
security = HTTPBearer()

# Cache for Supabase client
_supabase_client: Optional[Client] = None


def get_supabase_auth_client() -> Client:
    """Get or create Supabase client for auth verification"""
    global _supabase_client
    
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
        
        if not url or not key:
            raise ValueError("Supabase configuration not found")
            
        _supabase_client = create_client(url, key)
    
    return _supabase_client


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify JWT token from Authorization header
    
    Returns:
        Dict containing user info from the token
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    try:
        # Get Supabase JWT secret
        jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
        if not jwt_secret:
            logger.error("SUPABASE_JWT_SECRET not configured")
            raise HTTPException(
                status_code=500,
                detail="Authentication service misconfigured"
            )
        
        # Decode and verify the JWT
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
        
        # Check if token is expired
        exp = payload.get("exp", 0)
        if exp < datetime.utcnow().timestamp():
            raise HTTPException(
                status_code=401,
                detail="Token expired"
            )
        
        # Extract user info
        user_info = {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated"),
            "metadata": payload.get("user_metadata", {})
        }
        
        logger.info(f"Authenticated user: {user_info['email']}")
        return user_info
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    except Exception as e:
        logger.error(f"Auth verification error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )


async def require_auth(user: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """
    Dependency to require authentication for an endpoint
    
    Usage:
        @app.get("/protected")
        async def protected_endpoint(user = Depends(require_auth)):
            return {"user_id": user["user_id"]}
    """
    if not user.get("user_id"):
        raise HTTPException(
            status_code=401,
            detail="User ID not found in token"
        )
    
    return user


async def get_current_user(user: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get current authenticated user info
    Alias for require_auth for better semantic meaning
    """
    return user


# Optional: Role-based access control
def require_role(required_role: str):
    """
    Dependency factory for role-based access control
    
    Usage:
        @app.get("/admin")
        async def admin_endpoint(user = Depends(require_role("admin"))):
            return {"message": "Admin access granted"}
    """
    async def role_checker(user: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
        user_role = user.get("role", "authenticated")
        
        # Check if user has required role
        if user_role != required_role and user_role != "service_role":
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return user
    
    return role_checker


# Health check for auth service
async def auth_health_check() -> Dict[str, Any]:
    """Check if authentication service is properly configured"""
    return {
        "configured": bool(os.environ.get("SUPABASE_JWT_SECRET")),
        "supabase_url": bool(os.environ.get("SUPABASE_URL")),
        "supabase_key": bool(os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
    }