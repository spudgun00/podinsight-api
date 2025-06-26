#!/usr/bin/env python3
"""
Comprehensive test suite for 768D Modal embedding integration
Tests the full pipeline: Modal endpoint → MongoDB vector search → API response
"""

import asyncio
import os
from dotenv import load_dotenv
import json
import time
from datetime import datetime
import aiohttp

# Load environment variables
load_dotenv()

# Import our modules - using the correct Modal-based embedder
from api.embeddings_768d_modal import get_embedder
from api.mongodb_vector_search import get_vector_search_handler
from api.search_lightweight_768d import SearchRequest, search_handler_lightweight_768d

async def test_modal_endpoint_direct():
    """Test Modal endpoint directly with HTTP calls"""
    print("\n🧪 Testing Modal Endpoint Directly...")

    try:
        async with aiohttp.ClientSession() as session:
            # Test health
            async with session.get(
                "https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run/health"
            ) as resp:
                health = await resp.json()
                print(f"✅ Health check: {health}")

            # Test single embedding
            start = time.time()
            async with session.post(
                "https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run/embed",
                json={"text": "AI venture capital trends"}
            ) as resp:
                result = await resp.json()
                embed_time = time.time() - start

                print(f"✅ Single embedding: {len(result['embedding'])}D in {embed_time:.2f}s")
                print(f"   First 5 values: {result['embedding'][:5]}")

            # Test batch embedding
            start = time.time()
            async with session.post(
                "https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run/embed_batch",
                json={"texts": ["AI agents", "venture capital", "blockchain"]}
            ) as resp:
                result = await resp.json()
                batch_time = time.time() - start

                print(f"✅ Batch embedding: {len(result['embeddings'])} texts in {batch_time:.2f}s")
                print(f"   Dimensions: {[len(e) for e in result['embeddings']]}")

        return True

    except Exception as e:
        print(f"❌ Modal endpoint test failed: {e}")
        return False


async def test_embeddings_module():
    """Test the embeddings_768d_modal module"""
    print("\n🧪 Testing Embeddings Module (Modal HTTP)...")

    try:
        embedder = get_embedder()

        # Test queries with timing
        test_queries = [
            "What did Sequoia say about AI valuations?",
            "confidence with humility",
            "DePIN infrastructure",
            "AI agents and automation",
            "venture capital investment thesis"
        ]

        print(f"🔧 Testing {len(test_queries)} queries...")

        for query in test_queries:
            start = time.time()
            embedding = embedder.encode_query(query)
            elapsed = time.time() - start

            print(f"✅ Query: '{query}'")
            print(f"   → {len(embedding)}D embedding in {elapsed:.2f}s")
            print(f"   → Sample values: {embedding[:3]}")

            # Verify it's a proper 768D float array
            assert len(embedding) == 768, f"Expected 768D, got {len(embedding)}D"
            assert all(isinstance(x, float) for x in embedding), "Embedding should be floats"

    except Exception as e:
        print(f"❌ Embeddings module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_vector_search_direct():
    """Test MongoDB vector search directly"""
    print("\n🧪 Testing MongoDB Vector Search (Direct)...")

    try:
        # Get handlers
        embedder = get_embedder()
        vector_handler = await get_vector_search_handler()

        # Test different query types
        test_queries = [
            ("AI agents and automation", 0.7),
            ("confidence with humility", 0.6),
            ("venture capital returns", 0.7),
            ("founder market fit", 0.65)
        ]

        for query, min_score in test_queries:
            print(f"\n🔍 Searching for: '{query}' (min_score={min_score})")

            # Generate embedding
            start = time.time()
            embedding = embedder.encode_query(query)
            embed_time = time.time() - start

            # Perform search
            start = time.time()
            results = await vector_handler.vector_search(
                embedding,
                limit=5,
                min_score=min_score
            )
            search_time = time.time() - start

            print(f"⏱️  Timing: embed={embed_time:.2f}s, search={search_time:.2f}s")
            print(f"📊 Found {len(results)} results above score {min_score}")

            if results:
                # Show top result
                top = results[0]
                print(f"\n   🥇 Top Result (score={top['score']:.3f}):")
                print(f"      Episode: {top['podcast_name']} - {top['episode_title']}")
                print(f"      Chunk: {top['text'][:150]}...")
                print(f"      Time: {top['start_time']:.1f}s - {top['end_time']:.1f}s")
            else:
                print("   ⚠️  No results found - may need to adjust min_score")

    except Exception as e:
        print(f"❌ Vector search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_full_api_search():
    """Test full API search handler with different queries"""
    print("\n🧪 Testing Full API Search Handler...")

    try:
        # Test semantic queries that should use vector search
        semantic_queries = [
            "venture capital AI investments",
            "confidence combined with humility",
            "what makes a great founder",
            "AI disrupting traditional industries",
            "future of work and automation"
        ]

        for query in semantic_queries:
            print(f"\n🔍 API Search: '{query}'")

            request = SearchRequest(
                query=query,
                limit=3,
                offset=0
            )

            start = time.time()
            response = await search_handler_lightweight_768d(request)
            total_time = time.time() - start

            print(f"📊 Results: {response.total_results} total")
            print(f"🔧 Search method: {response.search_method}")
            print(f"⏱️  Total time: {total_time:.2f}s")
            print(f"💾 Cache hit: {response.cache_hit}")

            if response.results:
                top = response.results[0]
                print(f"\n   🥇 Top Result (score={top.similarity_score:.3f}):")
                print(f"      {top.podcast_name} - {top.episode_title}")
                print(f"      {top.excerpt[:150]}...")
            else:
                print("   ⚠️  No results found")

            # Add small delay to avoid rate limiting
            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_fallback_behavior():
    """Test that fallback to text search works when vector search fails"""
    print("\n🧪 Testing Fallback Behavior...")

    try:
        # Test with a very specific/rare query that might not have good vector matches
        rare_queries = [
            "xyzabc123notarealquery",  # Should fall back to text search
            "\"exact phrase search\"",   # Should use text search
            "podcast:\"This Week in Startups\""  # Field-specific search
        ]

        for query in rare_queries:
            print(f"\n🔍 Testing fallback for: '{query}'")

            request = SearchRequest(query=query, limit=5)
            response = await search_handler_lightweight_768d(request)

            print(f"📊 Search method used: {response.search_method}")
            print(f"📊 Results found: {response.total_results}")

    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False

    return True


async def verify_mongodb_index():
    """Verify MongoDB vector index configuration"""
    print("\n🧪 Verifying MongoDB Vector Index...")

    try:
        vector_handler = await get_vector_search_handler()

        # Get index info
        indexes = await vector_handler.db.podcast_chunks.list_indexes().to_list(None)

        vector_index = None
        for idx in indexes:
            if idx.get('name') == 'vector_index':
                vector_index = idx
                break

        if vector_index:
            print("✅ Vector index found:")
            print(f"   Name: {vector_index['name']}")
            print(f"   Fields: {list(vector_index.get('key', {}).keys())}")

            # Check if it's a proper vector search index
            if 'vectorSearchOptions' in str(vector_index):
                print("   Type: Atlas Vector Search")
            else:
                print("   Type: Standard index (not vector search)")
        else:
            print("❌ No vector index found!")

            # List all indexes
            print("\n📋 Available indexes:")
            for idx in indexes:
                print(f"   - {idx['name']}: {list(idx.get('key', {}).keys())}")

    except Exception as e:
        print(f"❌ Index verification failed: {e}")
        return False

    return True


async def main():
    """Run all tests"""
    print("🚀 Starting Comprehensive 768D Modal Integration Tests")
    print("=" * 60)

    # Check environment
    if not os.getenv('MONGODB_URI'):
        print("❌ MONGODB_URI not set!")
        return

    print(f"📍 Environment:")
    print(f"   MONGODB_URI: {'✅ Set' if os.getenv('MONGODB_URI') else '❌ Missing'}")
    print(f"   Modal Endpoint: https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run")

    # Run tests in order
    tests = [
        ("Modal Endpoint Direct", test_modal_endpoint_direct),
        ("Embeddings Module", test_embeddings_module),
        ("MongoDB Index", verify_mongodb_index),
        ("Vector Search Direct", test_vector_search_direct),
        ("Full API Search", test_full_api_search),
        ("Fallback Behavior", test_fallback_behavior)
    ]

    results = []
    for name, test_func in tests:
        print(f"\n{'='*60}")
        success = await test_func()
        results.append((name, success))

        # Give Modal a brief rest between tests
        await asyncio.sleep(1)

    # Summary
    print("\n" + "="*60)
    print("📋 Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {name}: {status}")

    print(f"\n🏁 Overall: {passed}/{total} tests passed")

    # Close connections
    vector_handler = await get_vector_search_handler()
    await vector_handler.close()


if __name__ == "__main__":
    asyncio.run(main())
