#!/usr/bin/env python3
"""
Test MongoDB vector search with pre-computed embeddings
"""

import asyncio
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import json

# Load environment variables
load_dotenv()

async def test_direct_vector_search():
    """Test MongoDB vector search directly with a sample embedding"""
    print("\n🧪 Testing MongoDB Vector Search Directly...")
    
    # Connect to MongoDB
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client['podinsight']
    collection = db['transcript_chunks_768d']
    
    # Get a sample document to use its embedding
    sample_doc = collection.find_one({})
    if not sample_doc or 'embedding_768d' not in sample_doc:
        print("❌ No documents with embeddings found")
        return False
    
    # Use the sample embedding as our query
    query_embedding = sample_doc['embedding_768d']
    print(f"✅ Using embedding from: {sample_doc['text'][:50]}...")
    
    # Test vector search pipeline
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": query_embedding,
                "numCandidates": 50,
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
                "_id": 0,
                "episode_id": 1,
                "feed_slug": 1,
                "text": 1,
                "score": 1,
                "start_time": 1,
                "end_time": 1
            }
        }
    ]
    
    try:
        # Execute search
        results = list(collection.aggregate(pipeline))
        
        print(f"\n📊 Found {len(results)} similar chunks:")
        for i, result in enumerate(results):
            print(f"\n Result {i+1}:")
            print(f"   Score: {result['score']:.3f}")
            print(f"   Podcast: {result['feed_slug']}")
            print(f"   Text: {result['text'][:100]}...")
            print(f"   Time: {result.get('start_time', 0):.1f}s - {result.get('end_time', 0):.1f}s")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Vector search failed: {e}")
        client.close()
        return False


async def test_api_search():
    """Test the search API endpoint"""
    print("\n🧪 Testing Search API...")
    
    try:
        from api.search_lightweight import search_handler_lightweight, SearchRequest
        
        # Test with existing search (should fallback gracefully)
        request = SearchRequest(
            query="AI agents and automation",
            limit=3
        )
        
        response = await search_handler_lightweight(request)
        
        print(f"📊 API Results: {response.total_results} total")
        print(f"🔧 Search method: {response.search_method if hasattr(response, 'search_method') else 'unknown'}")
        
        for i, result in enumerate(response.results):
            print(f"\n Result {i+1}:")
            print(f"   Episode: {result.podcast_name} - {result.episode_title}")
            print(f"   Score: {result.similarity_score:.3f}")
            print(f"   Excerpt: {result.excerpt[:150]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def check_index_status():
    """Check vector index status"""
    print("\n🔍 Checking Vector Index Status...")
    
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client['podinsight']
    
    # Get collection stats
    stats = db.command("collStats", "transcript_chunks_768d")
    doc_count = stats.get('count', 0)
    size_mb = stats.get('size', 0) / (1024 * 1024)
    
    print(f"📊 Collection Stats:")
    print(f"   Documents: {doc_count:,}")
    print(f"   Size: {size_mb:.1f} MB")
    
    # List indexes
    indexes = db.transcript_chunks_768d.list_indexes()
    print(f"\n📋 Indexes:")
    for idx in indexes:
        print(f"   - {idx['name']}")
    
    client.close()
    return True


async def main():
    """Run all tests"""
    print("🚀 Testing 768D Vector Search Implementation")
    print("=" * 50)
    
    # Check environment
    if not os.getenv('MONGODB_URI'):
        print("❌ MONGODB_URI not set!")
        return
    
    # Run tests
    await check_index_status()
    await test_direct_vector_search()
    await test_api_search()
    
    print("\n✅ Tests complete!")


if __name__ == "__main__":
    asyncio.run(main())