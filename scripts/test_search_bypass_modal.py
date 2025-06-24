#!/usr/bin/env python3
"""
Test MongoDB vector search by using pre-existing embeddings
This bypasses the slow Modal endpoint to verify if the search pipeline works
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import json

load_dotenv()

async def test_mongodb_search():
    """Test MongoDB vector search with existing embeddings"""
    
    # Connect to MongoDB
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("❌ MONGODB_URI not found in environment")
        return
        
    print(f"🔗 Connecting to MongoDB...")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client["podinsight"]
    collection = db["transcript_chunks_768d"]
    
    try:
        # 1. First, find a document with an embedding
        print("\n📋 Finding a document with embedding_768d...")
        sample_doc = await collection.find_one(
            {"embedding_768d": {"$exists": True}},
            {"text": 1, "embedding_768d": 1, "episode_id": 1}
        )
        
        if not sample_doc:
            print("❌ No documents with embeddings found!")
            return
            
        print(f"✅ Found document: {sample_doc['text'][:100]}...")
        print(f"   Embedding dimensions: {len(sample_doc['embedding_768d'])}")
        
        # 2. Use this embedding to search for similar documents
        print("\n🔍 Searching for similar documents...")
        
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index_768d",
                    "path": "embedding_768d",
                    "queryVector": sample_doc["embedding_768d"],
                    "numCandidates": 100,
                    "limit": 10
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
                    "episode_id": 1,
                    "podcast_name": 1,
                    "episode_title": 1
                }
            }
        ]
        
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(None)
        
        print(f"\n📊 Search Results: Found {len(results)} similar documents")
        
        if results:
            print("\nTop 5 results:")
            for i, result in enumerate(results[:5]):
                print(f"\n{i+1}. Score: {result.get('score', 0):.4f}")
                print(f"   Text: {result.get('text', '')[:150]}...")
                print(f"   Podcast: {result.get('podcast_name', 'Unknown')}")
                print(f"   Episode: {result.get('episode_title', 'Unknown')}")
        else:
            print("❌ No results returned from vector search!")
            
            # Try to debug why
            print("\n🔍 Debugging: Checking index status...")
            
            # Check if any documents have embeddings
            count_with_embeddings = await collection.count_documents(
                {"embedding_768d": {"$exists": True}}
            )
            print(f"   Documents with embeddings: {count_with_embeddings}")
            
            # Check a few embedding samples
            print("\n   Checking embedding samples...")
            samples = await collection.find(
                {"embedding_768d": {"$exists": True}},
                {"embedding_768d": 1}
            ).limit(3).to_list(None)
            
            for i, doc in enumerate(samples):
                emb = doc.get("embedding_768d", [])
                print(f"   Sample {i+1}: {len(emb)} dimensions, "
                      f"first values: {emb[:3] if emb else 'None'}")
                      
    except Exception as e:
        print(f"\n❌ Error during search: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        client.close()
        print("\n✅ MongoDB connection closed")

if __name__ == "__main__":
    print("🚀 MongoDB Vector Search Test (Bypassing Modal)")
    print("=" * 50)
    asyncio.run(test_mongodb_search())