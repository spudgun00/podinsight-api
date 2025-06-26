#!/usr/bin/env python3
"""
Comprehensive E2E Production Test Suite
Tests all endpoints and functionality after cleanup deployment
"""

import requests
import json
import time
from datetime import datetime

# Production API URL
API_URL = "https://podinsight-api.vercel.app/api"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text:^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

def test_endpoint(name, func):
    """Run a test and report results"""
    try:
        start_time = time.time()
        result = func()
        elapsed = time.time() - start_time

        if result['success']:
            print(f"{GREEN}✓ {name}: PASSED{RESET} ({elapsed:.2f}s)")
            if 'details' in result:
                for detail in result['details']:
                    print(f"  {detail}")
        else:
            print(f"{RED}✗ {name}: FAILED{RESET} ({elapsed:.2f}s)")
            print(f"  Error: {result.get('error', 'Unknown error')}")

        return result
    except Exception as e:
        print(f"{RED}✗ {name}: EXCEPTION{RESET}")
        print(f"  Error: {str(e)}")
        return {'success': False, 'error': str(e)}

def test_health_endpoint():
    """Test /health endpoint"""
    response = requests.get(f"{API_URL}/health")
    data = response.json()

    success = (
        response.status_code == 200 and
        data.get('status') == 'healthy' and
        data.get('checks', {}).get('database') == 'connected'
    )

    return {
        'success': success,
        'details': [
            f"Status: {data.get('status')}",
            f"Database: {data.get('checks', {}).get('database')}",
            f"Version: {data.get('version')}"
        ],
        'response': data
    }

def test_search_basic():
    """Test basic search functionality"""
    query = "artificial intelligence"
    response = requests.post(
        f"{API_URL}/search",
        json={"query": query, "limit": 5}
    )
    data = response.json()

    success = (
        response.status_code == 200 and
        'results' in data and
        len(data['results']) > 0
    )

    return {
        'success': success,
        'details': [
            f"Query: '{query}'",
            f"Results: {len(data.get('results', []))}",
            f"Method: {data.get('search_method')}",
            f"First result: {data.get('results', [{}])[0].get('podcast_name', 'N/A')}"
        ],
        'response': data
    }

def test_search_with_metadata():
    """Test search returns proper metadata"""
    query = "venture capital"
    response = requests.post(
        f"{API_URL}/search",
        json={"query": query, "limit": 3}
    )
    data = response.json()

    results = data.get('results', [])
    success = len(results) > 0

    metadata_complete = all([
        r.get('podcast_name') and r.get('podcast_name') != 'Unknown Podcast' and
        r.get('episode_title') and r.get('episode_title') != 'Unknown Episode' and
        r.get('published_at') and
        r.get('excerpt')
        for r in results[:1]  # Check at least first result
    ])

    return {
        'success': success and metadata_complete,
        'details': [
            f"Query: '{query}'",
            f"Results with metadata: {len([r for r in results if r.get('podcast_name') != 'Unknown Podcast'])}",
            f"Sample: {results[0].get('podcast_name', 'N/A')} - {results[0].get('episode_title', 'N/A')[:50]}..." if results else "No results"
        ],
        'response': data
    }

def test_search_pagination():
    """Test search pagination"""
    query = "podcast"

    # First page
    response1 = requests.post(
        f"{API_URL}/search",
        json={"query": query, "limit": 2, "offset": 0}
    )
    data1 = response1.json()

    # Second page
    response2 = requests.post(
        f"{API_URL}/search",
        json={"query": query, "limit": 2, "offset": 2}
    )
    data2 = response2.json()

    # Check no overlap
    ids1 = [r['episode_id'] for r in data1.get('results', [])]
    ids2 = [r['episode_id'] for r in data2.get('results', [])]

    success = (
        len(ids1) > 0 and
        len(ids2) > 0 and
        len(set(ids1) & set(ids2)) == 0  # No overlap
    )

    return {
        'success': success,
        'details': [
            f"Page 1: {len(ids1)} results",
            f"Page 2: {len(ids2)} results",
            f"No overlap: {len(set(ids1) & set(ids2)) == 0}"
        ]
    }

def test_search_various_queries():
    """Test various search queries"""
    queries = [
        "GPT-4",
        "Sam Altman",
        "crypto",
        "startup funding",
        "machine learning"
    ]

    results = []
    for query in queries:
        response = requests.post(
            f"{API_URL}/search",
            json={"query": query, "limit": 2}
        )
        data = response.json()
        count = len(data.get('results', []))
        results.append(f"{query}: {count} results")

    total_success = sum(1 for r in results if "0 results" not in r)

    return {
        'success': total_success >= 3,  # At least 3 queries should return results
        'details': results
    }

def test_search_performance():
    """Test search response times"""
    queries = ["AI", "blockchain", "venture"]
    times = []

    for query in queries:
        start = time.time()
        response = requests.post(
            f"{API_URL}/search",
            json={"query": query, "limit": 5}
        )
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)

    return {
        'success': avg_time < 3.0,  # Should respond in under 3 seconds
        'details': [
            f"Average response time: {avg_time:.2f}s",
            f"Individual times: {[f'{t:.2f}s' for t in times]}"
        ]
    }

def test_search_edge_cases():
    """Test edge cases"""
    test_cases = [
        {"query": "", "limit": 5, "name": "Empty query"},
        {"query": "   openai   ", "limit": 5, "name": "Whitespace query"},
        {"query": "VENTURE CAPITAL", "limit": 5, "name": "Uppercase query"},
        {"query": "a" * 100, "limit": 5, "name": "Long query"},
        {"query": "特殊字符", "limit": 5, "name": "Unicode query"}
    ]

    results = []
    for case in test_cases:
        try:
            response = requests.post(
                f"{API_URL}/search",
                json={"query": case['query'], "limit": case['limit']}
            )
            if response.status_code == 200:
                results.append(f"{case['name']}: ✓ Handled")
            else:
                results.append(f"{case['name']}: Status {response.status_code}")
        except:
            results.append(f"{case['name']}: ✗ Failed")

    return {
        'success': all("✓" in r or "200" in r for r in results),
        'details': results
    }

def main():
    """Run all tests"""
    print_header("COMPREHENSIVE E2E PRODUCTION TEST")
    print(f"\nTesting: {API_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run all tests
    tests = [
        ("Health Check", test_health_endpoint),
        ("Basic Search", test_search_basic),
        ("Search Metadata", test_search_with_metadata),
        ("Search Pagination", test_search_pagination),
        ("Various Queries", test_search_various_queries),
        ("Performance", test_search_performance),
        ("Edge Cases", test_search_edge_cases)
    ]

    results = {}
    for name, test_func in tests:
        print(f"\n{YELLOW}Testing: {name}{RESET}")
        results[name] = test_endpoint(name, test_func)

    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for r in results.values() if r['success'])
    total = len(results)

    print(f"\nTotal Tests: {total}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{RED}Failed: {total - passed}{RESET}")

    if passed == total:
        print(f"\n{GREEN}🎉 ALL TESTS PASSED! Production is working correctly.{RESET}")
    else:
        print(f"\n{RED}⚠️  Some tests failed. Review details above.{RESET}")

    # Save detailed report
    report = {
        'timestamp': datetime.now().isoformat(),
        'api_url': API_URL,
        'summary': {
            'total': total,
            'passed': passed,
            'failed': total - passed
        },
        'results': {name: {
            'success': res['success'],
            'details': res.get('details', []),
            'error': res.get('error')
        } for name, res in results.items()}
    }

    with open('e2e_test_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: e2e_test_report.json")

if __name__ == "__main__":
    main()
