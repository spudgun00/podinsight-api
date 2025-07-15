#!/usr/bin/env python3
"""
Diagnose MongoDB text search performance issues
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, TEXT
import json

# Load environment
from dotenv import load_dotenv
load_dotenv()

async def diagnose_text_search():
    """Diagnose text search performance issues"""

    # Get MongoDB URI
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("❌ MONGODB_URI not set")
        return

    print("🔍 Connecting to MongoDB...")
    client = AsyncIOMotorClient(uri)

    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB")

        # Get database and collection
        db = client.podinsight
        collection = db.transcript_chunks_768d

        # 1. Check indexes
        print("\n📊 Checking indexes on transcript_chunks_768d:")
        indexes = await collection.list_indexes().to_list(None)

        text_index_found = False
        for idx in indexes:
            print(f"\n  Index: {idx['name']}")
            print(f"  Keys: {idx['key']}")

            # Check if it's a text index
            if '_fts' in idx['key'] and idx['key']['_fts'] == 'text':
                text_index_found = True
                print("  ✅ TEXT INDEX FOUND!")
                if 'weights' in idx:
                    print(f"  Weights: {idx['weights']}")

        if not text_index_found:
            print("\n❌ NO TEXT INDEX FOUND! This is why text search is slow.")
            print("   MongoDB is doing a full collection scan.")

            # Create text index
            print("\n🔨 Creating text index on 'text' field...")
            await collection.create_index([("text", TEXT)])
            print("✅ Text index created!")

        # 2. Count documents
        doc_count = await collection.count_documents({})
        print(f"\n📈 Total documents in collection: {doc_count:,}")

        # 3. Test a simple text search with explain
        test_query = "ai valuations"
        print(f"\n🧪 Testing text search for: '{test_query}'")

        # Run explain on the text search
        explain_result = await collection.find(
            {"$text": {"$search": test_query}}
        ).limit(1).explain()

        # Extract key metrics
        if 'executionStats' in explain_result:
            stats = explain_result['executionStats']
            print(f"\n📊 Execution Stats:")
            print(f"  - Execution time: {stats.get('executionTimeMillis', 'N/A')}ms")
            print(f"  - Total docs examined: {stats.get('totalDocsExamined', 'N/A')}")
            print(f"  - Total docs returned: {stats.get('nReturned', 'N/A')}")
            print(f"  - Index used: {stats.get('executionSuccess', False)}")

            # Check winning plan
            if 'winningPlan' in explain_result:
                plan = explain_result['winningPlan']
                stage = plan.get('stage', 'UNKNOWN')
                print(f"  - Query stage: {stage}")

                if stage == 'COLLSCAN':
                    print("  ❌ FULL COLLECTION SCAN! No index is being used.")
                elif stage == 'TEXT':
                    print("  ✅ Text index is being used")
                else:
                    print(f"  ⚠️  Unexpected stage: {stage}")

        # 4. Test actual search performance
        print(f"\n⏱️  Running actual text search...")
        import time
        start = time.time()

        cursor = collection.find({"$text": {"$search": test_query}}).limit(50)
        results = await cursor.to_list(50)

        elapsed = time.time() - start
        print(f"  - Found {len(results)} results in {elapsed:.2f}s")

        if elapsed > 5:
            print("  ❌ Text search is still slow!")
            print("\n🔍 Possible causes:")
            print("  1. Text index might need to be rebuilt")
            print("  2. Too many search terms causing complex query")
            print("  3. Network latency between Vercel and MongoDB")
            print("  4. MongoDB cluster under heavy load")
        else:
            print("  ✅ Text search performance is good!")

    finally:
        client.close()
        print("\n🔚 Diagnostics complete")

if __name__ == "__main__":
    asyncio.run(diagnose_text_search())
