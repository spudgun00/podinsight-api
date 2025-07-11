#!/usr/bin/env python3
"""
Test the new hybrid search implementation
Verifies that "What are VCs saying about AI valuations?" returns relevant results
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime

# API endpoint
API_URL = os.getenv("API_URL", "https://podinsight-api.vercel.app")
TEST_QUERY = "What are VCs saying about AI valuations?"

async def test_hybrid_search():
    """Test the hybrid search with the problematic query"""

    print(f"Testing hybrid search at: {API_URL}")
    print(f"Query: '{TEST_QUERY}'")
    print("=" * 80)

    # Prepare request
    url = f"{API_URL}/api/search"
    payload = {
        "query": TEST_QUERY,
        "limit": 10,
        "offset": 0
    }

    # Make request
    async with aiohttp.ClientSession() as session:
        try:
            print(f"\nSending POST request to {url}")
            print(f"Payload: {json.dumps(payload, indent=2)}")

            async with session.post(url, json=payload) as response:
                status = response.status
                data = await response.json()

                print(f"\nResponse Status: {status}")

                if status == 200:
                    # Check if we have an answer
                    if data.get("answer"):
                        answer = data["answer"]
                        print(f"\n✅ ANSWER FOUND:")
                        print(f"Text: {answer.get('text', 'No text')}")
                        print(f"Citations: {len(answer.get('citations', []))} sources")

                        # Show citations
                        for i, citation in enumerate(answer.get('citations', []), 1):
                            print(f"\nCitation {i}:")
                            print(f"  - Podcast: {citation.get('podcast_name')}")
                            print(f"  - Episode: {citation.get('episode_title')}")
                            print(f"  - Timestamp: {citation.get('timestamp')}")
                    else:
                        print("\n❌ No answer synthesized")

                    # Check search results
                    results = data.get("results", [])
                    print(f"\n📊 SEARCH RESULTS: {len(results)} chunks found")
                    print(f"Search Method: {data.get('search_method', 'unknown')}")
                    print(f"Processing Time: {data.get('processing_time_ms', 'N/A')}ms")

                    # Analyze top 5 results
                    print("\n🔍 TOP 5 RESULTS ANALYSIS:")
                    for i, result in enumerate(results[:5], 1):
                        print(f"\n{i}. Episode: {result.get('episode_title', 'Unknown')[:60]}...")
                        print(f"   Podcast: {result.get('podcast_name', 'Unknown')}")
                        print(f"   Score: {result.get('similarity_score', 0):.3f}")

                        # Check if result contains relevant keywords
                        excerpt = result.get('excerpt', '').lower()
                        has_ai = 'ai' in excerpt or 'artificial intelligence' in excerpt
                        has_valuation = 'valuation' in excerpt or 'value' in excerpt or 'worth' in excerpt

                        print(f"   Contains 'AI': {'✅' if has_ai else '❌'}")
                        print(f"   Contains 'valuation': {'✅' if has_valuation else '❌'}")
                        print(f"   Preview: {excerpt[:150]}...")

                        # Check for hybrid search info if available
                        if 'matches' in result:
                            print(f"   Keyword matches: {result['matches']}")
                        if 'hybrid_score' in result:
                            print(f"   Hybrid score: {result['hybrid_score']:.3f}")

                    # Summary
                    print("\n📈 SUMMARY:")
                    relevant_count = sum(1 for r in results[:10]
                                       if ('ai' in r.get('excerpt', '').lower() and
                                           ('valuation' in r.get('excerpt', '').lower() or
                                            'value' in r.get('excerpt', '').lower())))

                    print(f"Relevant results (containing both AI and valuation): {relevant_count}/10")

                    if relevant_count >= 5:
                        print("✅ SUCCESS: Hybrid search is returning relevant results!")
                    else:
                        print("⚠️  WARNING: Still seeing irrelevant results. Check hybrid implementation.")

                else:
                    print(f"\n❌ ERROR: {data}")

        except Exception as e:
            print(f"\n❌ Request failed: {str(e)}")
            import traceback
            traceback.print_exc()

async def test_comparison():
    """Compare results with a simpler query to verify hybrid is working"""

    print("\n" + "=" * 80)
    print("COMPARISON TEST: Simple query")

    simple_query = "AI"
    url = f"{API_URL}/api/search"
    payload = {
        "query": simple_query,
        "limit": 5
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    print(f"\nQuery '{simple_query}' returned {len(results)} results")
                    print(f"First result score: {results[0].get('similarity_score', 0):.3f}" if results else "No results")

        except Exception as e:
            print(f"Comparison test failed: {e}")

if __name__ == "__main__":
    print(f"Starting hybrid search test at {datetime.now()}")
    asyncio.run(test_hybrid_search())
    asyncio.run(test_comparison())
