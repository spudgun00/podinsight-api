#!/usr/bin/env python3
"""
Test search locally with full logging to debug the issue
"""

import os
import asyncio
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.search_lightweight_768d import search_handler_lightweight_768d, SearchRequest
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_search():
    """Test the search handler directly"""
    
    # Create a search request
    request = SearchRequest(
        query="AI startup valuations",
        limit=3,
        offset=0
    )
    
    print(f"🔍 Testing search: '{request.query}'")
    print("=" * 60)
    
    try:
        # Call the search handler
        response = await search_handler_lightweight_768d(request)
        
        print(f"\n✅ Search completed successfully")
        print(f"Search method: {response.search_method}")
        print(f"Total results: {response.total_results}")
        print(f"Returned results: {len(response.results)}")
        
        if response.results:
            print("\nResults:")
            for i, result in enumerate(response.results):
                print(f"\n{i+1}. {result.episode_title}")
                print(f"   Podcast: {result.podcast_name}")
                print(f"   Date: {result.published_date}")
                print(f"   Score: {result.similarity_score:.2%}")
                print(f"   Excerpt: {result.excerpt[:100]}...")
        else:
            print("\n❌ No results returned")
            
    except Exception as e:
        print(f"\n❌ Search failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())