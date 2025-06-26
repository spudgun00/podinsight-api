#!/usr/bin/env python3
"""
Test production API to diagnose why vector search isn't working
"""
import requests
import json

# Test queries
queries = [
    "venture capital",
    "AI startup valuations",
    "OpenAI",
    "podcast"
]

print("Testing production API diagnostics...\n")

for query in queries:
    print(f"Query: '{query}'")

    response = requests.post(
        "https://podinsight-api.vercel.app/api/search",
        json={"query": query, "limit": 3},
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"  Status: OK")
        print(f"  Search method: {data.get('search_method', 'unknown')}")
        print(f"  Results: {len(data.get('results', []))}")
        print(f"  Cache hit: {data.get('cache_hit', False)}")

        if data.get('results'):
            first = data['results'][0]
            print(f"  First result:")
            print(f"    Episode ID: {first.get('episode_id', 'N/A')}")
            print(f"    Score: {first.get('similarity_score', 'N/A')}")
    else:
        print(f"  Status: ERROR {response.status_code}")
        print(f"  Response: {response.text[:200]}")

    print()

# Test the health endpoint
print("\nTesting health endpoint...")
health = requests.get("https://podinsight-api.vercel.app/api/health")
print(f"Health status: {health.status_code}")
if health.status_code == 200:
    print(f"Health response: {health.json()}")
