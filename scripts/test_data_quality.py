#!/usr/bin/env python3
"""
Data Quality Test Suite - Catches NaN scores, empty results, and latency issues
Based on ChatGPT's recommended testing strategy
"""

import requests
import time
import json
import sys
from typing import Dict, List, Any
import concurrent.futures
from datetime import datetime

# Production endpoint
VERCEL_BASE = "https://podinsight-api.vercel.app"

def test_health_check():
    """Basic health check - expect 200 in <1s"""
    print("🏥 Testing health endpoint...")
    start = time.time()
    
    try:
        response = requests.get(f"{VERCEL_BASE}/api/health", timeout=5)
        latency = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        assert latency < 1000, f"Health check too slow: {latency:.0f}ms"
        
        print(f"   ✅ Health OK ({latency:.0f}ms)")
        return True
        
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

def validate_search_result(result: Dict, query: str) -> List[str]:
    """Validate a single search result and return list of issues"""
    issues = []
    
    # Check for NaN scores
    score = result.get("similarity_score")
    if score is None:
        issues.append("similarity_score is None")
    elif str(score).lower() == 'nan':
        issues.append("similarity_score is NaN")
    elif not isinstance(score, (int, float)):
        issues.append(f"similarity_score is not numeric: {type(score)}")
    elif score <= 0:
        issues.append(f"similarity_score is not positive: {score}")
    
    # Check for fake dates (today's date indicates metadata failure)
    published_at = result.get("published_at", "")
    if "2025-06-24" in published_at:
        issues.append("Published date is today (metadata failure)")
    
    # Check for missing content
    episode_title = result.get("episode_title", "")
    if "Episode from June 24, 2025" in episode_title:
        issues.append("Generic episode title (metadata failure)")
    
    excerpt = result.get("excerpt", "")
    if "No transcript available" in excerpt:
        issues.append("No transcript content")
    
    if not excerpt or len(excerpt.strip()) < 10:
        issues.append("Excerpt too short or empty")
    
    return issues

def test_known_queries():
    """Test queries that should return meaningful results"""
    print("🔍 Testing known high-recall queries...")
    
    # High-recall queries that should find content
    test_queries = [
        "openai",
        "sequoia capital", 
        "founder burnout",
        "artificial intelligence",
        "venture capital"
    ]
    
    all_passed = True
    
    for query in test_queries:
        print(f"   Testing: '{query}'")
        
        try:
            start = time.time()
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json={"query": query, "limit": 5},
                timeout=15
            )
            latency = (time.time() - start) * 1000
            
            # Basic response validation
            assert response.status_code == 200, f"Non-200 status: {response.status_code}"
            
            data = response.json()
            results = data.get("results", [])
            
            # Check for results
            assert len(results) >= 1, f"No results for high-recall query '{query}'"
            
            # Validate each result
            total_issues = []
            for i, result in enumerate(results):
                issues = validate_search_result(result, query)
                if issues:
                    total_issues.extend([f"Result {i+1}: {issue}" for issue in issues])
            
            if total_issues:
                print(f"      ❌ Data quality issues:")
                for issue in total_issues[:5]:  # Show first 5 issues
                    print(f"         - {issue}")
                all_passed = False
            else:
                print(f"      ✅ {len(results)} valid results ({latency:.0f}ms)")
            
            # Check search method
            search_method = data.get("search_method", "unknown")
            if search_method == "text":
                print(f"      ⚠️  Using text search fallback (vector search may be failing)")
            
        except AssertionError as e:
            print(f"      ❌ {e}")
            all_passed = False
        except Exception as e:
            print(f"      ❌ Exception: {e}")
            all_passed = False
        
        time.sleep(0.5)  # Rate limiting
    
    return all_passed

def test_warm_latency():
    """Test that warm requests are fast (<1s)"""
    print("⚡ Testing warm request latency...")
    
    query = "artificial intelligence"
    latencies = []
    
    # First request (might be cold)
    response = requests.post(
        f"{VERCEL_BASE}/api/search",
        json={"query": query, "limit": 3},
        timeout=30
    )
    
    # Warm requests
    for i in range(3):
        start = time.time()
        response = requests.post(
            f"{VERCEL_BASE}/api/search",
            json={"query": query, "limit": 3},
            timeout=10
        )
        latency = (time.time() - start) * 1000
        latencies.append(latency)
        
        time.sleep(0.2)
    
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    median_latency = sorted(latencies)[len(latencies) // 2]
    
    print(f"   Latencies: {[f'{l:.0f}ms' for l in latencies]}")
    print(f"   Median: {median_latency:.0f}ms, P95: {p95_latency:.0f}ms")
    
    if p95_latency < 1000:
        print("   ✅ Warm latency acceptable")
        return True
    else:
        print("   ❌ Warm latency too high (should be <1s)")
        return False

def test_bad_inputs():
    """Test bad inputs return proper responses"""
    print("🛡️  Testing bad input handling...")
    
    test_cases = [
        ("", "Empty string"),
        ("x", "Single character"),
        ("🦄🚀💻" * 100, "Long emoji string"),
        ("test" * 1000, "Very long string")
    ]
    
    all_passed = True
    
    for query, description in test_cases:
        try:
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json={"query": query, "limit": 1},
                timeout=10
            )
            
            # Should be 200 or 422, never 500
            assert response.status_code in [200, 422], f"{description}: Got {response.status_code}, expected 200 or 422"
            
            if response.status_code == 200:
                data = response.json()
                # Should return valid JSON structure
                assert "results" in data, f"{description}: Missing results field"
                
            print(f"   ✅ {description}: {response.status_code}")
            
        except Exception as e:
            print(f"   ❌ {description}: {e}")
            all_passed = False
    
    return all_passed

def test_concurrent_load():
    """Test concurrent requests"""
    print("🔄 Testing concurrent load...")
    
    def make_request(i):
        try:
            start = time.time()
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json={"query": f"test query {i}", "limit": 1},
                timeout=15
            )
            latency = (time.time() - start) * 1000
            return {
                "success": response.status_code == 200,
                "latency": latency,
                "status": response.status_code
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Fire 10 parallel requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    successful = [r for r in results if r.get("success")]
    latencies = [r["latency"] for r in results if "latency" in r]
    
    print(f"   Success rate: {len(successful)}/10")
    if latencies:
        print(f"   Max latency: {max(latencies):.0f}ms")
        
        # Fail if any request > 10s or success rate < 80%
        if max(latencies) > 10000:
            print("   ❌ Some requests too slow (>10s)")
            return False
        if len(successful) < 8:
            print("   ❌ Success rate too low (<80%)")
            return False
    
    print("   ✅ Concurrent load handled")
    return True

def main():
    """Run all data quality tests"""
    print(f"🧪 Data Quality Test Suite")
    print(f"Testing: {VERCEL_BASE}")
    print(f"Started: {datetime.now()}")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health_check),
        ("Known Queries", test_known_queries),
        ("Warm Latency", test_warm_latency),
        ("Bad Inputs", test_bad_inputs),
        ("Concurrent Load", test_concurrent_load)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"   ❌ Test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All data quality tests PASSED!")
        sys.exit(0)
    else:
        print("💥 Data quality tests FAILED - system not ready for production")
        sys.exit(1)

if __name__ == "__main__":
    main()