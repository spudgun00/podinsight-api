#!/usr/bin/env python3
"""
Test the context expansion implementation
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from api.search_lightweight_768d import search_handler_lightweight_768d, SearchRequest

async def test_search_with_context():
    """Test search with expanded context"""

    # Test queries
    queries = [
        "AI venture capital investments",
        "confidence with humility",
        "data entry automation"
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"🔍 Query: '{query}'")
        print('='*60)

        request = SearchRequest(
            query=query,
            limit=2,  # Just get top 2 results
            offset=0
        )

        try:
            response = await search_handler_lightweight_768d(request)

            print(f"\n📊 Results: {response.total_results} total")
            print(f"🔧 Method: {response.search_method}")

            for i, result in enumerate(response.results):
                print(f"\n--- Result {i+1} ---")
                print(f"📻 {result.podcast_name} - {result.episode_title}")
                print(f"⭐ Score: {result.similarity_score:.3f}")
                print(f"⏱️  Time: {result.timestamp['start_time']:.1f}s - {result.timestamp['end_time']:.1f}s")
                print(f"\n📝 Excerpt ({result.word_count} words):")
                print(f"{result.excerpt}")
                print("\n" + "-"*50)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Testing Context Expansion Feature")
    asyncio.run(test_search_with_context())
