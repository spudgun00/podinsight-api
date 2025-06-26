#!/usr/bin/env python3
"""Complete end-to-end test of the PodInsight system"""

import requests
import json
import time
import sys
from typing import Dict, List

def test_modal_endpoint():
    """Test Modal embedding endpoint"""
    print("\n1. Testing Modal Embedding Endpoint")
    print("=" * 50)

    modal_url = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

    try:
        response = requests.post(
            modal_url,
            json={"text": "openai"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            embedding = data.get("embedding", [])
            dimension = data.get("dimension", 0)
            print(f"✅ Modal endpoint working")
            print(f"   - Dimension: {dimension}")
            print(f"   - GPU: {data.get('gpu_available', False)}")
            print(f"   - Time: {data.get('total_time_ms', 0)}ms")
            return True
        else:
            print(f"❌ Modal endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Modal endpoint error: {e}")
        return False

def test_api_search():
    """Test API search endpoint"""
    print("\n2. Testing API Search Endpoint")
    print("=" * 50)

    api_url = "https://podinsight-api.vercel.app/api/search"

    test_queries = {
        "openai": "Should find OpenAI-related content",
        "venture capital": "Should find VC discussions",
        "artificial intelligence": "Should find AI discussions",
        "sam altman": "Should find Sam Altman mentions",
        "sequoia": "Should find Sequoia Capital content"
    }

    results = {}

    for query, description in test_queries.items():
        print(f"\n   Testing '{query}' - {description}")

        try:
            start = time.time()
            response = requests.post(
                api_url,
                json={"query": query},
                timeout=20
            )
            elapsed = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                num_results = len(data.get("results", []))
                method = data.get("searchMethod", "unknown")

                if num_results > 0:
                    print(f"   ✅ Found {num_results} results via {method} ({elapsed:.0f}ms)")
                    first = data["results"][0]
                    print(f"      Score: {first.get('score', 0):.4f}")
                    print(f"      Text: {first.get('text', '')[:80]}...")
                    results[query] = "PASS"
                else:
                    print(f"   ❌ No results found ({elapsed:.0f}ms)")
                    results[query] = "FAIL"
            else:
                print(f"   ❌ HTTP {response.status_code} ({elapsed:.0f}ms)")
                results[query] = "ERROR"

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results[query] = "ERROR"

    return results

def test_health_endpoint():
    """Test API health endpoint"""
    print("\n3. Testing Health Endpoint")
    print("=" * 50)

    try:
        response = requests.get(
            "https://podinsight-api.vercel.app/api/health",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   - Status: {data.get('status', 'unknown')}")
            print(f"   - Environment: {data.get('env', 'unknown')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 PodInsight Complete E2E Test Suite")
    print("Started:", time.strftime("%Y-%m-%d %H:%M:%S"))

    # Test components
    modal_ok = test_modal_endpoint()
    health_ok = test_health_endpoint()
    search_results = test_api_search()

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    print(f"Modal Endpoint: {'✅ PASS' if modal_ok else '❌ FAIL'}")
    print(f"Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")

    print(f"\nSearch Results:")
    passed = sum(1 for r in search_results.values() if r == "PASS")
    total = len(search_results)
    print(f"  Passed: {passed}/{total}")

    for query, result in search_results.items():
        emoji = "✅" if result == "PASS" else "❌"
        print(f"  {emoji} {query}: {result}")

    # Overall result
    all_passed = modal_ok and health_ok and passed == total

    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL TESTS PASSED - System is working correctly!")
    else:
        print("❌ SOME TESTS FAILED - Issues detected")

        if not modal_ok:
            print("\n⚠️  Modal endpoint issue - check deployment")
        if passed < total:
            print("\n⚠️  Search issues - possible causes:")
            print("   - Vercel deployment may be outdated")
            print("   - Environment variables may be missing")
            print("   - Caching issues")

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
