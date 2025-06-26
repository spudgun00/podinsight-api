import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.mongodb_vector_search import get_vector_search_handler

async def test_fix():
    """Test that the event loop fix works"""
    print("Testing MongoDB vector search with event loop fix...")

    # Get handler
    handler = await get_vector_search_handler()

    # Test embedding (first 10 values of a normalized vector)
    test_embedding = [0.1] * 768

    # Perform search
    results = await handler.vector_search(test_embedding, limit=5)

    print(f"Results: {len(results)}")
    if results:
        print(f"First result score: {results[0].get('score', 'N/A')}")
    else:
        print("No results returned")

    return len(results) > 0

if __name__ == "__main__":
    success = asyncio.run(test_fix())
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
