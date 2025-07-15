#!/usr/bin/env python3
"""
Check MongoDB text index configuration
Safe version without hardcoded credentials
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json
from datetime import datetime

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv not available, assume environment variables are already set
    pass

async def check_text_index():
    """Check text index configuration and performance"""

    # Get MongoDB URI from environment
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("❌ MONGODB_URI not set in environment")
        return

    print("🔍 Connecting to MongoDB...")
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000)

    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB")

        # Get database and collection
        db = client.podinsight
        collection = db.transcript_chunks_768d

        # 1. List all indexes
        print("\n📊 Current indexes on transcript_chunks_768d:")
        indexes = await collection.list_indexes().to_list(None)

        text_index_found = False
        text_index_details = None

        for idx in indexes:
            print(f"\n  Index: {idx['name']}")
            print(f"  Keys: {json.dumps(idx['key'], indent=4)}")

            # Check if it's a text index
            if '_fts' in idx['key'] and idx['key']['_fts'] == 'text':
                text_index_found = True
                text_index_details = idx
                print("  ✅ This is a TEXT INDEX")

                # Show which fields are indexed
                if 'weights' in idx:
                    print("  Indexed fields and weights:")
                    for field, weight in idx['weights'].items():
                        print(f"    - {field}: {weight}")

                # Show other index properties
                if 'default_language' in idx:
                    print(f"  Default language: {idx['default_language']}")
                if 'textIndexVersion' in idx:
                    print(f"  Text index version: {idx['textIndexVersion']}")

        if not text_index_found:
            print("\n❌ NO TEXT INDEX FOUND!")
            print("   This explains the slow performance.")
        else:
            print("\n✅ Text index exists, but let's verify it's being used...")

        # 2. Check if the 'text' field exists in documents
        print("\n📄 Checking document structure:")
        sample_doc = await collection.find_one()
        if sample_doc:
            print("  Sample document fields:", list(sample_doc.keys()))
            if 'text' in sample_doc:
                print("  ✅ 'text' field exists")
                print(f"  Text preview: {sample_doc['text'][:100]}...")
            else:
                print("  ❌ 'text' field NOT FOUND in documents!")
                print("     This would prevent text index from working")

        # 3. Test text search with explain
        test_query = "ai"
        print(f"\n🧪 Testing text search for: '{test_query}'")

        # Create the aggregation pipeline that matches your code
        pipeline = [
            {
                "$match": {
                    "$text": {"$search": test_query}
                }
            },
            {"$limit": 1}
        ]

        # Run explain
        explain_cmd = {
            "aggregate": "transcript_chunks_768d",
            "pipeline": pipeline,
            "explain": True,
            "cursor": {}
        }

        explain_result = await db.command(explain_cmd)

        # Analyze the explain output
        if 'stages' in explain_result:
            for i, stage in enumerate(explain_result['stages']):
                if '$cursor' in stage:
                    cursor_info = stage['$cursor']
                    if 'queryPlanner' in cursor_info:
                        winning_plan = cursor_info['queryPlanner'].get('winningPlan', {})
                        stage_type = winning_plan.get('stage', 'UNKNOWN')

                        print(f"\n📊 Query execution plan:")
                        print(f"  Stage: {stage_type}")

                        if stage_type == 'TEXT':
                            print("  ✅ Text index is being used!")
                            if 'indexName' in winning_plan:
                                print(f"  Index name: {winning_plan['indexName']}")
                        elif stage_type == 'COLLSCAN':
                            print("  ❌ FULL COLLECTION SCAN - Text index NOT being used!")
                        else:
                            print(f"  ⚠️  Unexpected stage type")

        # 4. Performance test
        print(f"\n⏱️  Running performance test...")
        import time

        # Test with simple query
        start = time.time()
        cursor = collection.find({"$text": {"$search": test_query}}).limit(50)
        results = await cursor.to_list(50)
        simple_time = time.time() - start
        print(f"  Simple query ('ai'): {len(results)} results in {simple_time:.2f}s")

        # Test with complex query (like your logs)
        complex_query = "vcs venture capitalists investors ai artificial intelligence ml valuations"
        start = time.time()
        cursor = collection.find({"$text": {"$search": complex_query}}).limit(50)
        results = await cursor.to_list(50)
        complex_time = time.time() - start
        print(f"  Complex query: {len(results)} results in {complex_time:.2f}s")

        # 5. Collection stats
        stats = await db.command("collStats", "transcript_chunks_768d")
        doc_count = stats.get('count', 0)
        size_mb = stats.get('size', 0) / (1024 * 1024)
        print(f"\n📈 Collection stats:")
        print(f"  Documents: {doc_count:,}")
        print(f"  Size: {size_mb:.1f} MB")

        # 6. Recommendations
        print("\n💡 Recommendations:")

        if not text_index_found:
            print("  1. Create a text index:")
            print('     db.transcript_chunks_768d.createIndex({"text": "text"})')
        elif simple_time > 5 or complex_time > 5:
            print("  1. Text index exists but performance is poor")
            print("  2. Consider rebuilding the index:")
            print("     - Drop existing text index")
            print("     - Recreate with specific configuration")
            print("  3. Check if index fits in memory (use db.stats())")

        if complex_time > simple_time * 3:
            print("  4. Complex queries are much slower")
            print("     - Consider limiting search terms")
            print("     - Remove synonym expansion")

    finally:
        client.close()
        print("\n🔚 Check complete")

if __name__ == "__main__":
    asyncio.run(check_text_index())
