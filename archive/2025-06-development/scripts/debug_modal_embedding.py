#!/usr/bin/env python3
"""
Debug the Modal embedding format issue
"""

import asyncio
import aiohttp
import json

MODAL_URL = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

async def test_modal():
    """Test Modal endpoint to see exact response"""

    async with aiohttp.ClientSession() as session:
        payload = {"text": "test query for openai"}

        async with session.post(MODAL_URL, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                data = await response.json()

                print("Response keys:", data.keys())
                print("\nEmbedding type:", type(data.get("embedding")))

                embedding = data.get("embedding")
                if embedding:
                    print("Embedding is a list:", isinstance(embedding, list))
                    print("Embedding length:", len(embedding))

                    if len(embedding) > 0:
                        print("\nFirst element type:", type(embedding[0]))
                        print("First element is a list:", isinstance(embedding[0], list))

                        if isinstance(embedding[0], list):
                            print("First element length:", len(embedding[0]))
                            print("First 3 values of nested array:", embedding[0][:3])
                        else:
                            print("First 3 values:", embedding[:3])

                print("\nDimension field:", data.get("dimension"))
                print("Model:", data.get("model"))

                # Save full response for inspection
                with open("modal_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                print("\nFull response saved to modal_response.json")
            else:
                print(f"Error: Status {response.status}")
                print(await response.text())

if __name__ == "__main__":
    asyncio.run(test_modal())
