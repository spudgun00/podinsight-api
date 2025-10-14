#!/usr/bin/env python3
"""Check duration_seconds for a specific episode in MongoDB"""

import os
import sys
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    episode_id = sys.argv[1] if len(sys.argv) > 1 else "1216c2e7-42b8-42ca-92d7-bad784f80af2"

    uri = os.environ.get("MONGODB_URI")
    client = AsyncIOMotorClient(uri)
    db = client["podinsight"]

    episode = await db["episode_metadata"].find_one({"episode_id": episode_id})

    if episode:
        duration = episode.get("duration_seconds", "NOT SET")
        print(f"MongoDB duration_seconds: {duration}s" if duration != "NOT SET" else f"MongoDB duration_seconds: {duration}")
    else:
        print(f"Episode {episode_id} not found")

    client.close()

if __name__ == "__main__":
    asyncio.run(main())
