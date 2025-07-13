#!/usr/bin/env python3
"""
Test script for search quality improvements
Tests the new relevance threshold and dynamic result count
"""
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import search handler
from api.search_lightweight_768d import search_handler_lightweight_768d, SearchRequest

async def test_search_quality():
    """Test search with various queries to verify quality improvements"""

    test_queries = [
        "AI valuations",
        "venture capital trends",
        "startup funding",
        "Marc Andreessen crypto",
        "Sequoia investments"
    ]

    print("Testing search quality improvements...")
    print(f"Relevance threshold: 0.6")
    print(f"Fetching 25 candidates, filtering by quality")
    print("-" * 80)

    for query in test_queries:
        print(f"\nTesting query: '{query}'")

        # Create search request
        request = SearchRequest(
            query=query,
            limit=10,
            offset=0
        )

        try:
            # Execute search
            result = await search_handler_lightweight_768d(request)

            # Check if result has the expected structure
            if hasattr(result, 'results'):
                results = result.results
                print(f"  Results returned: {len(results)}")

                # Show score distribution
                if results:
                    scores = []
                    for r in results:
                        # Handle both dict and object results
                        if isinstance(r, dict):
                            score = r.get('score', 0)
                        else:
                            score = getattr(r, 'score', 0)
                        scores.append(score)

                    if scores:
                        print(f"  Score range: {min(scores):.3f} - {max(scores):.3f}")
                        print(f"  All scores >= 0.6: {all(s >= 0.6 for s in scores)}")

                    # Show first result details
                    first = results[0]
                    if isinstance(first, dict):
                        title = first.get('episode_title', 'Unknown')
                        score = first.get('score', 0)
                    else:
                        title = getattr(first, 'episode_title', 'Unknown')
                        score = getattr(first, 'score', 0)
                    print(f"  Top result: {title[:50]}... (score: {score:.3f})")

                # Check synthesis
                if hasattr(result, 'synthesized_answer') and result.synthesized_answer:
                    print(f"  Synthesis: {'Yes' if result.synthesized_answer else 'No'}")
                    if result.synthesized_answer:
                        answer_preview = result.synthesized_answer[:100] + "..."
                        print(f"  Answer preview: {answer_preview}")
            else:
                print(f"  Error: Unexpected result structure")

        except Exception as e:
            print(f"  Error: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "-" * 80)
    print("Quality test complete!")

if __name__ == "__main__":
    asyncio.run(test_search_quality())
