#!/usr/bin/env python3
"""
Test 768D vector search implementation
"""

import asyncio
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Import our modules
from api.embeddings_768d import get_embedder
from api.mongodb_vector_search import get_vector_search_handler
from api.search_lightweight_768d import SearchRequest, search_handler_lightweight_768d

async def test_embeddings():
    """Test 768D embedding generation"""
    print("\n🧪 Testing 768D Embeddings Generation...")

    try:
        embedder = get_embedder()

        # Test queries
        test_queries = [
            "What did Sequoia say about AI valuations?",
            "confidence with humility",
            "DePIN infrastructure"
        ]

        for query in test_queries:
            embedding = embedder.encode_query(query)
            print(f"✅ Query: '{query}' → {len(embedding)}D embedding")
            print(f"   Sample values: {embedding[:5]}")

    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        return False

    return True


async def test_vector_search():
    """Test MongoDB vector search"""
    print("\n🧪 Testing MongoDB Vector Search...")

    try:
        # Get handlers
        embedder = get_embedder()
        vector_handler = await get_vector_search_handler()

        # Test query
        query = "AI agents and automation"
        print(f"🔍 Searching for: '{query}'")

        # Generate embedding
        embedding = embedder.encode_query(query)

        # Perform search
        results = await vector_handler.vector_search(
            embedding,
            limit=5,
            min_score=0.7
        )

        print(f"📊 Found {len(results)} results")

        for i, result in enumerate(results[:3]):
            print(f"\n Result {i+1}:")
            print(f"   Score: {result['score']:.3f}")
            print(f"   Episode: {result['podcast_name']} - {result['episode_title']}")
            print(f"   Chunk: {result['text'][:100]}...")
            print(f"   Time: {result['start_time']:.1f}s - {result['end_time']:.1f}s")

    except Exception as e:
        print(f"❌ Vector search test failed: {e}")
        return False

    return True


async def test_full_api():
    """Test full API search handler"""
    print("\n🧪 Testing Full API Search Handler...")

    try:
        # Create search request
        request = SearchRequest(
            query="venture capital AI investments",
            limit=5,
            offset=0
        )

        print(f"🔍 API Search: '{request.query}'")

        # Call search handler
        response = await search_handler_lightweight_768d(request)

        print(f"📊 Results: {response.total_results} total")
        print(f"🔧 Search method: {response.search_method}")
        print(f"💾 Cache hit: {response.cache_hit}")

        for i, result in enumerate(response.results[:3]):
            print(f"\n Result {i+1}:")
            print(f"   Score: {result.similarity_score:.3f}")
            print(f"   Episode: {result.podcast_name} - {result.episode_title}")
            print(f"   Date: {result.published_date}")
            print(f"   Excerpt: {result.excerpt[:150]}...")
            if result.timestamp:
                print(f"   Timestamp: {result.timestamp['start_time']:.1f}s")

    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """Run all tests"""
    print("🚀 Starting 768D Vector Search Tests")
    print("=" * 50)

    # Check environment
    if not os.getenv('MONGODB_URI'):
        print("❌ MONGODB_URI not set!")
        return

    # Run tests
    tests = [
        ("Embeddings", test_embeddings),
        ("Vector Search", test_vector_search),
        ("Full API", test_full_api)
    ]

    results = []
    for name, test_func in tests:
        success = await test_func()
        results.append((name, success))

    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {name}: {status}")

    # Close connections
    vector_handler = await get_vector_search_handler()
    await vector_handler.close()


if __name__ == "__main__":
    asyncio.run(main())
