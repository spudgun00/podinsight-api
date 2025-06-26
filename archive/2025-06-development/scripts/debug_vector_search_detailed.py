#!/usr/bin/env python3
"""
Debug exactly why vector search is failing in the Python code
Replicate the exact same flow as the API
"""

import os
import asyncio
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
import time
import traceback

async def debug_vector_search():
    """Debug the exact vector search flow"""

    # Step 1: Generate embedding via Modal (same as API)
    print("🔗 Step 1: Generating embedding via Modal...")
    modal_url = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

    async with aiohttp.ClientSession() as session:
        try:
            start = time.time()
            async with session.post(modal_url, json={"text": "AI startup valuations"}) as response:
                if response.status == 200:
                    modal_data = await response.json()
                    embedding = modal_data["embedding"]
                    modal_time = (time.time() - start) * 1000
                    print(f"   ✅ Modal embedding generated in {modal_time:.0f}ms")
                    print(f"   Embedding length: {len(embedding)}")
                else:
                    print(f"   ❌ Modal failed: {response.status}")
                    return
        except Exception as e:
            print(f"   ❌ Modal error: {e}")
            return

    # Step 2: Connect to MongoDB (same as API)
    print("\n🔗 Step 2: Connecting to MongoDB...")
    mongodb_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client.podinsight
    collection = db.transcript_chunks_768d

    try:
        # Step 3: Test vector search (replicate exact API pipeline)
        print("\n🔍 Step 3: Testing vector search pipeline...")

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
            {
                "$limit": 5
            },
            {
                "$addFields": {
                    "score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                "$match": {
                    "score": {"$exists": True, "$ne": None}
                }
            },
            {
                "$project": {
                    "episode_id": 1,
                    "feed_slug": 1,
                    "chunk_index": 1,
                    "text": 1,
                    "start_time": 1,
                    "end_time": 1,
                    "speaker": 1,
                    "score": 1
                }
            }
        ]

        start = time.time()
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(None)
        elapsed = (time.time() - start) * 1000

        print(f"   ✅ Vector search completed in {elapsed:.0f}ms")
        print(f"   Found {len(results)} results")

        for i, result in enumerate(results[:3]):
            print(f"   Result {i+1}: score={result.get('score', 'None')}, episode_id={result.get('episode_id', 'None')}")
            print(f"      Text: {result.get('text', 'None')[:100]}...")

        # Step 4: Test metadata enrichment (this might be the real issue)
        print("\n🔗 Step 4: Testing Supabase metadata enrichment...")

        # Get unique episode IDs
        episode_guids = list(set(chunk['episode_id'] for chunk in results))
        print(f"   Episode GUIDs to enrich: {episode_guids}")

        # Test Supabase connection (manually, since we don't have the pool here)
        print("   ⚠️  Supabase enrichment test requires Supabase connection")
        print("   This is likely where the 'today's date' issue originates")

        # Step 5: Check if these episode_ids exist in our test data
        for episode_id in episode_guids[:2]:
            print(f"   Checking episode_id: {episode_id}")
            if "pod-" in episode_id or "substack:" in episode_id:
                print("   → Real episode ID format")
            else:
                print("   → GUID format (needs Supabase lookup)")

    except Exception as e:
        print(f"❌ Vector search failed with exception:")
        print(f"   Error: {e}")
        print(f"   Type: {type(e).__name__}")
        print(f"   Traceback: {traceback.format_exc()}")

    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(debug_vector_search())
