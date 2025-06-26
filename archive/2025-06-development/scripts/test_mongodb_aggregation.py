#!/usr/bin/env python3
"""
Test MongoDB aggregation pipeline directly to see if vector search is working
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp

async def test_aggregation():
    """Test the MongoDB aggregation pipeline directly"""

    # Step 1: Generate embedding
    print("🔗 Generating embedding via Modal...")
    modal_url = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

    async with aiohttp.ClientSession() as session:
        async with session.post(modal_url, json={"text": "AI startup valuations"}) as response:
            if response.status != 200:
                print(f"❌ Modal failed: {response.status}")
                return
            modal_data = await response.json()
            embedding = modal_data["embedding"]
            print(f"✅ Got embedding with {len(embedding)} dimensions")

    # Step 2: Run aggregation pipeline
    print("\n🔍 Running MongoDB aggregation pipeline...")
    mongodb_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.podinsight
    collection = db.transcript_chunks_768d

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": embedding,
                "numCandidates": 100,
                "limit": 5,
                "filter": {}
            }
        },
        {"$limit": 5},
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
        {"$match": {"score": {"$exists": True, "$ne": None}}},
        {
            "$project": {
                "episode_id": 1,
                "feed_slug": 1,
                "text": 1,
                "score": 1,
                "_id": 0
            }
        }
    ]

    try:
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(None)

        print(f"\n✅ Found {len(results)} results")
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  Score: {result.get('score', 'N/A')}")
            print(f"  Episode ID: {result.get('episode_id', 'N/A')}")
            print(f"  Feed: {result.get('feed_slug', 'N/A')}")
            print(f"  Text: {result.get('text', '')[:100]}...")

        # Now check if these episode IDs exist in our test data
        if results:
            print("\n🔍 Checking episode data diversity...")
            episode_ids = list(set(r['episode_id'] for r in results))
            print(f"Unique episodes: {len(episode_ids)}")
            print(f"Episode IDs: {episode_ids}")

    except Exception as e:
        print(f"❌ Aggregation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_aggregation())
