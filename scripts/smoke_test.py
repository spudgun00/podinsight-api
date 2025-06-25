#!/usr/bin/env python3
"""Smoke test for CI/CD - fails if search doesn't work"""

import requests
import sys
import os

def smoke_test():
    """Test that basic search returns results"""
    api_url = os.getenv("API_URL", "https://podinsight-api.vercel.app/api/search")
    
    print(f"🔍 Running smoke test against {api_url}")
    
    try:
        # Test with a query that should always return results
        response = requests.post(
            api_url,
            json={"query": "openai", "limit": 5},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            return False
        
        data = response.json()
        total_results = data.get("total_results", 0)
        
        if total_results >= 5:
            print(f"✅ Smoke test passed! Found {total_results} results")
            return True
        else:
            print(f"❌ Smoke test failed! Only {total_results} results (expected >= 5)")
            return False
            
    except Exception as e:
        print(f"❌ Smoke test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = smoke_test()
    sys.exit(0 if success else 1)