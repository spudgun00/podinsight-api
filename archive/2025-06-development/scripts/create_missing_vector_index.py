#!/usr/bin/env python3
"""
Create Missing Vector Index for MongoDB Atlas
Since vector indexes can't be created via mongosh, use Python with proper Atlas API
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def create_vector_index():
    """Create the missing vector_index_768d"""

    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("❌ MONGODB_URI not set")
        return

    print("🔗 Connecting to MongoDB Atlas...")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.podinsight
    collection = db.transcript_chunks_768d

    try:
        print("📊 Collection stats:")
        total_docs = await collection.count_documents({})
        docs_with_embeddings = await collection.count_documents({"embedding_768d": {"$type": "array"}})
        print(f"   Total documents: {total_docs:,}")
        print(f"   With embeddings: {docs_with_embeddings:,}")
        print(f"   Coverage: {(docs_with_embeddings/total_docs*100):.1f}%")

        print("\n🔍 Checking existing indexes...")
        indexes = await collection.list_indexes().to_list(None)
        print(f"   Found {len(indexes)} indexes:")
        for idx in indexes:
            print(f"   - {idx.get('name', 'unnamed')}: {idx.get('key', {})}")

        # Check if vector index already exists
        vector_indexes = [idx for idx in indexes if 'vector' in idx.get('name', '').lower()]
        if vector_indexes:
            print(f"✅ Vector index already exists: {vector_indexes[0]['name']}")
            return

        print("\n⚠️  Vector index creation via Python client...")
        print("Note: Atlas Vector Search indexes must be created through:")
        print("1. Atlas UI -> Search -> Create Search Index -> JSON Editor")
        print("2. Atlas Admin API")
        print("3. Atlas CLI")

        # Try to create anyway (might work with newer driver versions)
        try:
            result = await collection.create_index(
                [("embedding_768d", "vector")],
                name="vector_index_768d",
                vector_options={
                    "dimensions": 768,
                    "similarity": "cosine"
                }
            )
            print(f"✅ Vector index created via Python: {result}")
        except Exception as e:
            print(f"❌ Python creation failed: {e}")
            print("\n📋 Manual Creation Required:")
            print("Go to Atlas UI -> Database -> Search -> Create Search Index")
            print("Use this JSON configuration:")

            index_config = {
                "name": "vector_index_768d",
                "type": "vectorSearch",
                "definition": {
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding_768d",
                            "numDimensions": 768,
                            "similarity": "cosine"
                        }
                    ]
                }
            }

            import json
            print(json.dumps(index_config, indent=2))

    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(create_vector_index())
