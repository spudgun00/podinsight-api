#!/usr/bin/env python3
"""
Check MongoDB vector index configuration and performance
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

async def check_vector_index():
    """Check vector index configuration and performance"""

    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("❌ MONGODB_URI not set")
        return

    print("🔍 Checking MongoDB Vector Index Configuration")
    print("=" * 60)

    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000)

    try:
        await client.admin.command('ping')
        print("✅ Connected to MongoDB\n")

        db = client.podinsight
        collection = db.transcript_chunks_768d

        # 1. Check all indexes
        print("📊 Current indexes on transcript_chunks_768d:")
        indexes = await collection.list_indexes().to_list(None)

        vector_index_found = False
        atlas_search_found = False

        for idx in indexes:
            print(f"\n  Index: {idx['name']}")
            print(f"  Keys: {idx.get('key', {})}")

            # Check for vector index patterns
            if 'embedding_768d' in str(idx):
                vector_index_found = True
                print("  ✅ Found embedding_768d reference")

            # Check for Atlas Search
            if idx['name'].startswith('$**'):
                atlas_search_found = True
                print("  📍 Possible Atlas Search index")

        # 2. Check if embedding_768d field exists
        print("\n📄 Checking document structure:")
        sample_doc = await collection.find_one({"embedding_768d": {"$exists": True}})

        if sample_doc and 'embedding_768d' in sample_doc:
            embedding = sample_doc['embedding_768d']
            print(f"  ✅ embedding_768d field exists")
            print(f"  Dimensions: {len(embedding) if isinstance(embedding, list) else 'Unknown'}")
            print(f"  Type: {type(embedding).__name__}")
        else:
            print("  ❌ No documents with embedding_768d field!")

        # 3. Test vector search performance
        print("\n⏱️  Testing vector search performance...")

        # Create a dummy 768D embedding
        dummy_embedding = [0.1] * 768

        # Test 1: Simple vector similarity
        print("\n  Test 1: Basic vector search")
        start = time.time()

        # Try a simple nearest neighbor query
        pipeline = [
            {
                "$match": {
                    "embedding_768d": {"$exists": True}
                }
            },
            {"$limit": 10}
        ]

        results = await collection.aggregate(pipeline).to_list(10)
        basic_time = time.time() - start
        print(f"  Basic query: {len(results)} results in {basic_time:.2f}s")

        # Test 2: Check if Atlas Search is configured
        print("\n  Test 2: Checking for Atlas Search index")
        try:
            # Try to list Atlas Search indexes
            search_indexes = await db.command({
                "listSearchIndexes": "transcript_chunks_768d"
            })

            if search_indexes.get('cursor', {}).get('firstBatch'):
                print("  ✅ Atlas Search indexes found:")
                for idx in search_indexes['cursor']['firstBatch']:
                    print(f"    - {idx.get('name', 'unnamed')}: {idx.get('status', 'unknown')}")
                    if 'latestDefinition' in idx:
                        mappings = idx['latestDefinition'].get('mappings', {})
                        fields = mappings.get('fields', {})
                        if 'embedding_768d' in fields:
                            print(f"      ✅ embedding_768d mapped as: {fields['embedding_768d'].get('type', 'unknown')}")
            else:
                print("  ❌ No Atlas Search indexes found")
        except Exception as e:
            print(f"  ⚠️  Could not check Atlas Search: {e}")

        # 4. Performance test with actual vector search (if index exists)
        if vector_index_found or atlas_search_found:
            print("\n  Test 3: Vector similarity search")

            # Atlas Search vector query
            vector_search_pipeline = [
                {
                    "$search": {
                        "index": "default",  # or your index name
                        "knnBeta": {
                            "vector": dummy_embedding,
                            "path": "embedding_768d",
                            "k": 10,
                            "numCandidates": 100
                        }
                    }
                }
            ]

            try:
                start = time.time()
                results = await collection.aggregate(vector_search_pipeline).to_list(10)
                vector_time = time.time() - start
                print(f"  Vector search: {len(results)} results in {vector_time:.2f}s")

                if vector_time > 2:
                    print("  ⚠️  Vector search is slow!")
                else:
                    print("  ✅ Vector search performance is good")
            except Exception as e:
                print(f"  ❌ Vector search failed: {e}")
                print("     This suggests the vector index is not properly configured")

        # 5. Collection statistics
        stats = await db.command("collStats", "transcript_chunks_768d")
        doc_count = stats.get('count', 0)
        size_mb = stats.get('size', 0) / (1024 * 1024)

        print(f"\n📈 Collection stats:")
        print(f"  Documents: {doc_count:,}")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"  Average doc size: {stats.get('avgObjSize', 0):,} bytes")

        # 6. Recommendations
        print("\n💡 Recommendations:")

        if not vector_index_found and not atlas_search_found:
            print("  ❌ No vector index detected!")
            print("  1. Create an Atlas Search index with knnVector mapping:")
            print("     - Go to Atlas UI → Collections → transcript_chunks_768d")
            print("     - Click 'Search Indexes' → 'Create Index'")
            print("     - Use this configuration:")
            print("""
     {
       "mappings": {
         "fields": {
           "embedding_768d": {
             "type": "knnVector",
             "dimensions": 768,
             "similarity": "cosine"
           }
         }
       }
     }
            """)
        elif basic_time > 1:
            print("  ⚠️  Even basic queries are slow")
            print("  1. Check cluster resources in Atlas")
            print("  2. Consider upgrading cluster tier")
            print("  3. Ensure vector index is ACTIVE, not BUILDING")
        else:
            print("  ✅ Vector index appears to be configured")
            print("  1. Monitor query performance in production")
            print("  2. Consider index tuning if needed")

    finally:
        client.close()
        print("\n🔚 Vector index check complete")

if __name__ == "__main__":
    asyncio.run(check_vector_index())
