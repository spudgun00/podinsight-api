#!/usr/bin/env python3
"""
Verify MongoDB performance improvements in production
Run this after deployment to ensure optimizations are working
"""

import os
import asyncio
import time
from motor.motor_asyncio import AsyncIOMotorClient

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

async def verify_performance():
    """Run performance verification tests"""

    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("❌ MONGODB_URI not set")
        return

    print("🔍 MongoDB Performance Verification")
    print("=" * 50)

    # Test connection with new timeout settings
    print("\n1️⃣ Testing Connection Time...")
    start = time.time()
    client = AsyncIOMotorClient(
        uri,
        serverSelectionTimeoutMS=10000,  # 10 seconds
        connectTimeoutMS=5000,            # 5 seconds
        socketTimeoutMS=45000,            # 45 seconds
        maxPoolSize=100,
        minPoolSize=10,
        maxIdleTimeMS=60000
    )

    try:
        # Test connection
        await client.admin.command('ping')
        connection_time = time.time() - start

        if connection_time < 1:
            print(f"✅ Connection established in {connection_time:.2f}s (Excellent!)")
        elif connection_time < 5:
            print(f"⚠️  Connection established in {connection_time:.2f}s (Acceptable)")
        else:
            print(f"❌ Connection took {connection_time:.2f}s (Too slow!)")

        db = client.podinsight

        # Test text search performance
        print("\n2️⃣ Testing Text Search Performance...")
        test_queries = [
            "ai",
            "venture capital",
            "artificial intelligence machine learning",
            "vcs investors valuations"  # Similar to production query
        ]

        for query in test_queries:
            # Count search terms
            term_count = len(query.split())

            start = time.time()
            results = await db.transcript_chunks_768d.find(
                {"$text": {"$search": query}}
            ).limit(50).to_list(50)
            search_time = time.time() - start

            if search_time < 1:
                status = "✅"
            elif search_time < 5:
                status = "⚠️"
            else:
                status = "❌"

            print(f"{status} Query '{query}' ({term_count} terms): "
                  f"{len(results)} results in {search_time:.2f}s")

        # Test lookup performance
        print("\n3️⃣ Testing $lookup Performance...")
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
        results = await db.transcript_chunks_768d.aggregate(pipeline).to_list(10)
        lookup_time = time.time() - start

        if lookup_time < 0.5:
            print(f"✅ $lookup performance: {lookup_time:.2f}s (Index is working!)")
        elif lookup_time < 2:
            print(f"⚠️  $lookup performance: {lookup_time:.2f}s (Slower than expected)")
        else:
            print(f"❌ $lookup performance: {lookup_time:.2f}s (Index may be missing!)")

        # Check indexes
        print("\n4️⃣ Verifying Indexes...")

        # Check text index
        text_indexes = await db.transcript_chunks_768d.list_indexes().to_list(None)
        has_text_index = any('_fts' in idx.get('key', {}) for idx in text_indexes)
        if has_text_index:
            print("✅ Text index exists on transcript_chunks_768d")
        else:
            print("❌ Text index MISSING on transcript_chunks_768d!")

        # Check episode_metadata index
        metadata_indexes = await db.episode_metadata.list_indexes().to_list(None)
        has_episode_index = any('episode_id' in idx.get('key', {}) for idx in metadata_indexes)
        if has_episode_index:
            print("✅ episode_id index exists on episode_metadata")
        else:
            print("❌ episode_id index MISSING on episode_metadata!")

        # Simulate full search
        print("\n5️⃣ Testing Full Hybrid Search Simulation...")

        # Text search
        start = time.time()
        text_results = await db.transcript_chunks_768d.aggregate([
            {"$match": {"$text": {"$search": "ai venture capital"}}},
            {"$addFields": {"text_score": {"$meta": "textScore"}}},
            {"$sort": {"text_score": -1}},
            {"$limit": 50},
            {
                "$lookup": {
                    "from": "episode_metadata",
                    "localField": "episode_id",
                    "foreignField": "episode_id",
                    "as": "metadata"
                }
            }
        ]).to_list(50)
        text_time = time.time() - start

        # Vector search simulation (just a simple query)
        start = time.time()
        vector_results = await db.transcript_chunks_768d.find().limit(50).to_list(50)
        vector_time = time.time() - start

        total_time = text_time + vector_time

        print(f"\nHybrid Search Performance:")
        print(f"  Text Search:   {text_time:.2f}s")
        print(f"  Vector Search: {vector_time:.2f}s")
        print(f"  Total Time:    {total_time:.2f}s")

        if total_time < 5:
            print("✅ Excellent performance!")
        elif total_time < 12:
            print("✅ Good performance (meeting target)")
        elif total_time < 20:
            print("⚠️  Performance needs monitoring")
        else:
            print("❌ Performance issues detected!")

        # Summary
        print("\n" + "=" * 50)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 50)

        improvements = []
        issues = []

        if connection_time < 1:
            improvements.append("Connection time excellent")
        else:
            issues.append(f"Connection time slow ({connection_time:.1f}s)")

        if has_text_index and has_episode_index:
            improvements.append("All indexes present")
        else:
            issues.append("Missing indexes")

        if total_time < 12:
            improvements.append(f"Search performance good ({total_time:.1f}s)")
        else:
            issues.append(f"Search performance slow ({total_time:.1f}s)")

        if improvements:
            print("\n✅ Improvements Working:")
            for imp in improvements:
                print(f"   - {imp}")

        if issues:
            print("\n❌ Issues Found:")
            for issue in issues:
                print(f"   - {issue}")

        if not issues:
            print("\n🎉 All optimizations working perfectly!")

    finally:
        client.close()

if __name__ == "__main__":
    print("Running MongoDB performance verification...")
    print("This will test the optimizations we deployed\n")
    asyncio.run(verify_performance())
