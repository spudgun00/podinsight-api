#!/usr/bin/env python3
"""Smoke test for CI/CD - fails if search doesn't work"""

import requests
import sys
import os

def smoke_test():
    """Test that basic search returns results"""
    api_url = os.getenv("API_URL", "https://podinsight-api.vercel.app/api/search")
    
    print(f"🔍 Running smoke test against {api_url}")
    
    # Test multiple queries
    test_queries = [
        ("openai", 5),
        ("venture capital", 1),
        ("podcast", 1)
    ]
    
    all_passed = True
    
    for query, expected_min in test_queries:
        try:
            response = requests.post(
                api_url,
                json={"query": query, "limit": 5},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ '{query}' returned status {response.status_code}")
                all_passed = False
                continue
            
            data = response.json()
            total_results = data.get("total_results", 0)
            
            if total_results >= expected_min:
                print(f"✅ '{query}' passed - found {total_results} results")
            else:
                print(f"❌ '{query}' failed - only {total_results} results (expected >= {expected_min})")
                all_passed = False
                
        except Exception as e:
            print(f"❌ '{query}' failed with exception: {e}")
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    success = smoke_test()
    sys.exit(0 if success else 1)