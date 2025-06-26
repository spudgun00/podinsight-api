#!/usr/bin/env python3
"""
Test the end-to-end embedding flow
"""

import asyncio
import aiohttp
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import numpy as np

load_dotenv()

MODAL_URL = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"
MONGODB_URI = os.getenv("MONGODB_URI")

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

async def test_flow():
    """Test the complete flow"""

    print("🔍 Testing End-to-End Embedding Flow")
    print("=" * 60)

    # 1. Get a known chunk from MongoDB
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.podinsight

    print("\n1. Getting a chunk containing 'venture capital'...")
    chunk = await db.transcript_chunks_768d.find_one(
        {"text": {"$regex": "venture capital", "$options": "i"}}
    )

    if not chunk:
        print("❌ No chunk found")
        return

    print(f"✅ Found chunk: {chunk['text'][:100]}...")
    original_embedding = chunk['embedding_768d']
    print(f"   Original embedding length: {len(original_embedding)}")

    # 2. Generate new embedding via Modal
    print("\n2. Generating new embedding via Modal...")
    async with aiohttp.ClientSession() as session:
        payload = {"text": chunk['text']}

        async with session.post(MODAL_URL, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                data = await response.json()
                new_embedding = data.get("embedding", [])
                dimension = data.get("dimension", 0)

                print(f"✅ Got embedding from Modal")
                print(f"   Dimension: {dimension}")
                print(f"   Length: {len(new_embedding)}")
                print(f"   Is nested: {isinstance(new_embedding[0], list) if new_embedding else 'N/A'}")

                # 3. Compare embeddings
                if len(new_embedding) == len(original_embedding):
                    similarity = cosine_similarity(original_embedding, new_embedding)
                    print(f"\n3. Cosine similarity: {similarity:.4f}")

                    if similarity >= 0.95:
                        print("✅ Embeddings match! The instruction is correct.")
                    else:
                        print("❌ Embeddings don't match well. Instruction might be wrong.")
                else:
                    print(f"❌ Embedding length mismatch: {len(new_embedding)} vs {len(original_embedding)}")
            else:
                print(f"❌ Modal error: {response.status}")

    # 4. Test a search query
    print("\n4. Testing search query 'venture capital'...")
    query_text = "venture capital"

    async with aiohttp.ClientSession() as session:
        payload = {"text": query_text}

        async with session.post(MODAL_URL, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                data = await response.json()
                query_embedding = data.get("embedding", [])

                print(f"✅ Got query embedding")
                print(f"   Length: {len(query_embedding)}")

                # Test vector search directly
                if len(query_embedding) == 768:
                    print("\n5. Testing direct MongoDB vector search...")

                    pipeline = [
                        {
                            "$vectorSearch": {
                                "index": "vector_index_768d",
                                "path": "embedding_768d",
                                "queryVector": query_embedding,
                                "numCandidates": 100,
                                "limit": 5
                            }
                        },
                        {
                            "$limit": 5
                        },
                        {
                            "$addFields": {
                                "score": {"$meta": "vectorSearchScore"}
                            }
                        }
                    ]

                    cursor = db.transcript_chunks_768d.aggregate(pipeline)
                    results = await cursor.to_list(None)

                    print(f"   Found {len(results)} results")
                    if results:
                        print(f"   Top score: {results[0].get('score', 0):.4f}")
                        print(f"   Text preview: {results[0].get('text', '')[:50]}...")

    client.close()
    print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_flow())
