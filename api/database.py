"""
Database connection pool manager for Supabase
Handles connection pooling to stay within free tier limits
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager
from supabase import create_client, Client
import os

logger = logging.getLogger(__name__)


class SupabasePool:
    """
    Connection pool manager for Supabase
    Limits concurrent connections to stay within free tier (20 total)
    """
    
    def __init__(self, max_connections: int = 10):
        """
        Initialize the connection pool
        
        Args:
            max_connections: Maximum connections per worker (default 10)
        """
        self.max_connections = max_connections
        self.semaphore = asyncio.Semaphore(max_connections)
        self.active_connections = 0
        self.total_requests = 0
        self.connection_errors = 0
        self._client: Optional[Client] = None
        
        # Connection monitoring
        self.connection_log: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "max_connections": max_connections,
            "peak_connections": 0,
            "total_requests": 0,
            "errors": 0
        }
        
    def _create_client(self) -> Client:
        """Create a new Supabase client"""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
        
        if not url or not key:
            raise ValueError("Supabase configuration not found")
            
        return create_client(url, key)
    
    @property
    def client(self) -> Client:
        """Get or create the Supabase client"""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool
        
        Yields:
            Supabase client instance
            
        Raises:
            RuntimeError: If connection limit would be exceeded
        """
        # Check if we're approaching the limit
        if self.active_connections >= 15:
            logger.warning(
                f"⚠️ High connection usage: {self.active_connections}/{self.max_connections} active connections"
            )
        
        # Wait for available connection slot
        async with self.semaphore:
            self.active_connections += 1
            self.total_requests += 1
            self.connection_log["total_requests"] = self.total_requests
            
            # Update peak connections
            if self.active_connections > self.connection_log["peak_connections"]:
                self.connection_log["peak_connections"] = self.active_connections
            
            # Log connection state
            logger.debug(
                f"Connection acquired: {self.active_connections}/{self.max_connections} active"
            )
            
            try:
                yield self.client
            except Exception as e:
                self.connection_errors += 1
                self.connection_log["errors"] += 1
                logger.error(f"Connection error: {str(e)}")
                raise
            finally:
                self.active_connections -= 1
                logger.debug(
                    f"Connection released: {self.active_connections}/{self.max_connections} active"
                )
    
    async def execute_with_retry(self, query_func, max_retries: int = 3):
        """
        Execute a query with automatic retry on connection failure
        
        Args:
            query_func: Function that performs the query (can be sync or async)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Query result
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with self.acquire() as client:
                    # Support both sync and async query functions
                    if asyncio.iscoroutinefunction(query_func):
                        return await query_func(client)
                    else:
                        result = query_func(client)
                        if asyncio.iscoroutine(result):
                            return await result
                        return result
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Query failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Query failed after {max_retries} attempts: {str(e)}")
        
        raise last_error
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            "active_connections": self.active_connections,
            "max_connections": self.max_connections,
            "total_requests": self.total_requests,
            "connection_errors": self.connection_errors,
            "utilization_percent": (self.active_connections / self.max_connections) * 100,
            **self.connection_log
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the connection pool"""
        try:
            async with self.acquire() as client:
                # Simple query to test connection
                result = client.table("episodes").select("id").limit(1).execute()
                
            return {
                "status": "healthy",
                "stats": self.get_stats(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "stats": self.get_stats(),
                "timestamp": datetime.now().isoformat()
            }


# Global connection pool instance
_pool: Optional[SupabasePool] = None


def get_pool() -> SupabasePool:
    """Get or create the global connection pool"""
    global _pool
    if _pool is None:
        _pool = SupabasePool(max_connections=10)
    return _pool


# Convenience function for async context
async def get_connection():
    """Get a connection from the pool"""
    pool = get_pool()
    async with pool.acquire() as client:
        yield client