#\!/usr/bin/env python3
"""Test the search API with detailed output"""

import requests
import json
import textwrap

def test_search_detailed():
    """Test search with detailed output"""
    url = "https://podinsight-api.vercel.app/api/search"

    queries = [
        "AI agents valuations",
        "venture capital trends",
        "B2B SaaS metrics"
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"Searching for: {query}")
        print(f"{'='*60}")

        response = requests.post(url, json={"query": query, "limit": 2})

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Found {len(data['results'])} results")
            print(f"Cache hit: {data.get('cache_hit', False)}")

            for i, result in enumerate(data['results'], 1):
                print(f"\n--- Result {i} ---")
                print(f"Podcast: {result.get('podcast_name', 'N/A')}")
                print(f"Episode: {result.get('title', 'N/A')[:80]}...")
                print(f"Date: {result.get('published_at', 'N/A')}")

                excerpt = result.get('excerpt', '')
                if excerpt:
                    # Wrap text for better readability
                    wrapped = textwrap.fill(excerpt, width=60, initial_indent="  ", subsequent_indent="  ")
                    print(f"Excerpt:\n{wrapped}")
        else:
            print(f"✗ Search failed: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    print("PodInsight Search API Test - Detailed Results")
    test_search_detailed()
