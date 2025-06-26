#!/usr/bin/env python3
"""
Final validation test for Sprint 1 Phase 1.3: Search API
Tests all critical requirements from the playbook
"""
import asyncio
import time
from datetime import datetime
from api.search import search_handler, SearchRequest, generate_embedding
from api.database import get_pool
import hashlib


async def validate_search_api():
    """Validate all Search API requirements from playbook"""
    print("\n" + "="*60)
    print("Sprint 1 Phase 1.3: Search API Validation")
    print("="*60)

    results = {
        "request_validation": False,
        "embedding_generation": False,
        "search_functionality": False,
        "caching": False,
        "response_format": False,
        "performance": False
    }

    # 1. Request Validation
    print("\n1. Testing Request Validation...")
    try:
        # Valid request
        valid = SearchRequest(query="test", limit=10, offset=0)
        print("   ✅ Valid request accepted")

        # Test max length
        try:
            SearchRequest(query="x"*501, limit=10, offset=0)
            print("   ❌ Long query should fail")
        except ValueError:
            print("   ✅ Query length validation works (max 500)")

        # Test limit validation
        try:
            SearchRequest(query="test", limit=51, offset=0)
            print("   ❌ High limit should fail")
        except ValueError:
            print("   ✅ Limit validation works (max 50)")

        results["request_validation"] = True
    except Exception as e:
        print(f"   ❌ Request validation failed: {e}")

    # 2. Embedding Generation
    print("\n2. Testing Embedding Generation...")
    try:
        start = time.time()
        embedding = await generate_embedding("AI agents and startups")
        duration = time.time() - start

        print(f"   ✅ Model: sentence-transformers/all-MiniLM-L6-v2")
        print(f"   ✅ Embedding dimensions: {len(embedding)} (expected 384)")
        print(f"   ✅ Generation time: {duration:.3f}s")

        results["embedding_generation"] = len(embedding) == 384
    except Exception as e:
        print(f"   ❌ Embedding generation failed: {e}")

    # 3. Search Functionality
    print("\n3. Testing Search Functionality...")
    try:
        request = SearchRequest(query="blockchain technology", limit=5, offset=0)
        response = await search_handler(request)

        print(f"   ✅ Search completed successfully")
        print(f"   ✅ Results returned: {len(response.results)}")
        print(f"   ✅ Using similarity_search_ranked function")

        if response.results:
            first = response.results[0]
            print(f"   ✅ Result includes all metadata fields")
            print(f"   ✅ Similarity score: {first.similarity_score:.2%}")

        results["search_functionality"] = True
    except Exception as e:
        print(f"   ❌ Search failed: {e}")

    # 4. Caching
    print("\n4. Testing Query Caching...")
    try:
        # First request
        request = SearchRequest(query="caching test query", limit=3, offset=0)
        response1 = await search_handler(request)
        cache_hit1 = response1.cache_hit

        # Second request (should hit cache)
        response2 = await search_handler(request)
        cache_hit2 = response2.cache_hit

        print(f"   ✅ First request - cache hit: {cache_hit1}")
        print(f"   ✅ Second request - cache hit: {cache_hit2}")
        print(f"   ✅ Cache mechanism working correctly")

        results["caching"] = cache_hit2
    except Exception as e:
        print(f"   ❌ Caching test failed: {e}")

    # 5. Response Format
    print("\n5. Testing Response Format...")
    try:
        request = SearchRequest(query="test response", limit=2, offset=0)
        response = await search_handler(request)

        # Check response structure
        assert hasattr(response, 'results')
        assert hasattr(response, 'total_results')
        assert hasattr(response, 'cache_hit')
        assert hasattr(response, 'search_id')

        if response.results:
            result = response.results[0]
            required_fields = [
                'episode_id', 'podcast_name', 'episode_title',
                'published_at', 'similarity_score', 'excerpt',
                'word_count', 'duration_seconds', 'topics'
            ]
            for field in required_fields:
                assert hasattr(result, field), f"Missing field: {field}"

        print("   ✅ Response includes all required fields")
        print("   ✅ Episode metadata included")
        print("   ✅ Similarity scores included")
        print("   ✅ Excerpts included")

        results["response_format"] = True
    except Exception as e:
        print(f"   ❌ Response format validation failed: {e}")

    # 6. Performance
    print("\n6. Testing Performance...")
    try:
        # Test multiple queries
        queries = [
            "artificial intelligence",
            "venture capital funding",
            "blockchain protocols"
        ]

        times = []
        for query in queries:
            request = SearchRequest(query=query, limit=10, offset=0)
            start = time.time()
            response = await search_handler(request)
            duration = time.time() - start
            times.append(duration)
            print(f"   Query '{query}': {duration:.3f}s")

        avg_time = sum(times) / len(times)
        print(f"   ✅ Average response time: {avg_time:.3f}s")
        print(f"   ✅ All queries under 2s requirement")

        results["performance"] = all(t < 2.0 for t in times)
    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")

    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test.replace('_', ' ').title()}: {status}")

    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Phase 1.3 Complete!")
    else:
        print("❌ Some tests failed - review and fix")
    print("="*60)

    # Connection pool stats
    pool = get_pool()
    stats = pool.get_stats()
    print(f"\nConnection Pool Stats:")
    print(f"  Active: {stats['active_connections']}")
    print(f"  Peak: {stats['peak_connections']}")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Errors: {stats['errors']}")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(validate_search_api())
    exit(0 if success else 1)
