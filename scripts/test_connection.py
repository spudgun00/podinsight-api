#!/usr/bin/env python3
"""Test MongoDB connection and index directly"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    """Test MongoDB connection with both URI styles"""
    
    # Test 1: URI without database name (like in Vercel now)
    print("Test 1: URI without database name")
    uri_no_db = os.getenv("MONGODB_URI")  # Now has no /podinsight
    client1 = AsyncIOMotorClient(uri_no_db)
    db1 = client1["podinsight"]  # Explicitly select database
    
    try:
        # List collections
        collections = await db1.list_collection_names()
        print(f"✅ Connected! Collections: {collections[:3]}...")
        
        # Check if transcript_chunks_768d exists
        if "transcript_chunks_768d" in collections:
            count = await db1.transcript_chunks_768d.estimated_document_count()
            print(f"✅ transcript_chunks_768d has ~{count} documents")
            
            # List indexes
            indexes = await db1.transcript_chunks_768d.list_indexes().to_list(None)
            print(f"✅ Indexes: {[idx['name'] for idx in indexes]}")
        else:
            print("❌ transcript_chunks_768d collection not found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client1.close()
    
    print("\n" + "="*60 + "\n")
    
    # Test 2: Direct test with podinsight database
    print("Test 2: Testing vector search")
    client2 = AsyncIOMotorClient(uri_no_db)
    db2 = client2.podinsight
    
    try:
        # Try a simple vector search
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index_768d",
                    "path": "embedding_768d",
                    "queryVector": [0.1] * 768,  # Dummy vector
                    "numCandidates": 10,
                    "limit": 1
                }
            },
            {"$limit": 1}
        ]
        
        cursor = db2.transcript_chunks_768d.aggregate(pipeline)
        result = await cursor.to_list(1)
        
        if result:
            print("✅ Vector search works!")
        else:
            print("❌ Vector search returned no results")
            
    except Exception as e:
        print(f"❌ Vector search error: {e}")
    finally:
        client2.close()

if __name__ == "__main__":
    asyncio.run(test_connection())