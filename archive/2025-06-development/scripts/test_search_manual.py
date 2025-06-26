#!/usr/bin/env python3
"""
Manual test script for the search API
Run this to test the search functionality locally
"""
import asyncio
import json
from datetime import datetime
from api.search import search_handler, SearchRequest, generate_embedding
from api.database import get_pool


async def test_search():
    """Test various search queries"""

    print("🔍 Testing PodInsightHQ Search API")
    print("=" * 50)

    # Test queries
    test_queries = [
        "AI agents and autonomous systems",
        "startup valuations and funding rounds",
        "DePIN infrastructure",
        "B2B SaaS growth metrics",
        "Crypto/Web3 decentralization"
    ]

    for query in test_queries:
        print(f"\n📝 Testing query: '{query}'")
        print("-" * 40)

        try:
            # Test embedding generation
            print("  Generating embedding...")
            start = datetime.now()
            embedding = await generate_embedding(query)
            embed_time = (datetime.now() - start).total_seconds()
            print(f"  ✅ Embedding generated: {len(embedding)} dimensions in {embed_time:.3f}s")

            # Test search
            print("  Executing search...")
            request = SearchRequest(query=query, limit=3, offset=0)
            start = datetime.now()
            response = await search_handler(request)
            search_time = (datetime.now() - start).total_seconds()

            print(f"  ✅ Search completed in {search_time:.3f}s")
            print(f"  📊 Results: {len(response.results)} episodes found (total: {response.total_results})")
            print(f"  💾 Cache hit: {response.cache_hit}")

            # Show top results
            if response.results:
                print("\n  Top results:")
                for i, result in enumerate(response.results[:3], 1):
                    print(f"\n  {i}. {result.episode_title}")
                    print(f"     Podcast: {result.podcast_name}")
                    print(f"     Similarity: {result.similarity_score:.2%}")
                    print(f"     Topics: {', '.join(result.topics) if result.topics else 'None'}")
                    print(f"     Published: {result.published_at[:10]}")
                    print(f"     Excerpt: {result.excerpt[:100]}...")
            else:
                print("  ❌ No results found")

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

    # Test caching
    print("\n\n🔄 Testing query caching...")
    print("-" * 40)

    cache_query = "artificial intelligence and machine learning"
    request = SearchRequest(query=cache_query, limit=5, offset=0)

    # First request
    print(f"Query: '{cache_query}'")
    start = datetime.now()
    response1 = await search_handler(request)
    time1 = (datetime.now() - start).total_seconds()
    print(f"First request: {time1:.3f}s (cache hit: {response1.cache_hit})")

    # Second request (should hit cache)
    start = datetime.now()
    response2 = await search_handler(request)
    time2 = (datetime.now() - start).total_seconds()
    print(f"Second request: {time2:.3f}s (cache hit: {response2.cache_hit})")

    if response2.cache_hit:
        speedup = (time1 - time2) / time1 * 100
        print(f"✅ Cache working! {speedup:.1f}% faster")

    # Test pagination
    print("\n\n📄 Testing pagination...")
    print("-" * 40)

    page_query = "technology and innovation"

    # Page 1
    request1 = SearchRequest(query=page_query, limit=5, offset=0)
    response1 = await search_handler(request1)
    print(f"Page 1: {len(response1.results)} results")

    # Page 2
    request2 = SearchRequest(query=page_query, limit=5, offset=5)
    response2 = await search_handler(request2)
    print(f"Page 2: {len(response2.results)} results")

    # Check for duplicates
    if response1.results and response2.results:
        ids1 = {r.episode_id for r in response1.results}
        ids2 = {r.episode_id for r in response2.results}
        if ids1.isdisjoint(ids2):
            print("✅ No duplicate results between pages")
        else:
            print("❌ Found duplicate results!")

    # Test connection pool stats
    pool = get_pool()
    stats = pool.get_stats()
    print("\n\n📊 Connection Pool Stats:")
    print("-" * 40)
    print(f"Active connections: {stats['active_connections']}/{stats['max_connections']}")
    print(f"Total requests: {stats['total_requests']}")
    print(f"Errors: {stats['errors']}")
    print(f"Peak connections: {stats['peak_connections']}")


async def test_edge_cases():
    """Test edge cases and error handling"""

    print("\n\n🧪 Testing edge cases...")
    print("=" * 50)

    # Test empty query
    try:
        request = SearchRequest(query="", limit=10, offset=0)
        print("❌ Empty query should have failed validation")
    except ValueError:
        print("✅ Empty query correctly rejected")

    # Test very long query
    try:
        request = SearchRequest(query="x" * 501, limit=10, offset=0)
        print("❌ Long query should have failed validation")
    except ValueError:
        print("✅ Long query correctly rejected")

    # Test invalid limit
    try:
        request = SearchRequest(query="test", limit=100, offset=0)
        print("❌ Invalid limit should have failed validation")
    except ValueError:
        print("✅ Invalid limit correctly rejected")

    # Test query with special characters
    special_query = "AI & ML: What's next? (2025 edition)"
    request = SearchRequest(query=special_query, limit=3, offset=0)
    response = await search_handler(request)
    print(f"✅ Special characters handled: {len(response.results)} results")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════╗
║     PodInsightHQ Search API - Manual Test Suite      ║
╚══════════════════════════════════════════════════════╝
    """)

    try:
        asyncio.run(test_search())
        asyncio.run(test_edge_cases())

        print("\n\n✅ All tests completed!")

    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
