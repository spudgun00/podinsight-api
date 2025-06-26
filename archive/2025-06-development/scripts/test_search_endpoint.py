#!/usr/bin/env python3
"""
Test the search endpoint directly
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

# Import the search handler directly
from api.search_lightweight_768d import search_handler_lightweight_768d, SearchRequest

async def test_search():
    """Test search with different queries"""

    queries = [
        ("AI venture capital investments", "Should match AI/VC content"),
        ("confidence with humility", "Should match leadership/founder content"),
        ("future of automation", "Should match tech trends")
    ]

    for query, description in queries:
        print(f"\n🔍 Testing: '{query}'")
        print(f"   ({description})")

        request = SearchRequest(
            query=query,
            limit=3,
            offset=0
        )

        try:
            response = await search_handler_lightweight_768d(request)

            print(f"\n📊 Results:")
            print(f"   Total: {response.total_results}")
            print(f"   Method: {response.search_method}")
            print(f"   Cache hit: {response.cache_hit}")

            if response.results:
                print(f"\n   Top matches:")
                for i, result in enumerate(response.results):
                    print(f"\n   {i+1}. {result.podcast_name} - {result.episode_title}")
                    print(f"      Score: {result.similarity_score:.3f}")
                    print(f"      Date: {result.published_date}")
                    print(f"      Excerpt: {result.excerpt[:150]}...")
                    if result.timestamp:
                        print(f"      Time: {result.timestamp['start_time']:.1f}s - {result.timestamp['end_time']:.1f}s")
            else:
                print("   ❌ No results found")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_search())
