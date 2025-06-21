#!/usr/bin/env python3
"""
Test the search API locally
"""

import requests
import json
import time

# Test queries
test_queries = [
    "What did Sequoia say about AI valuations?",
    "confidence with humility",
    "DePIN infrastructure", 
    "venture capital AI investments",
    "What makes a great founder?"
]

print("🚀 Testing Local API Search\n")

for query in test_queries:
    print(f"🔍 Query: '{query}'")
    
    # Make API request
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:8000/api/search",
            json={"query": query, "limit": 3}
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Success in {elapsed:.2f}s")
            print(f"📊 Found {data['total_results']} results")
            print(f"🔧 Search method: {data.get('search_method', 'unknown')}")
            print(f"💾 Cache hit: {data.get('cache_hit', False)}")
            
            # Show first result
            if data['results']:
                result = data['results'][0]
                print(f"\n   Top result:")
                print(f"   • {result['podcast_name']}: {result['episode_title']}")
                print(f"   • Score: {result['similarity_score']:.3f}")
                print(f"   • Excerpt: {result['excerpt'][:150]}...")
                if result.get('timestamp'):
                    print(f"   • Timestamp: {result['timestamp']['start_time']:.1f}s")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    print("-" * 60 + "\n")