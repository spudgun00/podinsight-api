#!/usr/bin/env python3
"""Test API search endpoint with POST method"""

import requests
import json
import time

API_URL = "https://podinsight-api.vercel.app/api/search"

def test_search_api():
    """Test the search API with POST requests"""

    test_queries = [
        "openai",
        "venture capital",
        "artificial intelligence",
        "sequoia capital",
        "founder burnout"
    ]

    print("Testing API Search Endpoint (POST)")
    print("=" * 60)

    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        start_time = time.time()

        try:
            response = requests.post(
                API_URL,
                json={"query": query},
                timeout=30
            )

            elapsed = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                num_results = len(data.get("results", []))
                search_method = data.get("searchMethod", "unknown")

                if num_results > 0:
                    print(f"✅ Status: 200 | Results: {num_results} | Method: {search_method} | Time: {elapsed:.0f}ms")
                    # Show first result preview
                    first_result = data["results"][0]
                    preview = first_result.get("text", "")[:100] + "..."
                    score = first_result.get("score", 0)
                    print(f"   Top result (score={score:.4f}): {preview}")
                else:
                    print(f"❌ Status: 200 | Results: 0 | Method: {search_method} | Time: {elapsed:.0f}ms")
            else:
                print(f"❌ Status: {response.status_code} | Time: {elapsed:.0f}ms")
                print(f"   Response: {response.text[:200]}")

        except requests.exceptions.Timeout:
            print(f"❌ Timeout after 30s")
        except Exception as e:
            print(f"❌ Exception: {type(e).__name__}: {str(e)}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_search_api()
