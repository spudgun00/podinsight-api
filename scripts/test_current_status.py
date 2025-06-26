import requests
import time
import json

queries = [
    "venture capital",
    "AI startup valuations",
    "product market fit",
    "founder burnout",
    "Series A metrics"
]

for query in queries:
    start = time.time()
    try:
        resp = requests.post(
            "https://podinsight-api.vercel.app/api/search",
            json={"query": query, "limit": 3},
            timeout=20
        )
        data = resp.json()
        elapsed = time.time() - start

        print(f"\n{query}:")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Results: {len(data.get('results', []))}")
        print(f"  Method: {data.get('search_method', 'unknown')}")

        if data.get('results'):
            print(f"  First result score: {data['results'][0].get('relevance_score', 'N/A')}")

    except Exception as e:
        print(f"\n{query}: ERROR - {e}")
