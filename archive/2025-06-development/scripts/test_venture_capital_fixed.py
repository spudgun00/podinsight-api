#!/usr/bin/env python3
"""
Test venture capital query with the fixed MongoDB handler
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.mongodb_vector_search import get_vector_search_handler
from api.embedding_utils import embed_query

async def test_venture_capital():
    """Test vector search for 'venture capital' query"""
    print("Testing 'venture capital' query with fixed MongoDB handler...")

    # Generate embedding
    query = "venture capital"
    embedding = embed_query(query)

    if not embedding:
        print("❌ Failed to generate embedding")
        return False

    print(f"✅ Generated embedding: length={len(embedding)}")

    # Get handler and search
    handler = await get_vector_search_handler()

    # Test 1: Basic search
    print("\nTest 1: Basic vector search...")
    results = await handler.vector_search(embedding, limit=5)
    print(f"Results: {len(results)}")

    if results:
        print(f"✅ First result score: {results[0].get('score', 'N/A')}")
        print(f"   Text preview: {results[0].get('text', 'N/A')[:100]}...")
    else:
        print("❌ No results returned")
        return False

    # Test 2: Search with different limit
    print("\nTest 2: Search with limit=10...")
    results2 = await handler.vector_search(embedding, limit=10)
    print(f"Results: {len(results2)}")

    # Test 3: Cache hit
    print("\nTest 3: Testing cache (should be fast)...")
    import time
    start = time.time()
    results3 = await handler.vector_search(embedding, limit=5)
    elapsed = time.time() - start
    print(f"Cache test: {len(results3)} results in {elapsed:.3f}s")

    return len(results) > 0

if __name__ == "__main__":
    success = asyncio.run(test_venture_capital())
    print(f"\n{'✅ ALL TESTS PASSED' if success else '❌ TESTS FAILED'}")
