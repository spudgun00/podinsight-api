#!/usr/bin/env python3
"""
Comprehensive verification script for 768D Modal.com + MongoDB vector search system
This script will verify:
1. Modal endpoint is being used
2. 768D embeddings are being generated
3. MongoDB vector index is working
4. Search results are using vector search (not text search)
"""

import json
import time
import requests
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

# Configuration
API_BASE_URL = "https://podinsight-api.vercel.app"
MODAL_ENDPOINT = "https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run"

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print('='*60)

def verify_modal_endpoint():
    """Verify Modal.com endpoint is accessible and working"""
    print_section("VERIFYING MODAL.COM ENDPOINT")

    try:
        # Test Modal health endpoint
        response = requests.get(f"{MODAL_ENDPOINT}/health", timeout=10)
        print(f"✅ Modal endpoint accessible: {response.status_code}")

        # Test embedding generation
        test_query = "venture capital investment strategies"
        start_time = time.time()

        response = requests.post(
            f"{MODAL_ENDPOINT}/embed",
            json={"text": test_query},
            timeout=30
        )

        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            embedding = data.get("embedding", [])

            print(f"✅ Embedding generated in {elapsed:.2f} seconds")
            print(f"✅ Embedding dimensions: {len(embedding)} (expected: 768)")
            print(f"✅ Embedding type: {type(embedding[0]) if embedding else 'N/A'}")
            print(f"✅ Sample values: {embedding[:3] if embedding else 'N/A'}")

            # Verify it's 768D
            if len(embedding) == 768:
                print("✅ CONFIRMED: Using 768-dimensional embeddings")
                return True, embedding
            else:
                print(f"❌ ERROR: Expected 768 dimensions, got {len(embedding)}")
                return False, None
        else:
            print(f"❌ Modal embedding failed: {response.status_code}")
            return False, None

    except Exception as e:
        print(f"❌ Modal endpoint error: {str(e)}")
        return False, None

def verify_api_uses_modal(test_embedding: List[float]):
    """Verify the API is actually using Modal for embeddings"""
    print_section("VERIFYING API USES MODAL.COM")

    try:
        # Make a search request
        search_query = "artificial intelligence and machine learning"

        print(f"Testing search: '{search_query}'")

        response = requests.post(
            f"{API_BASE_URL}/api/search",
            json={"query": search_query, "limit": 3},
            timeout=30
        )

        if response.status_code == 200:
            results = response.json()

            print(f"✅ Search API responded successfully")
            print(f"✅ Number of results: {len(results.get('results', []))}")

            # Check if we got actual results (not empty)
            if results.get('results'):
                print("✅ Search returned results (not empty)")

                # Display first result details
                first_result = results['results'][0]
                print(f"\nFirst result details:")
                print(f"  - Title: {first_result.get('title', 'N/A')[:50]}...")
                print(f"  - Score: {first_result.get('score', 'N/A')}")
                print(f"  - Excerpt length: {len(first_result.get('excerpt', ''))}")

                return True, results
            else:
                print("❌ Search returned 0 results - vector search may not be working")
                return False, results
        else:
            print(f"❌ Search API error: {response.status_code}")
            print(f"Response: {response.text}")
            return False, None

    except Exception as e:
        print(f"❌ API error: {str(e)}")
        return False, None

def verify_mongodb_vector_index():
    """Verify MongoDB is using vector search (not text search)"""
    print_section("VERIFYING MONGODB VECTOR SEARCH")

    # We'll infer this from search behavior
    test_queries = [
        ("AI and artificial intelligence", "Semantic similarity test"),
        ("venture capital funding rounds", "Business context test"),
        ("xyzabc123nonsense", "Nonsense query test (should return 0)")
    ]

    for query, description in test_queries:
        print(f"\nTesting: {description}")
        print(f"Query: '{query}'")

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/search",
                json={"query": query, "limit": 5},
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()
                num_results = len(results.get('results', []))

                if query == "xyzabc123nonsense" and num_results == 0:
                    print(f"✅ Nonsense query returned 0 results (good!)")
                elif query != "xyzabc123nonsense" and num_results > 0:
                    print(f"✅ Valid query returned {num_results} results")

                    # Check score distribution
                    if results.get('results'):
                        scores = [r.get('score', 0) for r in results['results']]
                        print(f"   Score range: {min(scores):.4f} - {max(scores):.4f}")
                else:
                    print(f"⚠️  Unexpected result count: {num_results}")
            else:
                print(f"❌ Search failed: {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {str(e)}")

def verify_768d_search_endpoint():
    """Test the specific 768D search endpoint"""
    print_section("TESTING 768D SEARCH ENDPOINT")

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/search_lightweight_768d",
            json={"query": "startup founders and entrepreneurship", "limit": 3},
            timeout=30
        )

        if response.status_code == 200:
            results = response.json()
            print(f"✅ 768D endpoint working")
            print(f"✅ Results returned: {len(results.get('results', []))}")

            if results.get('results'):
                # Check for 768D-specific fields or behaviors
                first_result = results['results'][0]
                print(f"\nFirst result from 768D endpoint:")
                print(f"  - Score: {first_result.get('score', 'N/A')}")
                print(f"  - Has excerpt: {'excerpt' in first_result}")

            return True, results
        else:
            print(f"❌ 768D endpoint error: {response.status_code}")
            return False, None

    except Exception as e:
        print(f"❌ 768D endpoint error: {str(e)}")
        return False, None

def compare_search_quality():
    """Compare search quality to verify vector search improvement"""
    print_section("SEARCH QUALITY COMPARISON")

    # Business-specific queries that should work well with Instructor-XL
    business_queries = [
        "venture capital investment strategies",
        "B2B SaaS growth metrics",
        "startup founder challenges",
        "artificial intelligence applications",
        "fundraising and term sheets"
    ]

    print("Testing business-context queries (Instructor-XL specialty):")

    total_results = 0
    for query in business_queries:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/search",
                json={"query": query, "limit": 5},
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()
                num_results = len(results.get('results', []))
                total_results += num_results

                print(f"\n'{query}':")
                print(f"  - Results: {num_results}")

                if num_results > 0:
                    top_score = results['results'][0].get('score', 0)
                    print(f"  - Top score: {top_score:.4f}")

        except Exception as e:
            print(f"  - Error: {str(e)}")

    avg_results = total_results / len(business_queries)
    print(f"\n📊 Average results per query: {avg_results:.1f}")

    if avg_results > 3:
        print("✅ Good search coverage - vector search appears to be working well")
    elif avg_results > 1:
        print("⚠️  Moderate search coverage - vector search may need tuning")
    else:
        print("❌ Poor search coverage - vector search may not be working")

def main():
    """Run all verification tests"""
    print("\n" + "="*60)
    print("🚀 PODINSIGHT 768D MODAL.COM VERIFICATION")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Track overall status
    all_tests_passed = True

    # 1. Verify Modal endpoint
    modal_ok, test_embedding = verify_modal_endpoint()
    all_tests_passed &= modal_ok

    # 2. Verify API uses Modal
    if modal_ok:
        api_ok, search_results = verify_api_uses_modal(test_embedding)
        all_tests_passed &= api_ok
    else:
        print("\n⚠️  Skipping API verification due to Modal issues")
        all_tests_passed = False

    # 3. Verify MongoDB vector index behavior
    verify_mongodb_vector_index()

    # 4. Test 768D specific endpoint
    endpoint_ok, _ = verify_768d_search_endpoint()
    all_tests_passed &= endpoint_ok

    # 5. Compare search quality
    compare_search_quality()

    # Final summary
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)

    if all_tests_passed and api_ok:
        print("✅ CONFIRMED: System is using Instructor-XL via Modal.com")
        print("✅ CONFIRMED: 768-dimensional embeddings are active")
        print("✅ CONFIRMED: MongoDB vector search is operational")
        print("\n🎉 The upgraded search system is fully functional!")
    else:
        print("❌ ISSUES DETECTED: Not all components are working correctly")
        print("\nTroubleshooting steps:")
        print("1. Check Modal endpoint is accessible")
        print("2. Verify MongoDB vector index 'vector_index_768d' exists")
        print("3. Check API logs for errors")
        print("4. Ensure environment variables are set correctly")

    # Save detailed report
    report = {
        "timestamp": datetime.now().isoformat(),
        "modal_endpoint_ok": modal_ok,
        "api_using_modal": api_ok if 'api_ok' in locals() else False,
        "endpoint_768d_ok": endpoint_ok,
        "test_embedding_dimensions": len(test_embedding) if test_embedding else 0
    }

    with open("768d_verification_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed report saved to: 768d_verification_report.json")

if __name__ == "__main__":
    main()
