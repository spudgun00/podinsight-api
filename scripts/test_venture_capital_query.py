#!/usr/bin/env python3
"""Test failing queries through all three paths"""

import os
import sys
import asyncio
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def test_modal_to_atlas(query="venture capital"):
    """Test 1: Modal → Atlas (proves embeddings + vector index work)"""
    print(f"\n1. Testing Modal → Atlas for '{query}'")
    print("=" * 60)
    
    # Get embedding from Modal
    modal_url = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"
    response = requests.post(modal_url, json={"text": query}, timeout=10)
    
    if response.status_code != 200:
        print(f"❌ Modal error: {response.status_code}")
        return False
    
    embedding = response.json()["embedding"]
    print(f"✅ Got embedding from Modal (dim: {len(embedding)})")
    
    # Search MongoDB Atlas
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client.podinsight
    
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": embedding,
                "numCandidates": 100,
                "limit": 5
            }
        },
        {
            "$addFields": {
                "score": {"$meta": "vectorSearchScore"}
            }
        },
        {
            "$project": {
                "text": 1,
                "score": 1,
                "episode_title": 1
            }
        }
    ]
    
    cursor = db.transcript_chunks_768d.aggregate(pipeline)
    results = await cursor.to_list(None)
    
    print(f"✅ Vector search returned {len(results)} results")
    for i, result in enumerate(results[:3]):
        print(f"   {i+1}. Score: {result.get('score', 0):.4f}")
        print(f"      Text: {result.get('text', '')[:100]}...")
    
    client.close()
    return len(results) > 0

async def test_atlas_fulltext(query="venture capital"):
    """Test 2: Atlas full-text search (proves data exists)"""
    print(f"\n\n2. Testing Atlas Full-Text Search for '{query}'")
    print("=" * 60)
    
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client.podinsight
    
    # Try different search methods
    # Method 1: Regex search
    regex_results = await db.transcript_chunks_768d.find(
        {"text": {"$regex": query, "$options": "i"}}
    ).limit(3).to_list(None)
    
    print(f"Regex search: Found {len(regex_results)} results")
    
    # Method 2: Text search (if text index exists)
    try:
        text_results = await db.transcript_chunks_768d.find(
            {"$text": {"$search": query}}
        ).limit(3).to_list(None)
        print(f"Text search: Found {len(text_results)} results")
    except Exception as e:
        print(f"Text search failed (no text index?): {e}")
        text_results = []
    
    # Show sample results
    all_results = regex_results + text_results
    if all_results:
        print("\nSample results:")
        for i, result in enumerate(all_results[:3]):
            print(f"   {i+1}. {result.get('episode_title', 'Unknown')}")
            print(f"      Text: {result.get('text', '')[:100]}...")
    
    client.close()
    return len(all_results) > 0

def test_api(query="venture capital"):
    """Test 3: API end-to-end"""
    print(f"\n\n3. Testing API End-to-End for '{query}'")
    print("=" * 60)
    
    api_url = "https://podinsight-api.vercel.app/api/search"
    
    response = requests.post(
        api_url,
        json={"query": query, "limit": 5},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        num_results = len(data.get("results", []))
        method = data.get("search_method", "unknown")
        
        print(f"✅ API returned {num_results} results via {method}")
        
        if num_results > 0:
            first = data["results"][0]
            print(f"   First result score: {first.get('similarity_score', 0):.4f}")
            print(f"   Text: {first.get('excerpt', '')[:100]}...")
        
        return num_results > 0
    else:
        print(f"❌ API error: {response.status_code}")
        return False

async def main():
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "venture capital"
    
    print(f"🔍 Testing '{query}' query through all paths")
    
    # Run all tests
    modal_atlas_ok = await test_modal_to_atlas(query)
    atlas_text_ok = await test_atlas_fulltext(query)
    api_ok = test_api(query)
    
    # Summary
    print("\n\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Modal → Atlas: {'✅ PASS' if modal_atlas_ok else '❌ FAIL'}")
    print(f"Atlas Text:    {'✅ PASS' if atlas_text_ok else '❌ FAIL'}")
    print(f"API:           {'✅ PASS' if api_ok else '❌ FAIL'}")
    
    if modal_atlas_ok and atlas_text_ok and not api_ok:
        print("\n🎯 Confirmed: Bug is 100% in API code or env vars!")
    elif not modal_atlas_ok:
        print("\n⚠️  Vector search issue - check embedding mismatch")
    elif not atlas_text_ok:
        print("\n⚠️  Data issue - 'venture capital' may not exist in chunks")

if __name__ == "__main__":
    asyncio.run(main())