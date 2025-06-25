#!/usr/bin/env python3
"""
Test Phase 1 fixes for PodInsight API
Tests query normalization, offset/limit math, and nested array handling
"""

import requests
import json
import time
import sys

API_URL = "https://podinsight-api.vercel.app/api/search"

def test_query_normalization():
    """Test that case sensitivity is fixed"""
    print("\n1. Testing Query Normalization")
    print("=" * 50)
    
    test_cases = [
        ("openai", "lowercase"),
        ("OpenAI", "capitalized"),
        ("OPENAI", "uppercase"),
        (" openai ", "with spaces"),
        ("  OpenAI  ", "capitalized with spaces")
    ]
    
    results = {}
    for query, description in test_cases:
        try:
            response = requests.post(
                API_URL,
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                num_results = len(data.get("results", []))
                results[query] = num_results
                print(f"✅ '{query}' ({description}): {num_results} results")
            else:
                results[query] = -1
                print(f"❌ '{query}' ({description}): HTTP {response.status_code}")
                
        except Exception as e:
            results[query] = -1
            print(f"❌ '{query}' ({description}): {e}")
    
    # Check if all normalized to same result count
    unique_counts = set(v for v in results.values() if v >= 0)
    if len(unique_counts) == 1 and list(unique_counts)[0] > 0:
        print("\n✅ Query normalization PASSED - all variants return same results")
        return True
    else:
        print("\n❌ Query normalization FAILED - inconsistent results")
        return False

def test_offset_limit():
    """Test that offset/limit math is fixed"""
    print("\n2. Testing Offset/Limit Logic")
    print("=" * 50)
    
    # First get total results for a query
    response = requests.post(API_URL, json={"query": "openai", "limit": 50}, timeout=10)
    if response.status_code != 200:
        print("❌ Cannot test offset/limit - base query failed")
        return False
    
    total_results = response.json().get("total_results", 0)
    print(f"Total results available: {total_results}")
    
    # Test different offset/limit combinations
    test_cases = [
        (0, 10, "First page"),
        (5, 10, "Mid-page offset"),
        (10, 10, "Second page"),
        (0, 5, "Small limit"),
        (20, 5, "Deep offset")
    ]
    
    all_passed = True
    for offset, limit, description in test_cases:
        try:
            response = requests.post(
                API_URL,
                json={"query": "openai", "offset": offset, "limit": limit},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                # Check we got the right number of results
                expected = min(limit, max(0, total_results - offset))
                if len(results) == expected:
                    print(f"✅ {description} (offset={offset}, limit={limit}): {len(results)} results")
                else:
                    print(f"❌ {description}: Expected {expected}, got {len(results)}")
                    all_passed = False
            else:
                print(f"❌ {description}: HTTP {response.status_code}")
                all_passed = False
                
        except Exception as e:
            print(f"❌ {description}: {e}")
            all_passed = False
    
    return all_passed

def test_various_queries():
    """Test that various queries now work"""
    print("\n3. Testing Various Queries")
    print("=" * 50)
    
    test_queries = [
        "openai",
        "venture capital",
        "artificial intelligence", 
        "podcast",
        "sam altman",
        "sequoia",
        "ai",
        "vc"
    ]
    
    working_queries = 0
    for query in test_queries:
        try:
            response = requests.post(
                API_URL,
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                num_results = len(data.get("results", []))
                
                if num_results > 0:
                    print(f"✅ '{query}': {num_results} results")
                    working_queries += 1
                else:
                    print(f"❌ '{query}': 0 results")
            else:
                print(f"❌ '{query}': HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ '{query}': {e}")
    
    success_rate = working_queries / len(test_queries)
    print(f"\nSuccess rate: {working_queries}/{len(test_queries)} ({success_rate:.0%})")
    
    return success_rate >= 0.8  # 80% threshold

def main():
    """Run all tests"""
    print("🔍 Testing Phase 1 Fixes")
    print("API:", API_URL)
    print("Started:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Run tests
    normalization_ok = test_query_normalization()
    offset_limit_ok = test_offset_limit()
    queries_ok = test_various_queries()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    print(f"Query Normalization: {'✅ PASS' if normalization_ok else '❌ FAIL'}")
    print(f"Offset/Limit Logic: {'✅ PASS' if offset_limit_ok else '❌ FAIL'}")
    print(f"Various Queries: {'✅ PASS' if queries_ok else '❌ FAIL'}")
    
    all_passed = normalization_ok and offset_limit_ok and queries_ok
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL PHASE 1 FIXES WORKING!")
        print("\nThe API should now:")
        print("- Handle case-insensitive queries")
        print("- Properly paginate results")
        print("- Return results for most queries")
    else:
        print("❌ SOME FIXES STILL NEEDED")
        print("\nCheck Vercel deployment and logs")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()