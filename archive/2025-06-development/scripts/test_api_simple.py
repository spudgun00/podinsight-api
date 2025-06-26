#!/usr/bin/env python3
"""Simple test to debug API issues"""

import requests
import json

# Test 1: Health check
print("1. Health Check")
response = requests.get("https://podinsight-api.vercel.app/api/health")
print(f"   Status: {response.status_code}")

# Test 2: Modal endpoint
print("\n2. Modal Endpoint")
modal_response = requests.post(
    "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run",
    json={"text": "test"},
    timeout=10
)
if modal_response.status_code == 200:
    data = modal_response.json()
    print(f"   ✅ Dimension: {data['dimension']}")
else:
    print(f"   ❌ Error: {modal_response.status_code}")

# Test 3: Search with different queries
print("\n3. Search Tests")
queries = ["test", "openai", "venture capital"]

for query in queries:
    print(f"\n   Query: '{query}'")

    # Try with explicit parameters
    response = requests.post(
        "https://podinsight-api.vercel.app/api/search",
        json={
            "query": query,
            "limit": 5,
            "offset": 0
        },
        timeout=15
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   Status: 200")
        print(f"   Results: {len(data.get('results', []))}")
        print(f"   Method: {data.get('search_method', 'unknown')}")
        print(f"   Total: {data.get('total_results', 0)}")

        # Show first result if any
        if data.get('results'):
            first = data['results'][0]
            print(f"   First result score: {first.get('similarity_score', 0)}")
    else:
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
