#!/usr/bin/env python3
"""Check for vector search indexes"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def check_indexes():
    """Check all indexes in detail"""
    uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(uri)
    db = client.podinsight

    print("Checking indexes on transcript_chunks_768d collection...\n")

    # Get all indexes with full details
    indexes = await db.transcript_chunks_768d.list_indexes().to_list(None)

    for idx in indexes:
        print(f"Index: {idx.get('name')}")
        print(f"  Keys: {idx.get('key', {})}")
        if 'textIndexVersion' in idx:
            print(f"  Type: Text Search (v{idx['textIndexVersion']})")
        print()

    # Try to check Atlas Search indexes (these are different from regular indexes)
    print("\nIMPORTANT: Atlas Vector Search indexes are managed separately!")
    print("They don't appear in list_indexes() output")
    print("\nTo verify vector index exists:")
    print("1. Go to MongoDB Atlas dashboard")
    print("2. Navigate to your cluster")
    print("3. Click 'Atlas Search' in the left menu")
    print("4. Check if 'vector_index_768d' exists and is ACTIVE")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_indexes())
