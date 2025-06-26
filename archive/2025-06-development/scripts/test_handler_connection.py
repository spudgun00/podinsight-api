#!/usr/bin/env python3
"""
Test the exact handler connection issue
"""

import os
import asyncio
import sys
sys.path.append('/Users/jamesgill/PodInsights/podinsight-api')

from api.mongodb_vector_search import get_vector_search_handler

async def test_handler():
    """Test if the handler connection works"""

    print("🔗 Testing vector search handler connection...")

    try:
        # This replicates the exact API call
        vector_handler = await get_vector_search_handler()

        print(f"   Handler created: {vector_handler}")
        print(f"   Client: {vector_handler.client}")
        print(f"   DB: {vector_handler.db}")
        print(f"   Collection: {vector_handler.collection}")

        if vector_handler.db is not None:
            print("   ✅ DB connection exists")

            # Test a simple operation
            try:
                count = await vector_handler.collection.count_documents({})
                print(f"   ✅ Collection accessible: {count:,} documents")

                # Test vector search with a dummy embedding
                dummy_embedding = [0.0] * 768
                results = await vector_handler.vector_search(dummy_embedding, limit=1)
                print(f"   ✅ Vector search works: {len(results)} results")

            except Exception as e:
                print(f"   ❌ Collection operation failed: {e}")
        else:
            print("   ❌ DB connection is None - this explains the fallback!")

    except Exception as e:
        print(f"   ❌ Handler creation failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_handler())
