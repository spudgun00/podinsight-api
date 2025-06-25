#!/usr/bin/env python3
"""Debug API search behavior"""

import requests
import json
import time

def test_modal_directly():
    """Test Modal endpoint with different queries"""
    print("\n1. Testing Modal Endpoint Directly")
    print("=" * 50)
    
    modal_url = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"
    queries = ["openai", "venture capital"]
    
    for query in queries:
        response = requests.post(modal_url, json={"text": query}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ '{query}' -> {data['dimension']}D embedding")
            print(f"   First 3 values: {data['embedding'][:3]}")
        else:
            print(f"❌ '{query}' -> Error {response.status_code}")

def test_api_with_debug():
    """Test API with various queries and show debug info"""
    print("\n2. Testing API Search with Debug Info")
    print("=" * 50)
    
    api_url = "https://podinsight-api.vercel.app/api/search"
    
    # Test queries that should work
    test_queries = [
        ("openai", "Works in some tests"),
        ("OpenAI", "Capitalized version"),
        ("venture capital", "Should have many results"),
        ("Venture Capital", "Capitalized version"),
        ("ai", "Short query"),
        ("vc", "Very short query"),
        ("podcast", "Generic term")
    ]
    
    for query, description in test_queries:
        print(f"\nTesting: '{query}' ({description})")
        
        try:
            start = time.time()
            response = requests.post(
                api_url,
                json={"query": query},
                headers={"Cache-Control": "no-cache"},
                timeout=20
            )
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                method = data.get("search_method", "unknown")
                
                print(f"  Status: 200 | Results: {len(results)} | Method: {method} | Time: {elapsed:.0f}ms")
                
                if len(results) > 0:
                    first = results[0]
                    print(f"  Top result score: {first.get('similarity_score', 0):.4f}")
                else:
                    # Check if it's falling back to text search
                    print(f"  ⚠️ No results - possible vector search failure")
                    
                # Show additional debug info if available
                if "debug" in data:
                    print(f"  Debug: {data['debug']}")
                    
            else:
                print(f"  Error: {response.status_code} | Time: {elapsed:.0f}ms")
                
        except Exception as e:
            print(f"  Exception: {e}")

def test_search_params():
    """Test different search parameters"""
    print("\n3. Testing Different Search Parameters")
    print("=" * 50)
    
    api_url = "https://podinsight-api.vercel.app/api/search"
    
    # Try different parameter formats
    test_cases = [
        {"query": "openai", "limit": 5},
        {"query": "openai", "offset": 0},
        {"query": "openai", "search_method": "vector_768d"},
        {"q": "openai"},  # Old parameter name
    ]
    
    for params in test_cases:
        print(f"\nParams: {params}")
        
        try:
            response = requests.post(api_url, json=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Results: {len(data.get('results', []))}")
            else:
                print(f"  ❌ Error: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")

if __name__ == "__main__":
    print("🔍 API Debug Script")
    print("Started:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    test_modal_directly()
    test_api_with_debug()
    test_search_params()