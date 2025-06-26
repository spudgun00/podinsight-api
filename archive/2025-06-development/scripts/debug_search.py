#!/usr/bin/env python3
import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# Add the api directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

async def test_search():
    """Test the search functionality step by step"""

    print("🔍 Debugging Search API")
    print("=" * 40)

    # Test 1: Check environment variables
    print("\n1. Checking environment variables...")
    hf_key = os.environ.get("HUGGINGFACE_API_KEY")
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY")

    print(f"   HUGGINGFACE_API_KEY: {'✅ Set' if hf_key else '❌ Missing'}")
    print(f"   SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Missing'}")
    print(f"   SUPABASE_KEY: {'✅ Set' if supabase_key else '❌ Missing'}")

    if not all([hf_key, supabase_url, supabase_key]):
        print("\n❌ Missing required environment variables!")
        return

    # Test 2: Test embedding generation
    print("\n2. Testing embedding generation...")
    try:
        from api.search_lightweight import generate_embedding_api
        embedding = await generate_embedding_api("test query")
        print(f"   ✅ Embedding generated: {len(embedding)} dimensions")
        print(f"   First 5 values: {embedding[:5]}")
    except Exception as e:
        print(f"   ❌ Error generating embedding: {str(e)}")
        return

    # Test 3: Test database connection
    print("\n3. Testing database connection...")
    try:
        from api.database import get_pool
        pool = get_pool()
        health = await pool.health_check()
        print(f"   ✅ Database pool healthy: {health}")
    except Exception as e:
        print(f"   ❌ Error connecting to database: {str(e)}")
        return

    # Test 4: Test the search function
    print("\n4. Testing search function...")
    try:
        from api.search_lightweight import search_episodes
        results = await search_episodes(embedding, limit=3, offset=0)
        print(f"   ✅ Search returned {len(results['results'])} results")
        if results['results']:
            print(f"   First result: {results['results'][0]['episode_title']}")
    except Exception as e:
        print(f"   ❌ Error in search function: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # Test 5: Test the full search handler
    print("\n5. Testing full search handler...")
    try:
        from api.search_lightweight import search_handler_lightweight, SearchRequest
        request = SearchRequest(query="AI agents", limit=3)
        response = await search_handler_lightweight(request)
        print(f"   ✅ Search handler successful!")
        print(f"   Results: {len(response.results)}")
        print(f"   Cache hit: {response.cache_hit}")
    except Exception as e:
        print(f"   ❌ Error in search handler: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 40)
    print("Debug complete!")

if __name__ == "__main__":
    asyncio.run(test_search())
