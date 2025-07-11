#!/usr/bin/env python3
"""
Test the no-results fix via the API endpoint
"""

import requests
import json
from datetime import datetime

# API endpoint
API_URL = "https://podinsight-api.vercel.app/api/search"

def test_no_results_queries():
    """Test queries that should return no results"""

    print("\n🧪 Testing No-Results Fix via API")
    print("=" * 60)

    # Test queries that should return no results
    test_queries = [
        "What are VCs saying about quantum computing valuations?",
        "Which unicorns have filed for IPO in Antarctica?",
        "What is the ARR of companies building time travel technology?",
        "How many VCs invested in underwater basket weaving startups?"
    ]

    for query in test_queries:
        print(f"\n📍 Testing: '{query}'")

        try:
            # Make API request
            response = requests.post(
                API_URL,
                json={"query": query, "limit": 10},
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # Check if answer is null
                if data.get("answer") is None:
                    print("   ✅ Answer is null (correct for no-results)")
                    print("   Frontend will show: 'No results found'")
                else:
                    print(f"   ❌ Answer is not null!")
                    answer = data["answer"]
                    print(f"   Text: {answer.get('text', '')[:100]}...")
                    print(f"   Citations: {len(answer.get('citations', []))}")

                    # Calculate what frontend would show
                    citation_count = len(answer.get('citations', []))
                    frontend_confidence = 50 + (citation_count * 5)
                    print(f"   ⚠️  Frontend would show: {frontend_confidence}% confidence")

                # Show other details
                print(f"   Total results: {data.get('total_results', 0)}")
                print(f"   Search method: {data.get('search_method', 'unknown')}")
                print(f"   Processing time: {data.get('processing_time_ms', 'N/A')}ms")

            else:
                print(f"   ❌ API Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")

        except Exception as e:
            print(f"   ❌ Request failed: {e}")

def test_positive_query():
    """Test a query that should return results"""

    print("\n\n📍 Testing positive query (should have results)")

    query = "AI startups"

    try:
        response = requests.post(
            API_URL,
            json={"query": query, "limit": 10},
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            print(f"   Query: '{query}'")
            print(f"   Total results: {data.get('total_results', 0)}")

            if data.get("answer") is None:
                print("   ⚠️  Answer is null (might be a real no-results case)")
            else:
                answer = data["answer"]
                print("   ✅ Answer object exists")
                print(f"   Text preview: {answer.get('text', '')[:100]}...")
                print(f"   Citations: {len(answer.get('citations', []))}")

                # Calculate frontend confidence
                citation_count = len(answer.get('citations', []))
                frontend_confidence = 50 + (citation_count * 5)
                print(f"   Frontend shows: {frontend_confidence}% confidence")

        else:
            print(f"   ❌ API Error: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Request failed: {e}")

def main():
    """Run all tests"""

    print("🚀 PodInsight No-Results Fix Test (Production API)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Testing: {API_URL}")

    # Test no-results queries
    test_no_results_queries()

    # Test positive query
    test_positive_query()

    print("\n\n✅ Test complete!")
    print("\nExpected behavior:")
    print("- No-results queries → answer: null → 'No results found'")
    print("- Positive queries → answer object → Frontend calculates confidence")
    print("\nNote: If this shows '55% confidence' for no-results, deploy the fix!")

if __name__ == "__main__":
    main()
