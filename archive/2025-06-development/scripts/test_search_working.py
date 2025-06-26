#!/usr/bin/env python3
"""
Quick test to verify MongoDB vector search is working after index creation
"""

import os
import asyncio
from dotenv import load_dotenv
import aiohttp
import json

# Load environment variables
load_dotenv()

API_URL = "https://podinsight-api.vercel.app/api/search"

async def test_search():
    """Test if search returns results"""

    test_queries = [
        "AI and machine learning",
        "venture capital",
        "startup founders",
        "cryptocurrency"
    ]

    async with aiohttp.ClientSession() as session:
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")

            try:
                async with session.post(
                    API_URL,
                    json={"query": query, "limit": 3},
                    headers={"Content-Type": "application/json"}
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])

                        if results:
                            print(f"✅ SUCCESS! Found {len(results)} results")
                            for i, result in enumerate(results, 1):
                                print(f"   {i}. {result.get('episode_title', 'Unknown')} (Score: {result.get('score', 0):.3f})")
                        else:
                            print(f"❌ No results found")
                    else:
                        print(f"❌ Error: Status {response.status}")
                        print(await response.text())

            except Exception as e:
                print(f"❌ Error: {e}")

            # Rate limiting
            await asyncio.sleep(3)

if __name__ == "__main__":
    print("🚀 Testing MongoDB Vector Search...")
    print(f"📍 API URL: {API_URL}")
    asyncio.run(test_search())
