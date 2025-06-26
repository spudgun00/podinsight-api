#!/usr/bin/env python3
"""
Test different embedding instructions to find the right match
"""

import asyncio
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MODAL_URL = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

async def generate_embedding(text: str, instruction: str = None) -> list:
    """Generate embedding with specific instruction"""
    async with aiohttp.ClientSession() as session:
        # If instruction is provided, format as instructor model expects
        if instruction:
            payload = {"text": f"{instruction} {text}"}
        else:
            payload = {"text": text}

        async with session.post(MODAL_URL, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("embedding", [])
    return None

async def test_instructions():
    """Test different instruction formats"""
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client.podinsight

    # Test queries
    test_queries = [
        "openai",
        "artificial intelligence",
        "sequoia capital"
    ]

    # Different instruction formats to test
    instructions = [
        None,  # No instruction
        "Represent the venture capital podcast discussion:",
        "Represent this document for retrieval:",
        "Represent the document:",
        "",  # Empty instruction
        "query:",
        "passage:",
    ]

    print("Testing different embedding instructions...")
    print("=" * 80)

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)

        for instruction in instructions:
            # Generate embedding
            if instruction is None:
                print(f"Testing: No instruction")
                embedding = await generate_embedding(query)
            else:
                print(f"Testing: '{instruction}'")
                embedding = await generate_embedding(query, instruction)

            if not embedding:
                print("  ❌ Failed to generate embedding")
                continue

            # Search with this embedding
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
                    "$limit": 5
                },
                {
                    "$addFields": {
                        "score": {"$meta": "vectorSearchScore"}
                    }
                },
                {
                    "$project": {
                        "text": {"$substr": ["$text", 0, 50]},
                        "score": 1
                    }
                }
            ]

            cursor = db.transcript_chunks_768d.aggregate(pipeline)
            results = await cursor.to_list(None)

            if results:
                print(f"  ✅ Found {len(results)} results")
                print(f"     Top score: {results[0]['score']:.4f}")
                print(f"     Text preview: {results[0]['text']}...")
            else:
                print(f"  ❌ No results found")

    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(test_instructions())
