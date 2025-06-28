#!/usr/bin/env python3
"""
Test script to see the actual synthesis output
"""
import requests
import json
from datetime import datetime

def test_synthesis(query, limit=3):
    """Test the synthesis endpoint and display the output"""
    url = "https://podinsight-api.vercel.app/api/search"

    print(f"\n🔍 Testing query: '{query}' (limit={limit})")
    print("=" * 60)

    try:
        response = requests.post(
            url,
            json={"query": query, "limit": limit},
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()

            # Display the synthesized answer
            if data.get("answer"):
                answer = data["answer"]
                print("\n📝 SYNTHESIZED ANSWER:")
                print("-" * 60)
                print(answer["text"])
                print("\n📚 CITATIONS:")
                for i, citation in enumerate(answer["citations"], 1):
                    print(f"  [{citation['number']}] Chunk #{citation['chunk_index'] + 1}")
                    if 'timestamp' in citation:
                        print(f"      Time: {citation['timestamp']['start']:.1f}s - {citation['timestamp']['end']:.1f}s")
                    print()

            # Display search results
            print(f"\n🎯 SEARCH RESULTS: {len(data['results'])} episodes")
            print("-" * 60)
            for i, result in enumerate(data["results"], 1):
                print(f"\n{i}. {result['episode_title']}")
                print(f"   Podcast: {result['podcast_name']}")
                print(f"   Date: {result['published_date']}")
                print(f"   Score: {result['similarity_score']:.3f}")
                print(f"   Excerpt: {result['excerpt'][:200]}...")

            # Display metadata
            print(f"\n📊 METADATA:")
            print("-" * 60)
            print(f"Total results: {data['total_results']}")
            print(f"Processing time: {data.get('processing_time_ms', 'N/A')}ms")
            print(f"Search method: {data['search_method']}")
            print(f"Cache hit: {data['cache_hit']}")

        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)

    except requests.Timeout:
        print("❌ Request timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Test different queries
    test_queries = [
        ("AI valuations", 3),
        ("machine learning startups", 2),
        ("venture capital trends", 1)
    ]

    for query, limit in test_queries:
        test_synthesis(query, limit)
        print("\n" + "="*80 + "\n")
