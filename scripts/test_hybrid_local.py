#!/usr/bin/env python3
"""
Test hybrid search implementation locally
"""

import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables before importing modules
from dotenv import load_dotenv
load_dotenv()

from api.improved_hybrid_search import get_hybrid_search_handler

async def test_hybrid_search():
    """Test hybrid search with the problematic query"""

    print("Testing hybrid search locally...")
    print("=" * 80)

    try:
        # Get hybrid handler
        handler = await get_hybrid_search_handler()

        # Test query
        query = "What are VCs saying about AI valuations?"
        print(f"Query: '{query}'")

        # Perform search
        results = await handler.search(query, limit=10)

        print(f"\nFound {len(results)} results")

        # Analyze results
        relevant_count = 0
        for i, result in enumerate(results[:5], 1):
            text_lower = result.get('text', '').lower()
            has_ai = 'ai' in text_lower or 'artificial intelligence' in text_lower
            has_valuation = 'valuation' in text_lower or 'value' in text_lower

            print(f"\n{i}. Episode: {result.get('episode_title', 'Unknown')[:60]}...")
            print(f"   Score: {result.get('score', 0):.3f}")
            print(f"   Contains AI: {'✅' if has_ai else '❌'}")
            print(f"   Contains valuation: {'✅' if has_valuation else '❌'}")

            if 'matches' in result:
                print(f"   Keyword matches: {result['matches']}")

            print(f"   Preview: {text_lower[:150]}...")

            if has_ai and has_valuation:
                relevant_count += 1

        print(f"\n{'='*80}")
        print(f"Summary: {relevant_count}/5 top results contain both AI and valuation terms")

        if relevant_count >= 3:
            print("✅ SUCCESS: Hybrid search is working well!")
        else:
            print("⚠️ WARNING: Results may not be fully relevant")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hybrid_search())
