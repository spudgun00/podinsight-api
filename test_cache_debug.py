#!/usr/bin/env python3
"""Debug cache functionality"""
import asyncio
from api.search import search_handler, SearchRequest, check_query_cache, store_query_cache
import hashlib
import time

async def debug_cache():
    """Debug why caching isn't working"""
    
    # Test query
    query = "test cache debug query"
    query_hash = hashlib.sha256(query.encode()).hexdigest()
    
    print(f"Query: {query}")
    print(f"Hash: {query_hash}")
    
    # Check if already cached
    cached = await check_query_cache(query_hash)
    print(f"\nInitial cache check: {cached is not None}")
    
    # Make first request
    request = SearchRequest(query=query, limit=3, offset=0)
    response1 = await search_handler(request)
    print(f"\nFirst request - cache hit: {response1.cache_hit}")
    
    # Wait for cache to be stored
    print("\nWaiting 2 seconds for cache storage...")
    await asyncio.sleep(2)
    
    # Check cache directly
    cached = await check_query_cache(query_hash)
    print(f"Direct cache check after wait: {cached is not None}")
    
    # Make second request
    response2 = await search_handler(request)
    print(f"\nSecond request - cache hit: {response2.cache_hit}")
    
    # If still not cached, store manually and test
    if not response2.cache_hit:
        print("\nManually storing in cache...")
        test_embedding = [0.1] * 384
        await store_query_cache(query, query_hash, test_embedding)
        await asyncio.sleep(1)
        
        # Check again
        cached = await check_query_cache(query_hash)
        print(f"Cache check after manual store: {cached is not None}")

if __name__ == "__main__":
    asyncio.run(debug_cache())