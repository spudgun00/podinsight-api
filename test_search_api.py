#!/usr/bin/env python3
"""
Test the search API with MongoDB integration
"""

import asyncio
import json
from api.search_lightweight import search_handler_lightweight, SearchRequest
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

async def test_search_api():
    """Test search API with various queries"""
    
    print("🧪 Testing Search API with MongoDB\n")
    
    # Test queries
    test_queries = [
        ("AI agents", 5),
        ("venture capital", 3),
        ("GPT-4", 3),
        ("cryptocurrency blockchain", 5),
        ("startup funding", 3)
    ]
    
    for query, limit in test_queries:
        print(f"\n📍 Testing query: '{query}' (limit: {limit})")
        print("-" * 60)
        
        # Create request
        request = SearchRequest(
            query=query,
            limit=limit,
            offset=0
        )
        
        try:
            # Call search handler
            response = await search_handler_lightweight(request)
            
            print(f"✅ Found {len(response.results)} results (total: {response.total_results})")
            
            # Show first result in detail
            if response.results:
                result = response.results[0]
                print(f"\n🎯 Top Result:")
                print(f"   Podcast: {result.podcast_name}")
                print(f"   Episode: {result.episode_title[:80]}...")
                print(f"   Score: {result.similarity_score:.2f}")
                print(f"   Topics: {', '.join(result.topics) if result.topics else 'None'}")
                print(f"   Excerpt: {result.excerpt[:200]}...")
                
                # Check if it's a real excerpt
                if "**" in result.excerpt:
                    print(f"   ✅ Real excerpt with highlighted terms!")
                else:
                    print(f"   ⚠️  Fallback excerpt (MongoDB might be down)")
                
                if result.s3_audio_path:
                    print(f"   🎵 Audio available: {result.s3_audio_path.split('/')[-2][:20]}...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test pagination
    print("\n\n📍 Testing pagination")
    print("-" * 60)
    
    request1 = SearchRequest(query="AI", limit=5, offset=0)
    request2 = SearchRequest(query="AI", limit=5, offset=5)
    
    response1 = await search_handler_lightweight(request1)
    response2 = await search_handler_lightweight(request2)
    
    print(f"Page 1: {len(response1.results)} results")
    print(f"Page 2: {len(response2.results)} results")
    
    # Check for duplicates
    ids1 = {r.episode_id for r in response1.results}
    ids2 = {r.episode_id for r in response2.results}
    
    if ids1.intersection(ids2):
        print("⚠️  Found duplicate episodes between pages!")
    else:
        print("✅ No duplicates - pagination working correctly")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_search_api())