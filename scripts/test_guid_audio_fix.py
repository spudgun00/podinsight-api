#!/usr/bin/env python3
"""
Test script to verify audio API works with GUIDs from search results
"""

import requests
import json
import time

# Test data from frontend report
TEST_GUIDS = [
    "673b06c4-cf90-11ef-b9e1-0b761165641d",  # From frontend test
    "9497d063-69c2-4701-9951-931c1599b170"   # Another from frontend
]

# Original ObjectId test (should still work)
TEST_OBJECTID = "685ba776e4f9ec2f0756267a"  # Known working ObjectId  # pragma: allowlist secret

API_BASE = "https://podinsight-api.vercel.app"

def test_audio_endpoint(episode_id, start_time_ms=30000):
    """Test audio endpoint with given episode ID"""
    url = f"{API_BASE}/api/v1/audio_clips/{episode_id}"
    params = {"start_time_ms": start_time_ms}

    print(f"\nTesting: {episode_id}")
    print(f"URL: {url}")
    print(f"Params: {params}")

    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success! Response:")
            print(f"  - Cache hit: {data.get('cache_hit')}")
            print(f"  - Generation time: {data.get('generation_time_ms')}ms")
            print(f"  - Clip URL: {data.get('clip_url')[:80]}...")
        else:
            print(f"Error response: {response.text}")

    except Exception as e:
        print(f"Request failed: {e}")

def main():
    print("=" * 80)
    print("Testing Audio API with GUIDs and ObjectIds")
    print("=" * 80)

    # Wait for deployment
    print("\nNote: If just deployed, the fix may take 6 minutes to be live on Vercel")

    # Test with ObjectId (backward compatibility)
    print("\n1. Testing with ObjectId (backward compatibility):")
    test_audio_endpoint(TEST_OBJECTID, 30000)

    # Test with GUIDs from frontend
    print("\n2. Testing with GUIDs from search results:")
    for guid in TEST_GUIDS:
        test_audio_endpoint(guid, 556789)
        time.sleep(1)  # Be nice to the server

if __name__ == "__main__":
    main()
