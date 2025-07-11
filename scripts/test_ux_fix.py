#!/usr/bin/env python3
"""
Test script to verify the UX fix - only show "No results found" for truly empty results
"""

import requests
import json
from datetime import datetime

# API endpoint (local for testing)
API_URL = "https://podinsight-api.vercel.app/api/search"

def test_queries():
    """Test various queries to ensure proper UX"""

    print("\n🧪 Testing UX Fix - Only null for truly empty results")
    print("=" * 60)

    test_cases = [
        {
            "query": "What are VCs saying about AI valuations?",
            "expected": "Should return synthesis even without specific $",
            "should_have_answer": True
        },
        {
            "query": "AI startups",
            "expected": "General query should return synthesis",
            "should_have_answer": True
        },
        {
            "query": "xyzqwerty123456",  # Gibberish
            "expected": "Truly no results - should return null",
            "should_have_answer": False
        },
        {
            "query": "underwater basket weaving quantum blockchain",  # Nonsense
            "expected": "No relevant results - should return null",
            "should_have_answer": False
        }
    ]

    for test in test_cases:
        query = test["query"]
        print(f"\n📍 Testing: '{query}'")
        print(f"   Expected: {test['expected']}")

        try:
            response = requests.post(
                API_URL,
                json={"query": query, "limit": 10},
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                has_answer = data.get("answer") is not None
                total_results = data.get("total_results", 0)

                print(f"   Total search results: {total_results}")

                if has_answer:
                    answer = data["answer"]
                    print(f"   ✅ Answer provided (good UX)")
                    print(f"   Text preview: {answer.get('text', '')[:100]}...")
                    print(f"   Citations: {len(answer.get('citations', []))}")
                else:
                    print(f"   ❌ Answer is null - Frontend shows 'No results found'")

                # Check if result matches expectation
                if has_answer == test["should_have_answer"]:
                    print(f"   ✅ CORRECT: Behavior matches expectation")
                else:
                    print(f"   ❌ WRONG: Expected answer={test['should_have_answer']}, got answer={has_answer}")

                # Show search method and scores if available
                print(f"   Search method: {data.get('search_method', 'unknown')}")

                # Check relevance scores if results exist
                if total_results > 0 and "results" in data:
                    scores = [r.get("score", 0) for r in data["results"][:3]]
                    print(f"   Top 3 scores: {scores}")

            else:
                print(f"   ❌ API Error: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Request failed: {e}")

def main():
    """Run all tests"""

    print("🚀 PodInsight UX Fix Test")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Testing: {API_URL}")
    print("\nFix: Only return null when NO relevant results (score < 0.5)")

    test_queries()

    print("\n\n✅ Test complete!")
    print("\nKey improvements:")
    print("- Queries with relevant content ALWAYS get a synthesis")
    print("- Only truly empty/irrelevant results show 'No results found'")
    print("- Better UX: Users see insights even without specific metrics")

if __name__ == "__main__":
    main()
