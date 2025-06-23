#!/usr/bin/env python3
"""
Simple test of search with context expansion
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from api.search_lightweight_768d import search_handler_lightweight_768d, SearchRequest

async def test():
    request = SearchRequest(
        query="data entry automation",
        limit=1,
        offset=0
    )
    
    print("🔍 Testing search for: 'data entry automation'")
    response = await search_handler_lightweight_768d(request)
    
    if response.results:
        result = response.results[0]
        print(f"\n✅ Found result:")
        print(f"Score: {result.similarity_score:.3f}")
        print(f"Original timestamp: {result.timestamp['start_time']:.1f}s - {result.timestamp['end_time']:.1f}s")
        print(f"\nExpanded excerpt ({result.word_count} words):")
        print(f"{result.excerpt}")
    else:
        print("❌ No results found")

asyncio.run(test())