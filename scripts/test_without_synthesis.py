#!/usr/bin/env python3
"""
Test search without synthesis by setting the env var
"""
import requests
import os

def test_without_synthesis():
    """Test if the issue is with synthesis"""
    
    # First, let's try a search that shouldn't trigger synthesis
    # by using a very obscure query that might not have good results
    
    print("Test 1: Query that might not trigger synthesis (no good results)")
    url = "https://podinsight-api.vercel.app/api/search"
    payload = {
        "query": "xyzabc123randomquery",  # Unlikely to match anything
        "limit": 1
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Got {len(data.get('results', []))} results")
            print(f"Has answer: {'answer' in data and data['answer'] is not None}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 2: Normal query
    print("Test 2: Normal query that should work")
    payload = {
        "query": "podcast",  # Simple word that should match
        "limit": 1
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Got {len(data.get('results', []))} results")
            print(f"Has answer: {'answer' in data and data['answer'] is not None}")
            
            # Check response size
            response_size = len(response.content)
            print(f"Response size: {response_size} bytes ({response_size/1024:.1f} KB)")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_without_synthesis()