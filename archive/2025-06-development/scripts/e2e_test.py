#!/usr/bin/env python3
"""
Complete E2E test suite for PodInsight API
Tests various queries to identify which work and which fail
"""
import requests
import json
from datetime import datetime

API_URL = "https://podinsight-api.vercel.app/api/search"

# Test queries
TEST_QUERIES = [
    # Working queries (from previous tests)
    "openai",
    "artificial intelligence",
    "sam altman",

    # Failing queries (from previous tests)
    "venture capital",
    "sequoia",
    "podcast",

    # Single word queries
    "venture",
    "capital",
    "vc",
    "ai",

    # New test queries
    "startup",
    "founder",
    "Y Combinator",
    "product market fit",
    "series A",
    "fundraising"
]

def test_query(query):
    """Test a single query and return results"""
    print(f"\n{'='*60}")
    print(f"Testing: '{query}'")
    print('='*60)

    try:
        response = requests.post(
            API_URL,
            json={"query": query, "limit": 10, "offset": 0},
            timeout=15  # Reduced timeout
        )

        if response.status_code == 200:
            data = response.json()
            result_count = len(data.get("results", []))
            search_method = data.get("search_method", "unknown")
            print(f"✅ SUCCESS - {result_count} results via {search_method}")

            # Show first result if any
            if result_count > 0:
                first = data["results"][0]
                print(f"   First result: {first['episode_title'][:60]}...")
                print(f"   Score: {first['similarity_score']:.4f}")

            return {"query": query, "status": "success", "count": result_count, "method": search_method}

        elif response.status_code == 503:
            print(f"❌ FAIL - 503 error (no results found)")
            return {"query": query, "status": "fail", "error": "503"}

        else:
            print(f"❌ ERROR - Status {response.status_code}")
            return {"query": query, "status": "error", "code": response.status_code}

    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT - Request took > 15s")
        return {"query": query, "status": "timeout"}

    except Exception as e:
        print(f"❌ EXCEPTION - {str(e)}")
        return {"query": query, "status": "exception", "error": str(e)}

def main():
    print(f"🔍 Running E2E tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {API_URL}")

    results = []

    # Test all queries
    for query in TEST_QUERIES:
        result = test_query(query)
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)

    working = [r for r in results if r["status"] == "success"]
    failing = [r for r in results if r["status"] != "success"]

    print(f"\n✅ Working queries ({len(working)}/{len(TEST_QUERIES)}):")
    for r in working:
        print(f"   - '{r['query']}' ({r['count']} results via {r['method']})")

    print(f"\n❌ Failing queries ({len(failing)}/{len(TEST_QUERIES)}):")
    for r in failing:
        print(f"   - '{r['query']}' ({r['status']})")

    # Analysis
    print(f"\n{'='*60}")
    print("ANALYSIS")
    print('='*60)

    # Check patterns
    single_word_results = [r for r in results if len(r["query"].split()) == 1]
    multi_word_results = [r for r in results if len(r["query"].split()) > 1]

    single_success = len([r for r in single_word_results if r["status"] == "success"])
    multi_success = len([r for r in multi_word_results if r["status"] == "success"])

    print(f"Single word queries: {single_success}/{len(single_word_results)} working")
    print(f"Multi word queries: {multi_success}/{len(multi_word_results)} working")

    # Check search methods
    vector_results = [r for r in working if r.get("method") == "vector_768d"]
    text_results = [r for r in working if r.get("method") == "text"]

    print(f"\nSearch methods:")
    print(f"   - Vector (768D): {len(vector_results)} queries")
    print(f"   - Text search: {len(text_results)} queries")

    # Save results
    with open("e2e_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "api_url": API_URL,
            "results": results,
            "summary": {
                "total_queries": len(TEST_QUERIES),
                "working": len(working),
                "failing": len(failing),
                "success_rate": f"{(len(working)/len(TEST_QUERIES)*100):.1f}%"
            }
        }, f, indent=2)

    print(f"\n📊 Results saved to e2e_results.json")
    print(f"🏁 Success rate: {(len(working)/len(TEST_QUERIES)*100):.1f}%")

if __name__ == "__main__":
    main()
