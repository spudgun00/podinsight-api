#!/usr/bin/env python3
"""Quick script to check episode metadata structure"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    uri = os.environ.get("MONGODB_URI")
    client = AsyncIOMotorClient(uri)
    db = client["podinsight"]

    # Get one episode
    episode = await db["episode_metadata"].find_one()

    if episode:
        print("Episode fields:")
        for key in episode.keys():
            value = episode[key]
            if isinstance(value, dict):
                print(f"  {key}: dict with keys {list(value.keys())[:5]}")
            else:
                print(f"  {key}: {type(value).__name__}")

        print("\nFull episode sample:")
        import json
        print(json.dumps({k: str(v)[:100] if not isinstance(v, dict) else "..." for k, v in episode.items()}, indent=2))

    client.close()

if __name__ == "__main__":
    asyncio.run(main())
