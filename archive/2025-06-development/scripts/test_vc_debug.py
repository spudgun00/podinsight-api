#!/usr/bin/env python3
"""Debug venture capital query"""
import requests
import time

API_URL = "https://podinsight-api.vercel.app/api/search"

print("Testing 'venture capital' query with extended timeout...")
start = time.time()

try:
    response = requests.post(
        API_URL,
        json={"query": "venture capital", "limit": 5, "offset": 0},
        timeout=30  # Extended timeout
    )
    elapsed = time.time() - start

    print(f"\nResponse in {elapsed:.1f}s")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Results: {len(data.get('results', []))}")
        print(f"Method: {data.get('search_method')}")
        if data.get('results'):
            print(f"First result: {data['results'][0]['episode_title'][:60]}...")
    else:
        print(f"Response: {response.text[:200]}")

except requests.exceptions.Timeout:
    print(f"TIMEOUT after 30s")
except Exception as e:
    print(f"ERROR: {e}")

# Test with normalized query
print("\n\nTesting normalized 'Venture Capital' query...")
try:
    response = requests.post(
        API_URL,
        json={"query": "Venture Capital", "limit": 5, "offset": 0},
        timeout=15
    )
    print(f"Status: {response.status_code}")
except Exception as e:
    print(f"ERROR: {e}")
