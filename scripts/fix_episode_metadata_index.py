#!/usr/bin/env python3
"""
Fix episode_metadata collection index to speed up $lookup operations
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import time

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

async def fix_episode_metadata_index():
    """Check and create index on episode_metadata collection"""

    # Get MongoDB URI
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("❌ MONGODB_URI not set")
        return

    print("🔍 Connecting to MongoDB...")
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000)

    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB")

        # Get database and collection
        db = client.podinsight
        metadata_collection = db.episode_metadata

        # 1. Check existing indexes
        print("\n📊 Checking indexes on episode_metadata collection:")
        indexes = await metadata_collection.list_indexes().to_list(None)

        episode_id_index_found = False
        for idx in indexes:
            print(f"  - {idx['name']}: {idx['key']}")
            if 'episode_id' in idx['key'] and idx['key']['episode_id'] == 1:
                episode_id_index_found = True

        if episode_id_index_found:
            print("\n✅ episode_id index already exists!")
        else:
            print("\n❌ No index on episode_id field!")
            print("📍 This is causing the $lookup performance issue")

            # Create the index
            print("\n🔨 Creating index on episode_id...")
            start = time.time()

            await metadata_collection.create_index(
                [("episode_id", 1)],
                name="episode_id_1",
                background=True  # Don't block other operations
            )

            elapsed = time.time() - start
            print(f"✅ Index created in {elapsed:.2f}s")

        # 2. Check collection stats
        stats = await db.command("collStats", "episode_metadata")
        doc_count = stats.get('count', 0)
        size_mb = stats.get('size', 0) / (1024 * 1024)

        print(f"\n📈 episode_metadata collection stats:")
        print(f"  - Documents: {doc_count:,}")
        print(f"  - Size: {size_mb:.1f} MB")

        # 3. Test the lookup performance
        print("\n🧪 Testing $lookup performance...")
        chunks_collection = db.transcript_chunks_768d

        # Test pipeline with lookup
        pipeline = [
            {"$match": {"$text": {"$search": "ai"}}},
            {"$limit": 10},
            {
                "$lookup": {
                    "from": "episode_metadata",
                    "localField": "episode_id",
                    "foreignField": "episode_id",
                    "as": "metadata"
                }
            }
        ]

        start = time.time()
        results = await chunks_collection.aggregate(pipeline).to_list(10)
        lookup_time = time.time() - start

        print(f"  - Found {len(results)} results with metadata")
        print(f"  - Lookup time: {lookup_time:.2f}s")

        if lookup_time > 1:
            print(f"  ⚠️  Lookup is still slow ({lookup_time:.2f}s)")
            print("     Consider denormalizing frequently used metadata fields")
        else:
            print(f"  ✅ Lookup performance is good!")

        # 4. Additional recommendations
        print("\n💡 Additional Optimizations:")
        print("  1. Consider creating a compound index if filtering by other fields")
        print("  2. For best performance, denormalize podcast_name and episode_title")
        print("  3. Or use $lookup with pipeline for more control")

    finally:
        client.close()
        print("\n🔚 Index optimization complete")

if __name__ == "__main__":
    asyncio.run(fix_episode_metadata_index())
