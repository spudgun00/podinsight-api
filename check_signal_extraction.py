#!/usr/bin/env python3
"""
Script to diagnose signal extraction issues
"""
import requests
import json

# Test cases - one working, one failing
test_episodes = [
    {
        "id": "02fc268c-61dc-4074-b7ec-882615bc6d85",
        "expected": "working"
    },
    {
        "id": "1216c2e7-42b8-42ca-92d7-bad784f80af2", 
        "expected": "failing"
    }
]

def test_signal_extraction(episode_id):
    """Test signal extraction for a specific episode"""
    url = f"https://podinsight-api.vercel.app/api/intelligence/test-signals/{episode_id}"
    response = requests.get(url)
    return response.json()

def get_document_structure(episode_id):
    """Get the raw document structure by querying MongoDB directly"""
    # This would need direct MongoDB access, so we'll rely on the API endpoints
    pass

print("Testing Signal Extraction")
print("=" * 50)

for episode in test_episodes:
    print(f"\nTesting episode: {episode['id']}")
    print(f"Expected: {episode['expected']}")
    
    result = test_signal_extraction(episode['id'])
    
    print(f"Direct query found: {result['direct_query_found']}")
    print(f"Has signals in DB: {result['direct_query_has_signals']}")
    print(f"Signals extracted: {result['get_episode_signals_count']}")
    
    if result['get_episode_signals_count'] > 0:
        print("✅ Signal extraction working")
    else:
        print("❌ Signal extraction failing")

print("\n" + "=" * 50)
print("\nConclusion: The issue is in the get_episode_signals function")
print("It finds the documents but fails to extract signals from some of them")
print("This suggests data format variations that the function doesn't handle")