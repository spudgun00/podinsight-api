#!/usr/bin/env python3
"""Quick E2E test for key queries"""
import requests
import time

API_URL = "https://podinsight-api.vercel.app/api/search"

# Key test queries
TEST_QUERIES = [
    "openai",           # Known working
    "venture capital",  # Known failing
    "podcast",          # Known failing
    "startup"          # Unknown
]

print("🔍 Quick E2E Test")
print(f"API: {API_URL}\n")

for query in TEST_QUERIES:
    print(f"Testing '{query}'... ", end="", flush=True)
    start = time.time()

    try:
        response = requests.post(
            API_URL,
            json={"query": query, "limit": 5, "offset": 0},
            timeout=10
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            data = response.json()
            count = len(data.get("results", []))
            method = data.get("search_method", "?")
            print(f"✅ {count} results via {method} ({elapsed:.1f}s)")
        elif response.status_code == 503:
            print(f"❌ 503 error ({elapsed:.1f}s)")
        else:
            print(f"❌ HTTP {response.status_code} ({elapsed:.1f}s)")

    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT (>10s)")
    except Exception as e:
        print(f"❌ ERROR: {str(e)[:50]}...")

print("\n✅ = Working | ❌ = Failing")
