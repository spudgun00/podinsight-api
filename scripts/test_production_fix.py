import asyncio
import os
import sys
import requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.mongodb_vector_search import get_vector_search_handler
from api.embeddings_768d_modal import generate_embedding_768d

async def test_production_fix():
    """Test the fix with real embedding generation"""
    print("Testing with 'venture capital' query...")

    # Generate real embedding
    embedding = generate_embedding_768d("venture capital")
    print(f"Generated embedding: length={len(embedding)}, first 5 values={embedding[:5]}")

    # Get handler and search
    handler = await get_vector_search_handler()
    results = await handler.vector_search(embedding, limit=5)

    print(f"\nVector search results: {len(results)}")
    for i, result in enumerate(results[:3]):
        print(f"\nResult {i+1}:")
        print(f"  Score: {result.get('score', 'N/A')}")
        print(f"  Text: {result.get('text', 'N/A')[:100]}...")
        print(f"  Episode ID: {result.get('episode_id', 'N/A')}")

    return len(results) > 0

if __name__ == "__main__":
    success = asyncio.run(test_production_fix())
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
