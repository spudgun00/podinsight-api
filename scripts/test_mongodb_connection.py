#!/usr/bin/env python3
"""Test MongoDB connection directly"""

import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def test_connection():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("MONGODB_URI not found in environment")
        return

    print("Testing MongoDB connection...")

    try:
        # Create client with same settings as improved_hybrid_search.py
        client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            maxPoolSize=10,
            retryWrites=True
        )

        # Test the connection
        db = client["podinsight"]
        collection = db["transcript_chunks_768d"]

        # Try a simple count
        count = await collection.count_documents({}, limit=1)
        print(f"✅ Connection successful! Collection exists.")

        # Try to list collections
        collections = await db.list_collection_names()
        print(f"Available collections: {', '.join(collections[:5])}...")

        # Check if our collection has the right indexes
        indexes = await collection.list_indexes().to_list(None)
        print(f"Number of indexes: {len(indexes)}")
        for idx in indexes:
            if 'vector' in idx.get('name', '').lower():
                print(f"  - Found vector index: {idx.get('name')}")

    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_connection())
