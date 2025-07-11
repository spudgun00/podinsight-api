#!/usr/bin/env python3
"""
Test script to verify the no-results fix for frontend display
"""

import asyncio
import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.search_lightweight_768d import SearchRequest, search_handler_lightweight_768d

async def test_no_results_query():
    """Test queries that should return no results"""

    print("\n🧪 Testing No-Results Fix")
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
            # Create request
            request = SearchRequest(
                query=query,
                limit=10,
                offset=0
            )

            # Call the handler
            response = await search_handler_lightweight_768d(request)

            # Check the response
            print(f"   Results count: {response.results_count}")

            if response.answer is None:
                print("   ✅ Answer is null (correct for no-results)")
                print("   Frontend will show: 'No results found'")
            else:
                print(f"   ❌ Answer is not null: {response.answer}")
                print(f"   Text: {response.answer.text[:100]}...")
                print(f"   Citations: {len(response.answer.citations)}")
                if hasattr(response.answer, 'confidence') and response.answer.confidence:
                    print(f"   ⚠️  Confidence: {response.answer.confidence}")

            # Show search method
            print(f"   Search method: {response.search_method}")
            print(f"   Processing time: {response.processing_time_ms}ms")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

async def test_positive_query():
    """Test a query that should return results"""

    print("\n\n📍 Testing positive query (should have results)")

    query = "AI startups"  # Simple query that should have results

    try:
        request = SearchRequest(
            query=query,
            limit=10,
            offset=0
        )

        response = await handler_768d(request)

        print(f"   Query: '{query}'")
        print(f"   Results count: {response.results_count}")

        if response.answer is None:
            print("   ⚠️  Answer is null (might be a real no-results case)")
        else:
            print("   ✅ Answer object exists")
            print(f"   Text preview: {response.answer.text[:100]}...")
            print(f"   Citations: {len(response.answer.citations)}")
            if hasattr(response.answer, 'confidence') and response.answer.confidence:
                print(f"   Confidence: {response.answer.confidence}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

async def main():
    """Run all tests"""

    print("🚀 PodInsight No-Results Fix Test")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test no-results queries
    await test_no_results_query()

    # Test positive query
    await test_positive_query()

    print("\n\n✅ Test complete!")
    print("\nKey points:")
    print("- When answer is null → Frontend shows 'No results found'")
    print("- When answer exists → Frontend calculates confidence from citations")
    print("- No more '55% confidence' on empty results!")

if __name__ == "__main__":
    asyncio.run(main())
